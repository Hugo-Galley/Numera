"""Logos de comptes : recherche d'icônes Simple Icons, favicon d'un domaine, lecture d'une image."""
from app.core.errors import BusinessRuleError, NotFoundError
from app.integrations import logos


def search_logos(q: str, limit: int) -> list[dict]:
    return logos.search_icons(q, limit)


async def logo_from_domain(domain: str) -> dict:
    try:
        normalized = logos.normalize_domain(domain)
    except ValueError:
        raise BusinessRuleError("Invalid domain")
    try:
        return {"ref": await logos.fetch_favicon_ref(normalized)}
    except logos.LogoError as exc:
        raise NotFoundError(str(exc))


def get_logo_image(ref: str) -> tuple[bytes | str, str]:
    """(contenu, type MIME) d'un logo : icône Simple Icons (SVG) ou favicon téléchargé (PNG)."""
    m = logos.SI_REF_RE.match(ref)
    if m:
        svg = logos.simple_icon_svg(m.group(1))
        if svg:
            return svg, "image/svg+xml"
    path = logos.favicon_path(ref)
    if path and path.is_file():
        return path.read_bytes(), "image/png"
    raise NotFoundError("Logo not found")
