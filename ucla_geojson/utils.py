import hashlib
import re
from typing import Tuple


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug


def hash_centroid(centroid: Tuple[float, float]) -> str:
    s = f"{centroid[0]:.5f},{centroid[1]:.5f}"
    return hashlib.md5(s.encode()).hexdigest()[:6]


def shorten(text: str, tail: int = 10) -> str:
    return f"{text[:tail]}...{text[:-tail]}"
