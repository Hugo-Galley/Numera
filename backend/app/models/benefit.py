from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow_naive
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import Account


class Benefit(Base):
    """Aide perçue chaque mois (prime d'activité, APL…) auprès d'un organisme (CAF, CPAM…).

    Avec `auto_generate`, une entrée provisoire est créée chaque mois sur `account_id`
    (`services/budget/benefit_generation.py`) puis remplacée par le vrai versement. Les versements réels
    sont retrouvés dans les entrées dont le libellé contient `match_pattern` (`services/budget/benefits.py`). `next_declaration_date` porte
    l'échéance de la déclaration périodique (trimestrielle pour la prime d'activité).
    """

    __tablename__ = "benefits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    organization: Mapped[str] = mapped_column(String(60), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)  # montant mensuel attendu, devise du compte
    payment_day: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    # Texte cherché dans le libellé bancaire (ou la note) des entrées, insensible à la casse
    match_pattern: Mapped[str] = mapped_column(String(120), nullable=False)
    # Compte de réception : restreint la recherche des versements (tous les comptes si NULL)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    declaration_interval_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_declaration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # "si:<slug>" (Simple Icons) ou "file:<hash>.png" (favicon local), comme les récurrences
    logo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Crée chaque mois une entrée provisoire du montant attendu (compte de réception requis)
    auto_generate: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)

    account: Mapped["Account"] = relationship("Account", lazy="selectin")
