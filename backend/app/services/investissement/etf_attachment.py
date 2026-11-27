"""Applique `domain/etf_attachment.py` : chaque position est décrite par le profil de son propre fonds."""
import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.etf_attachment import HoldingRef, ProfileRef, plan_attachments
from app.repositories.investissement import etf_profiles as profiles_repo
from app.repositories.investissement import holdings as holdings_repo

logger = get_logger(__name__)


def _aliases(raw: str | None) -> list[str]:
    try:
        values = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    return [str(v) for v in values] if isinstance(values, list) else []


def _new_profile(name: str, ticker: str, isin: str) -> dict[str, Any]:
    """Profil vide : sa composition sera lue au prochain passage."""
    return {"name": name, "ticker": ticker, "isin": isin, "aliases": json.dumps([ticker, isin]), "countries": "{}",
            "sectors": "{}", "top_holdings": "[]", "composition_sources": "{}", "is_system": False}


def attach_to_own_profiles(db: Session, *, commit: bool = True) -> int:
    """Renvoie le nombre de positions modifiées ; nombre de requêtes constant. `commit=False` : flush seulement."""
    db.flush()
    rows = holdings_repo.attachment_rows(db)
    plan = plan_attachments(
        [HoldingRef(i, ticker, isin, profile_id) for i, ticker, isin, profile_id, _ in rows],
        [ProfileRef(i, ticker, isin, _aliases(aliases), is_system)
         for i, ticker, isin, aliases, is_system in profiles_repo.attachment_rows(db)])
    targets: dict[int, int | None] = {**plan.moves, **dict.fromkeys(plan.detach)}
    if plan.create_isins:
        # La première position de chaque ISIN donne son nom et son ticker au profil
        first: dict[str, tuple[str, str]] = {}
        for holding_id, ticker, _, _, name in rows:
            if holding_id in plan.pending:
                first.setdefault(plan.pending[holding_id], (name, ticker))
        profiles_repo.insert_many(db, [_new_profile(name, ticker, isin) for isin, (name, ticker) in first.items()])
        created = profiles_repo.ids_by_isin(db, plan.create_isins)
        targets.update({holding_id: created[isin] for holding_id, isin in plan.pending.items()})
    if not targets:
        return 0
    holdings_repo.set_etf_profiles(db, targets)
    if commit:
        db.commit()
    logger.info(f"{len(targets)} position(s) rattachée(s) au profil de leur fonds, "
                f"{len(plan.create_isins)} profil(s) créé(s)")
    return len(targets)
