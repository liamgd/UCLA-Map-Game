import json
from typing import Any, Dict, List, Set, Tuple

from .fetcher import fetch_osm_data


def open_campus() -> List[Dict[str, Any]]:
    with open("public/campus.geojson", "r") as f:
        campus: List[Dict[str, Any]] = json.load(f)["features"]
        return campus


def probe_duplicate_centroids() -> None:
    campus = open_campus()
    centroids_found: Set[Tuple[float, float]] = set()
    duplicate_centroids: Set[Tuple[float, float]] = set()

    for feature in campus:
        props = feature["properties"]
        centroid: Tuple[float, float] = tuple(props["centroid"])
        if centroid in centroids_found:
            duplicate_centroids.add(centroid)
        centroids_found.add(centroid)

    for feature in campus:
        props = feature["properties"]
        centroid: Tuple[float, float] = tuple(props["centroid"])
        if centroid in duplicate_centroids:
            print(props["centroid"], props["name"])


def feature_type_tree() -> None:
    campus = open_campus()
    categories: Set[str] = set()

    for feature in campus:
        props = feature["properties"]
        categories.add(props["category"])

    print(*sorted(categories), sep="\n")


def probe_names_categories() -> None:
    campus = open_campus()
    names_categories: Dict[str, str] = {
        feature["properties"]["name"]: feature["properties"]["category"]
        for feature in campus
    }
    categories_dups = list(names_categories.values())
    categories = iter(set(names_categories.values()))
    category_counts: Dict[str, int] = {
        category: categories_dups.count(category) for category in categories
    }
    print(category_counts)
    with open("probe/names_categories.json", "w", encoding="utf-8") as f:
        json.dump(names_categories, f, ensure_ascii=False, indent=2)


def probe_info() -> None:
    data = fetch_osm_data()
    campus = open_campus()

    info = {}
    found_count = {}
    for x in range(len(data["elements"])):
        element = data["elements"][x]
        if element["type"] == "node":
            continue

        name = ""
        for feature in campus:
            props = feature["properties"]
            if props["osm_ids"][0].endswith(str(element["id"])):
                if props["name"] in found_count:
                    found_count[props["name"]] += 1
                    name = props["name"] + f" {found_count[props["name"]]}"
                else:
                    found_count[props["name"]] = 1
                    name = props["name"]
                zone = props["zone"]
                break
        if name == "":
            continue

        tags = element.get("tags") or {}

        info[name] = tags.copy()
        info[name]["zone"] = zone
        info[name]["id"] = element["id"]
        if element["type"] == "relation":
            info[name]["type"] = "multipolygon relation"
        if "name" in info[name]:
            del info[name]["name"]
        info[name]["category"] = ""

    with open("probe/info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    names = "\n".join(info.keys()) + "\n"
    with open("probe/names.txt", "w", encoding="utf-8") as f:
        f.write(names)


def transpose_verified_categories() -> None:
    with open("verified_categories.json", "r") as f:
        verified_categories = json.load(f)

    by_category: Dict[List[Dict]] = {}
    for name, tags in verified_categories.items():
        cat = tags.pop("category")
        if cat in by_category:
            by_category[cat][name] = tags
        else:
            by_category[cat] = {name: tags}

    # print(
    #     *(f"{cat}: {len(features)}" for cat, features in by_category.items()),
    #     sep="\n",
    # )

    with open("verified_categories_T.json", "w", encoding="utf-8") as f:
        json.dump(by_category, f, ensure_ascii=False, indent=2)


def C_includes(*args):
    return lambda x: any(arg in x for arg in args)


def C_or(*args):
    return lambda x: x in args


CLASSIFICATION = [
    (
        "Mistake (Delete)",
        {"name": C_includes("Feature in Dickson", "Unnamed College")},
    ),
    ("Student Services / Auditorium", {"building": "auditorium"}),
    (
        "Campus Services",
        {
            "name": C_includes(
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
        {"name": C_includes("Krieger", "Fernald")},
    ),
    ("UCLA Extension", {"name": C_includes("UCLA Extension")}),
    ("UCLA Extension", {"id": 184772366}),
    ("Unknown / Roof", {"building": "roof"}),
    ("Green Space / Forest", {"natural": C_or("shrubland", "wood")}),
    ("Student Services / Makerspace", {"leisure": "hackerspace"}),
    ("Athletics / Kickball Court", {"sport": "kickball"}),
    ("Student Services / Museum", {"tourism": "museum"}),
    ("Student Services / Dining", {"amenity": "food_court"}),
    ("Athletics / Sports Area", {"id": C_or(422876728, 422876720)}),
    ("Athletics / Archery Field", {"sport": "archery"}),
    ("Athletics / Grandstand", {"building": "grandstand"}),
    ("Athletics / Basketball Court", {"sport": "basketball"}),
    ("Athletics / Football Field", {"sport": "american_football"}),
    ("Athletics / Tennis Court", {"leisure": "pitch", "sport": "tennis"}),
    (
        "Athletics / Soccer Field",
        {"leisure": "pitch", "sport": C_includes("soccer")},
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
        {"amenity": "parking", "name": C_includes("Structure")},
    ),
    ("Parking / Lot", {"amenity": "parking", "parking": "surface"}),
    ("Parking / Structure", {"amenity": "parking"}),
    ("Athletics / Stadium", {"leisure": "stadium"}),
    ("Student Services / Library", {"amenity": "library"}),
    (
        "Healthcare",
        {"healthcare": C_or("clinic", "hospital", "blood_donation")},
    ),
    (
        "Healthcare",
        {"id": C_or(46364638, 49832949, 422876610, 422876569)},
    ),  # Gonda + clinics
    ("Research Institute", {"amenity": "research_institute"}),
    (
        "Research Institute",
        {"id": C_or(13007994, 53334145, 422876595)},
    ),  # CNSI + STRB
    (
        "Pre-University Education",
        {"name": C_includes("UCLA Lab School", "Academy")},
    ),
    ("Student Services / Retail", {"building": "retail"}),
    (
        "Student Services / Retail",
        {"name": C_includes("Union")},
    ),
    (
        "Athletics / Sports Area",
        {"id": C_or(590016847, 422876683, 422876709, 422876613)},
    ),  # Wasserman, LATC bldg, Wallis bldg, Park Pool Locker Rooms
    ("Athletics / Sports Area", {"name": C_includes("Sunset Canyon")}),
    ("Athletics / Sports Area", {"name": C_includes("Pool")}),
    ("Housing / Sorority", {"building:use": "sorority"}),
    ("Housing / Sorority", {"id": 422298411}),
    ("Housing / Fraternity", {"building:use": "fraternity"}),
    (
        "Housing / Fraternity",
        {"name": C_includes("Fraternity", "Alpha Tau Omega")},
    ),
    (
        "Athletics / Gym Center",
        {"leisure": "fitness_centre"},
    ),
    (
        "Athletics / Gym Center",
        {"id": C_or(422876520, 422876656)},
    ),  # Acosta, Wooden
    (
        "Housing / Off-Campus",
        {
            "zone": "Southwest Campus",
            "building": C_or("yes", "residential", "dormitory"),
        },
    ),
    (
        "Housing / Special",
        {"building": "house"},
    ),
    (
        "Housing / Special",
        {"name": C_includes("House")},
    ),
    (
        "Unknown / Feature",
        {"id": 422876654},
    ),  # Upper Picnic Area Modular Units
    ("Unknown / Building", {"name": C_includes("Building in ")}),
    ("Academic", {"name": C_includes("Bradley")}),
    ("Housing / On-Campus", {"zone": "The Hill"}),
    ("Academic", {"building": C_or("university", "school", "college")}),
    ("Campus Services / Power Plant", {"power": "plant"}),
    ("Campus Services", {"building": "office"}),
    ("Unknown / Feature", {"name": C_includes("Feature in Drake Stadium")}),
    ("Unknown", {"name": C_includes("Tent")}),
    (
        "Academic",
        {
            "id": C_or(
                422876526, 422876627, 422876727, 331542, 422876593, 422876589
            )
        },
    ),  # Bradley, Public Affairs, Macgowan East, CHS, MacDonald MRL, Rosenfeld
    (
        "Unknown / Building",
        {"building": "yes", "zone": C_includes("North", "Center", "South")},
    ),
    ("Housing / Off-Campus", {"building": "apartments"}),
    ("Unassigned", {}),
]


def new_classification() -> None:
    with open("verified_categories.json", "r") as f:
        verified_categories = json.load(f)

    correct = 0
    incorrect = 0
    unassigned = 0
    for name, feature_tags in verified_categories.items():
        for cat, rule in CLASSIFICATION:
            for rule_tag, rule_target in rule.items():
                if rule_tag not in feature_tags:
                    break
                if callable(rule_target):
                    if not rule_target(feature_tags[rule_tag]):
                        break
                elif feature_tags[rule_tag] != rule_target:
                    break
            else:
                feature_tags["calculated_category"] = cat
                if cat == feature_tags["category"]:
                    correct += 1
                elif cat == "Unassigned":
                    unassigned += 1
                    print(
                        f"{name} is {feature_tags["category"]} but is unassigned"
                    )
                else:
                    incorrect += 1
                    print(
                        f"{name} is {feature_tags["category"]} but calculated {cat}"
                    )
                break

    print(f"{correct} correct")
    print(f"{incorrect} incorrect")
    print(f"{unassigned} unassigned")

    with open("calculated_categories.json", "w", encoding="utf-8") as f:
        json.dump(verified_categories, f, ensure_ascii=False, indent=2)
