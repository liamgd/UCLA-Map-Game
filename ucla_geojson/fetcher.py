import json
import urllib.parse
import urllib.request

from .constants import BBOX_QUERY, GREEK_NAME_RE, OVERPASS_URL


def fetch_osm_data():
    query = f"""
[out:json][timeout:90];

// Get UCLA campus area(s)
area["amenity"="university"]["name"~"^(University of California, Los Angeles|UCLA)$",i]->.ucla;

// Get buildings, shops, and recreational areas inside UCLA campus
(
  way["building"](area.ucla);
  relation["building"](area.ucla);
  way["shop"](area.ucla);
  relation["shop"](area.ucla);
  way["amenity"="parking"][!building](area.ucla);
  relation["amenity"="parking"][!building](area.ucla);
  way["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court|park|garden)$"](area.ucla);
  relation["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court|park|garden)$"](area.ucla);
    way["landuse"~"^(grass|recreation_ground|forest|meadow|shrubland)$"](area.ucla);
    relation["landuse"~"^(grass|recreation_ground|forest|meadow|shrubland)$"](area.ucla);
    way["natural"~"^(scrub|shrub|shrubland|wood|grassland)$"](area.ucla);
    relation["natural"~"^(scrub|shrub|shrubland|wood|grassland)$"](area.ucla);
)->.campus;

// Also get *any* building, shop, or recreational area with name/operator containing UCLA in bbox
(
  way["building"]["name"~"UCLA",i]{BBOX_QUERY};
  way["building"]["operator"~"UCLA",i]{BBOX_QUERY};
  relation["building"]["name"~"UCLA",i]{BBOX_QUERY};
  relation["building"]["operator"~"UCLA",i]{BBOX_QUERY};
  way["shop"]["name"~"UCLA",i]{BBOX_QUERY};
  way["shop"]["operator"~"UCLA",i]{BBOX_QUERY};
  relation["shop"]["name"~"UCLA",i]{BBOX_QUERY};
  relation["shop"]["operator"~"UCLA",i]{BBOX_QUERY};
  way["amenity"="parking"][!building]["name"~"UCLA",i]{BBOX_QUERY};
  way["amenity"="parking"][!building]["operator"~"UCLA",i]{BBOX_QUERY};
  relation["amenity"="parking"][!building]["name"~"UCLA",i]{BBOX_QUERY};
  relation["amenity"="parking"][!building]["operator"~"UCLA",i]{BBOX_QUERY};
  way["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court|park|garden)$"]["name"~"UCLA",i]{BBOX_QUERY};
  way["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court|park|garden)$"]["operator"~"UCLA",i]{BBOX_QUERY};
  relation["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court|park|garden)$"]["name"~"UCLA",i]{BBOX_QUERY};
  relation["leisure"~"^(stadium|sports_centre|pitch|swimming_pool|track|tennis_court|park|garden)$"]["operator"~"UCLA",i]{BBOX_QUERY};
    way["landuse"~"^(grass|recreation_ground|forest|meadow|shrubland)$"]["name"~"UCLA",i]{BBOX_QUERY};
    way["landuse"~"^(grass|recreation_ground|forest|meadow|shrubland)$"]["operator"~"UCLA",i]{BBOX_QUERY};
    relation["landuse"~"^(grass|recreation_ground|forest|meadow|shrubland)$"]["name"~"UCLA",i]{BBOX_QUERY};
    relation["landuse"~"^(grass|recreation_ground|forest|meadow|shrubland)$"]["operator"~"UCLA",i]{BBOX_QUERY};
    way["natural"~"^(scrub|shrub|shrubland|wood|grassland)$"]["name"~"UCLA",i]{BBOX_QUERY};
    way["natural"~"^(scrub|shrub|shrubland|wood|grassland)$"]["operator"~"UCLA",i]{BBOX_QUERY};
    relation["natural"~"^(scrub|shrub|shrubland|wood|grassland)$"]["name"~"UCLA",i]{BBOX_QUERY};
    relation["natural"~"^(scrub|shrub|shrubland|wood|grassland)$"]["operator"~"UCLA",i]{BBOX_QUERY};
)->.ucla_related;

// Get fraternities and sororities in the bounding box (many are just building=yes with Greek names)
(
  way["amenity"="fraternity"]{BBOX_QUERY};
  way["amenity"="sorority"]{BBOX_QUERY};
  way["building"="fraternity"]{BBOX_QUERY};
  way["building"="sorority"]{BBOX_QUERY};

  relation["amenity"="fraternity"]{BBOX_QUERY};
  relation["amenity"="sorority"]{BBOX_QUERY};
  relation["building"="fraternity"]{BBOX_QUERY};
  relation["building"="sorority"]{BBOX_QUERY};

  way["building"]["name"~"{GREEK_NAME_RE}",i]{BBOX_QUERY};
  way["building"]["operator"~"{GREEK_NAME_RE}",i]{BBOX_QUERY};
  relation["building"]["name"~"{GREEK_NAME_RE}",i]{BBOX_QUERY};
  relation["building"]["operator"~"{GREEK_NAME_RE}",i]{BBOX_QUERY};
)->.greek;

// Combine
(.campus; .ucla_related; .greek;);
out body; >; out skel qt;
"""
    url = f"{OVERPASS_URL}?{urllib.parse.urlencode({'data': query})}"
    with urllib.request.urlopen(url) as resp:
        data = json.load(resp)
    print(f"Fetched {len(data.get('elements', []))} elements")
    return data
