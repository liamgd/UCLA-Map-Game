import re
from datetime import datetime, timezone

from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.geometry.polygon import orient

from .classification import determine_category, determine_zone
from .constants import (
    BLACKLIST,
    EXCLUDE_BUILDINGS,
    MIN_AREA_EXCLUDE,
    MIN_AREA_UNNAMED,
    SINGLE_TOLERANCE_M,
)
from .geometry import area_m2, build_geometries, simplify_geom_m
from .utils import hash_centroid, slugify


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
            or "Unnamed Building"
        )

        if name == "Unnamed Building" and A < MIN_AREA_UNNAMED:
            continue
        if building_type in EXCLUDE_BUILDINGS and A < MIN_AREA_EXCLUDE:
            continue
        if A < MIN_AREA_EXCLUDE and name == "Unnamed Building":
            continue
        if any(re.search(pattern, name, re.I) for pattern in BLACKLIST):
            continue

        if name == "Unnamed Building":
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
        category, important_off = determine_category(tags, name, zone)

        fid = f"{slugify(name)}-{hash_centroid(centroid)}"
        props = {
            "id": fid,
            "name": name,
            "aliases": aliases,
            "zone": zone,
            "category": category,
            "important_off_campus": bool(important_off),
            "centroid": centroid,
            "osm_ids": [osm_id_str],
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

        g_view = simplify_geom_m(geom, SINGLE_TOLERANCE_M)
        if not g_view:
            continue

        features.append({"type": "Feature", "properties": props, "geometry": mapping(g_view)})

        if idx % 100 == 0 or idx == total:
            print(f"  processed {idx}/{total} elements")

    print(f"Generated {len(features)} features")
    return features
