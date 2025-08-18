import json
import os
from typing import Any, Dict, List


def write_single(features: List[Dict[str, Any]]) -> None:
    print("Writing output files...")
    os.makedirs("public", exist_ok=True)
    fc = {"type": "FeatureCollection", "features": features}
    with open("public/campus.geojson", "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
    with open("public/attribution.txt", "w", encoding="utf-8") as f:
        f.write(
            "© OpenStreetMap contributors — Data: ODbL 1.0 (opendatacommons.org/licenses/odbl/)"
        )
