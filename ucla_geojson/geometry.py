from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

from shapely.geometry import LinearRing, LineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import linemerge, polygonize, transform, unary_union

from .constants import _TO_DEG, _TO_M


def build_geometries(osm_data: Dict[str, Any]) -> Tuple[
    Dict[int, Dict[str, Any]],
    List[Dict[str, Any]],
    Dict[int, Polygon],
    Dict[int, Union[Polygon, MultiPolygon]],
    Set[int],
    Set[int],
]:
    print("Building geometries...")
    elements = osm_data.get("elements", [])
    nodes: Dict[int, Dict[str, Any]] = {
        el["id"]: el for el in elements if el["type"] == "node"
    }
    ways: Dict[int, Dict[str, Any]] = {
        el["id"]: el for el in elements if el["type"] == "way"
    }
    rels: List[Dict[str, Any]] = [el for el in elements if el["type"] == "relation"]

    way_polys: Dict[int, Polygon] = {}
    way_lines: Dict[int, LineString] = {}
    invalid_ways: Dict[int, str] = {}
    for wid, way in ways.items():
        coords, missing = [], False
        for nid in way.get("nodes", []):
            n = nodes.get(nid)
            if not n:
                missing = True
                break
            coords.append((n["lon"], n["lat"]))
        if missing or len(coords) < 2:
            invalid_ways[wid] = "missing nodes"
            continue

        way_lines[wid] = LineString(coords)

        if len(coords) < 3 or coords[0] != coords[-1]:
            continue

        ring = LinearRing(coords)
        if not ring.is_valid:
            invalid_ways[wid] = "invalid ring"
            continue
        poly = Polygon(ring)
        if not poly.is_valid or poly.is_empty:
            invalid_ways[wid] = "invalid polygon"
            continue
        way_polys[wid] = poly

    rel_polys: Dict[int, Union[Polygon, MultiPolygon]] = {}
    ways_in_building_rels: Set[int] = set()
    ways_in_multipolygon_holes: Set[int] = set()
    inner_count = 0

    skipped_relations = {}

    for rel in rels:
        if "members" not in rel:
            continue
        outer_polys, outer_lines, inner_polys, inner_lines = [], [], [], []
        missing_outers = []
        for m in rel["members"]:
            if m.get("type") != "way":
                continue
            wid = m.get("ref")
            role = m.get("role")
            poly = way_polys.get(wid)
            line = way_lines.get(wid)
            if role == "outer":
                if poly:
                    outer_polys.append(poly)
                    tags = rel.get("tags", {})
                    if "building" in tags or tags.get("leisure") == "stadium":
                        ways_in_building_rels.add(wid)
                elif line:
                    outer_lines.append(line)
                    tags = rel.get("tags", {})
                    if "building" in tags or tags.get("leisure") == "stadium":
                        ways_in_building_rels.add(wid)
                else:
                    missing_outers.append((wid, invalid_ways.get(wid, "missing way")))
            elif role == "inner":
                if poly:
                    inner_polys.append(poly)
                elif line:
                    inner_lines.append(line)
                else:
                    continue
                ways_in_multipolygon_holes.add(wid)
                inner_count += 1

        if missing_outers:
            skipped_relations[rel["id"]] = missing_outers
            print(
                f"  Skipping relation {rel['id']} due to missing outer ways: {missing_outers}"
            )
            continue

        merged = None
        if outer_polys:
            merged = unary_union(outer_polys)
        if outer_lines:
            line_union = unary_union(outer_lines)
            merged_lines = linemerge(line_union)
            line_polys = list(polygonize(merged_lines))
            if line_polys:
                poly_union = unary_union(line_polys)
                merged = poly_union if merged is None else unary_union([merged, poly_union])
        if merged:
            merged = merged.buffer(0)

        if merged and (inner_polys or inner_lines):
            inner_geoms: List[Polygon] = []
            if inner_polys:
                inner_geoms.extend(inner_polys)
            if inner_lines:
                inner_line_union = unary_union(inner_lines)
                merged_inner_lines = linemerge(inner_line_union)
                inner_line_polys = list(polygonize(merged_inner_lines))
                if inner_line_polys:
                    inner_geoms.extend(inner_line_polys)
            if inner_geoms:
                inner_union = unary_union(inner_geoms)
                if not inner_union.is_empty:
                    merged = merged.difference(inner_union).buffer(0)

        if (
            merged
            and isinstance(merged, (Polygon, MultiPolygon))
            and not merged.is_empty
        ):
            rel_polys[rel["id"]] = merged

    if skipped_relations:
        print(
            f"  Omitted {len(skipped_relations)} relations with missing outer members"
        )

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


def area_m2(geom: BaseGeometry) -> float:
    return transform(_TO_M, geom).area


def simplify_geom_m(geom: BaseGeometry, tol_m: float) -> Optional[BaseGeometry]:
    g_m = transform(_TO_M, geom)
    g_s = g_m.simplify(tol_m, preserve_topology=True)
    if g_s.is_empty:
        return None
    return transform(_TO_DEG, g_s)
