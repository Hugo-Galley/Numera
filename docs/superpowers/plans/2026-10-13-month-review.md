# Revue de fin de mois guidée — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un parcours guidé de revue de fin de mois (5 étapes), un marqueur de clôture non bloquant, un drapeau « dépense exceptionnelle » avec lecture « hors exceptionnel » des KPI, une pop-up de rappel sur le Dashboard et deux outils MCP en lecture seule.

**Architecture:** Une table `month_closures` (photo des chiffres à la clôture) et une colonne `transactions.is_exceptional`, créées par une seule migration Alembic. Un nouveau router `/month-review` orchestre les étapes en réutilisant `budget_analytics`, `budget_alerts` et la route de vérification de compte ; la logique pure (bornes du mois, étape 1, chiffres « hors exceptionnel », tolérance de comparaison) vit dans `app/core/month_review.py`. Le frontend ajoute une page `/month-review`, une pop-up sur le Dashboard et une case dans l'éditeur de transaction.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, pytest · React 18, TypeScript, Tailwind, shadcn/Radix, react-router v7 · FastMCP.

**Spec:** `docs/superpowers/specs/2026-10-13-month-review-design.md`

## Global Constraints

- Python 3.11 ou 3.12 (pas 3.14) ; tests : `cd backend && PYTHONPATH=. python3.11 -m pytest <cible> -v` (`PYTHONPATH=.` obligatoire).
- Montants toujours positifs, le sens est porté par `type`. KPI calculés côté backend uniquement ; le frontend n'affiche que ce que renvoie l'API.
- Schéma modifié → migration Alembic dans `backend/alembic/versions/` (tête actuelle : `a7d4c1e9b3f2`).
- Un nouveau router est ajouté à `protected_routers` de `backend/app/main.py` (JWT obligatoire).
- MCP en lecture seule : aucun outil d'écriture, uniquement des routes `GET`.
- Un mois clôturé n'est jamais verrouillé : aucune écriture n'est bloquée.
- Une dépense exceptionnelle reste dans les totaux officiels, les soldes et `running_balance` ; les alertes budget et la projection de fin de mois ne changent pas.
- Frontend : appels API uniquement via `@/lib/api`, montants via `formatCurrency` avec la classe `amount-blur`, retours via `toast`, `localStorage` toujours dans un try/catch. Seule vérification : `cd frontend && npm run build` (0 erreur TypeScript).
- Commits directement sur `main` (pas de branche ni de PR), message en français style `type(portée): résumé`, terminés par `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- La documentation (ARCHITECTURE.md, skill, README MCP) est mise à jour dans le même enchaînement de commits que le code (Task 7).

## Review Focus

Entrées ou conditions que le spec sous-entend sans les détailler ; chacune a son test dans la tâche indiquée.

1. **Mois sans aucune transaction** : `GET /month-review` répond `200` avec des étapes vides et la clôture reste possible (Task 3 `test_empty_month_returns_200`, Task 4 `test_empty_month_can_be_closed`).
2. **Mois ou année invalides** (`month=13`) : `422`, jamais `500` (Task 3, `test_invalid_month_is_422`).
3. **Double clôture** (double clic, deux onglets) : une seule ligne en base, la dernière photo gagne (Task 4, `test_close_twice_keeps_one_row`).
4. **Dépense exceptionnelle dans la catégorie « Investissement »** : déjà exclue de `depenses_reelles`, elle ne doit pas être retranchée une seconde fois (Task 2, `test_exceptional_investment_category_not_double_counted`).
5. **Compte en devise étrangère** : la dérive des taux ne doit pas faire passer un mois clôturé à « modifié » ; comparaison avec tolérance relative (Task 2, `test_differs_tolerates_small_drift`).

---

## File Structure

| Fichier | Rôle |
|---|---|
| `backend/app/models/month_closure.py` (créer) | Modèle `MonthClosure` |
| `backend/alembic/versions/b3e8d2c5a1f7_month_closures_and_is_exceptional.py` (créer) | Table + colonne |
| `backend/app/models/transaction.py`, `backend/app/models/__init__.py` (modifier) | Colonne `is_exceptional`, export du modèle |
| `backend/app/schemas/transaction.py` (modifier) | `is_exceptional` en lecture/création/mise à jour |
| `backend/app/api/transactions.py` (modifier) | Ignorer `is_exceptional: null` au PATCH |
| `backend/app/core/month_review.py` (créer) | Logique pure : bornes du mois, étape 1, top dépenses, hors exceptionnel, tolérance |
| `backend/app/schemas/month_review.py` (créer) | Schémas de la revue |
| `backend/app/api/month_review.py` (créer) | Router `/month-review` |
| `backend/app/schemas/insight.py`, `backend/app/api/analytics/reports.py` (modifier) | Champs « hors exceptionnel » du rapport mensuel |
| `backend/app/main.py` (modifier) | Enregistrement du router |
| `mcp-server/server_api.py` (modifier) | Outils `get_month_review`, `list_month_closures` |
| `frontend/src/types/monthReview.ts` (créer) | Types de la revue |
| `frontend/src/pages/MonthReview.tsx` (créer) | Page du parcours |
| `frontend/src/components/month-review/{CategorizeStep,AccountsStep,BudgetStep,CloseStep,MonthReviewPopup}.tsx` (créer) | Étapes et pop-up |
| `frontend/src/App.tsx`, `components/layout/Sidebar.tsx`, `components/layout/Omnibox.tsx`, `pages/Dashboard.tsx`, `pages/AccountDetail.tsx` (modifier) | Route, navigation, pop-up, case « Exceptionnelle » |
| `backend/tests/test_exceptional_flag.py`, `backend/tests/test_month_review.py` (créer) | Tests |

---

### Task 1: Modèle, migration et drapeau `is_exceptional`

**Files:**
- Create: `backend/app/models/month_closure.py`
- Create: `backend/alembic/versions/b3e8d2c5a1f7_month_closures_and_is_exceptional.py`
- Modify: `backend/app/models/transaction.py` (après `reimbursement_offset`, ligne ~47)
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/schemas/transaction.py` (`TransactionBase`, `TransactionUpdate`)
- Modify: `backend/app/api/transactions.py` (`update_transaction`, avant la boucle `setattr`, ligne ~484)
- Test: `backend/tests/test_exceptional_flag.py`

**Interfaces:**
- Produces: `MonthClosure` (colonnes `id`, `year`, `month`, `closed_at`, `highlight`, `tx_count`, `income`, `expenses`, `unresolved_count`) ; `Transaction.is_exceptional: bool` ; champ `is_exceptional` dans `TransactionRead`/`TransactionCreate`/`TransactionUpdate`.

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/test_exceptional_flag.py` :

```python
from datetime import datetime

from app.core.finance import month_label_from_date
from app.models.account import Account
from app.models.transaction import Transaction


def _account(db):
    acc = Account(name="Principal", type="courant", currency="EUR", active=True)
    db.add(acc)
    db.commit()
    return acc


def _tx(db, account, type_, amount, date, merchant="x"):
    t = Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_,
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
    )
    db.add(t)
    db.commit()
    return t


def test_patch_sets_and_clears_flag(client, db_session):
    acc = _account(db_session)
    tx = _tx(db_session, acc, "Sortie", 120.0, datetime(2025, 10, 5), "CANAPE")

    res = client.patch(f"/transactions/{tx.id}", json={"is_exceptional": True})
    assert res.status_code == 200
    assert res.json()["is_exceptional"] is True
    db_session.refresh(tx)
    assert tx.is_exceptional is True

    res = client.patch(f"/transactions/{tx.id}", json={"is_exceptional": False})
    assert res.json()["is_exceptional"] is False


def test_null_flag_is_ignored(client, db_session):
    acc = _account(db_session)
    tx = _tx(db_session, acc, "Sortie", 120.0, datetime(2025, 10, 5), "CANAPE")
    client.patch(f"/transactions/{tx.id}", json={"is_exceptional": True})

    res = client.patch(f"/transactions/{tx.id}", json={"is_exceptional": None, "note": "garantie 2 ans"})
    assert res.status_code == 200
    assert res.json()["is_exceptional"] is True
    assert res.json()["note"] == "garantie 2 ans"


def test_flag_leaves_totals_and_balance_unchanged(client, db_session):
    acc = _account(db_session)
    _tx(db_session, acc, "Entree", 1000.0, datetime(2025, 10, 1), "SALAIRE")
    tx = _tx(db_session, acc, "Sortie", 100.0, datetime(2025, 10, 5), "CANAPE")
    params = {"month": 10, "year": 2025}

    before = client.get("/analytics/budget", params=params).json()
    client.patch(f"/transactions/{tx.id}", json={"is_exceptional": True})
    after = client.get("/analytics/budget", params=params).json()

    assert before["depenses_totales"] == after["depenses_totales"] == 100.0
    assert before["depenses_reelles"] == after["depenses_reelles"]
    db_session.refresh(tx)
    assert tx.running_balance == 900.0
```

- [ ] **Step 2: Vérifier qu'ils échouent**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_exceptional_flag.py -v`
Expected: FAIL (`KeyError: 'is_exceptional'` ou `422` sur le PATCH).

- [ ] **Step 3: Créer le modèle `MonthClosure`**

Créer `backend/app/models/month_closure.py` :

```python
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow_naive
from app.db.base import Base


class MonthClosure(Base):
    """Mois revu par l'utilisateur. Marqueur non bloquant : la photo des chiffres sert à détecter une modification ultérieure."""

    __tablename__ = "month_closures"
    __table_args__ = (UniqueConstraint("year", "month", name="uq_month_closures_year_month"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, nullable=False)
    highlight: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Photo prise à la clôture
    tx_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    income: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expenses: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unresolved_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```

- [ ] **Step 4: Ajouter la colonne et exporter le modèle**

Dans `backend/app/models/transaction.py`, juste après la ligne `reimbursement_offset` :

```python
    # Dépense hors norme (achat ponctuel) : reste dans les totaux, isolée dans la lecture « hors exceptionnel »
    is_exceptional: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
```

Dans `backend/app/models/__init__.py`, ajouter l'import `from app.models.month_closure import MonthClosure` après celui de `reimbursement`, et `"MonthClosure",` dans `__all__`.

- [ ] **Step 5: Schémas de transaction**

Dans `backend/app/schemas/transaction.py` :
- `TransactionBase` : ajouter `is_exceptional: bool = False` après `custom_color`.
- `TransactionUpdate` : ajouter `is_exceptional: bool | None = None` après `custom_color`.

Dans `backend/app/api/transactions.py`, dans `update_transaction`, juste avant `for field, value in update_data.items():` :

```python
    # La colonne n'est pas nullable : un `null` explicite équivaut à « ne pas modifier »
    if update_data.get("is_exceptional", True) is None:
        update_data.pop("is_exceptional")
```

- [ ] **Step 6: Migration Alembic**

Créer `backend/alembic/versions/b3e8d2c5a1f7_month_closures_and_is_exceptional.py` :

```python
"""revue de fin de mois : table month_closures et colonne transactions.is_exceptional

Revision ID: b3e8d2c5a1f7
Revises: a7d4c1e9b3f2
Create Date: 2026-10-13 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3e8d2c5a1f7"
down_revision: Union[str, None] = "a7d4c1e9b3f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "month_closures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=False),
        sa.Column("highlight", sa.String(length=500), nullable=True),
        sa.Column("tx_count", sa.Integer(), nullable=False),
        sa.Column("income", sa.Float(), nullable=False),
        sa.Column("expenses", sa.Float(), nullable=False),
        sa.Column("unresolved_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year", "month", name="uq_month_closures_year_month"),
    )
    op.create_index(op.f("ix_month_closures_id"), "month_closures", ["id"], unique=False)
    op.add_column(
        "transactions",
        sa.Column("is_exceptional", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch:
        batch.drop_column("is_exceptional")
    op.drop_index(op.f("ix_month_closures_id"), table_name="month_closures")
    op.drop_table("month_closures")
```

- [ ] **Step 7: Vérifier les tests et la migration**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_exceptional_flag.py -v`
Expected: 3 PASS.

Run (migration sur une base jetable, montée puis redescendue) :

```bash
cd backend && DB="$(mktemp -d)/mig.db" && \
DATABASE_URL="sqlite:///$DB" PYTHONPATH=. python3.11 -m alembic upgrade head && \
sqlite3 "$DB" ".schema month_closures" && sqlite3 "$DB" "PRAGMA table_info(transactions)" | grep is_exceptional && \
DATABASE_URL="sqlite:///$DB" PYTHONPATH=. python3.11 -m alembic downgrade -1 && \
DATABASE_URL="sqlite:///$DB" PYTHONPATH=. python3.11 -m alembic upgrade head
```
Expected: schéma de `month_closures` affiché, la ligne `is_exceptional` présente, downgrade puis upgrade sans erreur.

- [ ] **Step 8: Commit**

```bash
cd /Users/hugogalley/DEV/numera && git add backend/app/models backend/app/schemas/transaction.py backend/app/api/transactions.py backend/alembic/versions/b3e8d2c5a1f7_month_closures_and_is_exceptional.py backend/tests/test_exceptional_flag.py
git commit -m "$(cat <<'EOF'
feat(revue-mois): table month_closures et drapeau is_exceptional

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Logique « hors exceptionnel » et rapport mensuel

**Files:**
- Create: `backend/app/core/month_review.py`
- Modify: `backend/app/schemas/insight.py` (`MonthlyReport`)
- Modify: `backend/app/api/analytics/reports.py` (`get_monthly_report`)
- Test: `backend/tests/test_month_review.py` (début du fichier)

**Interfaces:**
- Consumes: `NET_AMOUNT`, `_get_ticket_restaurant_account_ids` de `app/api/analytics/utils.py` ; `Transaction.is_exceptional` (Task 1).
- Produces (dans `app/core/month_review.py`) :
  - `month_bounds(year: int, month: int) -> tuple[datetime, datetime]` (début inclus, début du mois suivant exclu)
  - `exceptional_expenses(db: Session, start: datetime, end: datetime, rates: dict[str, float], account_id: int | None = None) -> float`
  - `without_exceptional(budget: dict, exceptional: float) -> dict` (clés `exceptional_expenses`, `real_expenses_excl_exceptional`, `savings_excl_exceptional`, `savings_rate_excl_exceptional`, `burn_rate_excl_exceptional`)
  - `differs(current: float, snapshot: float) -> bool`
  - Champs du rapport mensuel : les 5 clés ci-dessus.

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/test_month_review.py` :

```python
from datetime import datetime

import pytest

from app.core.finance import month_label_from_date
from app.core.month_review import differs
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction


def _tx(db, account, type_, amount, date, merchant="x", category=None, exceptional=False):
    t = Transaction(
        account_id=account.id, date=date, month_label=month_label_from_date(date), type=type_,
        merchant=merchant, amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
        category_id=category.id if category else None, is_exceptional=exceptional,
    )
    db.add(t)
    db.commit()
    return t


def _courant(db, **kwargs):
    acc = Account(name="Principal", type="courant", currency="EUR", active=True, **kwargs)
    db.add(acc)
    db.commit()
    return acc


def test_monthly_report_exposes_figures_without_exceptional(client, db_session):
    acc = _courant(db_session)
    courses = Category(name="Courses", type="depense")
    db_session.add(courses)
    db_session.commit()
    _tx(db_session, acc, "Entree", 2000.0, datetime(2025, 10, 1), "SALAIRE")
    _tx(db_session, acc, "Sortie", 300.0, datetime(2025, 10, 8), "MARCHE", courses)
    _tx(db_session, acc, "Sortie", 200.0, datetime(2025, 10, 20), "CANAPE", courses, exceptional=True)

    report = client.get("/analytics/monthly-report", params={"month": 10, "year": 2025}).json()

    assert report["real_expenses"] == 500.0
    assert report["exceptional_expenses"] == 200.0
    assert report["real_expenses_excl_exceptional"] == 300.0
    assert report["savings"] == 1500.0
    assert report["savings_excl_exceptional"] == 1700.0
    assert report["savings_rate"] == 75.0
    assert report["savings_rate_excl_exceptional"] == 85.0
    assert report["burn_rate_excl_exceptional"] == pytest.approx(300.0 / 31, abs=0.02)


def test_exceptional_investment_category_not_double_counted(client, db_session):
    acc = _courant(db_session)
    invest = Category(name="Investissement", type="depense")
    db_session.add(invest)
    db_session.commit()
    _tx(db_session, acc, "Entree", 2000.0, datetime(2025, 10, 1), "SALAIRE")
    _tx(db_session, acc, "Sortie", 500.0, datetime(2025, 10, 3), "PEA", invest, exceptional=True)
    _tx(db_session, acc, "Sortie", 100.0, datetime(2025, 10, 4), "BOULANGERIE")

    report = client.get("/analytics/monthly-report", params={"month": 10, "year": 2025}).json()

    assert report["real_expenses"] == 100.0  # 600 de dépenses − 500 d'investissement
    assert report["exceptional_expenses"] == 0.0
    assert report["real_expenses_excl_exceptional"] == 100.0


def test_differs_tolerates_small_drift():
    assert differs(1000.0, 1002.0) is False  # 0,2 % : dérive de taux de change
    assert differs(1000.0, 1010.0) is True
    assert differs(0.0, 0.005) is False
    assert differs(0.0, 0.02) is True
```

- [ ] **Step 2: Vérifier qu'ils échouent**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_month_review.py -v`
Expected: FAIL (`ModuleNotFoundError: app.core.month_review`).

- [ ] **Step 3: Écrire `app/core/month_review.py`**

```python
"""Logique de la revue de fin de mois : bornes, étape 1, top dépenses, lecture « hors exceptionnel »."""
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.analytics.utils import NET_AMOUNT, _get_ticket_restaurant_account_ids, net_amount
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction

# Même liste que budget_analytics : ces catégories ne sont pas de la consommation
INVESTMENT_CATEGORIES = ["Investissement", "Epargne"]
CATEGORIZE_LIMIT = 50
TOP_EXPENSES_LIMIT = 10


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    return start, end


def differs(current: float, snapshot: float) -> bool:
    """Écart significatif entre un chiffre recalculé et sa photo (tolère la dérive des taux de change)."""
    return abs(current - snapshot) > max(0.01, 0.005 * abs(snapshot))


def exceptional_expenses(
    db: Session,
    start: datetime,
    end: datetime,
    rates: dict[str, float],
    account_id: int | None = None,
) -> float:
    """Dépenses nettes marquées exceptionnelles, hors catégories d'investissement (déjà exclues des dépenses réelles)."""
    query = (
        db.query(Account.currency, func.coalesce(func.sum(NET_AMOUNT), 0.0))
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.is_exceptional.is_(True),
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
            or_(Category.name.is_(None), Category.name.notin_(INVESTMENT_CATEGORIES)),
        )
    )
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    else:
        query = query.filter(Account.type.in_(["courant", "epargne"]))
        tr_accounts = _get_ticket_restaurant_account_ids(db)
        if tr_accounts:
            query = query.filter(Transaction.account_id.notin_(tr_accounts))
    rows = query.group_by(Account.currency).all()
    return float(sum(total / rates.get(currency, 1.0) for currency, total in rows))


def without_exceptional(budget: dict, exceptional: float) -> dict:
    """Lecture « hors exceptionnel » à partir du dict de `budget_analytics` ; les totaux officiels ne bougent pas."""
    real = float(budget["depenses_reelles"])
    income = float(budget["revenus_totaux"])
    real_excl = real - exceptional
    rate_excl = float(budget["taux_epargne"]) + (exceptional / income * 100.0 if income > 0 else 0.0)
    burn_excl = float(budget["burn_rate"]) * (real_excl / real) if real > 0 else 0.0
    return {
        "exceptional_expenses": round(exceptional, 2),
        "real_expenses_excl_exceptional": round(real_excl, 2),
        "savings_excl_exceptional": round(float(budget["revenus_apres_depenses"]) + exceptional, 2),
        "savings_rate_excl_exceptional": round(max(min(rate_excl, 100.0), -100.0), 2),
        "burn_rate_excl_exceptional": round(max(burn_excl, 0.0), 2),
    }


def _review_tx(tx: Transaction) -> dict:
    return {
        "id": tx.id,
        "date": tx.date,
        "merchant": tx.merchant,
        "amount": round(net_amount(tx), 2),
        "category_name": tx.category.name if tx.category else None,
        "is_exceptional": bool(tx.is_exceptional),
    }


def tx_count(db: Session, start: datetime, end: datetime) -> int:
    return db.query(Transaction).filter(Transaction.date >= start, Transaction.date < end).count()


def categorize_step(db: Session, start: datetime, end: datetime) -> dict:
    """Étape 1 : dépenses du mois sans catégorie (mêmes filtres que l'audit, bornés au mois)."""
    base = db.query(Transaction).filter(
        Transaction.category_id.is_(None),
        Transaction.type == "Sortie",
        Transaction.is_transfer.is_(False),
        Transaction.date >= start,
        Transaction.date < end,
    )
    count = base.count()
    total = (
        db.query(func.coalesce(func.sum(NET_AMOUNT), 0.0))
        .filter(
            Transaction.category_id.is_(None),
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
        )
        .scalar()
    )
    items = base.order_by(Transaction.amount.desc(), Transaction.id.asc()).limit(CATEGORIZE_LIMIT).all()
    return {"count": count, "total": round(float(total or 0.0), 2), "items": [_review_tx(t) for t in items]}


def top_expenses(db: Session, start: datetime, end: datetime) -> list[dict]:
    """Plus grosses dépenses nettes du mois (hors virements et investissement), à marquer exceptionnelles."""
    rows = (
        db.query(Transaction)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.date >= start,
            Transaction.date < end,
            or_(Category.name.is_(None), Category.name.notin_(INVESTMENT_CATEGORIES)),
        )
        .order_by(NET_AMOUNT.desc(), Transaction.id.asc())
        .limit(TOP_EXPENSES_LIMIT)
        .all()
    )
    return [_review_tx(t) for t in rows]
```

- [ ] **Step 4: Champs du rapport mensuel**

Dans `backend/app/schemas/insight.py`, classe `MonthlyReport`, avant `money_flow` :

```python
    exceptional_expenses: float
    real_expenses_excl_exceptional: float
    savings_excl_exceptional: float
    savings_rate_excl_exceptional: float
    burn_rate_excl_exceptional: float
```

Dans `backend/app/api/analytics/reports.py` : vérifier avec `grep -n "get_exchange_rates" backend/app/api/analytics/reports.py` ; si absent, ajouter `from app.core.currency import get_exchange_rates`, puis `from app.core.month_review import exceptional_expenses, month_bounds, without_exceptional`. Dans `get_monthly_report`, juste avant `return MonthlyReport(` :

```python
    start, end = month_bounds(year, month)
    rates = await get_exchange_rates("EUR")
    excl = without_exceptional(current_budget, exceptional_expenses(db, start, end, rates, account_id))
```

et remplacer `money_flow=flow_data` (dernier argument) par :

```python
        money_flow=flow_data,
        **excl,
```

- [ ] **Step 5: Vérifier**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_month_review.py tests/test_exceptional_flag.py tests/test_import_and_analytics.py -v`
Expected: tous PASS (les tests existants du rapport mensuel doivent rester verts).

- [ ] **Step 6: Commit**

```bash
cd /Users/hugogalley/DEV/numera && git add backend/app/core/month_review.py backend/app/schemas/insight.py backend/app/api/analytics/reports.py backend/tests/test_month_review.py
git commit -m "$(cat <<'EOF'
feat(revue-mois): lecture « hors exceptionnel » du rapport mensuel

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Router `/month-review` — lecture de l'état du mois

**Files:**
- Create: `backend/app/schemas/month_review.py`
- Create: `backend/app/api/month_review.py`
- Modify: `backend/app/main.py` (import + `protected_routers`)
- Test: `backend/tests/test_month_review.py` (ajouts)

**Interfaces:**
- Consumes: `month_bounds`, `exceptional_expenses`, `without_exceptional`, `differs`, `categorize_step`, `top_expenses`, `tx_count` (Task 2) ; `budget_analytics`, `budget_alerts` ; `_get_balance_for_account` (`app/api/accounts.py`) ; `MonthClosure` (Task 1).
- Produces: `GET /month-review?year=&month=` → `MonthReviewRead` ; `_build_review(db, year, month) -> tuple[dict, dict]` (la revue, et la photo courante `{tx_count, income, expenses, unresolved_count}`) ; schémas `MonthReviewRead`, `ClosureRead`, `CloseRequest`.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `backend/tests/test_month_review.py` :

```python
PARAMS = {"year": 2025, "month": 10}


@pytest.fixture()
def october(db_session):
    acc = _courant(db_session, last_verified_at=datetime(2025, 10, 15))
    courses = Category(name="Courses", type="depense")
    db_session.add(courses)
    db_session.commit()
    _tx(db_session, acc, "Entree", 2000.0, datetime(2025, 10, 1), "SALAIRE")
    _tx(db_session, acc, "Sortie", 300.0, datetime(2025, 10, 8), "MARCHE", courses)
    nocat = _tx(db_session, acc, "Sortie", 80.0, datetime(2025, 10, 12), "NOCAT")
    exc = _tx(db_session, acc, "Sortie", 200.0, datetime(2025, 10, 20), "CANAPE", courses, exceptional=True)
    _tx(db_session, acc, "Sortie", 100.0, datetime(2025, 9, 10), "AUTREMOIS")  # autre mois, sans catégorie
    return acc, courses, nocat, exc


def test_review_step1_is_bounded_to_month(client, october):
    data = client.get("/month-review", params=PARAMS).json()
    assert data["categorize"]["count"] == 1
    assert [i["merchant"] for i in data["categorize"]["items"]] == ["NOCAT"]
    assert data["categorize"]["total"] == 80.0
    assert data["closed"] is False
    assert data["closure"] is None
    assert data["modified_since_close"] is False


def test_review_accounts_step_flags_stale_accounts(client, october):
    acc = october[0]
    data = client.get("/month-review", params=PARAMS).json()
    assert data["accounts"]["unverified_count"] == 1
    assert data["accounts"]["accounts"][0]["verified_since_month_end"] is False

    assert client.post(f"/accounts/{acc.id}/verify").status_code == 200
    data = client.get("/month-review", params=PARAMS).json()
    assert data["accounts"]["unverified_count"] == 0
    assert data["accounts"]["accounts"][0]["verified_since_month_end"] is True


def test_review_budget_shows_figures_without_exceptional(client, october):
    b = client.get("/month-review", params=PARAMS).json()["budget"]
    assert b["income"] == 2000.0
    assert b["real_expenses"] == 580.0
    assert b["exceptional_expenses"] == 200.0
    assert b["real_expenses_excl_exceptional"] == 380.0
    assert b["savings"] == 1420.0
    assert b["savings_excl_exceptional"] == 1620.0
    assert b["savings_rate_excl_exceptional"] == 81.0
    assert b["burn_rate_excl_exceptional"] == pytest.approx(380.0 / 31, abs=0.02)
    assert b["previous_real_expenses"] == 100.0
    assert [t["merchant"] for t in b["top_expenses"]] == ["MARCHE", "CANAPE", "NOCAT"]
    assert b["top_expenses"][1]["is_exceptional"] is True


def test_empty_month_returns_200(client, db_session):
    res = client.get("/month-review", params={"year": 2024, "month": 2})
    assert res.status_code == 200
    data = res.json()
    assert data["categorize"]["count"] == 0
    assert data["budget"]["income"] == 0.0
    assert data["budget"]["top_expenses"] == []


def test_invalid_month_is_422(client):
    assert client.get("/month-review", params={"year": 2025, "month": 13}).status_code == 422
```

- [ ] **Step 2: Vérifier qu'ils échouent**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_month_review.py -v`
Expected: les nouveaux tests FAIL (`404` sur `/month-review`).

- [ ] **Step 3: Schémas**

Créer `backend/app/schemas/month_review.py` :

```python
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.category import BudgetAlert


class ReviewTransaction(BaseModel):
    id: int
    date: datetime
    merchant: str
    amount: float  # net des remboursements, devise du compte
    category_name: str | None = None
    is_exceptional: bool = False


class CategorizeStep(BaseModel):
    count: int
    total: float
    items: list[ReviewTransaction]


class AccountCheck(BaseModel):
    id: int
    name: str
    currency: str
    balance: float
    last_verified_at: datetime
    verified_since_month_end: bool


class AccountsStep(BaseModel):
    unverified_count: int
    accounts: list[AccountCheck]


class BudgetStep(BaseModel):
    income: float
    real_expenses: float
    savings: float
    savings_rate: float
    burn_rate: float
    exceptional_expenses: float
    real_expenses_excl_exceptional: float
    savings_excl_exceptional: float
    savings_rate_excl_exceptional: float
    burn_rate_excl_exceptional: float
    previous_real_expenses: float
    alerts: list[BudgetAlert]
    top_expenses: list[ReviewTransaction]


class ClosureRead(BaseModel):
    year: int
    month: int
    closed_at: datetime
    highlight: str | None = None
    tx_count: int
    income: float
    expenses: float
    unresolved_count: int

    model_config = {"from_attributes": True}


class MonthReviewRead(BaseModel):
    year: int
    month: int
    closed: bool
    closure: ClosureRead | None = None
    modified_since_close: bool
    categorize: CategorizeStep
    accounts: AccountsStep
    budget: BudgetStep


class CloseRequest(BaseModel):
    year: int = Field(ge=2000, le=2200)
    month: int = Field(ge=1, le=12)
    highlight: str | None = Field(default=None, max_length=500)
```

- [ ] **Step 4: Router (lecture)**

Créer `backend/app/api/month_review.py` :

```python
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.accounts import _get_balance_for_account
from app.api.analytics.budget import budget_alerts, budget_analytics
from app.api.deps import get_db
from app.core.currency import get_exchange_rates
from app.core.month_review import (
    categorize_step,
    differs,
    exceptional_expenses,
    month_bounds,
    top_expenses,
    tx_count,
    without_exceptional,
)
from app.core.time import utcnow_naive
from app.models.account import Account
from app.models.month_closure import MonthClosure
from app.schemas.month_review import ClosureRead, MonthReviewRead

router = APIRouter(prefix="/month-review", tags=["month-review"])


def _accounts_step(db: Session, end: datetime) -> dict:
    """Étape 2 : un compte est « vérifié » s'il l'a été depuis la fin du mois (ou aujourd'hui si le mois n'est pas fini)."""
    now = utcnow_naive()
    reference = min(end, datetime(now.year, now.month, now.day))
    accounts = db.query(Account).filter(Account.active.is_(True)).order_by(Account.id.asc()).all()
    items = [
        {
            "id": acc.id,
            "name": acc.name,
            "currency": acc.currency,
            "balance": round(_get_balance_for_account(db, acc.id), 2),
            "last_verified_at": acc.last_verified_at,
            "verified_since_month_end": acc.last_verified_at >= reference,
        }
        for acc in accounts
    ]
    return {"unverified_count": sum(1 for i in items if not i["verified_since_month_end"]), "accounts": items}


async def _build_review(db: Session, year: int, month: int) -> tuple[dict, dict]:
    start, end = month_bounds(year, month)
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)

    budget = await budget_analytics(month=month, year=year, account_id=None, db=db)
    previous = await budget_analytics(month=prev_month, year=prev_year, account_id=None, db=db)
    alerts = await budget_alerts(year=year, month=month, account_id=None, db=db)
    rates = await get_exchange_rates("EUR")

    categorize = categorize_step(db, start, end)
    accounts = _accounts_step(db, end)
    current = {
        "tx_count": tx_count(db, start, end),
        "income": round(float(budget["revenus_totaux"]), 2),
        "expenses": round(float(budget["depenses_reelles"]), 2),
        "unresolved_count": categorize["count"] + accounts["unverified_count"],
    }

    closure = db.query(MonthClosure).filter(MonthClosure.year == year, MonthClosure.month == month).first()
    modified = closure is not None and (
        current["tx_count"] != closure.tx_count
        or differs(current["income"], closure.income)
        or differs(current["expenses"], closure.expenses)
    )

    review = {
        "year": year,
        "month": month,
        "closed": closure is not None,
        "closure": ClosureRead.model_validate(closure) if closure else None,
        "modified_since_close": modified,
        "categorize": categorize,
        "accounts": accounts,
        "budget": {
            "income": current["income"],
            "real_expenses": current["expenses"],
            "savings": budget["revenus_apres_depenses"],
            "savings_rate": budget["taux_epargne"],
            "burn_rate": budget["burn_rate"],
            **without_exceptional(budget, exceptional_expenses(db, start, end, rates)),
            "previous_real_expenses": previous["depenses_reelles"],
            "alerts": alerts,
            "top_expenses": top_expenses(db, start, end),
        },
    }
    return review, current


@router.get("", response_model=MonthReviewRead)
async def get_month_review(
    year: int = Query(ge=2000, le=2200),
    month: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
):
    """État de la revue d'un mois : étapes 1 à 3 calculées, statut de clôture, indicateur de modification."""
    review, _ = await _build_review(db, year, month)
    return review
```

- [ ] **Step 5: Enregistrer le router**

Dans `backend/app/main.py` : ajouter `from app.api.month_review import router as month_review_router` après l'import de `reimbursements_router`, puis `month_review_router,` dans `protected_routers` après `reimbursements_router,`.

- [ ] **Step 6: Vérifier**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_month_review.py -v`
Expected: tous PASS.

- [ ] **Step 7: Commit**

```bash
cd /Users/hugogalley/DEV/numera && git add backend/app/schemas/month_review.py backend/app/api/month_review.py backend/app/main.py backend/tests/test_month_review.py
git commit -m "$(cat <<'EOF'
feat(revue-mois): route GET /month-review (étapes catégoriser, soldes, budget)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Clôture, réouverture et liste des clôtures

**Files:**
- Modify: `backend/app/api/month_review.py`
- Test: `backend/tests/test_month_review.py` (ajouts)

**Interfaces:**
- Consumes: `_build_review` (Task 3), `MonthClosure`, `CloseRequest`, `ClosureRead`.
- Produces: `POST /month-review/close` → `MonthReviewRead` ; `DELETE /month-review?year=&month=` → `204` (idempotent) ; `GET /month-review/closures` → `list[ClosureRead]` triée du plus récent au plus ancien.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `backend/tests/test_month_review.py` (et `from app.models.month_closure import MonthClosure` en tête) :

```python
def _close(client, highlight=None, **period):
    return client.post("/month-review/close", json={**(period or PARAMS), "highlight": highlight})


def test_close_stores_snapshot(client, october):
    res = _close(client, "Canapé acheté")
    assert res.status_code == 200
    body = res.json()
    assert body["closed"] is True
    assert body["modified_since_close"] is False
    closure = body["closure"]
    assert closure["highlight"] == "Canapé acheté"
    assert closure["tx_count"] == 4
    assert closure["income"] == 2000.0
    assert closure["expenses"] == 580.0
    assert closure["unresolved_count"] == 2  # 1 dépense sans catégorie + 1 compte non vérifié


def test_close_twice_keeps_one_row(client, october, db_session):
    _close(client, "a")
    _close(client, "b")
    rows = db_session.query(MonthClosure).all()
    assert len(rows) == 1
    assert rows[0].highlight == "b"


def test_reopen_deletes_closure_and_is_idempotent(client, october):
    _close(client)
    assert client.delete("/month-review", params=PARAMS).status_code == 204
    assert client.get("/month-review", params=PARAMS).json()["closed"] is False
    assert client.delete("/month-review", params=PARAMS).status_code == 204


def test_modified_since_close_after_new_transaction(client, october, db_session):
    _close(client)
    _tx(db_session, october[0], "Sortie", 15.0, datetime(2025, 10, 25), "NEW")
    data = client.get("/month-review", params=PARAMS).json()
    assert data["closed"] is True
    assert data["modified_since_close"] is True


def test_recategorizing_does_not_flag_modification(client, october):
    _, courses, nocat, _ = october
    _close(client)
    client.patch(f"/transactions/{nocat.id}", json={"category_id": courses.id})
    assert client.get("/month-review", params=PARAMS).json()["modified_since_close"] is False


def test_empty_month_can_be_closed(client, db_session):
    res = _close(client, year=2024, month=2)
    assert res.status_code == 200
    assert res.json()["closed"] is True
    assert res.json()["closure"]["tx_count"] == 0


def test_closures_list_most_recent_first(client, october):
    _close(client, year=2025, month=9)
    _close(client)
    closures = client.get("/month-review/closures").json()
    assert [(c["year"], c["month"]) for c in closures] == [(2025, 10), (2025, 9)]
```

- [ ] **Step 2: Vérifier qu'ils échouent**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_month_review.py -v`
Expected: les nouveaux tests FAIL (`404`/`405`).

- [ ] **Step 3: Implémenter les routes**

Dans `backend/app/api/month_review.py`, ajouter à l'import des schémas `CloseRequest`, puis à la fin du fichier :

```python
@router.post("/close", response_model=MonthReviewRead)
async def close_month(payload: CloseRequest, db: Session = Depends(get_db)):
    """Marque le mois comme revu et fige la photo des chiffres. Idempotent : re-clôturer remplace la photo."""
    _, current = await _build_review(db, payload.year, payload.month)
    closure = (
        db.query(MonthClosure)
        .filter(MonthClosure.year == payload.year, MonthClosure.month == payload.month)
        .first()
    )
    if closure is None:
        closure = MonthClosure(year=payload.year, month=payload.month)
        db.add(closure)
    closure.closed_at = utcnow_naive()
    closure.highlight = (payload.highlight or "").strip() or None
    closure.tx_count = current["tx_count"]
    closure.income = current["income"]
    closure.expenses = current["expenses"]
    closure.unresolved_count = current["unresolved_count"]
    db.commit()
    review, _ = await _build_review(db, payload.year, payload.month)
    return review


@router.delete("", status_code=204)
def reopen_month(
    year: int = Query(ge=2000, le=2200),
    month: int = Query(ge=1, le=12),
    db: Session = Depends(get_db),
):
    """Rouvre un mois (supprime sa clôture). Sans effet si le mois n'était pas clôturé."""
    db.query(MonthClosure).filter(MonthClosure.year == year, MonthClosure.month == month).delete()
    db.commit()


@router.get("/closures", response_model=list[ClosureRead])
def list_closures(db: Session = Depends(get_db)):
    return db.query(MonthClosure).order_by(MonthClosure.year.desc(), MonthClosure.month.desc()).all()
```

- [ ] **Step 4: Vérifier la suite complète**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests -q`
Expected: tout PASS (les 250 tests existants + les nouveaux).

- [ ] **Step 5: Commit**

```bash
cd /Users/hugogalley/DEV/numera && git add backend/app/api/month_review.py backend/tests/test_month_review.py
git commit -m "$(cat <<'EOF'
feat(revue-mois): clôture, réouverture et liste des mois clôturés

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Outils MCP en lecture seule

**Files:**
- Modify: `mcp-server/server_api.py` (après `get_monthly_report`, ligne ~640)

**Interfaces:**
- Consumes: `GET /month-review`, `GET /month-review/closures` (Tasks 3-4).
- Produces: outils MCP `get_month_review(month, year)` et `list_month_closures()`.

- [ ] **Step 1: Ajouter les deux outils**

Dans `mcp-server/server_api.py`, juste après la fonction `get_monthly_report` :

```python
@mcp.tool()
def get_month_review(month: int | None = None, year: int | None = None) -> str:
    """Revue de fin de mois : points à traiter (dépenses sans catégorie, comptes non vérifiés),
    comparaison au budget avec et sans dépenses exceptionnelles, et statut de clôture.

    Args:
        month: Mois (1-12, optionnel, défaut: mois précédent)
        year: Année (optionnel, défaut: année du mois précédent)
    """
    try:
        now = datetime.now()
        default_year, default_month = (now.year - 1, 12) if now.month == 1 else (now.year, now.month - 1)
        params = {
            "month": month if month is not None else default_month,
            "year": year if year is not None else default_year,
        }
        resp = api.get("/month-review", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"🗓️ Revue de fin de mois :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def list_month_closures() -> str:
    """Mois clôturés (revue de fin de mois) avec la date, le fait marquant et la photo des chiffres."""
    try:
        resp = api.get("/month-review/closures")
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"✅ Mois clôturés :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"
```

- [ ] **Step 2: Vérifier**

Run: `cd /Users/hugogalley/DEV/numera && python3.11 -c "import ast,sys; ast.parse(open('mcp-server/server_api.py').read()); print('ok')" && grep -c "@mcp.tool()" mcp-server/server_api.py`
Expected: `ok`, puis un compte supérieur de 2 à l'ancien (35 outils + 2).

Comparer à l'ancien total : `git show HEAD:mcp-server/server_api.py | grep -c "@mcp.tool()"` (doit être inférieur de 2).

- [ ] **Step 3: Commit**

```bash
cd /Users/hugogalley/DEV/numera && git add mcp-server/server_api.py
git commit -m "$(cat <<'EOF'
feat(mcp): outils get_month_review et list_month_closures

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Frontend — page, étapes, pop-up, navigation, case « Exceptionnelle »

**Files:**
- Create: `frontend/src/types/monthReview.ts`
- Create: `frontend/src/components/month-review/CategorizeStep.tsx`
- Create: `frontend/src/components/month-review/AccountsStep.tsx`
- Create: `frontend/src/components/month-review/BudgetStep.tsx`
- Create: `frontend/src/components/month-review/CloseStep.tsx`
- Create: `frontend/src/components/month-review/MonthReviewPopup.tsx`
- Create: `frontend/src/pages/MonthReview.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/components/layout/Omnibox.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/AccountDetail.tsx`

**Interfaces:**
- Consumes: `GET /month-review`, `POST /month-review/close`, `DELETE /month-review`, `GET /month-review/closures`, `PATCH /transactions/{id}` (`category_id`, `is_exceptional`), `POST /accounts/{id}/verify`, `GET /categories`.
- Produces: route `/month-review?year=&month=` ; composant `MonthReviewPopup` (sans props).

- [ ] **Step 1: Types**

Créer `frontend/src/types/monthReview.ts` :

```ts
export interface ReviewTransaction {
  id: number
  date: string
  merchant: string
  amount: number
  category_name: string | null
  is_exceptional: boolean
}

export interface ReviewAccount {
  id: number
  name: string
  currency: string
  balance: number
  last_verified_at: string
  verified_since_month_end: boolean
}

export interface BudgetAlertLite {
  category_id: number
  category_name: string
  monthly_limit: number | null
  monthly_spent: number
  monthly_ratio: number | null
}

export interface ReviewBudget {
  income: number
  real_expenses: number
  savings: number
  savings_rate: number
  burn_rate: number
  exceptional_expenses: number
  real_expenses_excl_exceptional: number
  savings_excl_exceptional: number
  savings_rate_excl_exceptional: number
  burn_rate_excl_exceptional: number
  previous_real_expenses: number
  alerts: BudgetAlertLite[]
  top_expenses: ReviewTransaction[]
}

export interface MonthClosureSummary {
  year: number
  month: number
  closed_at: string
  highlight: string | null
  tx_count: number
  income: number
  expenses: number
  unresolved_count: number
}

export interface MonthReview {
  year: number
  month: number
  closed: boolean
  closure: MonthClosureSummary | null
  modified_since_close: boolean
  categorize: { count: number; total: number; items: ReviewTransaction[] }
  accounts: { unverified_count: number; accounts: ReviewAccount[] }
  budget: ReviewBudget
}
```

- [ ] **Step 2: Étape 1 — Catégoriser**

Créer `frontend/src/components/month-review/CategorizeStep.tsx` :

```tsx
import { useEffect, useState } from "react"
import { CheckCircle2 } from "lucide-react"
import { toast } from "sonner"

import { Card, CardContent } from "@/components/ui/card"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { MonthReview } from "@/types/monthReview"

interface CategoryOption {
  id: number
  name: string
}

export function CategorizeStep({
  step,
  onChanged,
}: {
  step: MonthReview["categorize"]
  onChanged: () => void
}) {
  const [categories, setCategories] = useState<CategoryOption[]>([])

  useEffect(() => {
    api.get<CategoryOption[]>("/categories").then(setCategories).catch(() => setCategories([]))
  }, [])

  async function assign(id: number, categoryId: string) {
    if (!categoryId) return
    try {
      await api.patch(`/transactions/${id}`, { category_id: Number(categoryId) })
      toast.success("Catégorie enregistrée")
      onChanged()
    } catch {
      toast.error("Échec de la catégorisation")
    }
  }

  if (step.count === 0) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 p-6 text-emerald-700">
          <CheckCircle2 className="h-5 w-5" />
          Toutes les dépenses du mois sont catégorisées.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="space-y-4 p-6">
        <p className="text-sm text-slate-600">
          {step.count} dépense{step.count > 1 ? "s" : ""} sans catégorie, soit{" "}
          <span className="amount-blur font-semibold">{formatCurrency(step.total)}</span>.
          {step.count > step.items.length && ` Les ${step.items.length} plus grosses sont listées.`}
        </p>
        <ul className="divide-y">
          {step.items.map((tx) => (
            <li key={tx.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div>
                <p className="font-medium">{tx.merchant}</p>
                <p className="text-xs text-slate-500">{new Date(tx.date).toLocaleDateString("fr-FR")}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="amount-blur font-semibold">{formatCurrency(tx.amount)}</span>
                <select
                  defaultValue=""
                  onChange={(e) => assign(tx.id, e.target.value)}
                  className="h-9 rounded-md border border-slate-200 bg-white px-2 text-sm"
                  aria-label={`Catégorie de ${tx.merchant}`}
                >
                  <option value="">Choisir…</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 3: Étape 2 — Soldes**

Créer `frontend/src/components/month-review/AccountsStep.tsx` :

```tsx
import { useState } from "react"
import { CheckCircle2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { MonthReview } from "@/types/monthReview"

export function AccountsStep({
  step,
  onChanged,
}: {
  step: MonthReview["accounts"]
  onChanged: () => void
}) {
  const [busyId, setBusyId] = useState<number | null>(null)

  async function verify(id: number) {
    setBusyId(id)
    try {
      await api.post(`/accounts/${id}/verify`)
      toast.success("Solde validé")
      onChanged()
    } catch {
      toast.error("Échec de la validation")
    } finally {
      setBusyId(null)
    }
  }

  return (
    <Card>
      <CardContent className="space-y-4 p-6">
        <p className="text-sm text-slate-600">
          Comparez le solde affiché avec celui de votre relevé, puis validez chaque compte.
        </p>
        <ul className="divide-y">
          {step.accounts.map((acc) => (
            <li key={acc.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div>
                <p className="font-medium">{acc.name}</p>
                <p className="text-xs text-slate-500">
                  Dernière validation : {new Date(acc.last_verified_at).toLocaleDateString("fr-FR")}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="amount-blur font-semibold">{formatCurrency(acc.balance, acc.currency)}</span>
                {acc.verified_since_month_end ? (
                  <span className="flex items-center gap-1 text-sm text-emerald-700">
                    <CheckCircle2 className="h-4 w-4" /> Validé
                  </span>
                ) : (
                  <Button size="sm" variant="outline" disabled={busyId === acc.id} onClick={() => verify(acc.id)}>
                    Valider le solde
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 4: Étape 3 — Budget**

Créer `frontend/src/components/month-review/BudgetStep.tsx` :

```tsx
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { api } from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { ReviewBudget } from "@/types/monthReview"

function Row({ label, value, extra }: { label: string; value: string; extra?: string }) {
  return (
    <div className="flex items-baseline justify-between py-2">
      <span className="text-sm text-slate-600">{label}</span>
      <span className="text-right">
        <span className="amount-blur font-semibold">{value}</span>
        {extra && <span className="amount-blur ml-2 text-xs text-slate-500">{extra}</span>}
      </span>
    </div>
  )
}

export function BudgetStep({ budget, onChanged }: { budget: ReviewBudget; onChanged: () => void }) {
  const hasExceptional = budget.exceptional_expenses > 0
  const diff = budget.real_expenses - budget.previous_real_expenses
  const overruns = budget.alerts.filter((a) => a.monthly_ratio !== null && a.monthly_ratio >= 1)

  async function toggle(id: number, value: boolean) {
    try {
      await api.patch(`/transactions/${id}`, { is_exceptional: value })
      toast.success(value ? "Marquée exceptionnelle" : "Marquage retiré")
      onChanged()
    } catch {
      toast.error("Échec de la mise à jour")
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="divide-y p-6">
          <Row label="Revenus" value={formatCurrency(budget.income)} />
          <Row
            label="Dépenses réelles"
            value={formatCurrency(budget.real_expenses)}
            extra={`${diff >= 0 ? "+" : ""}${formatCurrency(diff)} vs mois précédent`}
          />
          {hasExceptional && (
            <Row
              label="Dépenses hors exceptionnelles"
              value={formatCurrency(budget.real_expenses_excl_exceptional)}
              extra={`dont ${formatCurrency(budget.exceptional_expenses)} exceptionnelles`}
            />
          )}
          <Row
            label="Épargne du mois"
            value={formatCurrency(budget.savings)}
            extra={hasExceptional ? `${formatCurrency(budget.savings_excl_exceptional)} hors exceptionnelles` : undefined}
          />
          <Row
            label="Taux d'épargne"
            value={`${budget.savings_rate.toFixed(1)} %`}
            extra={hasExceptional ? `${budget.savings_rate_excl_exceptional.toFixed(1)} % hors exceptionnelles` : undefined}
          />
          <Row
            label="Burn rate (par jour)"
            value={formatCurrency(budget.burn_rate)}
            extra={hasExceptional ? `${formatCurrency(budget.burn_rate_excl_exceptional)} hors exceptionnelles` : undefined}
          />
        </CardContent>
      </Card>

      {overruns.length > 0 && (
        <Card>
          <CardContent className="space-y-2 p-6">
            <p className="text-sm font-semibold">Budgets dépassés</p>
            {overruns.map((a) => (
              <div key={a.category_id} className="flex justify-between text-sm">
                <span>{a.category_name}</span>
                <span className="amount-blur text-rose-600">
                  {formatCurrency(a.monthly_spent)} / {formatCurrency(a.monthly_limit ?? 0)}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="space-y-3 p-6">
          <p className="text-sm text-slate-600">
            Plus grosses dépenses du mois. Marquez un achat ponctuel comme <strong>exceptionnel</strong> pour
            juger le mois sans lui (il reste dans les totaux et les soldes).
          </p>
          <ul className="divide-y">
            {budget.top_expenses.map((tx) => (
              <li key={tx.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <p className="font-medium">{tx.merchant}</p>
                  <p className="text-xs text-slate-500">
                    {new Date(tx.date).toLocaleDateString("fr-FR")}
                    {tx.category_name ? ` · ${tx.category_name}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="amount-blur font-semibold">{formatCurrency(tx.amount)}</span>
                  <Button
                    size="sm"
                    variant={tx.is_exceptional ? "default" : "outline"}
                    onClick={() => toggle(tx.id, !tx.is_exceptional)}
                  >
                    {tx.is_exceptional ? "Exceptionnelle" : "Marquer exceptionnelle"}
                  </Button>
                </div>
              </li>
            ))}
            {budget.top_expenses.length === 0 && (
              <li className="py-3 text-sm text-slate-500">Aucune dépense ce mois-ci.</li>
            )}
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 5: Étape 5 — Clôturer**

Créer `frontend/src/components/month-review/CloseStep.tsx` :

```tsx
import { AlertTriangle, CheckCircle2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { formatCurrency } from "@/lib/utils"
import type { MonthReview } from "@/types/monthReview"

export function CloseStep({
  review,
  highlight,
  busy,
  onClose,
  onReopen,
}: {
  review: MonthReview
  highlight: string
  busy: boolean
  onClose: () => void
  onReopen: () => void
}) {
  const unresolved = review.categorize.count + review.accounts.unverified_count

  return (
    <Card>
      <CardContent className="space-y-4 p-6">
        {review.closed && review.closure && (
          <div className="flex items-start gap-3 rounded-lg bg-emerald-50 p-4 text-emerald-800">
            <CheckCircle2 className="mt-0.5 h-5 w-5" />
            <div className="text-sm">
              <p className="font-semibold">
                Clôturé le {new Date(review.closure.closed_at).toLocaleDateString("fr-FR")}
              </p>
              {review.closure.unresolved_count > 0 && (
                <p>{review.closure.unresolved_count} point(s) restaient à traiter à la clôture.</p>
              )}
            </div>
          </div>
        )}
        {review.modified_since_close && (
          <div className="flex items-start gap-3 rounded-lg bg-amber-50 p-4 text-sm text-amber-900">
            <AlertTriangle className="mt-0.5 h-5 w-5" />
            Des transactions ont changé depuis la clôture. Vous pouvez re-clôturer pour mettre la photo à jour.
          </div>
        )}

        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-slate-500">Dépenses sans catégorie</dt>
            <dd className="font-semibold">{review.categorize.count}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Comptes à valider</dt>
            <dd className="font-semibold">{review.accounts.unverified_count}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Dépenses réelles</dt>
            <dd className="amount-blur font-semibold">{formatCurrency(review.budget.real_expenses)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Épargne</dt>
            <dd className="amount-blur font-semibold">{formatCurrency(review.budget.savings)}</dd>
          </div>
          <div className="col-span-2">
            <dt className="text-slate-500">Fait marquant</dt>
            <dd className="font-medium">{highlight.trim() || "—"}</dd>
          </div>
        </dl>

        {unresolved > 0 && !review.closed && (
          <p className="text-sm text-slate-500">
            Il reste {unresolved} point(s) à traiter ; vous pouvez tout de même clôturer, ils seront notés.
          </p>
        )}

        <div className="flex flex-wrap gap-3">
          <Button onClick={onClose} disabled={busy}>
            {review.closed ? "Re-clôturer le mois" : "Clôturer le mois"}
          </Button>
          {review.closed && (
            <Button variant="outline" onClick={onReopen} disabled={busy}>
              Rouvrir le mois
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 6: Page du parcours**

Créer `frontend/src/pages/MonthReview.tsx` :

```tsx
import { useCallback, useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { ChevronLeft, ChevronRight, ClipboardCheck } from "lucide-react"
import { toast } from "sonner"

import { AccountsStep } from "@/components/month-review/AccountsStep"
import { BudgetStep } from "@/components/month-review/BudgetStep"
import { CategorizeStep } from "@/components/month-review/CategorizeStep"
import { CloseStep } from "@/components/month-review/CloseStep"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { MonthReview as MonthReviewData } from "@/types/monthReview"

const STEPS = ["Catégoriser", "Soldes", "Budget", "Fait marquant", "Clôturer"] as const

function previousMonth() {
  const d = new Date()
  d.setDate(1)
  d.setMonth(d.getMonth() - 1)
  return { year: d.getFullYear(), month: d.getMonth() + 1 }
}

export default function MonthReview() {
  const [params, setParams] = useSearchParams()
  const fallback = previousMonth()
  const year = Number(params.get("year")) || fallback.year
  const month = Number(params.get("month")) || fallback.month

  const [review, setReview] = useState<MonthReviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const [step, setStep] = useState(0)
  const [highlight, setHighlight] = useState("")
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await api.get<MonthReviewData>(`/month-review?year=${year}&month=${month}`)
      setReview(data)
      setHighlight((current) => current || data.closure?.highlight || "")
    } catch {
      toast.error("Impossible de charger la revue du mois")
    }
  }, [year, month])

  useEffect(() => {
    setLoading(true)
    setHighlight("")
    load().finally(() => setLoading(false))
  }, [load])

  function go(delta: number) {
    const d = new Date(year, month - 1 + delta, 1)
    setParams({ year: String(d.getFullYear()), month: String(d.getMonth() + 1) })
    setStep(0)
  }

  async function closeMonth() {
    setBusy(true)
    try {
      const data = await api.post<MonthReviewData>("/month-review/close", {
        year,
        month,
        highlight: highlight.trim() || null,
      })
      setReview(data)
      toast.success("Mois clôturé")
    } catch {
      toast.error("Échec de la clôture")
    } finally {
      setBusy(false)
    }
  }

  async function reopenMonth() {
    setBusy(true)
    try {
      await api.delete(`/month-review?year=${year}&month=${month}`)
      toast.success("Mois rouvert")
      await load()
    } catch {
      toast.error("Échec de la réouverture")
    } finally {
      setBusy(false)
    }
  }

  const label = new Date(year, month - 1, 1).toLocaleDateString("fr-FR", { month: "long", year: "numeric" })

  function status(i: number): "ok" | "todo" | "neutral" {
    if (!review) return "neutral"
    if (i === 0) return review.categorize.count === 0 ? "ok" : "todo"
    if (i === 1) return review.accounts.unverified_count === 0 ? "ok" : "todo"
    if (i === 3) return highlight.trim() ? "ok" : "neutral"
    if (i === 4) return review.closed ? "ok" : "neutral"
    return "neutral"
  }

  return (
    <div className="space-y-6 pb-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-3xl font-bold tracking-tight">
            <ClipboardCheck className="h-7 w-7 text-emerald-600" />
            Revue de mois
          </h1>
          <p className="text-slate-500">Passez le mois en revue, étape par étape, puis clôturez-le.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => go(-1)} aria-label="Mois précédent">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="min-w-36 text-center font-semibold capitalize">{label}</span>
          <Button variant="outline" size="icon" onClick={() => go(1)} aria-label="Mois suivant">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {STEPS.map((name, i) => {
          const s = status(i)
          return (
            <button
              key={name}
              onClick={() => setStep(i)}
              className={cn(
                "rounded-full border px-4 py-1.5 text-sm transition-colors",
                step === i ? "border-slate-900 bg-slate-900 text-white" : "bg-white hover:bg-slate-50",
                step !== i && s === "ok" && "border-emerald-200 text-emerald-700",
                step !== i && s === "todo" && "border-amber-300 text-amber-700"
              )}
            >
              {i + 1}. {name}
            </button>
          )
        })}
      </div>

      {loading || !review ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <>
          {step === 0 && <CategorizeStep step={review.categorize} onChanged={load} />}
          {step === 1 && <AccountsStep step={review.accounts} onChanged={load} />}
          {step === 2 && <BudgetStep budget={review.budget} onChanged={load} />}
          {step === 3 && (
            <Card>
              <CardContent className="space-y-3 p-6">
                <label htmlFor="highlight" className="text-sm text-slate-600">
                  Un fait marquant à retenir de ce mois (optionnel) : résiliation, grosse dépense, changement d'épargne…
                </label>
                <textarea
                  id="highlight"
                  value={highlight}
                  maxLength={500}
                  onChange={(e) => setHighlight(e.target.value)}
                  rows={4}
                  className="w-full rounded-md border border-slate-200 bg-white p-3 text-sm"
                />
              </CardContent>
            </Card>
          )}
          {step === 4 && (
            <CloseStep
              review={review}
              highlight={highlight}
              busy={busy}
              onClose={closeMonth}
              onReopen={reopenMonth}
            />
          )}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 7: Pop-up du Dashboard**

Créer `frontend/src/components/month-review/MonthReviewPopup.tsx` :

```tsx
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ClipboardCheck } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { api } from "@/lib/api"
import type { MonthClosureSummary, MonthReview } from "@/types/monthReview"

// Confort par appareil : le stockage peut être indisponible, la pop-up fonctionne sans.
function readStorage(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeStorage(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* stockage indisponible : la pop-up reviendra, sans conséquence */
  }
}

const todayKey = () => new Date().toLocaleDateString("sv-SE")

export function MonthReviewPopup() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [review, setReview] = useState<MonthReview | null>(null)

  useEffect(() => {
    let cancelled = false
    const now = new Date()
    const target =
      now.getMonth() === 0
        ? { year: now.getFullYear() - 1, month: 12 }
        : { year: now.getFullYear(), month: now.getMonth() }
    const suffix = `${target.year}-${target.month}`
    if (readStorage(`month-review-skip-${suffix}`) === "1") return
    if (readStorage(`month-review-snooze-${suffix}`) === todayKey()) return

    ;(async () => {
      try {
        const closures = await api.get<MonthClosureSummary[]>("/month-review/closures")
        if (closures.some((c) => c.year === target.year && c.month === target.month)) return
        const data = await api.get<MonthReview>(`/month-review?year=${target.year}&month=${target.month}`)
        const hasActivity = data.budget.income > 0 || data.budget.real_expenses > 0 || data.categorize.count > 0
        if (!cancelled && hasActivity) {
          setReview(data)
          setOpen(true)
        }
      } catch {
        /* confort : aucun message en cas d'échec */
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (!review) return null

  const suffix = `${review.year}-${review.month}`
  const label = new Date(review.year, review.month - 1, 1).toLocaleDateString("fr-FR", { month: "long" })
  const points = review.categorize.count + review.accounts.unverified_count

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 capitalize">
            <ClipboardCheck className="h-5 w-5 text-emerald-600" />
            {label} n'est pas encore clôturé
          </DialogTitle>
          <DialogDescription>
            {points > 0
              ? `${review.categorize.count} dépense(s) sans catégorie et ${review.accounts.unverified_count} compte(s) à valider.`
              : "Tout semble en ordre : il ne reste qu'à vérifier le budget et à clôturer."}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:justify-between">
          <Button
            variant="ghost"
            onClick={() => {
              writeStorage(`month-review-skip-${suffix}`, "1")
              setOpen(false)
            }}
          >
            Pas ce mois-ci
          </Button>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => {
                writeStorage(`month-review-snooze-${suffix}`, todayKey())
                setOpen(false)
              }}
            >
              Plus tard
            </Button>
            <Button onClick={() => navigate(`/month-review?year=${review.year}&month=${review.month}`)}>
              Faire la revue
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 8: Route, navigation, Dashboard**

`frontend/src/App.tsx` : ajouter `import MonthReview from "@/pages/MonthReview"` (après `Reimbursements`) et, dans les routes, après `/reimbursements` : `<Route path="/month-review" element={<MonthReview />} />`.

`frontend/src/components/layout/Sidebar.tsx` : ajouter `ClipboardCheck` à l'import `lucide-react` existant, puis dans le groupe « Vue d'ensemble », après « Bilan Mensuel » :
`{ name: "Revue de mois", href: "/month-review", icon: ClipboardCheck },`

`frontend/src/components/layout/Omnibox.tsx` : ajouter `ClipboardCheck` à l'import `lucide-react` existant, puis dans `NAVIGATION`, après « Tableau de bord » :
`{ name: "Revue de mois", href: "/month-review", icon: ClipboardCheck },`

`frontend/src/pages/Dashboard.tsx` : ajouter `import { MonthReviewPopup } from "@/components/month-review/MonthReviewPopup"` et, juste après l'ouverture de `<div className="space-y-10 pb-10">`, la ligne `<MonthReviewPopup />`.

- [ ] **Step 9: Case « Exceptionnelle » dans l'éditeur de transaction**

Dans `frontend/src/pages/AccountDetail.tsx` :

1. Type `Transaction` (ligne ~290) : après `is_transfer?: boolean`, ajouter `is_exceptional?: boolean`.
2. État (ligne ~459) : après `const [txIsRecurring, setTxIsRecurring] = useState(false)`, ajouter `const [txIsExceptional, setTxIsExceptional] = useState(false)`.
3. `resetTxForm` (ligne ~617) : après `setTxIsRecurring(false)`, ajouter `setTxIsExceptional(false)`.
4. `handleEditTransaction` (ligne ~713) : après `setTxIsRecurring(tx.is_recurring)`, ajouter `setTxIsExceptional(!!tx.is_exceptional)`.
5. Les **deux** objets `payload` (création ligne ~650 et mise à jour ligne ~691) : après `is_recurring: txIsRecurring,` ajouter `is_exceptional: txType === "Sortie" && txIsExceptional,`.
6. Formulaire (ligne ~1207), juste après le bloc de la case « Transaction récurrente » :

```tsx
                      {txType === "Sortie" && (
                        <div className="flex items-center space-x-2 py-2">
                          <Checkbox id="exceptional" checked={txIsExceptional} onCheckedChange={(checked) => setTxIsExceptional(!!checked)} />
                          <Label htmlFor="exceptional" className="text-sm font-medium leading-none cursor-pointer">Dépense exceptionnelle (achat ponctuel)</Label>
                        </div>
                      )}
```

- [ ] **Step 10: Vérifier le build**

Run: `cd /Users/hugogalley/DEV/numera/frontend && npm run build`
Expected: `tsc --noEmit` sans erreur puis build Vite réussi.

- [ ] **Step 11: Contrôle manuel (dev)**

Lancer `cd backend && uvicorn app.main:app --reload --port 8001` et `cd frontend && npm run dev`. Vérifier : la page `/month-review` charge le mois précédent ; catégoriser une dépense retire la ligne ; « Valider le solde » passe le compte en « Validé » ; marquer une dépense exceptionnelle affiche la ligne « hors exceptionnelles » ; clôturer puis rouvrir ; la pop-up apparaît sur le Dashboard tant que le mois précédent n'est pas clôturé, et « Plus tard » / « Pas ce mois-ci » la masquent ; mode confidentialité (œil) floute les montants.

- [ ] **Step 12: Commit**

```bash
cd /Users/hugogalley/DEV/numera && git add frontend/src
git commit -m "$(cat <<'EOF'
feat(revue-mois): page de revue, pop-up du Dashboard et case « exceptionnelle »

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Documentation et validation finale

**Files:**
- Modify: `ARCHITECTURE.md`, `CLAUDE.md`, `frontend/src/CLAUDE.md`, `mcp-server/README.md`, `ROADMAP.md`, `.claude/skills/numera-expert/SKILL.md`, `docs/superpowers/specs/2026-10-13-month-review-design.md`

- [ ] **Step 1: ARCHITECTURE.md**

- Ligne des champs de `transactions` (~133) : ajouter `is_exceptional` (dépense hors norme : reste dans les totaux, isolée dans la lecture « hors exceptionnel »).
- Section modèle de données, après `reimbursement_claims` (~167) : ajouter  
  `- \`month_closures\` (revue de fin de mois : \`year\`, \`month\` uniques ensemble, \`closed_at\`, \`highlight\`, photo \`tx_count\`/\`income\`/\`expenses\`/\`unresolved_count\`). Marqueur non bloquant ; « modifié depuis la clôture » = écart entre la photo et le recalcul. Logique : \`core/month_review.py\`.`
- Section routes, après `/reimbursements` (~197) : ajouter  
  `- \`/month-review\` : \`GET ?year=&month=\` (étapes catégoriser, soldes, budget + statut), \`POST /close\` (\`year\`, \`month\`, \`highlight\`), \`DELETE ?year=&month=\` (rouvrir), \`GET /closures\``
- Ligne `GET /analytics/monthly-report` (~238) : préciser les champs `exceptional_expenses`, `real_expenses_excl_exceptional`, `savings_excl_exceptional`, `savings_rate_excl_exceptional`, `burn_rate_excl_exceptional`.

- [ ] **Step 2: CLAUDE.md racine, frontend et MCP**

- `CLAUDE.md` (ligne MCP, ~68) : remplacer « 35 outils » par « 37 outils ». Dans « Règles métier critiques », ajouter : `10. Revue de fin de mois : clôturer = marquer (jamais verrouiller) ; \`is_exceptional\` reste dans les totaux officiels, seules les lectures « hors exceptionnel » l'isolent.`
- `frontend/src/CLAUDE.md` : ajouter `/month-review` (revue de fin de mois, `MonthReview.tsx`, pop-up `MonthReviewPopup` sur le Dashboard) à la liste des routes de `App.tsx`.
- `mcp-server/README.md` : « 35 outils » → « 37 outils » (ligne 9) et ajouter `get_month_review`, `list_month_closures` à la liste des outils d'analyse (ligne 33).

- [ ] **Step 3: ROADMAP, skill et spec**

- `ROADMAP.md` : point 4 des « Idées retenues » → préfixer `*(réalisé : page /month-review, drapeau exceptionnel)*`, comme le point 2.
- `.claude/skills/numera-expert/SKILL.md` : ajouter une courte section « Revue de fin de mois » : marqueur non bloquant, photo `month_closures`, `is_exceptional` hors catégories d'investissement, étape 1 bornée au mois (≠ Centre d'Actions global).
- Spec, §3.1 : corriger « doublons non ignorés (`is_duplicate_ignored`) » en « mêmes filtres que la requête `uncategorized-expenses` de l'audit (`Sortie`, hors virement, sans catégorie), bornés au mois » ; et §4 étape 3 : « chaque dépassement permet de marquer… » → « la liste des plus grosses dépenses du mois permet de marquer une transaction exceptionnelle ».

- [ ] **Step 4: Validation complète**

Run: `cd /Users/hugogalley/DEV/numera && make validate`
Expected: tests backend tous PASS, build frontend sans erreur TypeScript.

- [ ] **Step 5: Commit**

```bash
cd /Users/hugogalley/DEV/numera && git add ARCHITECTURE.md CLAUDE.md frontend/src/CLAUDE.md mcp-server/README.md ROADMAP.md .claude/skills/numera-expert/SKILL.md docs/superpowers
git commit -m "$(cat <<'EOF'
docs(revue-mois): architecture, MCP, roadmap et skill numera-expert

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```
