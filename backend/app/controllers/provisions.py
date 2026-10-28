from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import provisions as prov
from app.db.session import get_db
from app.models.account import Account
from app.models.category import Category
from app.models.provision import Provision
from app.schemas.provision import ProvisionCreate, ProvisionRead, ProvisionSummary, ProvisionUpdate

router = APIRouter(prefix="/provisions", tags=["provisions"])


def _check_refs(db: Session, category_id: int | None, account_id: int | None) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    if account_id is not None and db.get(Account, account_id) is None:
        raise HTTPException(status_code=404, detail="Compte introuvable")


async def _read(db: Session, provision: Provision) -> dict:
    return prov.to_read((await prov.compute_states(db, [provision]))[0])


@router.get("", response_model=list[ProvisionRead])
async def list_provisions(db: Session = Depends(get_db)):
    provisions = db.query(Provision).order_by(Provision.active.desc(), Provision.name.asc()).all()
    states = await prov.compute_states(db, provisions)
    return [prov.to_read(st) for st in sorted(states, key=lambda st: (not st.provision.active, st.next_due))]


@router.get("/summary", response_model=ProvisionSummary)
async def provisions_summary(db: Session = Depends(get_db)):
    return await prov.summary(db)


@router.post("", response_model=ProvisionRead, status_code=201)
async def create_provision(payload: ProvisionCreate, db: Session = Depends(get_db)):
    _check_refs(db, payload.category_id, payload.account_id)
    provision = Provision(**payload.model_dump())
    db.add(provision)
    db.commit()
    db.refresh(provision)
    return await _read(db, provision)


@router.patch("/{provision_id}", response_model=ProvisionRead)
async def update_provision(provision_id: int, payload: ProvisionUpdate, db: Session = Depends(get_db)):
    provision = db.get(Provision, provision_id)
    if provision is None:
        raise HTTPException(status_code=404, detail="Provision introuvable")
    data = payload.model_dump(exclude_unset=True)
    _check_refs(db, data.get("category_id"), data.get("account_id"))
    for field in ("name", "amount", "interval_months", "due_date", "active"):
        if field in data and data[field] is None:
            data.pop(field)  # colonnes non nullables : `null` = ne pas modifier
    for field, value in data.items():
        setattr(provision, field, value)
    db.commit()
    db.refresh(provision)
    return await _read(db, provision)


@router.delete("/{provision_id}", status_code=204)
def delete_provision(provision_id: int, db: Session = Depends(get_db)):
    provision = db.get(Provision, provision_id)
    if provision is None:
        raise HTTPException(status_code=404, detail="Provision introuvable")
    db.delete(provision)
    db.commit()
