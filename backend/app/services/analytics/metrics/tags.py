"""Dépenses par tag."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import InternalError
from app.core.logging import get_logger
from app.domain.metrics import tag_totals
from app.integrations.currency import get_exchange_rates
from app.repositories.analytics import metrics as repo
from app.repositories.analytics.common import ticket_restaurant_account_ids
from app.services.budget_period import period_bounds

logger = get_logger(__name__)


async def compute_tags(db: Session, month: int | None = None, year: int | None = None,
                       start_date: datetime | None = None, end_date: datetime | None = None,
                       account_id: int | None = None) -> list[dict]:
    try:
        start = start_date
        end = end_date or datetime.now()
        rates = await get_exchange_rates("EUR")
        if month and year and not start_date:
            start, end = period_bounds(db, year, month)
        tr_accounts = set() if account_id else ticket_restaurant_account_ids(db)
        return tag_totals(repo.tag_spending_rows(db, start, end, account_id, tr_accounts), rates)
    except Exception as e:
        logger.error(f"Error in tags_analytics: {e}")
        raise InternalError(str(e))
