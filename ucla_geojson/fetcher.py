import asyncio
import json
import urllib.parse
import urllib.request
from typing import Dict, Iterable, List, Tuple

from .constants import BBOX_QUERY, GREEK_NAME_RE, OVERPASS_URL


BASE_LINES = [
    "[out:json][timeout:90];",
    "",
    'area["amenity"="university"]["name"~"^(University of California, Los Angeles|UCLA)$",i]->.ucla;',
]


def _tag_lines(tags: Iterable[str], location: str) -> List[str]:
    lines: List[str] = []
    for element in ("way", "relation"):
        for tag in tags:
            lines.append(f"{element}{tag}{location};")
    return lines


def _campus_lines() -> List[str]:
    tags = [
        '["building"]',
        '["shop"]',
        '["amenity"~"^(school|kindergarten)$"]',
        '["amenity"="parking"][!building]',
        '["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court|park|garden)$"]',
        '["landuse"~"^(grass|recreation_ground|forest|meadow|shrubland)$"]',
        '["natural"~"^(scrub|shrub|shrubland|wood|grassland)$"]',
    ]
    return _tag_lines(tags, "(area.ucla)")


def _ucla_related_lines() -> List[str]:
    tags = [
        '["building"]',
        '["shop"]',
        '["amenity"~"^(school|kindergarten)$"]',
        '["amenity"="parking"][!building]',
        '["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court|park|garden)$"]',
        '["landuse"~"^(grass|recreation_ground|forest|meadow|shrubland)$"]',
        '["natural"~"^(scrub|shrub|shrubland|wood|grassland)$"]',
    ]
    lines: List[str] = []
    for element in ("way", "relation"):
        for tag in tags:
            for attr in ("name", "operator"):
                lines.append(
                    f"{element}{tag}[\"{attr}\"~\"UCLA\",i]{BBOX_QUERY};"
                )
    return lines


def _greek_lines() -> List[str]:
    lines: List[str] = []
    values = ["fraternity", "sorority"]
    for element in ("way", "relation"):
        for val in values:
            lines.append(f"{element}[\"amenity\"=\"{val}\"]{BBOX_QUERY};")
            lines.append(f"{element}[\"building\"=\"{val}\"]{BBOX_QUERY};")
    for element in ("way", "relation"):
        for attr in ("name", "operator"):
            lines.append(
                f"{element}[\"building\"][\"{attr}\"~\"{GREEK_NAME_RE}\",i]{BBOX_QUERY};"
            )
    return lines


def _wrap(lines: Iterable[str], name: str) -> List[str]:
    return ["("] + list(lines) + [f")->.{name};"]


def _build_query() -> Tuple[str, Dict[str, str]]:
    sections = {
        "campus": _campus_lines(),
        "ucla_related": _ucla_related_lines(),
        "greek": _greek_lines(),
    }
    body: List[str] = []
    for name, lines in sections.items():
        body.extend(_wrap(lines, name))
    final_lines = (
        BASE_LINES
        + body
        + ["(.campus; .ucla_related; .greek; relation(7493269););", "out body; >; out skel qt;"]
    )
    single = "\n".join(final_lines)

    split_queries: Dict[str, str] = {}
    for name, lines in sections.items():
        tail = f"(.{name}; {'relation(7493269);' if name == 'campus' else ''});"
        q_lines = BASE_LINES + _wrap(lines, name) + [tail, "out body; >; out skel qt;"]
        split_queries[name] = "\n".join(q_lines)

    return single, split_queries


def _build_url(query: str) -> str:
    return f"{OVERPASS_URL}?{urllib.parse.urlencode({'data': query})}"


async def _fetch(query: str) -> Dict[str, object]:
    url = _build_url(query)

    def _read() -> Dict[str, object]:
        with urllib.request.urlopen(url) as resp:
            return json.load(resp)

    data = await asyncio.to_thread(_read)
    print(f"Fetched {len(data.get('elements', []))} elements")
    return data


async def fetch_osm_data_async(split: bool = True) -> Dict[str, object]:
    single_query, split_queries = _build_query()
    if not split:
        return await _fetch(single_query)

    tasks = [_fetch(q) for q in split_queries.values()]
    results = await asyncio.gather(*tasks)
    combined: Dict[str, object] = {"elements": []}
    seen = set()
    for data in results:
        for el in data.get("elements", []):
            key = (el.get("type"), el.get("id"))
            if key not in seen:
                combined["elements"].append(el)
                seen.add(key)
    print(f"Fetched {len(combined['elements'])} combined elements")
    return combined


def fetch_osm_data(split: bool = True) -> Dict[str, object]:
    return asyncio.run(fetch_osm_data_async(split=split))


__all__ = ["fetch_osm_data"]

