from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from app.core import logos

router = APIRouter(prefix="/logos", tags=["logos"])
public_router = APIRouter(prefix="/logos", tags=["logos"])


class LogoSuggestion(BaseModel):
    ref: str
    title: str
    hex: str


class DomainIn(BaseModel):
    domain: str


class LogoRef(BaseModel):
    ref: str


@router.get("/search", response_model=list[LogoSuggestion])
def search_logos(q: str = Query("", max_length=60), limit: int = Query(8, ge=1, le=20)) -> list[dict]:
    return logos.search_icons(q, limit)


@router.post("/from-domain", response_model=LogoRef)
async def logo_from_domain(body: DomainIn) -> dict:
    try:
        domain = logos.normalize_domain(body.domain)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid domain")
    try:
        return {"ref": await logos.fetch_favicon_ref(domain)}
    except logos.LogoError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@public_router.get("/img/{ref}")
def get_logo_image(ref: str) -> Response:
    headers = {"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"}
    m = logos.SI_REF_RE.match(ref)
    if m:
        svg = logos.simple_icon_svg(m.group(1))
        if svg:
            return Response(svg, media_type="image/svg+xml", headers=headers)
    path = logos.favicon_path(ref)
    if path and path.is_file():
        return Response(path.read_bytes(), media_type="image/png", headers=headers)
    raise HTTPException(status_code=404, detail="Logo not found")
