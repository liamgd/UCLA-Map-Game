import hashlib
import json
import os
from datetime import datetime

import pyproj
import requests
from shapely.geometry import LinearRing, MultiPolygon, Polygon, mapping
from shapely.geometry.polygon import orient
from shapely.ops import transform, unary_union

# -------------------
# Config
# -------------------
BBOX = (34.058, -118.456, 34.082, -118.433)  # (south, west, north, east)
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
SINGLE_TOLERANCE_M = 0.4  # meters detail for BOTH draw and hit
EXCLUDE_BUILDINGS = {"hut", "shed", "garage", "kiosk", "tent", "container"}
MIN_AREA_UNNAMED = 80  # m²
MIN_AREA_EXCLUDE = 120  # m²

# Projections (meters <-> lon/lat)
_TO_M = pyproj.Transformer.from_crs(
    "EPSG:4326", "EPSG:3310", always_xy=True
).transform
_TO_DEG = pyproj.Transformer.from_crs(
    "EPSG:3310", "EPSG:4326", always_xy=True
).transform


# -------------------
# Utils
# -------------------
def slugify(text: str) -> str:
    import re

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug


def hash_centroid(centroid):
    s = f"{centroid[0]:.5f},{centroid[1]:.5f}"
    return hashlib.md5(s.encode()).hexdigest()[:6]


def fetch_osm_data():
    query = f"""
[out:json][timeout:90];
(
  way["building"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  relation["building"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out body; >; out skel qt;
"""
    r = requests.get(OVERPASS_URL, params={"data": query})
    r.raise_for_status()
    return r.json()


def build_geometries(osm_data):
    elements = osm_data.get("elements", [])
    nodes = {el["id"]: el for el in elements if el["type"] == "node"}
    ways = {el["id"]: el for el in elements if el["type"] == "way"}
    rels = [el for el in elements if el["type"] == "relation"]

    way_polys = {}
    for wid, way in ways.items():
        # Build closed ring; skip if any node missing
        coords = []
        missing = False
        for nid in way.get("nodes", []):
            n = nodes.get(nid)
            if not n:
                missing = True
                break
            coords.append((n["lon"], n["lat"]))
        if missing or len(coords) < 3:
            continue
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        ring = LinearRing(coords)
        if not ring.is_valid:
            continue
        poly = Polygon(ring)
        if not poly.is_valid or poly.is_empty:
            continue
        way_polys[wid] = poly

    rel_polys = {}
    for rel in rels:
        if "members" not in rel:
            continue
        outers = []
        inners = []
        for m in rel["members"]:
            if m.get("type") != "way":
                continue
            poly = way_polys.get(m.get("ref"))
            if not poly:
                continue
            role = m.get("role")
            if role == "outer":
                outers.append(poly)
            elif role == "inner":
                inners.append(poly)
        if outers:
            merged = unary_union(outers)
            if (
                isinstance(merged, (Polygon, MultiPolygon))
                and not merged.is_empty
            ):
                rel_polys[rel["id"]] = merged
    return ways, rels, way_polys, rel_polys


def area_m2(geom):
    return transform(_TO_M, geom).area


def simplify_geom_m(geom, tol_m):
    g_m = transform(_TO_M, geom)
    g_s = g_m.simplify(tol_m, preserve_topology=True)
    if g_s.is_empty:
        return None
    return transform(_TO_DEG, g_s)


def determine_zone(centroid):
    lat, lon = centroid[1], centroid[0]
    # Heuristic split; tune later with zones.geojson if desired
    if lon <= -118.445:
        return "The Hill"
    if lon >= -118.44:
        return "Westwood"
    return "North Campus" if lat >= 34.07 else "South Campus"


# -------------------
# Processing
# -------------------
def process_features(osm_data):
    ways, rels, way_polys, rel_polys = build_geometries(osm_data)
    features = []

    for el in osm_data.get("elements", []):
        if el["type"] == "way":
            geom = way_polys.get(el["id"])
            osm_id_str = f"way/{el['id']}"
        elif el["type"] == "relation":
            geom = rel_polys.get(el["id"])
            osm_id_str = f"relation/{el['id']}"
        else:
            continue

        if geom is None or geom.is_empty:
            continue

        # Normalize orientation
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
        )

        if not name and A < MIN_AREA_UNNAMED:
            continue
        if building_type in EXCLUDE_BUILDINGS and A < MIN_AREA_EXCLUDE:
            continue
        if not name and A < MIN_AREA_EXCLUDE:
            continue

        name = (
            name
            or tags.get("ref")
            or tags.get("operator")
            or "Unnamed Building"
        )

        # aliases
        aliases = []
        for k in ("alt_name", "short_name", "old_name"):
            if tags.get(k):
                aliases += [a.strip() for a in tags[k].split(";")]
        aliases = list({a for a in aliases if a and a != name})

        # centroid
        c = geom.centroid
        centroid = [round(c.x, 6), round(c.y, 6)]

        # ID + props
        fid = f"{slugify(name)}-{hash_centroid(centroid)}"
        props = {
            "id": fid,
            "name": name,
            "aliases": aliases,
            "zone": determine_zone(centroid),
            "centroid": centroid,
            "osm_ids": [osm_id_str],
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

        # One geometry for both render and hit
        g_view = simplify_geom_m(geom, SINGLE_TOLERANCE_M)
        if not g_view:
            continue

        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": mapping(g_view),
            }
        )

    return features


def write_single(features):
    os.makedirs("public", exist_ok=True)
    fc = {"type": "FeatureCollection", "features": features}
    with open("public/campus.geojson", "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
    with open("public/attribution.txt", "w", encoding="utf-8") as f:
        f.write(
            "© OpenStreetMap contributors — Data: ODbL 1.0 (opendatacommons.org/licenses/odbl/)"
        )


def main():
    data = fetch_osm_data()
    features = process_features(data)
    write_single(features)
    # Print only the single file to STDOUT
    with open("public/campus.geojson", "r", encoding="utf-8") as f:
        print(f.read())


if __name__ == "__main__":
    main()
