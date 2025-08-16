import re
from dataclasses import dataclass
from typing import Callable, Dict

from shapely.geometry import Point, Polygon

from .constants import GREEK_NAME_RE, ZONE_COORDS


def _norm(s: str) -> str:
    return s.lower() if s else ""

POOL_HINTS = {"pool", "aquatic"}
STADIUM_HINTS = {"stadium", "pavilion"}
COURT_HINTS = {"court", "tennis"}
FIELD_HINTS = {
    "track",
    "field",
    "intramural",
    "im field",
    "drake",
    "spaulding",
}

DINING_HINTS = {
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


def _hint_in(name_norm: str, hints: set) -> bool:
    return any(h in name_norm for h in hints)


ZONE_POLYGONS = {name: Polygon(coords) for name, coords in ZONE_COORDS.items()}


@dataclass
class CategoryRule:
    """Rule used to map a feature to a high level category."""

    name: str
    predicate: Callable[[Dict[str, str], str, str], bool]


def determine_zone(centroid):
    """Determine the major campus zone for a feature."""
    lon, lat = centroid[0], centroid[1]
    point = Point(lon, lat)
    for zone, poly in ZONE_POLYGONS.items():
        if poly.contains(point):
            return zone
    if lon <= -118.445:
        return "The Hill"
    if lon >= -118.44:
        return "Westwood"
    return "North Campus" if lat >= 34.07 else "South Campus"


def determine_category(tags: Dict[str, str], name: str, zone: str) -> str:
    """Return the high-level category for a feature."""

    name_norm = _norm(name)
    ctx = {
        "btype": _norm(tags.get("building")),
        "amenity": _norm(tags.get("amenity")),
        "leisure": _norm(tags.get("leisure")),
        "shop": _norm(tags.get("shop")),
        "healthcare": _norm(tags.get("healthcare")),
        "operator": _norm(tags.get("operator") or ""),
        "landuse": _norm(tags.get("landuse")),
        "natural": _norm(tags.get("natural")),
        "parking": _norm(tags.get("parking")),
        "tourism": _norm(tags.get("tourism")),
    }

    def is_hospital(c):
        return "hospital" in (c["amenity"] + " " + name_norm)

    def is_medical(c):
        return (
            c["healthcare"]
            or c["amenity"] in {"clinic", "doctors", "dentist", "hospital"}
            or _hint_in(name_norm, MEDICAL_HINTS)
        )

    def is_lower_ed(c):
        return c["amenity"] in {"school", "kindergarten"} or c["btype"] in {
            "school",
            "kindergarten",
        }

    def is_housing(c):
        return (
            c["btype"]
            in {"residential", "dormitory", "apartments", "fraternity", "sorority"}
            or c["amenity"] in {"fraternity", "sorority"}
            or re.search(GREEK_NAME_RE, name, re.I)
            or _hint_in(name_norm, HOUSING_HINTS)
        )

    def is_food(c):
        return (
            c["amenity"]
            in {"restaurant", "fast_food", "cafe", "café", "food_court"}
            or c["shop"] in {"convenience", "supermarket"}
            or _hint_in(name_norm, DINING_HINTS)
        )

    def is_library(c):
        return c["amenity"] == "library" or "library" in name_norm

    def is_museum(c):
        return c["tourism"] in {"museum", "gallery"} or (
            _hint_in(name_norm, LIBRARY_MUSEUM_HINTS) and not is_library(c)
        )

    def is_performance(c):
        return _hint_in(name_norm, PERFORMANCE_HINTS) or c["amenity"] in {
            "theatre",
            "arts_centre",
            "concert_hall",
        }

    def is_pool(c):
        return c["leisure"] == "swimming_pool" or _hint_in(name_norm, POOL_HINTS)

    def is_stadium(c):
        return c["leisure"] == "stadium" or _hint_in(name_norm, STADIUM_HINTS)

    def is_court(c):
        return c["leisure"] == "tennis_court" or _hint_in(name_norm, COURT_HINTS)

    def is_field(c):
        return c["leisure"] in {"pitch", "track", "sports_centre"} or _hint_in(
            name_norm, FIELD_HINTS
        )

    def is_green(c):
        return (
            c["leisure"] in {"park", "garden"}
            or c["landuse"] in {"grass", "recreation_ground", "forest", "meadow", "shrubland"}
            or c["natural"] in {"scrub", "shrub", "shrubland", "wood", "grassland"}
        )

    def is_parking(c):
        return (
            c["amenity"] == "parking"
            or c["parking"] in {"multi-storey", "underground"}
            or "parking" in (c["btype"] + " " + c["operator"])
            or "parking" in name_norm
        )

    def is_parking_structure(c):
        return is_parking(c) and ("structure" in name_norm or c["btype"] == "parking")

    def is_operations(c):
        return _hint_in(name_norm, SERVICE_HINTS)

    rules = [
        CategoryRule("Hospital", lambda c, n, z: is_hospital(c)),
        CategoryRule("Clinic/Health", lambda c, n, z: is_medical(c)),
        CategoryRule("Lower Education", lambda c, n, z: is_lower_ed(c)),
        CategoryRule("Off-Campus Housing", lambda c, n, z: z == "Westwood" and is_housing(c)),
        CategoryRule("On-Campus Housing", lambda c, n, z: is_housing(c)),
        CategoryRule("Food Service", lambda c, n, z: is_food(c)),
        CategoryRule("Library", lambda c, n, z: is_library(c)),
        CategoryRule("Museum", lambda c, n, z: is_museum(c)),
        CategoryRule("Performing Arts", lambda c, n, z: is_performance(c)),
        CategoryRule("Pool", lambda c, n, z: is_pool(c)),
        CategoryRule("Stadium", lambda c, n, z: is_stadium(c)),
        CategoryRule("Sports Court/Pitch", lambda c, n, z: is_court(c)),
        CategoryRule("Sports Field", lambda c, n, z: is_field(c)),
        CategoryRule("Green Space", lambda c, n, z: is_green(c)),
        CategoryRule("Parking Structure", lambda c, n, z: is_parking_structure(c)),
        CategoryRule("Parking Lot", lambda c, n, z: is_parking(c)),
        CategoryRule("Operations", lambda c, n, z: is_operations(c)),
    ]

    for rule in rules:
        if rule.predicate(ctx, name_norm, zone):
            return rule.name

    if zone in {"North Campus", "South Campus"}:
        return "Academic/Research"
    if zone == "The Hill":
        return "On-Campus Housing"
    return "Unknown"
