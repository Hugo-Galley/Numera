"""Logos de marques : catalogue Simple Icons embarqué (CC0) + favicons mis en cache localement."""
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ICONS_FILE = Path(__file__).resolve().parent.parent / "assets" / "simple_icons" / "icons.json"
LOGOS_DIR = Path(settings.logos_dir)

SI_REF_RE = re.compile(r"^si:([a-z0-9]{1,60})$")
FILE_REF_RE = re.compile(r"^file:([0-9a-f]{16}\.png)$")
DOMAIN_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")
FAVICON_URL = "https://www.google.com/s2/favicons"
MAX_FAVICON_BYTES = 200_000


class LogoError(Exception):
    pass


@lru_cache(maxsize=1)
def _icons() -> dict[str, dict]:
    with open(ICONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def search_icons(query: str, limit: int = 8) -> list[dict]:
    q = _norm(query)
    if not q:
        return []
    exact: list[dict] = []
    prefix: list[dict] = []
    contains: list[dict] = []
    for slug, ic in _icons().items():
        names = [_norm(ic["t"]), slug, *(_norm(a) for a in ic.get("a", []))]
        bucket = None
        if q in names:
            bucket = exact
        elif any(n.startswith(q) for n in names):
            bucket = prefix
        elif any(q in n for n in names):
            bucket = contains
        if bucket is not None:
            bucket.append({"ref": f"si:{slug}", "title": ic["t"], "hex": ic["h"]})
    prefix.sort(key=lambda r: len(r["title"]))
    contains.sort(key=lambda r: len(r["title"]))
    return (exact + prefix + contains)[:limit]


def simple_icon_svg(slug: str) -> str | None:
    ic = _icons().get(slug)
    if not ic:
        return None
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" role="img">'
        f'<title>{ic["t"].replace("&", "&amp;").replace("<", "&lt;")}</title>'
        f'<path fill="#{ic["h"]}" d="{ic["p"]}"/></svg>'
    )


def normalize_domain(raw: str) -> str:
    d = raw.strip().lower()
    d = re.sub(r"^[a-z][a-z0-9+.-]*://", "", d)
    d = re.split(r"[/?#]", d, maxsplit=1)[0]
    if d.startswith("www."):
        d = d[4:]
    if not DOMAIN_RE.match(d):
        raise ValueError("invalid domain")
    return d


def favicon_path(ref: str) -> Path | None:
    m = FILE_REF_RE.match(ref)
    return LOGOS_DIR / m.group(1) if m else None


async def fetch_favicon_ref(domain: str) -> str:
    """Télécharge (une seule fois) le favicon du domaine et renvoie sa référence `file:<hash>.png`."""
    name = hashlib.sha256(domain.encode()).hexdigest()[:16] + ".png"
    ref = f"file:{name}"
    path = LOGOS_DIR / name
    if path.exists():
        return ref
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            res = await client.get(FAVICON_URL, params={"domain": domain, "sz": 64})
    except httpx.HTTPError as exc:
        logger.warning("favicon fetch failed for %s: %s", domain, exc)
        raise LogoError("favicon service unreachable") from exc
    ctype = res.headers.get("content-type", "")
    if res.status_code != 200 or not ctype.startswith("image/") or not res.content or len(res.content) > MAX_FAVICON_BYTES:
        raise LogoError("no logo found for this domain")
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(res.content)
    return ref
