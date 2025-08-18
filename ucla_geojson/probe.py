import json
from typing import Any, Dict, List, Set, Tuple


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
