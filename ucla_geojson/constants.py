import pyproj

BBOX = (34.058, -118.456, 34.082, -118.433)  # (south, west, north, east)
BBOX_QUERY = f"({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]})"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
SINGLE_TOLERANCE_M = 0.4  # meters detail for BOTH draw and hit
EXCLUDE_BUILDINGS = {"hut", "shed", "garage", "kiosk", "tent", "container"}
MIN_AREA_UNNAMED = 80  # m²
MIN_AREA_EXCLUDE = 120  # m²

_TO_M = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3310", always_xy=True).transform
_TO_DEG = pyproj.Transformer.from_crs("EPSG:3310", "EPSG:4326", always_xy=True).transform

GREEK_NAME_RE = (
    r"(fraternity|sorority|alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|"
    r"lambda|mu|nu|xi|omicron|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega)"
)

IMPORTANT_OFF_CAMPUS = {
    # substrings -> category
    "hammer museum": "Museum",
    "geffen playhouse": "Playhouse",
    "ronald reagan ucla medical center": "Hospital",
    "ucla health westwood": "Clinic/Health",
    "marina aquatics center": "Boathouse",
}

BLACKLIST = {
    r"\bAxiom Apartments\b",
    r"\bMurdock Plaza\b",
}
