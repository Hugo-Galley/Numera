from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.sync_bridge import run_async
from app.db.session import get_db
from app.schemas.insight import SubscriptionIgnore, SubscriptionsResponse
from app.services.analytics import subscriptions as service

router = APIRouter()


@router.get("/subscriptions", response_model=SubscriptionsResponse)
def get_subscriptions_analytics(
    account_id: int | None = Query(default=None),
    include_other: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    """Abonnements et charges fixes ; include_other ajoute les récurrences qui ne sont pas des sorties (hors totaux)."""
    return run_async(service.compute_subscriptions(db, account_id, include_other))


@router.post("/subscriptions/ignore")
def ignore_subscription_detection(
    data: SubscriptionIgnore,
    db: Session = Depends(get_db),
):
    """Exclut de la détection toutes les transactions de ce marchand à ce montant."""
    return service.ignore_subscription_detection(db, data)
