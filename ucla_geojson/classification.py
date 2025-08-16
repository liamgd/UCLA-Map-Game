import re
from typing import Dict

from shapely.geometry import Point, Polygon

from .constants import GREEK_NAME_RE


def _norm(s: str) -> str:
    """Normalize a string for fuzzy comparisons."""
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


# --- Zone definitions -----------------------------------------------------

# Simple polygonal boundaries used for zoning.  These were manually derived
# to provide a more accurate split of the campus than the previous set of
# latitude/longitude thresholds.  The coordinates are ordered as (lon, lat).
ZONE_POLYGONS = {
    "The Hill": Polygon(
        [
            (-118.456, 34.069),
            (-118.456, 34.076),
            (-118.447, 34.076),
            (-118.447, 34.069),
        ]
    ),
    "Westwood": Polygon(
        [
            (-118.447, 34.058),
            (-118.447, 34.075),
            (-118.433, 34.075),
            (-118.433, 34.058),
        ]
    ),
    "North Campus": Polygon(
        [
            (-118.447, 34.0705),
            (-118.447, 34.075),
            (-118.44, 34.075),
            (-118.44, 34.0705),
        ]
    ),
    "South Campus": Polygon(
        [
            (-118.447, 34.058),
            (-118.447, 34.0705),
            (-118.44, 34.0705),
            (-118.44, 34.058),
        ]
    ),
}


def _hint_in(name_norm: str, hints: set) -> bool:
    return any(h in name_norm for h in hints)


def determine_zone(centroid):
    """Return the campus zone for a given centroid.

    The previous implementation used a pair of longitude/latitude thresholds
    to split the campus.  This version uses polygon containment which better
    captures the irregular campus outline while retaining a threshold-based
    fallback for outliers.
    """

    point = Point(centroid)
    for zone, poly in ZONE_POLYGONS.items():
        if poly.contains(point):
            return zone

    # Fallback to the old heuristic in case a point falls outside all
    # predefined polygons (e.g. newly added data slightly outside bounds).
    lon, lat = point.x, point.y
    if lon <= -118.445:
        return "The Hill"
    if lon >= -118.44:
        return "Westwood"
    return "North Campus" if lat >= 34.0705 else "South Campus"


def determine_category(tags: Dict[str, str], name: str, zone: str) -> str:
    """Return the category for a feature.

    This version organises the category logic into a sequence of rules rather
    than a long chain of conditionals.  Each rule encapsulates the criteria for
    identifying a category, making it easier to maintain and extend.
    """

    name_norm = _norm(name)
    btype = _norm(tags.get("building"))
    amenity = _norm(tags.get("amenity"))
    leisure = _norm(tags.get("leisure"))
    shop = _norm(tags.get("shop"))
    healthcare = _norm(tags.get("healthcare"))
    operator = _norm(tags.get("operator") or "")
    landuse = _norm(tags.get("landuse"))
    natural = _norm(tags.get("natural"))
    parking = _norm(tags.get("parking"))

    def is_medical():
        return (
            healthcare
            or amenity in {"clinic", "hospital", "doctors", "dentist"}
            or _hint_in(name_norm, MEDICAL_HINTS)
        )

    rules = [
        (
            "Hospital",
            lambda: is_medical()
            and ("hospital" in amenity or "hospital" in name_norm),
        ),
        ("Clinic/Health", is_medical),
        (
            "Lower Education",
            lambda: amenity in {"school", "kindergarten"}
            or btype in {"school", "kindergarten"},
        ),
        (
            "Housing",
            lambda: btype
            in {"residential", "dormitory", "apartments", "fraternity", "sorority"}
            or amenity in {"fraternity", "sorority"}
            or re.search(GREEK_NAME_RE, name, re.I)
            or _hint_in(name_norm, HOUSING_HINTS),
        ),
        (
            "Food Service",
            lambda: amenity
            in {"restaurant", "fast_food", "cafe", "café", "food_court"}
            or shop in {"convenience", "supermarket"}
            or _hint_in(name_norm, DINING_HINTS),
        ),
        (
            "Library",
            lambda: amenity == "library" or "library" in name_norm,
        ),
        (
            "Museum",
            lambda: _hint_in(name_norm, LIBRARY_MUSEUM_HINTS),
        ),
        (
            "Performing Arts",
            lambda: _hint_in(name_norm, PERFORMANCE_HINTS)
            or amenity in {"theatre", "arts_centre", "concert_hall"},
        ),
        ("Pool", lambda: leisure == "swimming_pool" or _hint_in(name_norm, POOL_HINTS)),
        ("Stadium", lambda: leisure == "stadium" or _hint_in(name_norm, STADIUM_HINTS)),
        (
            "Sports Court/Pitch",
            lambda: leisure == "tennis_court" or _hint_in(name_norm, COURT_HINTS),
        ),
        (
            "Sports Field",
            lambda: leisure in {"pitch", "track", "sports_centre"}
            or _hint_in(name_norm, FIELD_HINTS),
        ),
        (
            "Green Space",
            lambda: leisure in {"park", "garden"}
            or landuse
            in {"grass", "recreation_ground", "forest", "meadow", "shrubland"}
            or natural in {"scrub", "shrub", "shrubland", "wood", "grassland"},
        ),
        (
            "Parking",
            lambda: amenity == "parking"
            or parking in {"multi-storey", "underground"}
            or "parking" in (btype + " " + operator + " " + name_norm),
        ),
        ("Operations", lambda: _hint_in(name_norm, SERVICE_HINTS)),
    ]

    for cat, check in rules:
        if check():
            if cat == "Housing":
                return "Off-Campus Housing" if zone == "Westwood" else "On-Campus Housing"
            if cat == "Library" and "library" not in name_norm and amenity != "library":
                # If the library rule matched due to hints but the name does not
                # explicitly mention a library, treat it as a museum instead.
                return "Museum"
            if cat == "Parking":
                sub = (
                    "Structure"
                    if "structure" in name_norm
                    or btype == "parking"
                    or parking in {"multi-storey", "underground"}
                    else "Lot"
                )
                return f"Parking {sub}"
            return cat

    if zone in {"North Campus", "South Campus"}:
        return "Academic/Research"
    if zone == "The Hill":
        return "On-Campus Housing"
    return "Unknown"
