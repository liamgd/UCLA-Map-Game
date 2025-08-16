from time import perf_counter

from .fetcher import fetch_osm_data
from .builder import process_features
from .writer import write_single


def main():
    print("Starting build_ucla_geojson...")
    start_time = perf_counter()

    data = timed("fetch_osm_data", fetch_osm_data)
    features = timed("process_features", process_features, data)
    timed("write_single", write_single, features)

    total_time = perf_counter() - start_time
    print(
        f"Done. Wrote {len(features)} features to public/campus.geojson in {total_time:.2f} seconds"
    )


def timed(label, func, *args, **kwargs):
    start = perf_counter()
    result = func(*args, **kwargs)
    duration = perf_counter() - start
    print(f"{label} took {duration:.2f} seconds")
    return result
