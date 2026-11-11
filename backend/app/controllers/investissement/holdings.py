
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.sync_bridge import run_async
from app.db.session import get_db
from app.schemas.holding import (
    ApplyCostsRequest,
    BaselineInventoryRequest,
    CostEstimateRead,
    PortfolioHoldingCreate,
    PortfolioHoldingRead,
    PortfolioHoldingUpdate,
)
from app.schemas.market import HoldingSuggestion
from app.services.investissement.holdings import inventory as service

router = APIRouter(prefix="/holdings", tags=["holdings"])


@router.get("", response_model=list[PortfolioHoldingRead])
def list_holdings(
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return run_async(service.list_holdings(db, account_id))


@router.get("/suggestions", response_model=list[HoldingSuggestion])
def get_holding_suggestions(
    account_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """
    Suggests holdings for the Point Zéro baseline by analyzing historical transaction notes.
    """
    return run_async(service.suggestions(db, account_id))


@router.get("/estimate-costs", response_model=list[CostEstimateRead])
def get_cost_estimates(account_id: int = Query(...), db: Session = Depends(get_db)):
    """
    PRU estimé de chaque ligne du Point Zéro, déduit des achats saisis avant sa date (moyenne pondérée,
    frais inclus). `coverage` = part de l'inventaire expliquée par ces achats : en dessous de 1, des titres
    détenus avant le premier achat saisi ne sont pas pris en compte. Aucune écriture.
    """
    return run_async(service.cost_estimates(db, account_id))


@router.post("/apply-costs", response_model=list[PortfolioHoldingRead])
def apply_costs(payload: ApplyCostsRequest, db: Session = Depends(get_db)):
    """Enregistre les PRU validés dans l'inventaire Point Zéro, puis recalcule les positions."""
    return run_async(service.apply_costs(db, payload))


@router.post("/baseline", response_model=list[PortfolioHoldingRead])
def set_baseline_inventory(
    payload: BaselineInventoryRequest,
    db: Session = Depends(get_db),
):
    """
    Point Zéro / état des lieux des positions d'un compte, à une date donnée (maintenant par défaut).
    Remplace l'inventaire ; les opérations sur titres postérieures à cette date sont rejouées par-dessus.
    """
    return run_async(service.set_baseline(db, payload))


@router.post("", response_model=PortfolioHoldingRead, status_code=201)
def create_holding(
    payload: PortfolioHoldingCreate,
    db: Session = Depends(get_db),
):
    """Ajoute une ligne à l'inventaire Point Zéro du compte, datée de maintenant."""
    return run_async(service.create_holding(db, payload))


@router.put("/{holding_id}", response_model=PortfolioHoldingRead)
def update_holding(
    holding_id: int,
    payload: PortfolioHoldingUpdate,
    db: Session = Depends(get_db),
):
    """
    Métadonnées (nom, ISIN, profil ETF) : modifiées directement.
    Quantité, PRU, devise : modifient la ligne d'inventaire Point Zéro du titre, puis les positions sont
    recalculées (impossible pour une position qui ne vient que d'opérations : modifier les opérations).
    """
    return run_async(service.update_holding(db, holding_id, payload))


@router.delete("/{holding_id}", status_code=204)
def delete_holding(holding_id: int, db: Session = Depends(get_db)):
    """Retire le titre de l'inventaire Point Zéro (refusé s'il reste des opérations sur ce titre)."""
    run_async(service.delete_holding(db, holding_id))
