from time import perf_counter
from typing import Any, Callable, TypeVar

from .builder import process_features
from .fetcher import fetch_osm_data
from .writer import write_single


T = TypeVar("T")


def main() -> None:
    print("Starting build_ucla_geojson...")
    start_time = perf_counter()

    data = timed("fetch_osm_data", fetch_osm_data, split=True)
    features = timed("process_features", process_features, data)
    timed("write_single", write_single, features)

    total_time = perf_counter() - start_time
    print(
        f"Done. Wrote {len(features)} features to public/campus.geojson in {total_time:.2f} total seconds"
    )


def timed(label: str, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    start = perf_counter()
    result = func(*args, **kwargs)
    duration = perf_counter() - start
    print(f"({label} took {duration:.2f} seconds)")
    return result
