import re
from typing import Dict

from shapely.geometry import Point

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

# Additional indicators that a building or amenity is used for academic or research
# purposes.  These sets are consulted directly when determining if a feature
# should be classified as "Academic/Research".
ACADEMIC_BUILDINGS = {
    "university",
    "college",
    "education",
    "educational",
    "laboratory",
    "lab",
    "research",
    "research_institute",
    "faculty",
    "classroom",
    "lecture_hall",
    "training",
}

ACADEMIC_AMENITIES = {
    "university",
    "college",
    "research",
    "research_institute",
    "educational_institution",
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
COURT_HINTS = {
    "court",
    "tennis",
    # Additional sports courts
    "basketball",
    "volleyball",
    "pickleball",
    "badminton",
    "arena",
    "gym",
}
FIELD_HINTS = {
    "track",
    "field",
    "intramural",
    "im field",
    "drake",
    "spaulding",
    # Additional field sports and athletics
    "baseball",
    "softball",
    "soccer",
    "football",
    "lacrosse",
    "athletics",
    "athletic",
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

# Terms that strongly indicate residential or student housing facilities.  These
# hints are used to classify housing-related features.  Note that generic
# building descriptors like "hall" or "plaza" are intentionally excluded
# here.  Many academic buildings on campus are named "Hall" or include
# "Plaza" in their names (e.g. Boelter Hall, Dickson Plaza), and treating
# those terms as housing would misclassify academic spaces as residences.
HOUSING_HINTS = {
    "residence",
    "res hall",
    "apartments",
    "apartment",
    # Dorm names on The Hill
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
    # Greek housing
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

# Names that indicate open or landscaped spaces rather than buildings.  These
# help classify plazas, quads, and lawns as green space.
GREEN_NAME_HINTS = {
    "plaza",
    "quad",
    "lawn",
    "garden",
    "park",
    "square",
    "grove",
    "courtyard",
    "green",
}


def _hint_in(name_norm: str, hints: set) -> bool:
    return any(h in name_norm for h in hints)


def determine_zone(centroid, main_campus):
    """Return the campus zone for a given centroid.

    The previous implementation used a pair of longitude/latitude thresholds
    to split the campus.  This version uses polygon containment which better
    captures the irregular campus outline while retaining a threshold-based
    fallback for outliers.
    """

    point = Point(centroid)

    lat, lon = point.x, point.y
    if not main_campus:
        if lon <= 34.0630 or (lon <= 34.0644 and lat <= -118.4482036664417):
            return "Southwest Campus"
        return "Westwood"
    if lat <= -0.1135 * lon - 114.5823:
        return "The Hill"
    if lon >= 34.0732:
        return "North Campus"
    if lon <= 34.0698:
        return "South Campus"
    return "Center Campus"


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
        # Academic and research facilities: look for building or amenity types
        # that denote higher education or research, or names containing common
        # academic keywords.  Placing this before the housing rule prevents
        # halls such as Boelter Hall or Knudsen Hall from being misclassified
        # as housing.
        (
            "Academic/Research",
            lambda: (
                btype in ACADEMIC_BUILDINGS
                or amenity in ACADEMIC_AMENITIES
                or _hint_in(name_norm, ACADEMIC_HINTS)
            ),
        ),
        (
            "Housing",
            lambda: btype
            in {
                "residential",
                "dormitory",
                "apartments",
                "fraternity",
                "sorority",
            }
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
        (
            "Pool",
            lambda: leisure == "swimming_pool"
            or _hint_in(name_norm, POOL_HINTS),
        ),
        (
            "Stadium",
            lambda: leisure == "stadium" or _hint_in(name_norm, STADIUM_HINTS),
        ),
        (
            "Sports Court/Pitch",
            lambda: leisure == "tennis_court"
            or _hint_in(name_norm, COURT_HINTS),
        ),
        (
            "Sports Field",
            lambda: leisure in {"pitch", "track", "sports_centre"}
            or _hint_in(name_norm, FIELD_HINTS),
        ),
        (
            "Green Space",
            lambda: (
                leisure in {"park", "garden"}
                or landuse
                in {
                    "grass",
                    "recreation_ground",
                    "forest",
                    "meadow",
                    "shrubland",
                }
                or natural
                in {"scrub", "shrub", "shrubland", "wood", "grassland"}
                or _hint_in(name_norm, GREEN_NAME_HINTS)
            ),
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
                return (
                    "Off-Campus Housing"
                    if zone in ("Westwood", "Southwest Campus")
                    else "On-Campus Housing"
                )
            if (
                cat == "Library"
                and "library" not in name_norm
                and amenity != "library"
            ):
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

    # # Default fallback based on the campus zone.  Features in the academic core
    # # (North, Center, or South Campus) that didn't match any specific rule are
    # # treated as academic/research facilities.  Features on the Hill are
    # # considered on-campus housing, and those in Westwood are considered
    # # off-campus housing.  This eliminates the "Unknown" category entirely.
    # if zone in {"North Campus", "Center Campus", "South Campus"}:
    #     return "Academic/Research"
    # if zone == "The Hill":
    #     return "On-Campus Housing"
    # if zone == "Southwest Campus":
    #     return "On-Campus Housing"
    # # Default for Westwood or any other zones
    # return "Off-Campus Housing"
    return "Unknown"
