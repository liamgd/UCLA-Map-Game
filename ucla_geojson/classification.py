import re
from typing import Dict, Tuple

from .constants import GREEK_NAME_RE, IMPORTANT_OFF_CAMPUS


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


def determine_zone(centroid):
    lat, lon = centroid[1], centroid[0]
    if lon <= -118.445:
        return "The Hill"
    if lon >= -118.44:
        return "Westwood"
    return "North Campus" if lat >= 34.07 else "South Campus"


def determine_category(tags: Dict[str, str], name: str, zone: str) -> Tuple[str, bool]:
    """Returns (category, is_important_off_campus).

    The previous category hierarchy used both categories and subtypes.  This
    function now collapses the hierarchy by promoting the former subtypes to the
    category level.
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

    for key, cat in IMPORTANT_OFF_CAMPUS.items():
        if key in name_norm:
            return cat, True

    if (
        healthcare
        or amenity in {"clinic", "hospital", "doctors", "dentist"}
        or _hint_in(name_norm, MEDICAL_HINTS)
    ):
        cat = "Hospital" if "hospital" in (amenity + " " + name_norm) else "Clinic/Health"
        return cat, zone == "Westwood"

    if (
        btype in {"residential", "dormitory", "apartments", "fraternity", "sorority"}
        or amenity in {"fraternity", "sorority"}
        or re.search(GREEK_NAME_RE, name, re.I)
        or _hint_in(name_norm, HOUSING_HINTS)
    ):
        cat = (
            "Fraternity/Sorority"
            if amenity in {"fraternity", "sorority"}
            or btype in {"fraternity", "sorority"}
            or re.search(GREEK_NAME_RE, name, re.I)
            else "Housing"
        )
        return cat, False

    if (
        amenity in {"restaurant", "fast_food", "cafe", "café", "food_court"}
        or shop in {"convenience", "supermarket"}
        or _hint_in(name_norm, DINING_HINTS)
    ):
        return "Food Service", False

    if amenity == "library" or _hint_in(name_norm, LIBRARY_MUSEUM_HINTS):
        cat = "Library" if "library" in (amenity + " " + name_norm) else "Museum"
        return cat, zone == "Westwood"

    if _hint_in(name_norm, PERFORMANCE_HINTS) or amenity in {
        "theatre",
        "arts_centre",
        "concert_hall",
    }:
        return "Performing Arts", zone == "Westwood"

    if leisure in {
        "stadium",
        "sports_centre",
        "pitch",
        "swimming_pool",
        "track",
        "tennis_court",
    } or _hint_in(name_norm, ATHLETIC_HINTS):
        return "Athletics", False

    if (
        leisure in {"park", "garden"}
        or landuse in {"grass", "recreation_ground", "forest", "meadow", "shrubland"}
        or natural in {"scrub", "shrub", "shrubland", "wood", "grassland"}
    ):
        return "Green Space", False

    if (
        amenity == "parking"
        or tags.get("parking") in {"multi-storey", "underground"}
        or "parking" in (btype + " " + operator)
        or "parking" in name_norm
    ):
        sub = "Structure" if "structure" in name_norm or btype == "parking" else "Lot"
        return f"Parking {sub}", False

    if _hint_in(name_norm, SERVICE_HINTS):
        return "Operations", False

    if zone in {"North Campus", "South Campus"}:
        return "Academic/Research", False
    if zone == "The Hill":
        return "Housing", False
    return "Unknown", False
