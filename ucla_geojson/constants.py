import pyproj

BBOX = (34.058, -118.465, 34.082, -118.433)  # (south, west, north, east)
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

BLACKLIST = {
    r"\bAxiom Apartments\b",
    r"\bMurdock Plaza\b",
}

# Approximate polygon coordinates (lon, lat) for campus zoning.  These are
# used to determine which major area of campus a feature belongs to.  The
# polygons were hand-drawn to more closely match the shape of UCLA's regions
# rather than relying on simple latitude/longitude thresholds.
ZONE_COORDS = {
    "The Hill": [
        (-118.4595, 34.0763),
        (-118.4595, 34.0685),
        (-118.4500, 34.0685),
        (-118.4500, 34.0763),
    ],
    "North Campus": [
        (-118.4500, 34.0763),
        (-118.4500, 34.0710),
        (-118.4400, 34.0710),
        (-118.4400, 34.0763),
    ],
    "South Campus": [
        (-118.4500, 34.0710),
        (-118.4500, 34.0610),
        (-118.4400, 34.0610),
        (-118.4400, 34.0710),
    ],
    "Westwood": [
        (-118.4400, 34.0750),
        (-118.4400, 34.0580),
        (-118.4330, 34.0580),
        (-118.4330, 34.0750),
    ],
}

