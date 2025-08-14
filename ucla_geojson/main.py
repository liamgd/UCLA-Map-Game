from .fetcher import fetch_osm_data
from .builder import process_features
from .writer import write_single


def main():
    print("Starting build_ucla_geojson...")
    data = fetch_osm_data()
    features = process_features(data)
    write_single(features)
    print(f"Done. Wrote {len(features)} features to public/campus.geojson")
