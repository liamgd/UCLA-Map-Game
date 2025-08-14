import json

with open("public/campus.geojson", "r") as f:
    campus = json.load(f)["features"]
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
