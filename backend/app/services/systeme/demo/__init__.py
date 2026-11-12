"""Instance de démonstration : données fictives, régénérées chaque jour.

Activé par `DEMO_MODE=true` (la configuration exige alors une base dont le nom contient « demo »).
Au démarrage puis à chaque passage de la tâche de fond, `ensure_demo_data` efface la base et la régénère
si elle date d'un autre jour : chaque visiteur repart d'un jeu propre, daté par rapport à aujourd'hui.
Le générateur est déterministe (graine fixe) : même jour, mêmes données.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.time import today_local
from app.db.base import Base
from app.models.system_setting import SystemSetting
from app.services.systeme.demo.generator import generate_demo_data
from app.services.systeme.demo.guard import (
    DEMO_MAX_UPLOAD_BYTES,
    DEMO_STAMP_KEY,
    demo_write_allowed,
    is_blocked_in_demo,
)

__all__ = [
    "DEMO_MAX_UPLOAD_BYTES",
    "DEMO_STAMP_KEY",
    "demo_write_allowed",
    "ensure_demo_data",
    "generate_demo_data",
    "is_blocked_in_demo",
    "wipe_database",
]

logger = get_logger(__name__)


def wipe_database(db: Session) -> None:
    """Vide toutes les tables (le schéma et `alembic_version` restent)."""
    db.close()
    with db.get_bind().engine.connect() as connection:
        # FK circulaires (transactions <-> investment_transactions) : suspendues le temps du vidage
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
        connection.commit()
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")


async def ensure_demo_data(db: Session) -> bool:
    """Régénère la démo si elle n'a pas été produite aujourd'hui. Renvoie True si elle l'a été."""
    stamp = db.get(SystemSetting, DEMO_STAMP_KEY)
    if stamp is not None and stamp.value == today_local().isoformat():
        return False
    logger.info("Demo mode: regenerating demo data")
    wipe_database(db)
    await generate_demo_data(db)
    return True
