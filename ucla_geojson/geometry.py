from shapely.geometry import LinearRing, MultiPolygon, Polygon
from shapely.ops import transform, unary_union

from .constants import _TO_DEG, _TO_M


def build_geometries(osm_data):
    print("Building geometries...")
    elements = osm_data.get("elements", [])
    nodes = {el["id"]: el for el in elements if el["type"] == "node"}
    ways = {el["id"]: el for el in elements if el["type"] == "way"}
    rels = [el for el in elements if el["type"] == "relation"]

    way_polys = {}
    for wid, way in ways.items():
        coords, missing = [], False
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
    ways_in_building_rels = set()
    ways_in_multipolygon_holes = set()
    inner_count = 0

    for rel in rels:
        if "members" not in rel:
            continue
        outers, inners = [], []
        for m in rel["members"]:
            if m.get("type") != "way":
                continue
            poly = way_polys.get(m.get("ref"))
            if not poly:
                continue
            role = m.get("role")
            if role == "outer":
                outers.append(poly)
                tags = rel.get("tags", {})
                if "building" in tags or tags.get("leisure") == "stadium":
                    ways_in_building_rels.add(m.get("ref"))
            elif role == "inner":
                inners.append(poly)
                ways_in_multipolygon_holes.add(m.get("ref"))
                inner_count += 1

        if outers:
            merged = unary_union(outers)
            if inners:
                inner_union = unary_union(inners)
                if not inner_union.is_empty:
                    merged = merged.difference(inner_union)
            if (
                isinstance(merged, (Polygon, MultiPolygon))
                and not merged.is_empty
            ):
                rel_polys[rel["id"]] = merged

    print(f"  Removed {inner_count} multipolygon holes")
    print(
        f"Built {len(way_polys)} way polygons and {len(rel_polys)} relation polygons"
    )

    return (
        ways,
        rels,
        way_polys,
        rel_polys,
        ways_in_building_rels,
        ways_in_multipolygon_holes,
    )


def area_m2(geom):
    return transform(_TO_M, geom).area


def simplify_geom_m(geom, tol_m):
    g_m = transform(_TO_M, geom)
    g_s = g_m.simplify(tol_m, preserve_topology=True)
    if g_s.is_empty:
        return None
    return transform(_TO_DEG, g_s)
