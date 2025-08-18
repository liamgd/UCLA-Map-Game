import hashlib
import re


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug


def hash_centroid(centroid):
    s = f"{centroid[0]:.5f},{centroid[1]:.5f}"
    return hashlib.md5(s.encode()).hexdigest()[:6]


def shorten(text, tail=10):
    return f"{text[:tail]}...{text[:-tail]}"
