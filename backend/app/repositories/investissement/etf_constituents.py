"""Lignes de composition des ETF (`etf_constituents`), écrites et lues en masse."""
from collections.abc import Iterable, Sequence
from typing import cast

from sqlalchemy import Table, delete, insert
from sqlalchemy.orm import Session

from app.domain.etf_composition import EtfConstituentRow, EtfLine
from app.models.etf_constituent import EtfConstituent


def replace(db: Session, profile_id: int, lines: Sequence[EtfLine]) -> None:
    """Remplace les lignes d'un profil (un `DELETE`, un `INSERT` groupé). Pas de commit."""
    db.execute(delete(EtfConstituent).where(EtfConstituent.profile_id == profile_id))
    if lines:
        # Table Core (et non l'ORM, qui éclaterait le lot selon les colonnes à NULL) ; `__table__` est typé trop large
        db.execute(insert(cast(Table, EtfConstituent.__table__)), [
            {"profile_id": profile_id, **{field: getattr(line, field) for field in EtfConstituentRow._fields}}
            for line in lines
        ])


def for_profiles(db: Session, ids: Iterable[int]) -> dict[int, list[EtfConstituentRow]]:
    """Lignes des profils demandés, en une requête et sans objet ORM ; un profil sans ligne est absent."""
    wanted = list(set(ids))
    if not wanted:
        return {}
    columns = [getattr(EtfConstituent, field) for field in EtfConstituentRow._fields]
    result: dict[int, list[EtfConstituentRow]] = {}
    query = db.query(EtfConstituent.profile_id, *columns).filter(EtfConstituent.profile_id.in_(wanted))
    for profile_id, *values in query.order_by(EtfConstituent.id):
        result.setdefault(profile_id, []).append(EtfConstituentRow(*values))
    return result
