import pyproj
from typing import Callable, Set, Tuple

BBOX: Tuple[float, float, float, float] = (
    34.058,
    -118.465,
    34.082,
    -118.433,
)  # (south, west, north, east)
BBOX_QUERY: str = f"({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]})"
OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
SINGLE_TOLERANCE_M: float = 0.4  # meters detail for BOTH draw and hit
EXCLUDE_BUILDINGS: Set[str] = {"hut", "shed", "garage", "kiosk", "tent", "container"}
MIN_AREA_UNNAMED: int = 80  # m²
MIN_AREA_EXCLUDE: int = 120  # m²

_TO_M: Callable[[float, float], Tuple[float, float]] = pyproj.Transformer.from_crs(
    "EPSG:4326", "EPSG:3310", always_xy=True
).transform
_TO_DEG: Callable[[float, float], Tuple[float, float]] = pyproj.Transformer.from_crs(
    "EPSG:3310", "EPSG:4326", always_xy=True
).transform

GREEK_NAME_RE: str = (
    r"(fraternity|sorority|alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|"
    r"lambda|mu|nu|xi|omicron|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega)"
)

BLACKLIST: Set[str] = {
    r"\bAxiom Apartments\b",
    r"\bMurdock Plaza\b",
}
