import re
from typing import Callable, Dict, Iterable, List, Sequence, Set, Tuple

from shapely.geometry import Point

from .constants import GREEK_NAME_RE


def _hint_in(name_norm: str, hints: Set[str]) -> bool:
    return any(h in name_norm for h in hints)


def _includes(*args):
    return lambda x: any(arg in x for arg in args)


def _or(*args):
    return lambda x: x in args


CLASSIFICATION = [
    ("UCLA Extension", {"name": _includes("UCLA Extension")}),
    ("UCLA Extension", {"id": 184772366}),
    ("Mistake (Delete)", {"building": "college"}),
    ("Student Services / Auditorium", {"building": "auditorium"}),
    (
        "Campus Services",
        {
            "name": _includes(
                "Programs",
                "Management Commons",
                "Entrepreneurs",
                "Maintenance",
                "Campus Services",
                "Conference",
                "Health & Safety",
                "JD Morgan",
                "North Campus Student Center",
                "Strathmore",
                "Police",
                "Alumni",
                "Steam Plant",
                "Information",
                "Pavillion",
                "Faculty Center",
                "Design & Construction",
            )
        },
    ),
    ("Campus Services / Warehouse", {"building": "warehouse"}),
    (
        "Student Services / Childcare",
        {"name": _includes("Krieger", "Fernald")},
    ),
    ("Unknown / Roof", {"building": "roof"}),
    ("Green Space / Forest", {"natural": _or("shrubland", "wood")}),
    ("Student Services / Makerspace", {"leisure": "hackerspace"}),
    ("Athletics / Kickball Court", {"sport": "kickball"}),
    ("Student Services / Museum", {"tourism": "museum"}),
    ("Student Services / Dining", {"amenity": "food_court"}),
    ("Athletics / Sports Area", {"id": _or(422876728, 422876720)}),
    ("Athletics / Archery Field", {"sport": "archery"}),
    ("Athletics / Grandstand", {"building": "grandstand"}),
    ("Athletics / Basketball Court", {"sport": "basketball"}),
    ("Athletics / Football Field", {"sport": "american_football"}),
    ("Athletics / Tennis Court", {"leisure": "pitch", "sport": "tennis"}),
    (
        "Athletics / Soccer Field",
        {"leisure": "pitch", "sport": _includes("soccer")},
    ),
    ("Athletics / Softball Field", {"leisure": "pitch", "sport": "softball"}),
    ("Athletics / Unknown Pitch", {"leisure": "pitch"}),
    ("Athletics / Track", {"leisure": "track"}),
    ("Athletics / Swimming Pool", {"leisure": "swimming_pool"}),
    ("Athletics / Sports Area", {"leisure": "sports_centre"}),
    ("Athletics / Sports Area", {"amenity": "community_centre"}),
    ("Athletics / Sports Area", {"landuse": "recreation_ground"}),
    ("Green Space / Garden", {"building": "greenhouse"}),
    ("Green Space / Garden", {"leisure": "garden"}),
    ("Green Space / Grass", {"id": 293613409}),  # Wilson Plaza
    ("Green Space / Grass", {"landuse": "grass"}),
    ("Green Space / Park", {"leisure": "park"}),
    (
        "Parking / Structure",
        {"amenity": "parking", "name": _includes("Structure")},
    ),
    ("Parking / Lot", {"amenity": "parking", "parking": "surface"}),
    ("Parking / Structure", {"amenity": "parking"}),
    ("Athletics / Stadium", {"leisure": "stadium"}),
    ("Student Services / Library", {"amenity": "library"}),
    (
        "Healthcare",
        {"healthcare": _or("clinic", "hospital", "blood_donation")},
    ),
    (
        "Healthcare",
        {"id": _or(46364638, 49832949, 422876610, 422876569)},
    ),  # Gonda + clinics
    ("Research Institute", {"amenity": "research_institute"}),
    (
        "Research Institute",
        {"id": _or(13007994, 53334145, 422876595)},
    ),  # CNSI + STRB
    (
        "Pre-University Education",
        {"name": _includes("UCLA Lab School", "Academy")},
    ),
    ("Student Services / Retail", {"building": "retail"}),
    (
        "Student Services / Retail",
        {"name": _includes("Union")},
    ),
    (
        "Athletics / Sports Area",
        {"id": _or(590016847, 422876683, 422876709, 422876613)},
    ),  # Wasserman, LATC bldg, Wallis bldg, Park Pool Locker Rooms
    ("Athletics / Sports Area", {"name": _includes("Sunset Canyon")}),
    ("Athletics / Sports Area", {"name": _includes("Pool")}),
    ("Housing / Sorority", {"building:use": "sorority"}),
    ("Unknown / Building", {"id": 422298411}),
    ("Housing / Fraternity", {"building:use": "fraternity"}),
    (
        "Housing / Fraternity",
        {"name": _includes("Fraternity", "Alpha Tau Omega")},
    ),
    (
        "Athletics / Gym Center",
        {"leisure": "fitness_centre"},
    ),
    (
        "Athletics / Gym Center",
        {"id": _or(422876520, 422876656)},
    ),  # Acosta, Wooden
    (
        "Housing / Off-Campus",
        {
            "zone": "Southwest Campus",
            "building": _or("yes", "residential", "dormitory"),
        },
    ),
    (
        "Housing / Special",
        {"building": "house"},
    ),
    (
        "Housing / Special",
        {"name": _includes("House")},
    ),
    (
        "Unknown / Feature",
        {"id": 422876654},
    ),  # Upper Picnic Area Modular Units
    ("Unknown / Building", {"name": _includes("Building in ")}),
    ("Academic", {"name": _includes("Bradley")}),
    ("Housing / On-Campus", {"zone": "The Hill"}),
    ("Academic", {"building": _or("university", "school", "college")}),
    ("Campus Services / Power Plant", {"power": "plant"}),
    ("Campus Services", {"building": "office"}),
    (
        "Unknown / Feature",
        {"id": _or(534392315, 243722217, 819656027, 733431549)},
    ),
    ("Unknown", {"name": _includes("Tent")}),
    (
        "Academic",
        {
            "id": _or(
                422876526, 422876627, 422876727, 331542, 422876593, 422876589
            )
        },
    ),  # Bradley, Public Affairs, Macgowan East, CHS, MacDonald MRL, Rosenfeld
    (
        "Unknown / Building",
        {"building": "yes", "zone": _includes("North", "Center", "South")},
    ),
    ("Housing / Off-Campus", {"building": "apartments"}),
    ("Unassigned", {}),
]


def determine_zone(centroid: Sequence[float], main_campus: bool) -> str:
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


def determine_category(tags: Dict[str, str]) -> str:
    """Return the category for a feature.

    This version organises the category logic into a sequence of rules rather
    than a long chain of conditionals.  Each rule encapsulates the criteria for
    identifying a category, making it easier to maintain and extend.
    """
    for cat, rule in CLASSIFICATION:
        for rule_tag, rule_target in rule.items():
            if rule_tag not in tags:
                break
            if callable(rule_target):
                if not rule_target(tags[rule_tag]):
                    break
            elif tags[rule_tag] != rule_target:
                break
        else:
            if cat == "Unassigned":
                # raise RuntimeError(f"{name} is unassigned")
                print(f"Warning: {tags["id"]} is unassigned")
            return cat
