import hashlib
import json
import os
import re
from datetime import datetime, timezone

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
# Classification dictionaries
# -------------------
# Normalize text once
def _norm(s: str) -> str:
    return s.lower() if s else ""


ACADEMIC_HINTS = {
    "hall",
    "laboratory",
    "lab",
    "center",
    "centre",
    "institute",
    "school",
    "department",
    "engineering",
    "math",
    "physics",
    "chemistry",
    "biology",
    "geology",
    "history",
    "philosophy",
    "linguistics",
    "music",
    "theater",
    "theatre",
    "film",
    "statistics",
    "computer",
    "informatics",
    "nanoscience",
    "biomedical",
    "sciences",
    "anthropology",
    "psychology",
}

ADMIN_HINTS = {
    "murphy",
    "registrar",
    "admissions",
    "financial aid",
    "administration",
    "ucla police",
    "ucpd",
    "student affairs",
    "career center",
}

ATHLETIC_HINTS = {
    "pauley",
    "pavilion",
    "stadium",
    "track",
    "intramural",
    "im field",
    "drake",
    "spaulding",
    "gym",
    "athletic",
    "marina aquatic",
    "boathouse",
    "tennis",
    "pool",
}

DINING_HINTS = {
    # dining halls & quick-service on The Hill
    "rendezvous",
    "feast",
    "covel",
    "de neve",
    "epicuria",
    "bruins",
    "b-plate",
    "bruincafe",
    "bruin plate",
    "bruincafé",
    "hederick",
    "sproul commons",
    "deneve",
    "ckc",
    "the study",
    "the den",
    "cafe",
    "café",
    "restaurant",
    "food court",
    "hilltop shop",
    "hill top shop",
}

HOUSING_HINTS = {
    "residence",
    "res hall",
    "hall",
    "apartments",
    "apartment",
    "plaza",
    "rieber",
    "hedrick",
    "sproul",
    "de neve",
    "sunset village",
    "acacia",
    "gardenia",
    "holly",
    "dykstra",
    "delta terrace",
    "dogwood",
    "saxon",
    "wyton",
    "gayley court",
    "gayley heights",
    "fraternity",
    "sorority",
}

LIBRARY_MUSEUM_HINTS = {
    "library",
    "powell",
    "yrl",
    "young research library",
    "biomedical library",
    "fowler museum",
    "hammer museum",
    "hammer",
}

PERFORMANCE_HINTS = {
    "royce hall",
    "geffen playhouse",
    "schoenberg",
    "capitol steps",
    "freud",
    "gindi",
    "theatre",
    "theater",
    "konkoff",
}

MEDICAL_HINTS = {
    "medical",
    "health",
    "hospital",
    "clinic",
    "chs",
    "ronald reagan ucla",
    "ucla health",
    "dental",
    "rehabilitation",
    "neuroscience",
}

SERVICE_HINTS = {
    "utility",
    "plant",
    "power",
    "central plant",
    "mail",
    "loading",
    "warehouse",
    "service",
    "maintenance",
}

PARKING_HINTS = {
    "parking",
    "structure",
    "garage",
    "p1",
    "p2",
    "p3",
    "p4",
    "p5",
    "p6",
    "p7",
    "p8",
    "p9",
    "p10",
}
GREEK_NAME_RE = r"(fraternity|sorority|alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|omicron|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega)"

IMPORTANT_OFF_CAMPUS = {
    # substrings -> (category, subtype)
    "hammer museum": ("Libraries/Museums", "Museum"),
    "geffen playhouse": ("Performance/Venues", "Playhouse"),
    "ronald reagan ucla medical center": ("Medical/Health", "Hospital"),
    "ucla health westwood": ("Medical/Health", "Clinic/Health"),
    "marina aquatics center": ("Athletic/Recreational", "Boathouse"),
}


# -------------------
# Utils
# -------------------
def slugify(text: str) -> str:
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

// Get UCLA campus area(s)
area["amenity"="university"]["name"~"^(University of California, Los Angeles|UCLA)$",i]->.ucla;

// Get buildings, shops, and recreational areas inside UCLA campus
(
  way["building"](area.ucla);
  relation["building"](area.ucla);
  way["shop"](area.ucla);
  relation["shop"](area.ucla);
  way["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court)$"](area.ucla);
  relation["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court)$"](area.ucla);
)->.campus;

// Also get *any* building, shop, or recreational area with name/operator containing UCLA in bbox
(
  way["building"]["name"~"UCLA",i](34.058,-118.456,34.082,-118.433);
  way["building"]["operator"~"UCLA",i](34.058,-118.456,34.082,-118.433);
  relation["building"]["name"~"UCLA",i](34.058,-118.456,34.082,-118.433);
  relation["building"]["operator"~"UCLA",i](34.058,-118.456,34.082,-118.433);
  way["shop"]["name"~"UCLA",i](34.058,-118.456,34.082,-118.433);
  way["shop"]["operator"~"UCLA",i](34.058,-118.456,34.082,-118.433);
  relation["shop"]["name"~"UCLA",i](34.058,-118.456,34.082,-118.433);
  relation["shop"]["operator"~"UCLA",i](34.058,-118.456,34.082,-118.433);
  way["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court)$"]["name"~"UCLA",i](34.058,-118.456,34.082,-118.433);
  way["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court)$"]["operator"~"UCLA",i](34.058,-118.456,34.082,-118.433);
  relation["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court)$"]["name"~"UCLA",i](34.058,-118.456,34.082,-118.433);
  relation["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court)$"]["operator"~"UCLA",i](34.058,-118.456,34.082,-118.433);
)->.ucla_related;

// Get fraternities and sororities in the bounding box (many are just building=yes with Greek names)
(
  way["amenity"="fraternity"](34.058,-118.456,34.082,-118.433);
  way["amenity"="sorority"](34.058,-118.456,34.082,-118.433);
  way["building"="fraternity"](34.058,-118.456,34.082,-118.433);
  way["building"="sorority"](34.058,-118.456,34.082,-118.433);

  relation["amenity"="fraternity"](34.058,-118.456,34.082,-118.433);
  relation["amenity"="sorority"](34.058,-118.456,34.082,-118.433);
  relation["building"="fraternity"](34.058,-118.456,34.082,-118.433);
  relation["building"="sorority"](34.058,-118.456,34.082,-118.433);

  way["building"]["name"~"{GREEK_NAME_RE}",i](34.058,-118.456,34.082,-118.433);
  way["building"]["operator"~"{GREEK_NAME_RE}",i](34.058,-118.456,34.082,-118.433);
  relation["building"]["name"~"{GREEK_NAME_RE}",i](34.058,-118.456,34.082,-118.433);
  relation["building"]["operator"~"{GREEK_NAME_RE}",i](34.058,-118.456,34.082,-118.433);
)->.greek;


// Combine
(.campus; .ucla_related; .greek;);
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
    ways_in_building_rels = set()  # track ways handled by a parent relation

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
                # mark this way as belonging to a parent relation so we don't
                # output it twice. Stadiums often use relations without a
                # building tag, so explicitly handle those as well.
                tags = rel.get("tags", {})
                if "building" in tags or tags.get("leisure") == "stadium":
                    ways_in_building_rels.add(m.get("ref"))
            elif role == "inner":
                inners.append(poly)

        if outers:
            merged = unary_union(outers)
            if (
                isinstance(merged, (Polygon, MultiPolygon))
                and not merged.is_empty
            ):
                rel_polys[rel["id"]] = merged

    return (
        ways,
        rels,
        way_polys,
        rel_polys,
        ways_in_building_rels,
    )  # <-- return new set


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


def _hint_in(name_norm: str, hints: set) -> bool:
    return any(h in name_norm for h in hints)


def determine_category(tags: dict, name: str, zone: str):
    """
    Returns (category, subtype, is_important_off_campus)
    """
    name_norm = _norm(name)
    btype = _norm(tags.get("building"))
    amenity = _norm(tags.get("amenity"))
    leisure = _norm(tags.get("leisure"))
    shop = _norm(tags.get("shop"))
    healthcare = _norm(tags.get("healthcare"))
    operator = _norm(tags.get("operator") or "")

    # Off-campus important overrides
    for key, (cat, sub) in IMPORTANT_OFF_CAMPUS.items():
        if key in name_norm:
            return cat, sub, True

    # Medical/Health
    if (
        healthcare
        or amenity in {"clinic", "hospital", "doctors", "dentist"}
        or _hint_in(name_norm, MEDICAL_HINTS)
    ):
        subtype = (
            "Hospital"
            if "hospital" in (amenity + " " + name_norm)
            else "Clinic/Health"
        )
        return "Medical/Health", subtype, zone == "Westwood"

    # Housing
    if (
        btype
        in {"residential", "dormitory", "apartments", "fraternity", "sorority"}
        or amenity in {"fraternity", "sorority"}
        or re.search(GREEK_NAME_RE, name, re.I)  # <— add this
        or _hint_in(name_norm, HOUSING_HINTS)
    ):
        subtype = (
            "Fraternity/Sorority"
            if amenity in {"fraternity", "sorority"}
            or btype in {"fraternity", "sorority"}
            or re.search(GREEK_NAME_RE, name, re.I)  # <— and here
            else "Housing"
        )
        return "Residential", subtype, False

    # Dining
    if (
        amenity in {"restaurant", "fast_food", "cafe", "café", "food_court"}
        or shop in {"convenience", "supermarket"}
        or _hint_in(name_norm, DINING_HINTS)
    ):
        return "Dining", "Food Service", False

    # Libraries & Museums
    if amenity == "library" or _hint_in(name_norm, LIBRARY_MUSEUM_HINTS):
        sub = (
            "Library" if "library" in (amenity + " " + name_norm) else "Museum"
        )
        return "Libraries/Museums", sub, zone == "Westwood"

    # Performance/Venues
    if _hint_in(name_norm, PERFORMANCE_HINTS) or amenity in {
        "theatre",
        "arts_centre",
        "concert_hall",
    }:
        return "Performance/Venues", "Performing Arts", zone == "Westwood"

    # Athletic / Recreational
    if leisure in {
        "stadium",
        "sports_centre",
        "pitch",
        "swimming_pool",
        "track",
        "tennis_court",
    } or _hint_in(name_norm, ATHLETIC_HINTS):
        return "Athletic/Recreational", "Athletics", False

    # Parking
    if btype == "parking" or _hint_in(name_norm, PARKING_HINTS):
        return "Service/Support", "Parking", False

    # Administrative
    if _hint_in(name_norm, ADMIN_HINTS) or operator == "ucla administration":
        return "Administrative", "Administration", False

    # Academic default within campus
    if zone in {"North Campus", "South Campus"} and (
        btype in {"university", "school", "public"}
        or operator.startswith("ucla")
        or _hint_in(name_norm, ACADEMIC_HINTS)
    ):
        return "Academic", "Academic/Research", False

    # Service/Support fallback
    if _hint_in(name_norm, SERVICE_HINTS):
        return "Service/Support", "Operations", False

    # If nothing matched, infer by zone
    if zone in {"North Campus", "South Campus"}:
        return "Academic", "Academic/Research", False
    if zone == "The Hill":
        # unknown on The Hill? probably housing/dining
        return "Residential", "Housing", False
    # Westwood/other
    return "Other/Unknown", "Unknown", False


# -------------------
# Processing
# -------------------
def process_features(osm_data):
    ways, rels, way_polys, rel_polys, ways_in_building_rels = build_geometries(
        osm_data
    )
    features = []

    for el in osm_data.get("elements", []):
        if el["type"] == "way":
            # Skip ways that are members of a building relation; the relation carries the name/tags
            if el["id"] in ways_in_building_rels:
                continue
            geom = way_polys.get(el["id"])
            osm_id_str = f"way/{el['id']}"
        elif el["type"] == "relation":
            geom = rel_polys.get(el["id"])
            osm_id_str = f"relation/{el['id']}"
        else:
            continue
        ...

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
            or tags.get("ref")
            or tags.get("operator")
            or "Unnamed Building"
        )

        # Apply filters
        if name == "Unnamed Building" and A < MIN_AREA_UNNAMED:
            continue
        if building_type in EXCLUDE_BUILDINGS and A < MIN_AREA_EXCLUDE:
            continue
        if A < MIN_AREA_EXCLUDE and name == "Unnamed Building":
            continue

        # If it's a parking structure and still unnamed, synthesize a display name
        if name == "Unnamed Building":
            amenity = (tags.get("amenity") or "").lower()
            parking = (tags.get("parking") or "").lower()
            bldg = (tags.get("building") or "").lower()
            if (
                amenity == "parking"
                or bldg == "parking"
                or parking in {"multi-storey", "underground"}
            ):
                # Try to turn refs like "P8", "8", "PS-8" into "Parking Structure 8"
                ref = (tags.get("ref") or "").strip()
                m = re.search(
                    r"(?:^|[^0-9])([Pp]?\s*\d{1,2})(?:[^0-9]|$)", ref
                )
                if m:
                    num = re.sub(r"[^\d]", "", m.group(1))
                    name = f"Parking Structure {num}"
                else:
                    name = "Parking Structure"

        # aliases
        aliases = []
        for k in ("alt_name", "short_name", "old_name"):
            if tags.get(k):
                aliases += [a.strip() for a in tags[k].split(";")]
        if tags.get("ref"):
            aliases.append(tags["ref"])  # keep "P8" etc. searchable
        aliases = list(
            {
                a.strip(): None
                for a in aliases
                if a and a.strip().lower() != name.lower()
            }.keys()
        )

        # centroid
        c = geom.centroid
        centroid = [round(c.x, 6), round(c.y, 6)]

        # Zone
        zone = determine_zone(centroid)

        # Category / subtype / important
        category, subtype, important_off = determine_category(tags, name, zone)

        # ID + props
        fid = f"{slugify(name)}-{hash_centroid(centroid)}"
        props = {
            "id": fid,
            "name": name,
            "aliases": aliases,
            "zone": zone,
            "category": category,  # <- NEW
            "subtype": subtype,  # <- NEW
            "important_off_campus": bool(important_off),
            "centroid": centroid,
            "osm_ids": [osm_id_str],
            "updated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
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
    # with open("public/campus.geojson", "r", encoding="utf-8") as f:
    #     print(f.read())


if __name__ == "__main__":
    main()
