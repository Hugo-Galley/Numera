from fastapi import APIRouter, Query, Response
from pydantic import BaseModel

from app.services.systeme import logos as service

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
    return service.search_logos(q, limit)


@router.post("/from-domain", response_model=LogoRef)
async def logo_from_domain(body: DomainIn) -> dict:
    return await service.logo_from_domain(body.domain)


@public_router.get("/img/{ref}")
def get_logo_image(ref: str) -> Response:
    content, media_type = service.get_logo_image(ref)
    headers = {"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"}
    return Response(content, media_type=media_type, headers=headers)
