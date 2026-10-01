import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.etf_profile import EtfProfile
from app.schemas.etf_profile import EtfProfileCreate, EtfProfileRead, EtfProfileUpdate

router = APIRouter(prefix="/etf-profiles", tags=["etf-profiles"])


def _to_read_model(profile: EtfProfile) -> EtfProfileRead:
    return EtfProfileRead(
        id=profile.id,
        name=profile.name,
        ticker=profile.ticker,
        isin=profile.isin,
        aliases=json.loads(profile.aliases) if profile.aliases else [],
        countries=json.loads(profile.countries) if profile.countries else {},
        sectors=json.loads(profile.sectors) if profile.sectors else {},
        top_holdings=json.loads(profile.top_holdings) if profile.top_holdings else [],
        is_system=profile.is_system,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get("", response_model=List[EtfProfileRead])
def list_etf_profiles(db: Session = Depends(get_db)):
    profiles = db.query(EtfProfile).order_by(EtfProfile.is_system.desc(), EtfProfile.name.asc()).all()
    return [_to_read_model(p) for p in profiles]


@router.get("/{profile_id}", response_model=EtfProfileRead)
def get_etf_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(EtfProfile).filter(EtfProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="ETF profile not found")
    return _to_read_model(profile)


@router.post("", response_model=EtfProfileRead, status_code=201)
def create_etf_profile(payload: EtfProfileCreate, db: Session = Depends(get_db)):
    # Check if name or ticker already exists
    existing = db.query(EtfProfile).filter(
        (EtfProfile.ticker == payload.ticker.upper()) | (EtfProfile.name == payload.name)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="An ETF profile with this name or ticker already exists")

    profile = EtfProfile(
        name=payload.name,
        ticker=payload.ticker.upper(),
        isin=payload.isin.upper() if payload.isin else None,
        aliases=json.dumps(payload.aliases or [payload.ticker.upper()]),
        countries=json.dumps(payload.countries or {}),
        sectors=json.dumps(payload.sectors or {}),
        top_holdings=json.dumps([h.model_dump() for h in payload.top_holdings]),
        is_system=False,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _to_read_model(profile)


@router.put("/{profile_id}", response_model=EtfProfileRead)
def update_etf_profile(profile_id: int, payload: EtfProfileUpdate, db: Session = Depends(get_db)):
    profile = db.query(EtfProfile).filter(EtfProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="ETF profile not found")

    if payload.name is not None:
        profile.name = payload.name
    if payload.ticker is not None:
        profile.ticker = payload.ticker.upper()
    if payload.isin is not None:
        profile.isin = payload.isin.upper() if payload.isin else None
    if payload.aliases is not None:
        profile.aliases = json.dumps(payload.aliases)
    if payload.countries is not None:
        profile.countries = json.dumps(payload.countries)
    if payload.sectors is not None:
        profile.sectors = json.dumps(payload.sectors)
    if payload.top_holdings is not None:
        profile.top_holdings = json.dumps([h.model_dump() for h in payload.top_holdings])

    db.commit()
    db.refresh(profile)
    return _to_read_model(profile)


@router.delete("/{profile_id}", status_code=204)
def delete_etf_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.query(EtfProfile).filter(EtfProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="ETF profile not found")
    if profile.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system preset ETF profiles")

    db.delete(profile)
    db.commit()
