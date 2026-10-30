from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.etf_profile import AutoDecomposeRequest, EtfProfileCreate, EtfProfileRead, EtfProfileUpdate, EtfRefreshResult
from app.services.investissement import etf_profiles as service

router = APIRouter(prefix="/etf-profiles", tags=["etf-profiles"])


@router.get("", response_model=List[EtfProfileRead])
def list_etf_profiles(db: Session = Depends(get_db)):
    return service.list_profiles(db)


@router.post("/refresh-held", response_model=EtfRefreshResult)
async def refresh_held_profiles(db: Session = Depends(get_db)):
    """Actualise depuis Yahoo la composition de tous les profils rattachés à une position détenue."""
    refreshed = await service.refresh_held_etf_profiles(db, force=True)
    return EtfRefreshResult(refreshed=refreshed)


@router.get("/{profile_id}", response_model=EtfProfileRead)
def get_etf_profile(profile_id: int, db: Session = Depends(get_db)):
    return service.get_profile(db, profile_id)


@router.post("", response_model=EtfProfileRead, status_code=201)
def create_etf_profile(payload: EtfProfileCreate, db: Session = Depends(get_db)):
    return service.create_profile(db, payload)


@router.put("/{profile_id}", response_model=EtfProfileRead)
def update_etf_profile(profile_id: int, payload: EtfProfileUpdate, db: Session = Depends(get_db)):
    return service.update_profile(db, profile_id, payload)


@router.delete("/{profile_id}", status_code=204)
def delete_etf_profile(profile_id: int, db: Session = Depends(get_db)):
    service.delete_profile(db, profile_id)


@router.post("/{profile_id}/refresh", response_model=EtfProfileRead)
async def refresh_profile(profile_id: int, db: Session = Depends(get_db)):
    """Actualise la composition d'un profil depuis Yahoo (secteurs et top 10 ; jamais les pays)."""
    return await service.refresh_profile(db, profile_id)


@router.post("/auto-decompose", response_model=EtfProfileRead)
async def auto_decompose_profile(payload: AutoDecomposeRequest, db: Session = Depends(get_db)):
    """
    Crée le profil d'un ETF ou fonds inconnu à partir de la composition publiée par Yahoo
    (secteurs et top 10 ; la répartition par pays reste vide).
    """
    return await service.auto_decompose(db, payload)
