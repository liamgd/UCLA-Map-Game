import re
from datetime import datetime, timezone

from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import transform, unary_union

from .classification import determine_category, determine_zone
from .constants import (
    BLACKLIST,
    EXCLUDE_BUILDINGS,
    MIN_AREA_EXCLUDE,
    MIN_AREA_UNNAMED,
    SINGLE_TOLERANCE_M,
    _TO_M,
)
from .geometry import area_m2, build_geometries, simplify_geom_m
from .utils import hash_centroid, slugify


# Minimum child area to consider for subset detection (m²)
MIN_CHILD_AREA = 20
SUBSET_BUFFER_M = 0.25
OVERLAP_THRESHOLD = 0.60


def _outer_shell(geom):
    if isinstance(geom, Polygon):
        return Polygon(geom.exterior)
    if isinstance(geom, MultiPolygon):
        return unary_union([Polygon(p.exterior) for p in geom.geoms])
    return geom


def assign_parent_child(features):
    geoms_m = [transform(_TO_M, shape(f["geometry"])) for f in features]
    areas = [g.area for g in geoms_m]
    centroids = [g.centroid for g in geoms_m]
    names = [f["properties"]["name"] for f in features]
    outer_shells = [_outer_shell(g) for g in geoms_m]

    indices = sorted(range(len(features)), key=lambda i: areas[i], reverse=True)

    for i in indices:
        geom_a = geoms_m[i]
        area_a = areas[i]
        if area_a < MIN_CHILD_AREA:
            continue
        candidates = []
        for j in indices:
            if i == j or names[j].startswith("Unnamed "):
                continue
            outer_b = outer_shells[j]
            inter = geom_a.intersection(outer_b)
            overlap_area = inter.area
            if overlap_area == 0:
                inter = geom_a.buffer(SUBSET_BUFFER_M).intersection(outer_b)
                overlap_area = inter.area
            if overlap_area == 0:
                continue
            ratio = overlap_area / area_a
            if ratio >= OVERLAP_THRESHOLD:
                dist = centroids[i].distance(centroids[j])
                pid = features[j]["properties"]["id"]
                area_b = areas[j]
                candidates.append((area_b, dist, pid, j))
        if candidates:
            candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
            _, _, pid, parent_idx = candidates[0]
            child_props = features[i]["properties"]
            child_props["parent_id"] = pid
            parent_props = features[parent_idx]["properties"]
            parent_props["overlap_role"] = "parent"

def process_features(osm_data):
    print("Processing features...")
    ways, rels, way_polys, rel_polys, ways_in_building_rels = build_geometries(osm_data)
    features = []

    elements = osm_data.get("elements", [])
    total = len(elements)
    for idx, el in enumerate(elements, 1):
        if el["type"] == "way":
            if el["id"] in ways_in_building_rels:
                continue
            geom = way_polys.get(el["id"])
            osm_id_str = f"way/{el['id']}"
        elif el["type"] == "relation":
            geom = rel_polys.get(el["id"])
            osm_id_str = f"relation/{el['id']}"
        else:
            continue

        if geom is None or geom.is_empty:
            continue

        if isinstance(geom, Polygon):
            geom = orient(geom, sign=1.0)
        elif isinstance(geom, MultiPolygon):
            geom = MultiPolygon([orient(p, sign=1.0) for p in geom.geoms])

        A = area_m2(geom)
        tags = el.get("tags", {})
        building_type = (tags.get("building") or "").lower()

        name = (
            tags.get("name")
            or tags.get("official_name")
            or tags.get("alt_name")
            or tags.get("loc_name")
            or tags.get("ref")
            or tags.get("operator")
        )
        if not name:
            feature_type = (
                tags.get("natural")
                or tags.get("leisure")
                or tags.get("landuse")
                or building_type
                or tags.get("amenity")
                or "feature"
            ).lower()
            if feature_type == "yes":
                feature_type = "building"
            feature_type = feature_type.replace("_", " ")
            name = f"Unnamed {feature_type.title()}"

        if name.startswith("Unnamed ") and A < MIN_AREA_UNNAMED:
            continue
        if building_type in EXCLUDE_BUILDINGS and A < MIN_AREA_EXCLUDE:
            continue
        if A < MIN_AREA_EXCLUDE and name.startswith("Unnamed "):
            continue
        if any(re.search(pattern, name, re.I) for pattern in BLACKLIST):
            continue
        if name.startswith("Unnamed "):
            amenity = (tags.get("amenity") or "").lower()
            parking = (tags.get("parking") or "").lower()
            bldg = (tags.get("building") or "").lower()
            if (
                amenity == "parking"
                or bldg == "parking"
                or parking in {"multi-storey", "underground"}
            ):
                ref = (tags.get("ref") or "").strip()
                m = re.search(r"(?:^|[^0-9])([Pp]?\s*\d{1,2})(?:[^0-9]|$)", ref)
                if m:
                    num = re.sub(r"[^\d]", "", m.group(1))
                    name = f"Parking Structure {num}"
                else:
                    name = "Parking Structure"

        aliases = []
        for k in ("alt_name", "short_name", "old_name"):
            if tags.get(k):
                aliases += [a.strip() for a in tags[k].split(";")]
        if tags.get("ref"):
            aliases.append(tags["ref"])
        aliases = list(
            {
                a.strip(): None
                for a in aliases
                if a and a.strip().lower() != name.lower()
            }.keys()
        )

        c = geom.centroid
        centroid = [round(c.x, 6), round(c.y, 6)]

        zone = determine_zone(centroid)
        category = determine_category(tags, name, zone)

        fid = f"{slugify(name)}-{hash_centroid(centroid)}"
        props = {
            "id": fid,
            "name": name,
            "aliases": aliases,
            "zone": zone,
            "category": category,
            "centroid": centroid,
            "osm_ids": [osm_id_str],
            "area": round(A, 2),
            "overlap_role": "solo",
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        g_view = simplify_geom_m(geom, SINGLE_TOLERANCE_M)
        if not g_view:
            continue

        features.append({"type": "Feature", "properties": props, "geometry": mapping(g_view)})

        if idx % 100 == 0 or idx == total:
            print(f"  processed {idx}/{total} elements")

    deduped = {}
    removed_dupes = 0
    for feat in features:
        centroid = tuple(feat["properties"]["centroid"])
        existing = deduped.get(centroid)
        if existing is None:
            deduped[centroid] = feat
        else:
            existing_named = not existing["properties"]["name"].startswith("Unnamed ")
            new_named = not feat["properties"]["name"].startswith("Unnamed ")
            if new_named and not existing_named:
                deduped[centroid] = feat
            removed_dupes += 1

    print(f"Removed {removed_dupes} duplicate feature(s) by centroid")
    features = list(deduped.values())
    assign_parent_child(features)
    print(f"Generated {len(features)} features")
    return features
