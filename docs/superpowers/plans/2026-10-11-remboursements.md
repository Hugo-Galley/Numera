# Remboursements et dépenses avancées — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Déclarer des créances sur une `Sortie`, y affecter des `Entree` de remboursement, publier des KPI nets et une page « ce qu'on me doit ».

**Architecture:** Deux tables (`reimbursement_claims`, `reimbursement_allocations`) et une colonne dénormalisée `transactions.reimbursement_offset`, maintenues par un seul module `core/reimbursements.py`. Les KPI remplacent `Transaction.amount` par `NET_AMOUNT = amount − reimbursement_offset` (défini une fois dans `api/analytics/utils.py`). Front : un dialogue sur les lignes d'`AccountDetail` et une page `/reimbursements`.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, pytest · React 18, TypeScript, Tailwind, shadcn/ui, sonner · MCP (`mcp-server/server_api.py`).

**Spec:** `docs/superpowers/specs/2026-10-11-remboursements-design.md`

## Global Constraints

- Montants toujours positifs ; `amount` (devise du compte) n'est jamais modifié par une créance ou une affectation ; `running_balance` n'est pas recalculé par ce module.
- « Même devise » = même devise **de compte** (`Account.currency`) pour la dépense et le remboursement : `amount` est stocké dans la devise du compte.
- Toutes les sommes et comparaisons de plafond sont arrondies au centime (`round(x, 2)`), tolérance `0.005`.
- Erreurs métier : `HTTPException(status_code=400, detail=...)` en français ; introuvable : 404.
- KPI calculés côté backend uniquement ; le frontend n'additionne aucun montant pour un KPI.
- Nouveau router ajouté à `protected_routers` dans `app/main.py`.
- Tests backend : `cd backend && PYTHONPATH=. python3.11 -m pytest tests -q` (272 tests verts avant ce plan). Front : `cd frontend && npm run build` à 0 erreur TS.
- Tout montant affiché porte la classe `amount-blur` ; `toast` après chaque mutation.
- Commits directement sur `main`, message terminé par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Montant d'une dépense modifié sous ses créances** (ou d'une entrée sous ses affectations) via `PATCH /transactions/{id}` : refus 400, rien d'écrit — test dans Task 3.
2. **Changement de type** (`Sortie` → `Entree`) d'une transaction qui porte des créances ou affectations, y compris via `PATCH /transactions/bulk` : refus 400 — test dans Task 3.
3. **Suppression** de l'`Entree` affectée : l'offset de la `Sortie` retombe à 0 et la créance redevient ouverte — test dans Task 3.
4. **Règles de virement** qui tenteraient de lier une transaction à créance : `find_pairs` l'ignore, la liaison manuelle est refusée — test dans Task 3.
5. **Erreurs d'arrondi** (3 × 33,33 € pour une dépense de 99,99 €) : acceptées sans refus parasite — test dans Task 1.

---

## File Structure

| Fichier | Rôle |
|---|---|
| `backend/app/models/reimbursement.py` (créer) | `ReimbursementClaim`, `ReimbursementAllocation` |
| `backend/app/models/transaction.py` (modifier) | colonne `reimbursement_offset`, relation `claims`, propriété `has_claims` |
| `backend/app/models/__init__.py` (modifier) | import des deux modèles |
| `backend/alembic/versions/d4f2a8c6e1b9_remboursements.py` (créer) | migration |
| `backend/app/core/reimbursements.py` (créer) | moteur : règles, `sync_offsets`, candidates, garde-fous |
| `backend/app/schemas/reimbursement.py` (créer) | schémas API |
| `backend/app/api/reimbursements.py` (créer) | router `/reimbursements` |
| `backend/app/main.py` (modifier) | enregistrement du router |
| `backend/app/schemas/transaction.py` (modifier) | `reimbursement_offset`, `has_claims` dans `TransactionRead` |
| `backend/app/api/transactions.py` (modifier) | garde-fous update / bulk / delete / liaison virement |
| `backend/app/core/transfers.py` (modifier) | exclusion des transactions à remboursement |
| `backend/app/api/analytics/utils.py` (modifier) | `NET_AMOUNT`, `net_amount()` |
| `backend/app/api/analytics/{metrics,budget,reports,insights}.py` (modifier) | sommes nettes |
| `backend/app/api/analytics/audit.py` (modifier) | issue `unallocated-reimbursements` |
| `backend/tests/test_reimbursements.py` (créer) | moteur + API + garde-fous |
| `backend/tests/test_reimbursement_kpis.py` (créer) | KPI nets / bruts, audit |
| `mcp-server/server_api.py` (modifier) | 4 outils |
| `frontend/src/types/reimbursements.ts` (créer) | types d'API |
| `frontend/src/components/reimbursements/ReimbursementDialog.tsx` (créer) | dialogue depuis une transaction |
| `frontend/src/components/reimbursements/ClaimCandidatesDialog.tsx` (créer) | candidates d'une créance |
| `frontend/src/pages/Reimbursements.tsx` (créer) | page « ce qu'on me doit » |
| `frontend/src/pages/AccountDetail.tsx` (modifier) | bouton, badge, montant net |
| `frontend/src/App.tsx`, `components/layout/Sidebar.tsx`, `components/layout/Omnibox.tsx` (modifier) | navigation |
| Docs : `ARCHITECTURE.md`, `.claude/skills/numera-expert/SKILL.md`, `docs/ACTION_CENTER.md`, `mcp-server/README.md`, `CLAUDE.md`, `ROADMAP.md` | |

---

### Task 1: Modèle, migration et moteur `core/reimbursements.py`

**Files:**
- Create: `backend/app/models/reimbursement.py`, `backend/alembic/versions/d4f2a8c6e1b9_remboursements.py`, `backend/app/core/reimbursements.py`, `backend/tests/test_reimbursements.py`
- Modify: `backend/app/models/transaction.py`, `backend/app/models/__init__.py`

**Interfaces:**
- Produces (module `app.core.reimbursements`) :
  - `create_claim(db, transaction_id: int, debtor: str, expected_amount: float, note: str | None = None) -> ReimbursementClaim`
  - `update_claim(db, claim: ReimbursementClaim, data: dict) -> ReimbursementClaim` (clés possibles : `debtor`, `expected_amount`, `note`)
  - `delete_claim(db, claim: ReimbursementClaim) -> None`
  - `allocate(db, claim: ReimbursementClaim, entree_id: int, amount: float | None = None) -> ReimbursementAllocation`
  - `remove_allocation(db, allocation: ReimbursementAllocation) -> None`
  - `claim_received(db, claim_id: int) -> float`
  - `entree_allocated(db, entree_id: int) -> float`
  - `sync_offsets(db, tx_ids: set[int]) -> None` (ne commite pas)
  - Toutes les fonctions de mutation commitent.

- [ ] **Step 1: Modèles**

`backend/app/models/reimbursement.py` :

```python
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow_naive
from app.db.base import Base


class ReimbursementClaim(Base):
    """Créance : une part d'une Sortie qu'un tiers doit rembourser."""

    __tablename__ = "reimbursement_claims"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    debtor: Mapped[str] = mapped_column(String(120), nullable=False)
    expected_amount: Mapped[float] = mapped_column(Float, nullable=False)  # devise du compte de la dépense
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)

    allocations: Mapped[list["ReimbursementAllocation"]] = relationship(
        "ReimbursementAllocation", back_populates="claim", cascade="all, delete-orphan", lazy="selectin"
    )


class ReimbursementAllocation(Base):
    """Part d'une Entree affectée à une créance."""

    __tablename__ = "reimbursement_allocations"
    __table_args__ = (UniqueConstraint("claim_id", "entree_transaction_id", name="uq_reimbursement_allocation"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("reimbursement_claims.id", ondelete="CASCADE"), index=True)
    entree_transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)

    claim: Mapped[ReimbursementClaim] = relationship("ReimbursementClaim", back_populates="allocations")
```

Dans `backend/app/models/transaction.py`, après `merchant_id` :

```python
    # Total remboursé (Sortie) ou affecté à des créances (Entree) ; maintenu par core/reimbursements.py
    reimbursement_offset: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
```

après la relation `tags` :

```python
    claims: Mapped[list["ReimbursementClaim"]] = relationship(
        "ReimbursementClaim", lazy="selectin", passive_deletes=True, viewonly=True
    )
```

et après la propriété `recurring_logo` :

```python
    @property
    def has_claims(self) -> bool:
        """La dépense porte au moins une créance de remboursement."""
        return bool(self.claims)
```

Dans `backend/app/models/__init__.py`, ajouter `from app.models.reimbursement import ReimbursementAllocation, ReimbursementClaim` et les deux noms dans `__all__`.

- [ ] **Step 2: Migration**

`backend/alembic/versions/d4f2a8c6e1b9_remboursements.py` :

```python
"""remboursements : créances, affectations et offset des transactions

Revision ID: d4f2a8c6e1b9
Revises: c3e9a1d7f5b2
"""
import sqlalchemy as sa
from alembic import op

revision = "d4f2a8c6e1b9"
down_revision = "c3e9a1d7f5b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reimbursement_claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transaction_id", sa.Integer(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("debtor", sa.String(length=120), nullable=False),
        sa.Column("expected_amount", sa.Float(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_reimbursement_claims_id", "reimbursement_claims", ["id"])
    op.create_index("ix_reimbursement_claims_transaction_id", "reimbursement_claims", ["transaction_id"])

    op.create_table(
        "reimbursement_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("reimbursement_claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entree_transaction_id", sa.Integer(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("claim_id", "entree_transaction_id", name="uq_reimbursement_allocation"),
    )
    op.create_index("ix_reimbursement_allocations_id", "reimbursement_allocations", ["id"])
    op.create_index("ix_reimbursement_allocations_claim_id", "reimbursement_allocations", ["claim_id"])
    op.create_index("ix_reimbursement_allocations_entree_transaction_id", "reimbursement_allocations", ["entree_transaction_id"])

    with op.batch_alter_table("transactions") as batch:
        batch.add_column(sa.Column("reimbursement_offset", sa.Float(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch:
        batch.drop_column("reimbursement_offset")
    op.drop_table("reimbursement_allocations")
    op.drop_table("reimbursement_claims")
```

Vérifier : `cd backend && cp data/suivi_budget.db /tmp/claude-remb.db && DATABASE_URL=sqlite:////tmp/claude-remb.db PYTHONPATH=. python3.11 -m alembic upgrade head && DATABASE_URL=sqlite:////tmp/claude-remb.db PYTHONPATH=. python3.11 -m alembic downgrade -1` (si la variable d'environnement de la base porte un autre nom, la lire dans `app/core/config.py`). Attendu : aucune erreur.

- [ ] **Step 3: Tests du moteur (échouent)**

`backend/tests/test_reimbursements.py` :

```python
import asyncio
from datetime import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core import reimbursements as remb
from app.core.finance import month_label_from_date
from app.models.account import Account
from app.models.transaction import Transaction


def make_account(db: Session, name="Principal", currency="EUR", type_="courant"):
    acc = Account(name=name, type=type_, currency=currency, active=True)
    db.add(acc)
    db.commit()
    return acc


def tx(db: Session, account, type_, amount, date, merchant="x"):
    t = Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_,
        merchant=merchant, amount=amount, original_amount=amount, currency=account.currency, running_balance=0.0,
    )
    db.add(t)
    db.commit()
    return t


@pytest.fixture()
def resto(db_session: Session):
    main = make_account(db_session)
    sortie = tx(db_session, main, "Sortie", 90.0, datetime(2026, 9, 28), "RESTO LE PETIT")
    return main, sortie


def test_claim_and_allocation_update_offsets(db_session, resto):
    main, sortie = resto
    denis = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    remb.create_claim(db_session, sortie.id, "Julie", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3), "VIR DENIS")
    alloc = remb.allocate(db_session, denis, entree.id)
    assert alloc.amount == 30.0
    db_session.refresh(sortie); db_session.refresh(entree)
    assert sortie.reimbursement_offset == 30.0
    assert entree.reimbursement_offset == 30.0
    assert remb.claim_received(db_session, denis.id) == 30.0


def test_health_two_refunds_settle_one_claim(db_session, resto):
    main, _ = resto
    consult = tx(db_session, main, "Sortie", 30.0, datetime(2026, 9, 1), "DR MARTIN")
    claim = remb.create_claim(db_session, consult.id, "Sécu + mutuelle", 30.0)
    secu = tx(db_session, main, "Entree", 21.0, datetime(2026, 9, 6), "CPAM")
    mutuelle = tx(db_session, main, "Entree", 9.0, datetime(2026, 9, 12), "MUTUELLE")
    remb.allocate(db_session, claim, secu.id)
    remb.allocate(db_session, claim, mutuelle.id)
    assert remb.claim_received(db_session, claim.id) == 30.0
    db_session.refresh(consult)
    assert consult.reimbursement_offset == 30.0


def test_one_transfer_split_over_two_claims(db_session, resto):
    main, sortie = resto
    cine = tx(db_session, main, "Sortie", 40.0, datetime(2026, 9, 29), "CGR")
    c1 = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    c2 = remb.create_claim(db_session, cine.id, "Denis", 20.0)
    entree = tx(db_session, main, "Entree", 50.0, datetime(2026, 10, 3), "VIR DENIS")
    remb.allocate(db_session, c1, entree.id)
    remb.allocate(db_session, c2, entree.id)
    db_session.refresh(entree)
    assert entree.reimbursement_offset == 50.0
    with pytest.raises(HTTPException) as exc:
        remb.allocate(db_session, c2, entree.id, 25.0)
    assert exc.value.status_code == 400


def test_reallocating_same_entree_updates_amount(db_session, resto):
    main, sortie = resto
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    remb.allocate(db_session, claim, entree.id, 10.0)
    remb.allocate(db_session, claim, entree.id, 25.0)
    assert len(claim.allocations) == 1
    assert remb.claim_received(db_session, claim.id) == 25.0


def test_rules_are_enforced(db_session, resto):
    main, sortie = resto
    usd = make_account(db_session, "Revolut USD", "USD")
    entree_usd = tx(db_session, usd, "Entree", 30.0, datetime(2026, 10, 3))
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    cases = [
        lambda: remb.create_claim(db_session, entree.id, "X", 10.0),        # pas une Sortie
        lambda: remb.create_claim(db_session, sortie.id, "Julie", 70.0),    # 30 + 70 > 90
        lambda: remb.allocate(db_session, claim, sortie.id),                # pas une Entree
        lambda: remb.allocate(db_session, claim, entree_usd.id),            # devise différente
        lambda: remb.allocate(db_session, claim, entree.id, 31.0),          # > attendu
    ]
    for case in cases:
        with pytest.raises(HTTPException) as exc:
            case()
        assert exc.value.status_code == 400
    remb.allocate(db_session, claim, entree.id, 20.0)
    with pytest.raises(HTTPException):
        remb.update_claim(db_session, claim, {"expected_amount": 15.0})     # < reçu
    remb.update_claim(db_session, claim, {"expected_amount": 20.0, "debtor": "Denis M."})
    assert claim.expected_amount == 20.0 and claim.debtor == "Denis M."


def test_transfer_cannot_be_used(db_session, resto):
    main, sortie = resto
    sortie.is_transfer = True
    db_session.commit()
    with pytest.raises(HTTPException):
        remb.create_claim(db_session, sortie.id, "Denis", 30.0)


def test_rounding_three_thirds(db_session, resto):
    main, _ = resto
    dep = tx(db_session, main, "Sortie", 99.99, datetime(2026, 9, 1))
    for name in ("A", "B", "C"):
        remb.create_claim(db_session, dep.id, name, 33.33)
    entree = tx(db_session, main, "Entree", 99.99, datetime(2026, 9, 2))
    for c in dep.claims:
        remb.allocate(db_session, c, entree.id)
    db_session.refresh(dep)
    assert dep.reimbursement_offset == 99.99


def test_delete_claim_resets_offsets(db_session, resto):
    main, sortie = resto
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    remb.allocate(db_session, claim, entree.id)
    remb.delete_claim(db_session, claim)
    db_session.refresh(sortie); db_session.refresh(entree)
    assert sortie.reimbursement_offset == 0.0 and entree.reimbursement_offset == 0.0
```

- [ ] **Step 4: Lancer, vérifier l'échec**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_reimbursements.py -q`
Expected: erreur d'import `app.core.reimbursements`.

- [ ] **Step 5: Moteur**

`backend/app/core/reimbursements.py` :

```python
"""Remboursements : créances sur une Sortie et affectations d'Entree qui les soldent.

Seule porte d'entrée pour créer, modifier ou supprimer créances et affectations. Chaque mutation
recalcule `transactions.reimbursement_offset` des transactions touchées (`sync_offsets`), que les KPI
retranchent du montant (`api/analytics/utils.py::NET_AMOUNT`). Aucun montant bancaire n'est modifié.
"""
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.reimbursement import ReimbursementAllocation, ReimbursementClaim
from app.models.transaction import Transaction

EPS = 0.005


def cents(value: float | None) -> float:
    return round(float(value or 0.0), 2)


def _refuse(detail: str) -> None:
    raise HTTPException(status_code=400, detail=detail)


def _get_tx(db: Session, tx_id: int) -> Transaction:
    tx = db.get(Transaction, tx_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    return tx


def account_currency(db: Session, tx: Transaction) -> str:
    account = db.get(Account, tx.account_id)
    return account.currency if account else "EUR"


def claim_received(db: Session, claim_id: int) -> float:
    total = db.query(func.coalesce(func.sum(ReimbursementAllocation.amount), 0.0)).filter(
        ReimbursementAllocation.claim_id == claim_id
    ).scalar()
    return cents(total)


def entree_allocated(db: Session, entree_id: int) -> float:
    total = db.query(func.coalesce(func.sum(ReimbursementAllocation.amount), 0.0)).filter(
        ReimbursementAllocation.entree_transaction_id == entree_id
    ).scalar()
    return cents(total)


def sortie_expected(db: Session, sortie_id: int, exclude_claim_id: int | None = None) -> float:
    q = db.query(func.coalesce(func.sum(ReimbursementClaim.expected_amount), 0.0)).filter(
        ReimbursementClaim.transaction_id == sortie_id
    )
    if exclude_claim_id is not None:
        q = q.filter(ReimbursementClaim.id != exclude_claim_id)
    return cents(q.scalar())


def sortie_received(db: Session, sortie_id: int) -> float:
    total = (
        db.query(func.coalesce(func.sum(ReimbursementAllocation.amount), 0.0))
        .join(ReimbursementClaim, ReimbursementAllocation.claim_id == ReimbursementClaim.id)
        .filter(ReimbursementClaim.transaction_id == sortie_id)
        .scalar()
    )
    return cents(total)


def sync_offsets(db: Session, tx_ids: set[int]) -> None:
    """Recalcule `reimbursement_offset` des transactions données (sans commit)."""
    db.flush()
    for tx_id in tx_ids:
        tx = db.get(Transaction, tx_id)
        if tx is None:
            continue
        if tx.type == "Sortie":
            tx.reimbursement_offset = sortie_received(db, tx_id)
        elif tx.type == "Entree":
            tx.reimbursement_offset = entree_allocated(db, tx_id)
        else:
            tx.reimbursement_offset = 0.0


def has_reimbursement(db: Session, tx_id: int) -> bool:
    """La transaction porte une créance ou une affectation (elle ne peut plus être un virement)."""
    if db.query(ReimbursementClaim.id).filter(ReimbursementClaim.transaction_id == tx_id).first():
        return True
    return db.query(ReimbursementAllocation.id).filter(ReimbursementAllocation.entree_transaction_id == tx_id).first() is not None


def create_claim(db: Session, transaction_id: int, debtor: str, expected_amount: float, note: str | None = None) -> ReimbursementClaim:
    sortie = _get_tx(db, transaction_id)
    if sortie.type != "Sortie":
        _refuse("Une créance ne peut porter que sur une dépense (Sortie)")
    if sortie.is_transfer:
        _refuse("Un virement interne ne peut pas porter de créance")
    expected = cents(expected_amount)
    if expected <= 0:
        _refuse("Le montant attendu doit être positif")
    if sortie_expected(db, sortie.id) + expected > cents(sortie.amount) + EPS:
        _refuse("Le total des créances dépasse le montant de la dépense")
    claim = ReimbursementClaim(transaction_id=sortie.id, debtor=debtor.strip(), expected_amount=expected, note=note)
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


def update_claim(db: Session, claim: ReimbursementClaim, data: dict) -> ReimbursementClaim:
    if "expected_amount" in data and data["expected_amount"] is not None:
        expected = cents(data["expected_amount"])
        if expected <= 0:
            _refuse("Le montant attendu doit être positif")
        if expected < claim_received(db, claim.id) - EPS:
            _refuse("Le montant attendu ne peut pas être inférieur au montant déjà reçu : retirez d'abord des remboursements")
        sortie = _get_tx(db, claim.transaction_id)
        if sortie_expected(db, sortie.id, exclude_claim_id=claim.id) + expected > cents(sortie.amount) + EPS:
            _refuse("Le total des créances dépasse le montant de la dépense")
        claim.expected_amount = expected
    if data.get("debtor"):
        claim.debtor = data["debtor"].strip()
    if "note" in data:
        claim.note = data["note"]
    db.commit()
    db.refresh(claim)
    return claim


def delete_claim(db: Session, claim: ReimbursementClaim) -> None:
    touched = {claim.transaction_id, *(a.entree_transaction_id for a in claim.allocations)}
    db.delete(claim)
    sync_offsets(db, touched)
    db.commit()


def allocate(db: Session, claim: ReimbursementClaim, entree_id: int, amount: float | None = None) -> ReimbursementAllocation:
    entree = _get_tx(db, entree_id)
    if entree.type != "Entree":
        _refuse("Seule une entrée (Entree) peut rembourser une créance")
    if entree.is_transfer:
        _refuse("Un virement interne ne peut pas servir de remboursement")
    sortie = _get_tx(db, claim.transaction_id)
    if account_currency(db, entree) != account_currency(db, sortie):
        _refuse("La dépense et le remboursement doivent être dans la même devise")

    existing = (
        db.query(ReimbursementAllocation)
        .filter(ReimbursementAllocation.claim_id == claim.id, ReimbursementAllocation.entree_transaction_id == entree.id)
        .first()
    )
    current = cents(existing.amount) if existing else 0.0
    claim_room = cents(claim.expected_amount - (claim_received(db, claim.id) - current))
    entree_room = cents(entree.amount - (entree_allocated(db, entree.id) - current))
    value = cents(min(claim_room, entree_room) if amount is None else amount)
    if value <= 0:
        _refuse("Rien à affecter : la créance est soldée ou l'entrée est déjà entièrement affectée")
    if value > claim_room + EPS:
        _refuse("Le montant dépasse le reste dû de la créance")
    if value > entree_room + EPS:
        _refuse("Le montant dépasse la part non affectée de l'entrée")

    if existing:
        existing.amount = value
        allocation = existing
    else:
        allocation = ReimbursementAllocation(claim_id=claim.id, entree_transaction_id=entree.id, amount=value)
        db.add(allocation)
    sync_offsets(db, {sortie.id, entree.id})
    db.commit()
    db.refresh(allocation)
    db.refresh(claim)
    return allocation


def remove_allocation(db: Session, allocation: ReimbursementAllocation) -> None:
    claim = db.get(ReimbursementClaim, allocation.claim_id)
    touched = {allocation.entree_transaction_id, claim.transaction_id}
    db.delete(allocation)
    sync_offsets(db, touched)
    db.commit()
```

- [ ] **Step 6: Lancer les tests**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_reimbursements.py -q && PYTHONPATH=. python3.11 -m pytest tests -q`
Expected: tout PASS (tests existants inclus).

- [ ] **Step 7: Commit**

```bash
git add backend/app/models backend/alembic/versions/d4f2a8c6e1b9_remboursements.py backend/app/core/reimbursements.py backend/tests/test_reimbursements.py
git commit -m "feat(remboursements): modèle, migration et moteur de créances

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: API `/reimbursements`, candidates et `TransactionRead`

**Files:**
- Create: `backend/app/schemas/reimbursement.py`, `backend/app/api/reimbursements.py`
- Modify: `backend/app/core/reimbursements.py` (candidates, résumé, créances pour une entrée), `backend/app/main.py`, `backend/app/models/transaction.py`, `backend/app/schemas/transaction.py`, `backend/tests/test_reimbursements.py`

**Interfaces:**
- Consumes: Task 1 (`create_claim`, `update_claim`, `delete_claim`, `allocate`, `remove_allocation`, `claim_received`, `entree_allocated`, `account_currency`, `cents`).
- Produces (HTTP, consommé par Tasks 6 et 7) :
  - `GET /reimbursements/claims?status=open|settled|all&debtor=` → `list[ClaimRead]`
  - `GET /reimbursements/summary` → `ReimbursementSummary`
  - `POST /reimbursements/claims` (`ClaimCreate`) → `ClaimRead` 201
  - `PATCH /reimbursements/claims/{id}` (`ClaimUpdate`) → `ClaimRead`
  - `DELETE /reimbursements/claims/{id}` → 204
  - `GET /reimbursements/claims/{id}/candidates` → `list[CandidateRead]`
  - `POST /reimbursements/claims/{id}/allocations` (`AllocationCreate`) → `ClaimRead`
  - `DELETE /reimbursements/allocations/{id}` → 204
  - `GET /reimbursements/entries/{entree_id}/claims` → `EntryClaims`
  - `TransactionRead.reimbursement_offset: float`, `TransactionRead.has_claims: bool`, `TransactionRead.reimbursement_expected: float`
- Produces (Python) : `claim_view(db, claim) -> dict`, `candidates(db, claim) -> list[dict]`, `summary(db) -> dict`, `claims_for_entree(db, entree) -> dict` dans `app.core.reimbursements`.

- [ ] **Step 1: Tests API (échouent)**

Ajouter à `backend/tests/test_reimbursements.py` :

```python
def test_api_flow(client, db_session, resto):
    main, sortie = resto
    r = client.post("/reimbursements/claims", json={"transaction_id": sortie.id, "debtor": "Denis", "expected_amount": 30})
    assert r.status_code == 201
    claim_id = r.json()["id"]
    client.post("/reimbursements/claims", json={"transaction_id": sortie.id, "debtor": "Julie", "expected_amount": 30})
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3), "VIR SEPA DENIS DUPONT")
    autre = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 2), "REMBOURSEMENT AMAZON")

    cands = client.get(f"/reimbursements/claims/{claim_id}/candidates").json()
    assert [c["id"] for c in cands][:2] == [entree.id, autre.id]  # débiteur dans le libellé d'abord
    assert cands[0]["available"] == 30.0

    body = client.post(f"/reimbursements/claims/{claim_id}/allocations", json={"entree_id": entree.id}).json()
    assert body["received"] == 30.0 and body["remaining"] == 0.0
    assert body["expense"]["id"] == sortie.id and body["allocations"][0]["entree_id"] == entree.id

    assert [c["debtor"] for c in client.get("/reimbursements/claims").json()] == ["Julie"]
    assert [c["debtor"] for c in client.get("/reimbursements/claims", params={"status": "settled"}).json()] == ["Denis"]
    summary = client.get("/reimbursements/summary").json()
    assert summary["total_due"] == 30.0
    assert summary["debtors"] == [{"debtor": "Julie", "claims": 1, "due": 30.0}]

    listed = client.get("/transactions", params={"account_id": main.id}).json()
    by_id = {t["id"]: t for t in listed}
    assert by_id[sortie.id]["has_claims"] is True and by_id[sortie.id]["reimbursement_offset"] == 30.0
    assert by_id[sortie.id]["reimbursement_expected"] == 60.0
    assert by_id[entree.id]["reimbursement_offset"] == 30.0

    for_entree = client.get(f"/reimbursements/entries/{autre.id}/claims").json()
    assert [c["debtor"] for c in for_entree["open_claims"]] == ["Julie"]
    assert for_entree["available"] == 30.0

    alloc_id = body["allocations"][0]["id"]
    assert client.delete(f"/reimbursements/allocations/{alloc_id}").status_code == 204
    assert client.patch(f"/reimbursements/claims/{claim_id}", json={"expected_amount": 25}).json()["expected_amount"] == 25.0
    assert client.delete(f"/reimbursements/claims/{claim_id}").status_code == 204
    assert client.post("/reimbursements/claims", json={"transaction_id": entree.id, "debtor": "X", "expected_amount": 5}).status_code == 400
    assert client.get("/reimbursements/claims/9999/candidates").status_code == 404
```

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_reimbursements.py::test_api_flow -q` → FAIL (404).

- [ ] **Step 2: Fonctions de lecture dans le moteur**

Ajouter à `backend/app/core/reimbursements.py` (imports en tête : `from datetime import timedelta`) :

```python
CANDIDATE_DAYS_BEFORE = 7
CANDIDATE_DAYS_AFTER = 180
CANDIDATE_LIMIT = 30


def _label(tx: Transaction) -> str:
    return tx.merchant or tx.note or ""


def claim_view(db: Session, claim: ReimbursementClaim) -> dict:
    sortie = db.get(Transaction, claim.transaction_id)
    received = claim_received(db, claim.id)
    allocations = []
    for a in claim.allocations:
        entree = db.get(Transaction, a.entree_transaction_id)
        allocations.append({
            "id": a.id, "entree_id": a.entree_transaction_id, "amount": cents(a.amount),
            "date": entree.date if entree else None, "label": _label(entree) if entree else None,
            "account_id": entree.account_id if entree else None,
        })
    return {
        "id": claim.id,
        "debtor": claim.debtor,
        "expected_amount": cents(claim.expected_amount),
        "received": received,
        "remaining": cents(claim.expected_amount - received),
        "note": claim.note,
        "created_at": claim.created_at,
        "currency": account_currency(db, sortie),
        "expense": {
            "id": sortie.id, "account_id": sortie.account_id, "date": sortie.date,
            "label": _label(sortie), "amount": cents(sortie.amount),
        },
        "allocations": allocations,
    }


def list_claims(db: Session, status: str = "open", debtor: str | None = None) -> list[dict]:
    q = db.query(ReimbursementClaim).join(Transaction, ReimbursementClaim.transaction_id == Transaction.id)
    if debtor:
        q = q.filter(func.lower(ReimbursementClaim.debtor) == debtor.strip().lower())
    views = [claim_view(db, c) for c in q.order_by(Transaction.date.desc(), ReimbursementClaim.id).all()]
    if status == "open":
        return [v for v in views if v["remaining"] > EPS]
    if status == "settled":
        return [v for v in views if v["remaining"] <= EPS]
    return views


def summary(db: Session) -> dict:
    by_debtor: dict[str, dict] = {}
    for view in list_claims(db, "open"):
        key = view["debtor"].strip().lower()
        row = by_debtor.setdefault(key, {"debtor": view["debtor"], "claims": 0, "due": 0.0})
        row["claims"] += 1
        row["due"] = cents(row["due"] + view["remaining"])
    debtors = sorted(by_debtor.values(), key=lambda r: (-r["due"], r["debtor"]))
    return {"total_due": cents(sum(r["due"] for r in debtors)), "debtors": debtors}


def candidates(db: Session, claim: ReimbursementClaim) -> list[dict]:
    sortie = db.get(Transaction, claim.transaction_id)
    currency = account_currency(db, sortie)
    remaining = cents(claim.expected_amount - claim_received(db, claim.id))
    debtor = claim.debtor.strip().lower()
    already = {a.entree_transaction_id for a in claim.allocations}
    rows = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.type == "Entree",
            Transaction.is_transfer.is_(False),
            Account.currency == currency,
            Transaction.date >= sortie.date - timedelta(days=CANDIDATE_DAYS_BEFORE),
            Transaction.date <= sortie.date + timedelta(days=CANDIDATE_DAYS_AFTER),
        )
        .all()
    )
    out = []
    for e in rows:
        if e.id in already:
            continue
        available = cents(e.amount - entree_allocated(db, e.id))
        if available <= EPS:
            continue
        label = _label(e)
        out.append({
            "id": e.id, "account_id": e.account_id, "date": e.date, "label": label,
            "amount": cents(e.amount), "available": available,
            "day_gap": abs((e.date.date() - sortie.date.date()).days),
            "debtor_match": bool(debtor) and debtor in label.lower(),
        })
    out.sort(key=lambda c: (not c["debtor_match"], abs(c["available"] - remaining) > EPS, c["day_gap"], c["id"]))
    return out[:CANDIDATE_LIMIT]


def claims_for_entree(db: Session, entree: Transaction) -> dict:
    if entree.type != "Entree":
        _refuse("Seule une entrée (Entree) peut rembourser une créance")
    currency = account_currency(db, entree)
    label = _label(entree).lower()
    open_claims = [v for v in list_claims(db, "open") if v["currency"] == currency]
    open_claims.sort(key=lambda v: (v["debtor"].strip().lower() not in label, v["expense"]["date"]))
    allocations = (
        db.query(ReimbursementAllocation).filter(ReimbursementAllocation.entree_transaction_id == entree.id).all()
    )
    return {
        "entree_id": entree.id,
        "amount": cents(entree.amount),
        "available": cents(entree.amount - entree_allocated(db, entree.id)),
        "open_claims": open_claims,
        "allocations": [
            {"id": a.id, "claim_id": a.claim_id, "amount": cents(a.amount), "debtor": a.claim.debtor} for a in allocations
        ],
    }
```

- [ ] **Step 3: Schémas**

`backend/app/schemas/reimbursement.py` :

```python
from datetime import datetime

from pydantic import BaseModel, Field


class ClaimCreate(BaseModel):
    transaction_id: int
    debtor: str = Field(min_length=1, max_length=120)
    expected_amount: float = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)


class ClaimUpdate(BaseModel):
    debtor: str | None = Field(default=None, min_length=1, max_length=120)
    expected_amount: float | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=255)


class AllocationCreate(BaseModel):
    entree_id: int
    amount: float | None = Field(default=None, gt=0)


class ExpenseRef(BaseModel):
    id: int
    account_id: int
    date: datetime
    label: str
    amount: float


class AllocationRead(BaseModel):
    id: int
    entree_id: int
    amount: float
    date: datetime | None = None
    label: str | None = None
    account_id: int | None = None


class ClaimRead(BaseModel):
    id: int
    debtor: str
    expected_amount: float
    received: float
    remaining: float
    note: str | None = None
    created_at: datetime
    currency: str
    expense: ExpenseRef
    allocations: list[AllocationRead]


class DebtorDue(BaseModel):
    debtor: str
    claims: int
    due: float


class ReimbursementSummary(BaseModel):
    total_due: float
    debtors: list[DebtorDue]


class CandidateRead(BaseModel):
    id: int
    account_id: int
    date: datetime
    label: str
    amount: float
    available: float
    day_gap: int
    debtor_match: bool


class EntryAllocationRead(BaseModel):
    id: int
    claim_id: int
    amount: float
    debtor: str


class EntryClaims(BaseModel):
    entree_id: int
    amount: float
    available: float
    open_claims: list[ClaimRead]
    allocations: list[EntryAllocationRead]
```

- [ ] **Step 4: Router**

`backend/app/api/reimbursements.py` :

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core import reimbursements as remb
from app.models.reimbursement import ReimbursementAllocation, ReimbursementClaim
from app.models.transaction import Transaction
from app.schemas.reimbursement import (
    AllocationCreate,
    CandidateRead,
    ClaimCreate,
    ClaimRead,
    ClaimUpdate,
    EntryClaims,
    ReimbursementSummary,
)

router = APIRouter(prefix="/reimbursements", tags=["reimbursements"])


def _claim(db: Session, claim_id: int) -> ReimbursementClaim:
    claim = db.get(ReimbursementClaim, claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Créance introuvable")
    return claim


@router.get("/claims", response_model=list[ClaimRead])
def list_claims(
    status: str = Query(default="open", pattern="^(open|settled|all)$"),
    debtor: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Créances (« ce qu'on me doit ») ; `open` = reste dû > 0."""
    return remb.list_claims(db, status, debtor)


@router.get("/summary", response_model=ReimbursementSummary)
def reimbursement_summary(db: Session = Depends(get_db)):
    return remb.summary(db)


@router.post("/claims", response_model=ClaimRead, status_code=201)
def create_claim(payload: ClaimCreate, db: Session = Depends(get_db)):
    claim = remb.create_claim(db, payload.transaction_id, payload.debtor, payload.expected_amount, payload.note)
    return remb.claim_view(db, claim)


@router.patch("/claims/{claim_id}", response_model=ClaimRead)
def update_claim(claim_id: int, payload: ClaimUpdate, db: Session = Depends(get_db)):
    claim = remb.update_claim(db, _claim(db, claim_id), payload.model_dump(exclude_unset=True))
    return remb.claim_view(db, claim)


@router.delete("/claims/{claim_id}", status_code=204)
def delete_claim(claim_id: int, db: Session = Depends(get_db)):
    remb.delete_claim(db, _claim(db, claim_id))


@router.get("/claims/{claim_id}/candidates", response_model=list[CandidateRead])
def claim_candidates(claim_id: int, db: Session = Depends(get_db)):
    return remb.candidates(db, _claim(db, claim_id))


@router.post("/claims/{claim_id}/allocations", response_model=ClaimRead)
def allocate(claim_id: int, payload: AllocationCreate, db: Session = Depends(get_db)):
    claim = _claim(db, claim_id)
    remb.allocate(db, claim, payload.entree_id, payload.amount)
    return remb.claim_view(db, claim)


@router.delete("/allocations/{allocation_id}", status_code=204)
def remove_allocation(allocation_id: int, db: Session = Depends(get_db)):
    allocation = db.get(ReimbursementAllocation, allocation_id)
    if not allocation:
        raise HTTPException(status_code=404, detail="Affectation introuvable")
    remb.remove_allocation(db, allocation)


@router.get("/entries/{entree_id}/claims", response_model=EntryClaims)
def entry_claims(entree_id: int, db: Session = Depends(get_db)):
    entree = db.get(Transaction, entree_id)
    if not entree:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    return remb.claims_for_entree(db, entree)
```

`backend/app/main.py` : `from app.api.reimbursements import router as reimbursements_router` à côté de l'import de `transfer_rules_router`, et `reimbursements_router,` après `transfer_rules_router,` dans `protected_routers`.

`backend/app/schemas/transaction.py`, dans `TransactionRead` après `linked_account_id` :

```python
    reimbursement_offset: float = 0.0
    reimbursement_expected: float = 0.0
    has_claims: bool = False
```

et dans `backend/app/models/transaction.py`, après `has_claims` :

```python
    @property
    def reimbursement_expected(self) -> float:
        """Total attendu des créances de la dépense (affichage du statut de remboursement)."""
        return round(sum(c.expected_amount for c in self.claims), 2)
```

- [ ] **Step 5: Lancer les tests**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app backend/tests/test_reimbursements.py
git commit -m "feat(remboursements): API /reimbursements, candidates et résumé par débiteur

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Garde-fous sur les transactions et exclusion des virements

**Files:**
- Modify: `backend/app/core/reimbursements.py`, `backend/app/api/transactions.py` (`link_transactions` ~l.199, `create_transfer_counterpart` ~l.176, `bulk_update_transactions` ~l.341, `update_transaction` ~l.387, `delete_transaction` ~l.456), `backend/app/core/transfers.py` (`find_pairs`, `candidates_for`), `backend/tests/test_reimbursements.py`

**Interfaces:**
- Consumes: Task 1 (`sortie_expected`, `entree_allocated`, `has_reimbursement`, `sync_offsets`, `cents`, `EPS`).
- Produces: `check_transaction_change(db, tx, new_type: str, new_amount: float, sets_transfer: bool) -> None`, `detach_before_delete(db, tx) -> set[int]`, `locked_transaction_ids()` (sous-requête `select`) dans `app.core.reimbursements`.

- [ ] **Step 1: Tests (échouent)**

```python
def test_guards_on_transaction_mutations(client, db_session, resto):
    main, sortie = resto
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    remb.allocate(db_session, claim, entree.id)

    assert client.patch(f"/transactions/{sortie.id}", json={"amount": 20}).status_code == 400
    assert client.patch(f"/transactions/{entree.id}", json={"amount": 10}).status_code == 400
    assert client.patch(f"/transactions/{sortie.id}", json={"type": "Entree"}).status_code == 400
    assert client.patch("/transactions/bulk", json={"ids": [entree.id], "type": "Sortie"}).status_code == 400
    assert client.patch(f"/transactions/{sortie.id}", json={"is_transfer": True}).status_code == 400
    db_session.refresh(sortie)
    assert sortie.amount == 90.0 and sortie.type == "Sortie"
    assert client.patch(f"/transactions/{sortie.id}", json={"amount": 95}).status_code == 200


def test_deleting_entree_reopens_claim(client, db_session, resto):
    main, sortie = resto
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    remb.allocate(db_session, claim, entree.id)
    assert client.delete(f"/transactions/{entree.id}").status_code == 204
    db_session.expire_all()
    assert db_session.get(Transaction, sortie.id).reimbursement_offset == 0.0
    assert [c["remaining"] for c in client.get("/reimbursements/claims").json()] == [30.0]


def test_deleting_sortie_frees_entree(client, db_session, resto):
    main, sortie = resto
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    entree = tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3))
    remb.allocate(db_session, claim, entree.id)
    assert client.delete(f"/transactions/{sortie.id}").status_code == 204
    db_session.expire_all()
    assert db_session.get(Transaction, entree.id).reimbursement_offset == 0.0
    assert client.get("/reimbursements/claims", params={"status": "all"}).json() == []


def test_reimbursement_excludes_transfer_matching(client, db_session, resto):
    main, sortie = resto
    livret = make_account(db_session, "Livret A", type_="epargne")
    remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    mirror = tx(db_session, livret, "Entree", 90.0, datetime(2026, 9, 28))
    assert client.get("/transactions/potential-transfers").json() == []
    assert client.post(f"/transactions/{sortie.id}/link/{mirror.id}").status_code == 400
    assert client.get(f"/transactions/{mirror.id}/transfer-candidates").json() == []
```

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_reimbursements.py -q` → les 4 nouveaux tests FAIL.

- [ ] **Step 2: Fonctions de garde dans le moteur**

Ajouter à `backend/app/core/reimbursements.py` (import : `from sqlalchemy import func, select, union`) :

```python
def locked_transaction_ids():
    """Sous-requête des transactions portant une créance ou une affectation (exclues des virements)."""
    return union(
        select(ReimbursementClaim.transaction_id),
        select(ReimbursementAllocation.entree_transaction_id),
    )


def check_transaction_change(db: Session, tx: Transaction, new_type: str, new_amount: float, sets_transfer: bool) -> None:
    """Refuse une modification qui casserait les créances ou affectations de `tx`."""
    expected = sortie_expected(db, tx.id)
    allocated = entree_allocated(db, tx.id)
    if expected <= 0 and allocated <= 0:
        return
    if new_type != tx.type:
        _refuse("Cette transaction porte des remboursements : retirez-les avant de changer son type")
    if sets_transfer:
        _refuse("Cette transaction porte des remboursements : elle ne peut pas être un virement interne")
    if expected > 0 and cents(new_amount) < expected - EPS:
        _refuse("Le montant ne peut pas être inférieur au total des créances déclarées")
    if allocated > 0 and cents(new_amount) < allocated - EPS:
        _refuse("Le montant ne peut pas être inférieur au total déjà affecté à des créances")


def detach_before_delete(db: Session, tx: Transaction) -> set[int]:
    """Supprime créances et affectations de `tx` ; renvoie les transactions de l'autre côté à resynchroniser."""
    touched: set[int] = set()
    for claim in db.query(ReimbursementClaim).filter(ReimbursementClaim.transaction_id == tx.id).all():
        touched.update(a.entree_transaction_id for a in claim.allocations)
        db.delete(claim)
    for allocation in db.query(ReimbursementAllocation).filter(ReimbursementAllocation.entree_transaction_id == tx.id).all():
        touched.add(allocation.claim.transaction_id)
        db.delete(allocation)
    touched.discard(tx.id)
    return touched
```

- [ ] **Step 3: Brancher dans `api/transactions.py`**

Import en tête : `from app.core import reimbursements as remb`.

`update_transaction`, juste avant la boucle `for field, value in update_data.items():` :

```python
    remb.check_transaction_change(
        db,
        transaction,
        update_data.get("type", transaction.type),
        update_data.get("amount", transaction.amount),
        bool(update_data.get("is_transfer")),
    )
```

`bulk_update_transactions`, juste après le bloc qui refuse le re-typage d'un `Solde Initial` :

```python
    if bulk_type is not None:
        for tx in transactions:
            remb.check_transaction_change(db, tx, bulk_type, tx.amount, False)
```

`delete_transaction`, remplacer `db.delete(transaction)` / `db.commit()` par :

```python
    others = remb.detach_before_delete(db, transaction)
    db.delete(transaction)
    remb.sync_offsets(db, others)
    db.commit()
```

`link_transactions`, juste avant `link_pair(db, tx1, other, type, "manual")` :

```python
    if remb.has_reimbursement(db, tx1.id) or (type == "regular" and remb.has_reimbursement(db, other.id)):
        raise HTTPException(status_code=400, detail="Une transaction qui porte des remboursements ne peut pas être un virement interne")
```

`create_transfer_counterpart`, après le contrôle `tx.type != "Sortie"` :

```python
    if remb.has_reimbursement(db, tx.id):
        raise HTTPException(status_code=400, detail="Une transaction qui porte des remboursements ne peut pas être un virement interne")
```

- [ ] **Step 4: Exclure dans `core/transfers.py`**

Import en tête : `from app.core.reimbursements import locked_transaction_ids`. Le moteur `reimbursements` n'importe pas `transfers` : pas de cycle.

Dans `find_pairs`, ajouter `Transaction.id.notin_(locked_transaction_ids()),` aux filtres de `sorties_q` et de la requête des `Entree` (`if want_regular:`).

Dans `candidates_for`, juste après le calcul de `reference` :

```python
    if db.query(Transaction.id).filter(Transaction.id == tx.id, Transaction.id.in_(locked_transaction_ids())).first():
        return []
```

et, dans la boucle `for model, type_, kind in wanted:`, pour `model is Transaction` uniquement :

```python
        if model is Transaction:
            q = q.filter(Transaction.id.notin_(locked_transaction_ids()))
```

- [ ] **Step 5: Lancer les tests**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app backend/tests/test_reimbursements.py
git commit -m "feat(remboursements): garde-fous sur les transactions et exclusion des virements

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: KPI nets

**Files:**
- Modify: `backend/app/api/analytics/utils.py`, `metrics.py`, `budget.py`, `reports.py`, `insights.py`
- Create: `backend/tests/test_reimbursement_kpis.py`

**Interfaces:**
- Consumes: colonne `Transaction.reimbursement_offset` (Task 1), `app.core.reimbursements` (Task 1).
- Produces: `NET_AMOUNT` (expression SQLAlchemy) et `net_amount(tx: Transaction) -> float` dans `app.api.analytics.utils`.

- [ ] **Step 1: Tests (échouent)**

`backend/tests/test_reimbursement_kpis.py` :

```python
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.core import reimbursements as remb
from app.core.finance import month_label_from_date
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction


def _tx(db, account, type_, amount, date, merchant, category=None):
    t = Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_, merchant=merchant,
        amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
        category_id=category.id if category else None,
    )
    db.add(t)
    db.commit()
    return t


@pytest.fixture()
def scenario(db_session: Session):
    main = Account(name="Principal", type="courant", currency="EUR", active=True)
    resto_cat = Category(name="Restaurants", type="depense")
    remb_cat = Category(name="Remboursement (recu)", type="revenu")
    db_session.add_all([main, resto_cat, remb_cat])
    db_session.commit()
    sortie = _tx(db_session, main, "Sortie", 90.0, datetime(2026, 9, 28), "RESTO", resto_cat)
    entree = _tx(db_session, main, "Entree", 30.0, datetime(2026, 10, 3), "VIR DENIS", remb_cat)
    claim = remb.create_claim(db_session, sortie.id, "Denis", 30.0)
    remb.create_claim(db_session, sortie.id, "Julie", 30.0)
    remb.allocate(db_session, claim, entree.id)
    return main, sortie, entree


def test_budget_is_net_on_expense_month(client, scenario):
    sept = client.get("/analytics/budget", params={"month": 9, "year": 2026}).json()
    octo = client.get("/analytics/budget", params={"month": 10, "year": 2026}).json()
    assert sept["depenses_totales"] == 60.0
    assert octo["revenus_totaux"] == 0.0


def test_expenses_by_category_and_top_merchants_are_net(client, scenario):
    cats = client.get("/analytics/expenses-by-category", params={"month": 9, "year": 2026}).json()
    assert {i["category"]["name"]: i["total"] for i in cats["items"]}["Restaurants"] == 60.0
    top = client.get("/analytics/top-merchants", params={"month": 9, "year": 2026}).json()
    assert {i["merchant"]: i["total"] for i in top["items"]}["RESTO"] == 60.0


def test_timeseries_and_money_flow_are_net(client, scenario):
    flows = {f["month"]: f for f in client.get("/analytics/timeseries", params={"year": 2026}).json()["monthly_flows"]}
    assert flows[9]["expense"] == 60.0
    assert flows[10]["income"] == 0.0
    sept = client.get("/analytics/money-flow", params={"month": 9, "year": 2026}).json()
    assert sept["fixed_charges"]["amount"] + sept["variable_expenses"]["amount"] == 60.0
    assert client.get("/analytics/money-flow", params={"month": 10, "year": 2026}).json()["income"] == 0.0


def test_raw_cash_endpoints_are_unchanged(client, scenario):
    main, _, _ = scenario
    flow = client.get("/analytics/account-flow-summary", params={"account_id": main.id}).json()
    assert flow["avg_expense"] == 90.0


def test_partial_allocation_counts_remainder_as_income(client, db_session, scenario):
    main, sortie, _ = scenario
    big = _tx(db_session, main, "Entree", 50.0, datetime(2026, 10, 10), "VIR JULIE")
    julie = next(c for c in sortie.claims if c.debtor == "Julie")
    remb.allocate(db_session, julie, big.id)  # 30 affectés, 20 restent un revenu
    octo = client.get("/analytics/budget", params={"month": 10, "year": 2026}).json()
    assert octo["revenus_totaux"] == 20.0
    sept = client.get("/analytics/budget", params={"month": 9, "year": 2026}).json()
    assert sept["depenses_totales"] == 30.0
```

Si `/analytics/timeseries` ne renvoie pas les mois passés de 2026 parce qu'ils sont « futurs » par rapport à la date du jour, dater le scénario en 2025 (septembre/octobre) dans tout le fichier.

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_reimbursement_kpis.py -q` → FAIL (90 au lieu de 60).

- [ ] **Step 2: Définition unique**

Dans `backend/app/api/analytics/utils.py`, après les imports :

```python
# Montant « économique » : brut moins la part remboursée (Sortie) ou affectée à une créance (Entree).
# Les KPI de revenus/dépenses l'utilisent ; les flux de trésorerie (soldes, calendrier) restent en brut.
NET_AMOUNT = Transaction.amount - Transaction.reimbursement_offset


def net_amount(tx: Transaction) -> float:
    return float(tx.amount) - float(tx.reimbursement_offset or 0.0)
```

- [ ] **Step 3: Remplacer dans les endpoints « nets »**

Dans chaque fichier, importer `NET_AMOUNT` (et `net_amount` si besoin) depuis `app.api.analytics.utils`, puis remplacer `Transaction.amount` par `NET_AMOUNT` dans les `func.sum(...)` ci-dessous (numéros de ligne au moment de l'écriture du plan, vérifier avec `grep -n "func.sum(Transaction.amount)"`) :

| Fichier | Lignes | Endpoint |
|---|---|---|
| `metrics.py` | 91 | `/tags` |
| `metrics.py` | 149 | `/expenses-by-category` |
| `metrics.py` | 251 | `/top-merchants` |
| `metrics.py` | 389, 446, 468 | `/kpi-history` |
| `metrics.py` | 577, 586 | `/timeseries` (revenus, dépenses) — **pas** 670 (série salaire) |
| `budget.py` | 93, 137, 172, 210, 435, 454, 473 | `/budget` |
| `budget.py` | 562, 587 | `/budget-alerts` |
| `reports.py` | 325, 479, 510 | `/money-flow`, `/monthly-report` (via `_calculate_money_flow_data`), `/sankey` |

Ne **pas** toucher : `metrics.py` 309 et 329 (`/account-flow-summary`), 670 (salaire), 847 et 862 (`/calendar`), `reports.py` `/cashflow-projection`, `subscriptions.py`, `audit.py`, `tax`.

Remplacer `tx.amount` par `net_amount(tx)` dans : `reports.py:377` (`amount_eur = net_amount(tx) / rates.get(tx.currency, 1.0)`) et `insights.py:182` (`val_eur = net_amount(tx) / rates.get(curr, 1.0)`).

Puis vérifier qu'aucune autre boucle Python de ces quatre fichiers ne somme `tx.amount` pour un revenu ou une dépense : `grep -n "\.amount" backend/app/api/analytics/{metrics,budget,reports,insights}.py | grep -v InvestmentTransaction`. Toute ligne restante qui alimente un total revenus/dépenses d'un endpoint « net » passe à `net_amount(...)`.

- [ ] **Step 4: Lancer les tests**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests -q`
Expected: PASS (les tests existants ne créent aucune créance : offset 0, résultats identiques).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/analytics backend/tests/test_reimbursement_kpis.py
git commit -m "feat(remboursements): KPI revenus et dépenses nets des remboursements

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Centre d'Actions, MCP et documentation backend

**Files:**
- Modify: `backend/app/api/analytics/audit.py` (`data_audit`, avant le calcul de `high_count`), `backend/tests/test_reimbursement_kpis.py`, `mcp-server/server_api.py`, `mcp-server/README.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `.claude/skills/numera-expert/SKILL.md`, `docs/ACTION_CENTER.md`

**Interfaces:**
- Consumes: Tasks 1–2 (`ReimbursementClaim`, `claim_received`, routes HTTP).
- Produces: issue d'audit `id="unallocated-reimbursements"`, `type="reimbursements"`, `action_url="/reimbursements"`.

- [ ] **Step 1: Test d'audit (échoue)**

Ajouter à `backend/tests/test_reimbursement_kpis.py` :

```python
def test_audit_flags_unallocated_reimbursements(client, db_session, scenario):
    main, _, _ = scenario
    cat = db_session.query(Category).filter(Category.name == "Remboursement (recu)").one()
    from app.core.time import utcnow_naive
    _tx(db_session, main, "Entree", 12.0, utcnow_naive(), "CPAM", cat)
    issues = {i["id"]: i for i in client.get("/analytics/audit").json()["issues"]}
    assert issues["unallocated-reimbursements"]["count"] == 1
    assert issues["unallocated-reimbursements"]["action_url"] == "/reimbursements"


def test_audit_silent_without_open_claim(client, db_session):
    main = Account(name="P", type="courant", currency="EUR", active=True)
    cat = Category(name="Remboursement (recu)", type="revenu")
    db_session.add_all([main, cat])
    db_session.commit()
    from app.core.time import utcnow_naive
    _tx(db_session, main, "Entree", 12.0, utcnow_naive(), "CPAM", cat)
    ids = {i["id"] for i in client.get("/analytics/audit").json()["issues"]}
    assert "unallocated-reimbursements" not in ids
```

Vérifier dans `data_audit` le nom exact de la liste renvoyée (`issues`) et de l'URL de l'endpoint (`/analytics/audit`) ; ajuster le test si besoin.

Run → FAIL (`KeyError`).

- [ ] **Step 2: Issue d'audit**

Dans `data_audit` (`audit.py`), juste avant `high_count = ...` (imports : `from app.core import reimbursements as remb`, `from app.models.reimbursement import ReimbursementClaim`) :

```python
    has_open_claim = any(
        remb.claim_received(db, claim.id) < claim.expected_amount - remb.EPS
        for claim in db.query(ReimbursementClaim).all()
    )
    if has_open_claim:
        unallocated = (
            db.query(Transaction)
            .join(Category, Transaction.category_id == Category.id)
            .filter(
                Transaction.type == "Entree",
                Category.name.ilike("Remboursement%"),
                Transaction.reimbursement_offset == 0,
                Transaction.is_transfer.is_(False),
                Transaction.date >= now - timedelta(days=180),
            )
            .order_by(Transaction.date.desc())
            .all()
        )
        if unallocated:
            issues.append(DataAuditIssue(
                id="unallocated-reimbursements",
                type="reimbursements",
                severity="low",
                title="Remboursements à affecter",
                description="Ces remboursements reçus ne sont rattachés à aucune créance : ils comptent encore comme revenus et la dépense d'origine reste comptée en entier.",
                count=len(unallocated),
                action_label="Affecter",
                action_url="/reimbursements",
                samples=[_tx_sample(t) for t in unallocated[:5]],
            ))
```

(`now`, `timedelta`, `Category`, `_tx_sample` sont déjà disponibles dans `audit.py` ; vérifier par `grep -n "^from\|^import\|now = " backend/app/api/analytics/audit.py` et importer ce qui manque.)

Ajouter dans `data_audit_issue_details` une branche `if issue_id == "unallocated-reimbursements":` qui renvoie les mêmes transactions (même requête, sans limite de 5) au format des branches voisines.

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests -q` → PASS.

- [ ] **Step 3: Outils MCP**

Dans `mcp-server/server_api.py`, juste avant `@mcp.tool()\ndef add_holding(` :

```python
@mcp.tool()
def list_reimbursement_claims(status: str = "open", debtor: str | None = None) -> str:
    """Créances de remboursement (« ce qu'on me doit ») : dépense, débiteur, attendu, reçu, reste dû.
    `status` : open (reste dû > 0, défaut), settled ou all."""
    try:
        params = {"status": status}
        if debtor:
            params["debtor"] = debtor
        resp = api.get("/reimbursements/claims", params=params)
        error = handle_response(resp)
        if error:
            return error
        rows = [
            {
                "id": c["id"],
                "date": c["expense"]["date"][:10],
                "depense": c["expense"]["label"],
                "debiteur": c["debtor"],
                "attendu": c["expected_amount"],
                "recu": c["received"],
                "reste_du": c["remaining"],
            }
            for c in resp.json()
        ]
        total = round(sum(r["reste_du"] for r in rows), 2)
        return f"💸 {len(rows)} créance(s), {total} restant dû :\n\n" + (format_table(rows) if rows else "Aucune créance.")
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def create_reimbursement_claim(transaction_id: int, debtor: str, expected_amount: float, note: str | None = None) -> str:
    """Déclare qu'une dépense (Sortie) doit être remboursée en partie ou en totalité par `debtor`.
    Le total des créances d'une dépense ne peut pas dépasser son montant."""
    try:
        resp = api.post("/reimbursements/claims", json_data={
            "transaction_id": transaction_id, "debtor": debtor, "expected_amount": expected_amount, "note": note,
        })
        error = handle_response(resp)
        if error:
            return error
        return f"✅ Créance #{resp.json()['id']} créée ({debtor}, {expected_amount})."
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def allocate_reimbursement(claim_id: int, entree_id: int, amount: float | None = None) -> str:
    """Affecte une entrée (remboursement reçu) à une créance. Sans `amount` : le plus petit entre le reste dû
    et la part non affectée de l'entrée. Les KPI deviennent nets : la dépense baisse, l'entrée n'est plus un revenu."""
    try:
        payload = {"entree_id": entree_id}
        if amount is not None:
            payload["amount"] = amount
        resp = api.post(f"/reimbursements/claims/{claim_id}/allocations", json_data=payload)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"✅ Créance #{claim_id} : {data['received']} reçu, {data['remaining']} restant dû."
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def delete_reimbursement_claim(claim_id: int) -> str:
    """Supprime une créance et ses affectations (abandon d'une créance sans rien de reçu)."""
    try:
        resp = api.delete(f"/reimbursements/claims/{claim_id}")
        error = handle_response(resp)
        if error:
            return error
        return f"✅ Créance #{claim_id} supprimée."
    except Exception as e:
        return f"❌ Erreur : {e}"
```

Vérifier la signature de `api.get` (paramètre `params`) et l'existence de `api.delete` dans la classe client (~l.120-140) ; adapter l'appel si le nom diffère. Puis : `python3.11 -c "import ast;ast.parse(open('mcp-server/server_api.py').read())"`.

- [ ] **Step 4: Documentation**

- `mcp-server/README.md` et `CLAUDE.md` : `49 outils` → `53 outils`.
- `ARCHITECTURE.md` : dans la liste des tables, après `transfer_rules`, ajouter :
  `- \`reimbursement_claims\` (créance : \`transaction_id\` → Sortie, \`debtor\`, \`expected_amount\`, \`note\`) et \`reimbursement_allocations\` (\`claim_id\`, \`entree_transaction_id\`, \`amount\`, unique par couple). \`transactions.reimbursement_offset\` = total remboursé (Sortie) ou affecté (Entree), maintenu par \`core/reimbursements.py\`.`
  Ajouter \`reimbursement_offset\` à la liste des champs de \`transactions\`. Dans les routes, après \`/transfer-rules\` :
  `- \`/reimbursements\` : \`GET /claims?status=open|settled|all&debtor=\`, \`GET /summary\`, \`POST /claims\`, \`PATCH|DELETE /claims/{id}\`, \`GET /claims/{id}/candidates\`, \`POST /claims/{id}/allocations\`, \`DELETE /allocations/{id}\`, \`GET /entries/{entree_id}/claims\``
- `.claude/skills/numera-expert/SKILL.md` : nouvelle section après « Virements internes » :

```markdown
## Remboursements

Une `Sortie` porte des **créances** (`reimbursement_claims` : débiteur libre, montant attendu) ; des `Entree` leur sont **affectées** avec un montant (`reimbursement_allocations`, plusieurs entrées par créance et plusieurs créances par entrée). Tout passe par `core/reimbursements.py`, qui recalcule `transactions.reimbursement_offset` (Sortie : total reçu ; Entree : total affecté).

- KPI revenus/dépenses **nets** sur le mois et la catégorie de la dépense : `NET_AMOUNT = amount − reimbursement_offset` (`api/analytics/utils.py`) dans budget, budget-alerts, expenses-by-category, top-merchants, tags, kpi-history, timeseries, monthly-report, money-flow, sankey, insights. Restent **bruts** : soldes, account-flow-summary, calendar, cashflow-projection, subscriptions, tax.
- Règles : Sortie ↔ Entree, même devise de compte, jamais un virement interne (et `find_pairs` / `candidates_for` / la liaison manuelle excluent ces transactions), plafonds (créances ≤ dépense, affectations ≤ attendu et ≤ entrée), attendu jamais sous le reçu. Modifier le type ou baisser le montant d'une transaction liée est refusé (400) ; supprimer l'une libère l'autre.
- Abandon : ramener l'attendu au reçu, ou supprimer la créance. Pas d'espèces, pas de liaison automatique.
- Centre d'Actions : `unallocated-reimbursements` (entrées « Remboursement… » des 180 derniers jours non affectées, s'il existe une créance ouverte).
```

- `docs/ACTION_CENTER.md` : ajouter `unallocated-reimbursements` à la liste des issues d'audit, avec sa condition (ci-dessus) et son action (`/reimbursements`).

- [ ] **Step 5: Commit**

```bash
git add backend mcp-server CLAUDE.md ARCHITECTURE.md .claude/skills/numera-expert/SKILL.md docs/ACTION_CENTER.md
git commit -m "feat(remboursements): Centre d'Actions, outils MCP et documentation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Frontend — types et dialogue depuis une transaction

**Files:**
- Create: `frontend/src/types/reimbursements.ts`, `frontend/src/components/reimbursements/ReimbursementDialog.tsx`
- Modify: `frontend/src/pages/AccountDetail.tsx` (interface `Transaction` ~l.275-290, état ~l.309, cellule actions ~l.2036, cellule montant ~l.2019, fin du JSX ~l.2400)

**Interfaces:**
- Consumes: routes HTTP de Task 2 ; `TransactionRead.reimbursement_offset`, `has_claims`.
- Produces: `ReimbursementDialog` (`{ open, onOpenChange, transaction: ReimbursableTransaction | null, onDone: () => void }`) et les types de `types/reimbursements.ts` (utilisés par Task 7).

- [ ] **Step 1: Types**

`frontend/src/types/reimbursements.ts` :

```ts
export interface ExpenseRef {
  id: number
  account_id: number
  date: string
  label: string
  amount: number
}

export interface ClaimAllocation {
  id: number
  entree_id: number
  amount: number
  date: string | null
  label: string | null
  account_id: number | null
}

export interface Claim {
  id: number
  debtor: string
  expected_amount: number
  received: number
  remaining: number
  note: string | null
  created_at: string
  currency: string
  expense: ExpenseRef
  allocations: ClaimAllocation[]
}

export interface DebtorDue {
  debtor: string
  claims: number
  due: number
}

export interface ReimbursementSummary {
  total_due: number
  debtors: DebtorDue[]
}

export interface ClaimCandidate {
  id: number
  account_id: number
  date: string
  label: string
  amount: number
  available: number
  day_gap: number
  debtor_match: boolean
}

export interface EntryClaims {
  entree_id: number
  amount: number
  available: number
  open_claims: Claim[]
  allocations: { id: number; claim_id: number; amount: number; debtor: string }[]
}

export interface ReimbursableTransaction {
  id: number
  type: string
  merchant: string
  date: string
  amount: number
  currency: string
}
```

- [ ] **Step 2: Dialogue**

`frontend/src/components/reimbursements/ReimbursementDialog.tsx` :

```tsx
import { useCallback, useEffect, useState } from "react"
import { HandCoins, Plus, Trash2, Users } from "lucide-react"
import { format } from "date-fns"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { api, ApiError } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { Claim, EntryClaims, ReimbursableTransaction } from "@/types/reimbursements"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  transaction: ReimbursableTransaction | null
  onDone: () => void
}

const parseAmount = (value: string) => parseFloat(value.replace(",", "."))
const errorMessage = (e: unknown, fallback: string) => (e instanceof ApiError && e.message ? e.message : fallback)

export function ReimbursementDialog({ open, onOpenChange, transaction, onDone }: Props) {
  const [claims, setClaims] = useState<Claim[]>([])
  const [entry, setEntry] = useState<EntryClaims | null>(null)
  const [debtor, setDebtor] = useState("")
  const [expected, setExpected] = useState("")
  const [splitCount, setSplitCount] = useState("2")
  const [allocInputs, setAllocInputs] = useState<Record<number, string>>({})

  const isSortie = transaction?.type === "Sortie"

  const load = useCallback(async () => {
    if (!transaction) return
    try {
      if (transaction.type === "Sortie") {
        const all = await api.get<Claim[]>("/reimbursements/claims?status=all")
        setClaims(all.filter((c) => c.expense.id === transaction.id))
      } else {
        setEntry(await api.get<EntryClaims>(`/reimbursements/entries/${transaction.id}/claims`))
      }
    } catch {
      toast.error("Erreur lors du chargement des remboursements")
    }
  }, [transaction])

  useEffect(() => {
    if (open) {
      setDebtor("")
      setExpected("")
      setAllocInputs({})
      load()
    }
  }, [open, load])

  const declared = claims.reduce((sum, c) => sum + c.expected_amount, 0)

  async function addClaim(name: string, amount: number) {
    if (!transaction) return
    await api.post("/reimbursements/claims", { transaction_id: transaction.id, debtor: name, expected_amount: amount })
  }

  async function handleAdd() {
    const amount = parseAmount(expected)
    if (!debtor.trim() || !(amount > 0)) {
      toast.error("Indiquez un débiteur et un montant")
      return
    }
    try {
      await addClaim(debtor.trim(), amount)
      toast.success("Créance ajoutée")
      setDebtor("")
      setExpected("")
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, "Impossible d'ajouter la créance"))
    }
  }

  async function handleSplit() {
    if (!transaction) return
    const n = parseInt(splitCount)
    if (!(n >= 2)) {
      toast.error("Indiquez au moins 2 personnes (vous compris)")
      return
    }
    // La dépense est partagée entre n personnes dont vous : n − 1 créances d'une part chacune
    const share = Math.floor((transaction.amount / n) * 100) / 100
    try {
      for (let i = 1; i < n; i++) await addClaim(`Personne ${i}`, share)
      toast.success(`${n - 1} créances de ${formatCurrency(share, transaction.currency)} ajoutées : renommez les débiteurs`)
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, "Impossible de répartir la dépense"))
    }
  }

  async function handleDeleteClaim(claim: Claim) {
    if (!confirm(`Supprimer la créance de ${claim.debtor} ?`)) return
    try {
      await api.delete(`/reimbursements/claims/${claim.id}`)
      toast.success("Créance supprimée")
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, "Échec de la suppression"))
    }
  }

  async function handleRename(claim: Claim, name: string) {
    if (!name.trim() || name.trim() === claim.debtor) return
    try {
      await api.patch(`/reimbursements/claims/${claim.id}`, { debtor: name.trim() })
      load()
    } catch (e) {
      toast.error(errorMessage(e, "Échec de la modification"))
    }
  }

  async function handleAllocate(claim: Claim) {
    if (!transaction) return
    const raw = allocInputs[claim.id]
    const amount = raw ? parseAmount(raw) : undefined
    try {
      await api.post(`/reimbursements/claims/${claim.id}/allocations`, { entree_id: transaction.id, ...(amount ? { amount } : {}) })
      toast.success(`Remboursement affecté à ${claim.debtor}`)
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, "Échec de l'affectation"))
    }
  }

  async function handleRemoveAllocation(id: number) {
    try {
      await api.delete(`/reimbursements/allocations/${id}`)
      toast.success("Affectation retirée")
      load()
      onDone()
    } catch (e) {
      toast.error(errorMessage(e, "Échec de l'action"))
    }
  }

  if (!transaction) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <HandCoins className="h-5 w-5 text-emerald-600" />
            {isSortie ? "On me doit" : "Affecter un remboursement"}
          </DialogTitle>
          <DialogDescription>
            {transaction.merchant} · {format(new Date(transaction.date), "dd/MM/yyyy")} ·{" "}
            <span className="amount-blur">{formatCurrency(transaction.amount, transaction.currency)}</span>
          </DialogDescription>
        </DialogHeader>

        {isSortie ? (
          <div className="space-y-4">
            <div className="divide-y divide-slate-100 rounded-xl border border-slate-100">
              {claims.map((c) => (
                <div key={c.id} className="space-y-1 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <Input defaultValue={c.debtor} className="h-8 max-w-[12rem]" onBlur={(e) => handleRename(c, e.target.value)} />
                    <span className="text-sm text-slate-600">
                      <span className="amount-blur font-semibold text-emerald-600">{formatCurrency(c.received, c.currency)}</span>
                      {" / "}
                      <span className="amount-blur">{formatCurrency(c.expected_amount, c.currency)}</span>
                    </span>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-slate-400 hover:text-red-600" onClick={() => handleDeleteClaim(c)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                  {c.allocations.map((a) => (
                    <p key={a.id} className="text-xs text-slate-500">
                      {a.date ? format(new Date(a.date), "dd/MM/yyyy") : ""} · {a.label} ·{" "}
                      <span className="amount-blur">{formatCurrency(a.amount, c.currency)}</span>
                    </p>
                  ))}
                </div>
              ))}
              {claims.length === 0 && <p className="p-4 text-center text-sm italic text-slate-400">Aucune créance sur cette dépense.</p>}
            </div>
            <p className="text-xs text-slate-500">
              Déclaré : <span className="amount-blur">{formatCurrency(declared, transaction.currency)}</span> sur{" "}
              <span className="amount-blur">{formatCurrency(transaction.amount, transaction.currency)}</span>
            </p>
            <div className="grid grid-cols-[1fr_8rem_auto] items-end gap-2">
              <div className="grid gap-1">
                <Label htmlFor="claim-debtor">Qui me doit</Label>
                <Input id="claim-debtor" value={debtor} onChange={(e) => setDebtor(e.target.value)} placeholder="Denis, Sécu…" />
              </div>
              <div className="grid gap-1">
                <Label htmlFor="claim-amount">Montant</Label>
                <Input id="claim-amount" inputMode="decimal" value={expected} onChange={(e) => setExpected(e.target.value)} />
              </div>
              <Button className="gap-2" onClick={handleAdd}>
                <Plus className="h-4 w-4" />
                Ajouter
              </Button>
            </div>
            {claims.length === 0 && (
              <div className="flex items-end gap-2 rounded-xl bg-slate-50 p-3">
                <div className="grid gap-1">
                  <Label htmlFor="claim-split">Partager à parts égales entre (vous compris)</Label>
                  <Input id="claim-split" inputMode="numeric" className="w-24" value={splitCount} onChange={(e) => setSplitCount(e.target.value)} />
                </div>
                <Button variant="outline" className="gap-2" onClick={handleSplit}>
                  <Users className="h-4 w-4" />
                  Répartir
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-slate-600">
              Disponible : <span className="amount-blur font-semibold">{formatCurrency(entry?.available ?? 0, transaction.currency)}</span>
            </p>
            {entry?.allocations.map((a) => (
              <div key={a.id} className="flex items-center justify-between rounded-lg bg-emerald-50 px-3 py-2 text-sm">
                <span>
                  Affecté à {a.debtor} : <span className="amount-blur font-semibold">{formatCurrency(a.amount, transaction.currency)}</span>
                </span>
                <Button variant="ghost" size="sm" onClick={() => handleRemoveAllocation(a.id)}>Retirer</Button>
              </div>
            ))}
            <div className="max-h-72 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-100">
              {entry?.open_claims.map((c) => (
                <div key={c.id} className="flex items-center justify-between gap-3 p-3">
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900">{c.debtor}</p>
                    <p className="truncate text-xs text-slate-500">
                      {format(new Date(c.expense.date), "dd/MM/yyyy")} · {c.expense.label} · reste{" "}
                      <span className="amount-blur">{formatCurrency(c.remaining, c.currency)}</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      inputMode="decimal"
                      className="h-8 w-24"
                      placeholder={String(Math.min(c.remaining, entry.available))}
                      value={allocInputs[c.id] ?? ""}
                      onChange={(e) => setAllocInputs({ ...allocInputs, [c.id]: e.target.value })}
                    />
                    <Button size="sm" onClick={() => handleAllocate(c)}>Affecter</Button>
                  </div>
                </div>
              ))}
              {entry && entry.open_claims.length === 0 && (
                <p className="p-4 text-center text-sm italic text-slate-400">Aucune créance ouverte. Déclarez-la d'abord sur la dépense.</p>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
```

Vérifier que `ApiError` est bien exporté par `@/lib/api` et qu'il expose `message` (cf. `frontend/src/CLAUDE.md` : `ApiError(status, message, detail)`) ; sinon utiliser le message de repli seul.

- [ ] **Step 3: Intégration dans `AccountDetail.tsx`**

1. Interface `Transaction` (~l.289) : ajouter `reimbursement_offset?: number`, `reimbursement_expected?: number` et `has_claims?: boolean`.
2. Imports : `import { HandCoins } from "lucide-react"` (dans l'import lucide existant) et `import { ReimbursementDialog } from "@/components/reimbursements/ReimbursementDialog"`.
3. État, à côté de `transferTx` (~l.309) : `const [reimbursementTx, setReimbursementTx] = useState<Transaction | null>(null)`.
4. Cellule des actions, juste avant le bouton virement (`{(tx.type === "Sortie" || tx.type === "Entree") && (`) :

```tsx
                        {(tx.type === "Sortie" || tx.type === "Entree") && !tx.is_transfer && (
                          <Button
                            variant="ghost"
                            size="sm"
                            title={tx.type === "Sortie" ? "On me doit…" : "Affecter à une créance…"}
                            onClick={() => setReimbursementTx(tx)}
                            className="h-8 w-8 p-0"
                          >
                            <HandCoins className={`h-3.5 w-3.5 ${tx.has_claims || (tx.reimbursement_offset ?? 0) > 0 ? "text-emerald-600" : "text-slate-400"}`} />
                          </Button>
                        )}
```

5. Cellule du montant : après le `<span className="amount-blur">…{formatCurrency(tx.amount)}</span>` principal, ajouter :

```tsx
                        {(tx.reimbursement_offset ?? 0) > 0 && (
                          <span className="text-[10px] font-normal text-slate-400 amount-blur">
                            net {formatCurrency(tx.amount - (tx.reimbursement_offset ?? 0))}
                          </span>
                        )}
                        {tx.type === "Sortie" && tx.has_claims && (() => {
                          const received = tx.reimbursement_offset ?? 0
                          const expected = tx.reimbursement_expected ?? 0
                          const [label, tone] = received <= 0
                            ? ["À rembourser", "bg-amber-50 text-amber-700"]
                            : received < expected - 0.005
                              ? ["Partiel", "bg-sky-50 text-sky-700"]
                              : ["Remboursé", "bg-emerald-50 text-emerald-700"]
                          return <Badge variant="outline" className={`mt-0.5 border-none px-1 py-0 text-[10px] ${tone}`}>{label}</Badge>
                        })()}
```

6. À côté de `<TransferLinkDialog …/>` (~l.2400) :

```tsx
      <ReimbursementDialog
        open={reimbursementTx !== null}
        onOpenChange={(o) => !o && setReimbursementTx(null)}
        transaction={reimbursementTx}
        onDone={loadTransactions}
      />
```

- [ ] **Step 4: Vérifier**

Run: `cd frontend && npm run build`
Expected: build sans erreur TS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat(remboursements): dialogue « On me doit » sur les transactions

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Frontend — page Remboursements et navigation

**Files:**
- Create: `frontend/src/pages/Reimbursements.tsx`, `frontend/src/components/reimbursements/ClaimCandidatesDialog.tsx`
- Modify: `frontend/src/App.tsx` (import + route après `/recurring`), `frontend/src/components/layout/Sidebar.tsx` (groupe « Analyse & Outils », après « Récurrences »), `frontend/src/components/layout/Omnibox.tsx` (liste de navigation ~l.30-38), `ROADMAP.md`

**Interfaces:**
- Consumes: types de Task 6 (`Claim`, `ReimbursementSummary`, `ClaimCandidate`), routes HTTP de Task 2, `api.get<AccountLite[]>("/accounts")` et `AccountLite` de `@/types/transfers`.

- [ ] **Step 1: Dialogue des candidates**

`frontend/src/components/reimbursements/ClaimCandidatesDialog.tsx` :

```tsx
import { useEffect, useState } from "react"
import { format } from "date-fns"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { api, ApiError } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { Claim, ClaimCandidate } from "@/types/reimbursements"

interface Props {
  claim: Claim | null
  accountName: (id: number) => string
  onOpenChange: (open: boolean) => void
  onDone: () => void
}

export function ClaimCandidatesDialog({ claim, accountName, onOpenChange, onDone }: Props) {
  const [candidates, setCandidates] = useState<ClaimCandidate[] | null>(null)

  useEffect(() => {
    if (!claim) return
    setCandidates(null)
    api.get<ClaimCandidate[]>(`/reimbursements/claims/${claim.id}/candidates`)
      .then(setCandidates)
      .catch(() => toast.error("Erreur lors de la recherche des remboursements"))
  }, [claim])

  async function link(c: ClaimCandidate) {
    if (!claim) return
    try {
      await api.post(`/reimbursements/claims/${claim.id}/allocations`, { entree_id: c.id })
      toast.success("Remboursement lié")
      onDone()
    } catch (e) {
      toast.error(e instanceof ApiError && e.message ? e.message : "Échec de la liaison")
    }
  }

  return (
    <Dialog open={claim !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Lier un remboursement</DialogTitle>
          <DialogDescription>
            {claim?.debtor} · reste <span className="amount-blur">{claim ? formatCurrency(claim.remaining, claim.currency) : ""}</span> · {claim?.expense.label}
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-96 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-100">
          {candidates === null && <p className="p-6 text-center text-sm text-slate-400">Recherche…</p>}
          {candidates?.map((c) => (
            <div key={c.id} className="flex items-center justify-between gap-3 p-3">
              <div className="min-w-0">
                <p className="flex items-center gap-2 truncate font-medium text-slate-900">
                  {c.label}
                  {c.debtor_match && <Badge variant="outline" className="border-emerald-100 bg-emerald-50 px-1 py-0 text-[10px] text-emerald-700">Débiteur reconnu</Badge>}
                </p>
                <p className="text-xs text-slate-500">
                  {format(new Date(c.date), "dd/MM/yyyy")} · {accountName(c.account_id)} · disponible{" "}
                  <span className="amount-blur">{formatCurrency(c.available, claim?.currency)}</span>
                </p>
              </div>
              <Button size="sm" onClick={() => link(c)}>Lier</Button>
            </div>
          ))}
          {candidates?.length === 0 && (
            <p className="p-6 text-center text-sm italic text-slate-400">Aucune entrée disponible entre 7 jours avant et 180 jours après la dépense.</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 2: Page**

`frontend/src/pages/Reimbursements.tsx` :

```tsx
import { useCallback, useEffect, useState } from "react"
import { HandCoins, Link, Pencil, Trash2 } from "lucide-react"
import { format } from "date-fns"
import { toast } from "sonner"

import { ClaimCandidatesDialog } from "@/components/reimbursements/ClaimCandidatesDialog"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { Claim, ReimbursementSummary } from "@/types/reimbursements"
import type { AccountLite } from "@/types/transfers"

export default function Reimbursements() {
  const [status, setStatus] = useState<"open" | "settled">("open")
  const [debtor, setDebtor] = useState<string | null>(null)
  const [claims, setClaims] = useState<Claim[]>([])
  const [summary, setSummary] = useState<ReimbursementSummary | null>(null)
  const [accounts, setAccounts] = useState<AccountLite[]>([])
  const [loading, setLoading] = useState(true)
  const [linking, setLinking] = useState<Claim | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ status })
      if (debtor) params.set("debtor", debtor)
      const [c, s, a] = await Promise.all([
        api.get<Claim[]>(`/reimbursements/claims?${params}`),
        api.get<ReimbursementSummary>("/reimbursements/summary"),
        api.get<AccountLite[]>("/accounts"),
      ])
      setClaims(c)
      setSummary(s)
      setAccounts(a)
    } catch {
      toast.error("Erreur lors du chargement des remboursements")
    } finally {
      setLoading(false)
    }
  }, [status, debtor])

  useEffect(() => {
    load()
  }, [load])

  const accountName = (id: number) => accounts.find((a) => a.id === id)?.name ?? "Compte inconnu"

  async function editExpected(claim: Claim) {
    const value = prompt(`Montant attendu de ${claim.debtor} (reçu : ${claim.received})`, String(claim.expected_amount))
    if (value === null) return
    const amount = parseFloat(value.replace(",", "."))
    if (!(amount > 0)) return
    try {
      await api.patch(`/reimbursements/claims/${claim.id}`, { expected_amount: amount })
      toast.success("Créance modifiée")
      load()
    } catch {
      toast.error("Le montant attendu ne peut pas être inférieur au montant reçu")
    }
  }

  async function remove(claim: Claim) {
    if (!confirm(`Supprimer la créance de ${claim.debtor} ? La dépense redevient entièrement à votre charge.`)) return
    try {
      await api.delete(`/reimbursements/claims/${claim.id}`)
      toast.success("Créance supprimée")
      load()
    } catch {
      toast.error("Échec de la suppression")
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-8">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-black text-slate-900">
          <HandCoins className="h-6 w-6 text-emerald-600" />
          Remboursements
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Dépenses avancées pour d'autres et ce qu'on vous doit encore. Les remboursements liés sont déduits de vos dépenses, sur le mois de la dépense.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-slate-100 shadow-sm">
          <CardContent className="p-4">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">On me doit</p>
            <p className="mt-1 text-2xl font-black text-emerald-600 amount-blur">{formatCurrency(summary?.total_due ?? 0)}</p>
          </CardContent>
        </Card>
        {summary?.debtors.map((d) => (
          <button
            key={d.debtor}
            type="button"
            onClick={() => setDebtor(debtor === d.debtor ? null : d.debtor)}
            className={`rounded-xl border p-4 text-left shadow-sm transition-colors ${debtor === d.debtor ? "border-emerald-300 bg-emerald-50" : "border-slate-100 bg-white hover:border-emerald-200"}`}
          >
            <p className="font-bold text-slate-900">{d.debtor}</p>
            <p className="text-sm text-slate-500">
              <span className="amount-blur font-semibold text-slate-700">{formatCurrency(d.due)}</span> · {d.claims} créance{d.claims > 1 ? "s" : ""}
            </p>
          </button>
        ))}
      </div>

      <Tabs value={status} onValueChange={(v) => setStatus(v as "open" | "settled")}>
        <TabsList>
          <TabsTrigger value="open">À recevoir</TabsTrigger>
          <TabsTrigger value="settled">Soldées</TabsTrigger>
        </TabsList>
      </Tabs>

      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
        </div>
      ) : claims.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-12 text-center text-sm text-slate-400">
          <HandCoins className="mx-auto mb-3 h-8 w-8 text-slate-300" />
          {status === "open"
            ? "Personne ne vous doit rien. Déclarez une créance depuis une dépense (icône « On me doit » dans le détail d'un compte)."
            : "Aucune créance soldée."}
        </div>
      ) : (
        <div className="grid gap-3">
          {claims.map((c) => {
            const pct = c.expected_amount > 0 ? Math.min(100, (c.received / c.expected_amount) * 100) : 0
            return (
              <Card key={c.id} className="border-slate-100 shadow-sm">
                <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
                  <div className="min-w-0 flex-1 space-y-1">
                    <p className="font-bold text-slate-900">{c.debtor}</p>
                    <p className="truncate text-xs text-slate-500">
                      {format(new Date(c.expense.date), "dd/MM/yyyy")} · {c.expense.label} · {accountName(c.expense.account_id)} ·{" "}
                      <span className="amount-blur">{formatCurrency(c.expense.amount, c.currency)}</span>
                    </p>
                    <div className="h-1.5 w-full max-w-sm overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-emerald-500" style={{ width: `${pct}%` }} />
                    </div>
                    <p className="text-xs text-slate-500">
                      <span className="amount-blur">{formatCurrency(c.received, c.currency)}</span> reçu sur{" "}
                      <span className="amount-blur">{formatCurrency(c.expected_amount, c.currency)}</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-right text-lg font-black text-slate-900 amount-blur">{formatCurrency(c.remaining, c.currency)}</span>
                    {c.remaining > 0 && (
                      <Button size="sm" className="gap-2" onClick={() => setLinking(c)}>
                        <Link className="h-4 w-4" />
                        Lier un remboursement
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-slate-400 hover:text-indigo-600" onClick={() => editExpected(c)} aria-label="Modifier le montant attendu">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-slate-400 hover:text-red-600" onClick={() => remove(c)} aria-label="Supprimer la créance">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <ClaimCandidatesDialog
        claim={linking}
        accountName={accountName}
        onOpenChange={(o) => !o && setLinking(null)}
        onDone={() => {
          setLinking(null)
          load()
        }}
      />
    </div>
  )
}
```

Vérifier que `components/ui/tabs` et `components/ui/skeleton` existent (`ls frontend/src/components/ui`), et que les autres pages exportent `default` (sinon aligner l'export sur `App.tsx`).

- [ ] **Step 3: Navigation**

- `App.tsx` : `import Reimbursements from "@/pages/Reimbursements"` et `<Route path="/reimbursements" element={<Reimbursements />} />` après la route `/recurring`.
- `Sidebar.tsx` : ajouter `HandCoins` à l'import lucide et `{ name: "Remboursements", href: "/reimbursements", icon: HandCoins },` après « Récurrences ».
- `Omnibox.tsx` : ajouter `HandCoins` à l'import lucide et `{ name: "Remboursements", href: "/reimbursements", icon: HandCoins },` après « Fiscalité ».
- `ROADMAP.md:119` : remplacer `*(en cours de cadrage)*` du point 2 par `*(réalisé : page Remboursements, KPI nets)*`.

- [ ] **Step 4: Vérifier**

Run: `cd frontend && npm run build` → aucune erreur. Puis `cd backend && PYTHONPATH=. python3.11 -m pytest tests -q` → PASS.

Contrôle manuel (`make dev` ou backend `uvicorn app.main:app --reload --port 8001` + `npm run dev`) : créer une créance depuis une dépense, affecter une entrée, vérifier la page Remboursements, le badge, le mode confidentialité (montants floutés), le thème sombre et la largeur mobile.

- [ ] **Step 5: Commit**

```bash
git add frontend/src ROADMAP.md
git commit -m "feat(remboursements): page « ce qu'on me doit » et navigation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
