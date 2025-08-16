import json


def open_campus():
    with open("public/campus.geojson", "r") as f:
        campus = json.load(f)["features"]
        return campus


def probe_duplicate_centroids():
    campus = open_campus()
    centroids_found = set()
    duplicate_centroids = set()

    for feature in campus:
        props = feature["properties"]
        centroid = tuple(props["centroid"])
        if centroid in centroids_found:
            duplicate_centroids.add(centroid)
        centroids_found.add(centroid)

    for feature in campus:
        props = feature["properties"]
        centroid = tuple(props["centroid"])
        if centroid in duplicate_centroids:
            print(props["centroid"], props["name"])


def feature_type_tree():
    campus = open_campus()
    categories = set()

    for feature in campus:
        props = feature["properties"]
        categories.add(props["category"])

    print(*sorted(categories), sep="\n")


def probe_names_categories():
    campus = open_campus()
    names_categories = {
        feature["properties"]["name"]: feature["properties"]["category"]
        for feature in campus
    }
    categories_dups = list(names_categories.values())
    categories = iter(set(names_categories.values()))
    category_counts = {
        category: categories_dups.count(category) for category in categories
    }
    print(category_counts)
    with open("probe/names_categories.json", "w", encoding="utf-8") as f:
        json.dump(names_categories, f, ensure_ascii=False, indent=2)
