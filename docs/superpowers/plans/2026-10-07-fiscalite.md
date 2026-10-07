# Fiscalité et enveloppes françaises Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une page « Fiscalité » (`/tax`) qui suit plafonds, dates clés et récap fiscal annuel du CTO pour PEA, PER, CTO, assurance-vie et Livret A.

**Architecture:** Deux colonnes sur `accounts` (`tax_wrapper`, `opened_at`) et trois réglages dans `system_settings`. Les règles chiffrées vivent dans `core/tax_rules.py` (table par année), les calculs purs dans `core/tax.py`, l'agrégation base de données dans `api/analytics/tax.py`, exposée par un router `api/tax.py`. Tout est calculé à la volée côté backend ; le frontend est présentatif.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, pytest · React 18, TypeScript, Tailwind, shadcn/ui, lucide-react.

**Spec:** `docs/superpowers/specs/2026-10-07-fiscalite-design.md`

## Global Constraints

- Montants toujours positifs ; KPI calculés côté backend uniquement (règles métier 1 et 2 de `CLAUDE.md`).
- Python 3.11 ou 3.12 ; tests : `cd backend && PYTHONPATH=. python3.11 -m pytest tests/<fichier> -v`.
- Un nouveau router doit être ajouté à `protected_routers` dans `backend/app/main.py`.
- Schéma modifié → nouvelle migration Alembic ; la tête actuelle est `f1b7c4a9d2e6`.
- Frontend : `cd frontend && npm run build` doit rester à 0 erreur TypeScript ; montants via `formatCurrency` + classe `amount-blur` ; `toast` après chaque mutation ; `Skeleton` au chargement.
- Nouvelle page navigable → Sidebar **et** Omnibox.
- Valeurs réglementaires uniquement dans `core/tax_rules.py`, marquées « à vérifier » ; aucune autre valeur chiffrée codée en dur.
- Commits directement sur `main`, pas de branche ni de PR. Terminer chaque message de commit par `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Messages de commit et textes UI en français.

## Review Focus

- Enveloppe sans `opened_at` : pas de crash, âge `None`, alerte « date d'ouverture manquante » (Task 2 et 3).
- Année sans règles dans la table : repli sur la dernière année connue (Task 2).
- Aucun compte avec `tax_wrapper` : `overview` renvoie `wrappers: []`, la page affiche un message (Task 3 et 6).
- `revenus pro N-1 = 0` pour le PER : plafond = plancher, pas de division ni de plafond nul (Task 2).
- Compte CTO sans vente ni dividende pour l'année demandée : ligne à zéro, pas d'erreur (Task 4).
- Ventes dont le coût est inconnu (`realized_unknown_sales`) : signalées, jamais comptées à zéro en silence (Task 4).

---

## File Structure

| Fichier | Responsabilité |
|---|---|
| `backend/app/models/account.py` | colonnes `tax_wrapper`, `opened_at` |
| `backend/alembic/versions/a7c3e1f9b2d4_account_tax_wrapper.py` | migration |
| `backend/app/schemas/account.py` | champs exposés par l'API comptes |
| `backend/app/core/tax_rules.py` | table de règles par année (plafonds, taux) |
| `backend/app/core/tax.py` | calculs purs par enveloppe (sans base de données) |
| `backend/app/schemas/tax.py` | schémas Pydantic de l'API fiscalité |
| `backend/app/api/analytics/tax.py` | lecture des données, réglages, aperçu, récap annuel |
| `backend/app/api/tax.py` | router `/tax` |
| `backend/tests/test_tax_rules.py` | tests des calculs purs |
| `backend/tests/test_tax_api.py` | tests des endpoints |
| `frontend/src/pages/Tax.tsx` | page Fiscalité |
| `frontend/src/pages/Accounts.tsx` | champs enveloppe et date d'ouverture |

---

### Task 1: Colonnes `tax_wrapper` et `opened_at` sur les comptes

**Files:**
- Modify: `backend/app/models/account.py`
- Create: `backend/alembic/versions/a7c3e1f9b2d4_account_tax_wrapper.py`
- Modify: `backend/app/schemas/account.py`
- Modify: `backend/app/api/accounts.py` (fonction `create_account`)
- Test: `backend/tests/test_tax_api.py`

**Interfaces:**
- Produces: `Account.tax_wrapper: str | None` parmi `pea|per|cto|assurance_vie|livret_a` ; `Account.opened_at: date | None` ; exposés par `POST/PATCH/GET /accounts`.

- [ ] **Step 1: Écrire le test qui échoue**

Créer `backend/tests/test_tax_api.py` :

```python
"""Fiscalité : enveloppes, plafonds, dates clés, récap annuel du CTO."""
from datetime import date

import pytest


def _account(client, name="PEA", type_="investissement", **extra) -> dict:
    resp = client.post("/accounts", json={"name": name, "type": type_, "currency": "EUR", "color": None, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_account_keeps_tax_wrapper_and_opening_date(client):
    created = _account(client, tax_wrapper="pea", opened_at="2019-03-15")
    assert created["tax_wrapper"] == "pea"
    assert created["opened_at"] == "2019-03-15"

    resp = client.patch(f"/accounts/{created['id']}", json={"tax_wrapper": "cto", "opened_at": "2020-01-02"})
    assert resp.status_code == 200
    assert resp.json()["tax_wrapper"] == "cto"
    assert resp.json()["opened_at"] == "2020-01-02"

    cleared = client.patch(f"/accounts/{created['id']}", json={"tax_wrapper": None})
    assert cleared.json()["tax_wrapper"] is None
    assert cleared.json()["opened_at"] == "2020-01-02"


def test_account_rejects_unknown_wrapper(client):
    resp = client.post("/accounts", json={"name": "X", "type": "investissement", "currency": "EUR", "tax_wrapper": "lep"})
    assert resp.status_code == 422
```

- [ ] **Step 2: Vérifier l'échec**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_tax_api.py -v`
Expected: FAIL (`KeyError: 'tax_wrapper'`).

- [ ] **Step 3: Ajouter les colonnes au modèle**

Dans `backend/app/models/account.py`, vérifier que `Date` est importé depuis `sqlalchemy` et que `date` l'est depuis `datetime`, puis ajouter après `valuation_mode` :

```python
    # Enveloppe fiscale française (pea, per, cto, assurance_vie, livret_a) et date d'ouverture : page Fiscalité
    tax_wrapper: Mapped[str | None] = mapped_column(String(16), nullable=True)
    opened_at: Mapped[date | None] = mapped_column(Date, nullable=True)
```

- [ ] **Step 4: Écrire la migration**

Créer `backend/alembic/versions/a7c3e1f9b2d4_account_tax_wrapper.py` :

```python
"""enveloppe fiscale et date d'ouverture d'un compte

Revision ID: a7c3e1f9b2d4
Revises: f1b7c4a9d2e6
Create Date: 2026-10-07 23:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c3e1f9b2d4"
down_revision: Union[str, None] = "f1b7c4a9d2e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("accounts") as batch:
        batch.add_column(sa.Column("tax_wrapper", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("opened_at", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("opened_at")
        batch.drop_column("tax_wrapper")
```

- [ ] **Step 5: Exposer les champs dans les schémas**

Dans `backend/app/schemas/account.py`, remplacer `from datetime import datetime` par `from datetime import date, datetime`, ajouter avant `class AccountBase` :

```python
TaxWrapper = Literal["pea", "per", "cto", "assurance_vie", "livret_a"]
```

puis dans `AccountBase` (après `valuation_mode`) et dans `AccountUpdate` (après `valuation_mode`) :

```python
    tax_wrapper: TaxWrapper | None = None
    opened_at: date | None = None
```

- [ ] **Step 6: Persister à la création**

Dans `create_account` de `backend/app/api/accounts.py`, ajouter dans le constructeur `Account(...)`, après `fonds_investis_pct=payload.fonds_investis_pct,` :

```python
        tax_wrapper=payload.tax_wrapper,
        opened_at=payload.opened_at,
```

- [ ] **Step 7: Vérifier que les tests passent, ainsi que la migration**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_tax_api.py tests/test_assurance_vie.py -v && PYTHONPATH=. python3.11 -m alembic heads`
Expected: tests PASS ; `alembic heads` affiche `a7c3e1f9b2d4 (head)` une seule fois.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/account.py backend/alembic/versions/a7c3e1f9b2d4_account_tax_wrapper.py backend/app/schemas/account.py backend/app/api/accounts.py backend/tests/test_tax_api.py
git commit -m "feat(fiscalite): enveloppe fiscale et date d'ouverture sur les comptes

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Règles chiffrées et calculs purs

**Files:**
- Create: `backend/app/core/tax_rules.py`
- Create: `backend/app/core/tax.py`
- Test: `backend/tests/test_tax_rules.py`

**Interfaces:**
- Produces (`core/tax_rules.py`) :
  - `@dataclass(frozen=True) TaxRules(year, pea_ceiling, livret_a_ceiling, per_rate, per_floor, per_ceiling, av_allowance_single, av_allowance_couple, pfu_rate)`
  - `rules_for(year: int) -> TaxRules` (repli sur la dernière année connue)
- Produces (`core/tax.py`), toutes pures :
  - `years_between(start: date, end: date) -> float`
  - `pea_status(contributions: float, opened_at: date | None, withdrawals: list[date], today: date, rules: TaxRules) -> dict`
  - `per_deduction_ceiling(prior_year_income: float, rules: TaxRules) -> float`
  - `per_status(contributed_this_year: float, prior_year_income: float, tmi_pct: float, rules: TaxRules) -> dict`
  - `livret_a_status(balance: float, rules: TaxRules) -> dict`
  - `av_status(opened_at: date | None, household: str, today: date, rules: TaxRules) -> dict`
  - Chaque `*_status` renvoie un dict avec les clés `current`, `ceiling`, `remaining`, `used_pct`, `age_years`, `milestone_years`, `milestone_reached`, `estimated_tax_saving`, `allowance`, `alerts` (valeur `None` quand non pertinent).

- [ ] **Step 1: Écrire les tests qui échouent**

Créer `backend/tests/test_tax_rules.py` :

```python
"""Calculs fiscaux purs : aucun accès base de données."""
from datetime import date

import pytest

from app.core.tax import av_status, livret_a_status, pea_status, per_deduction_ceiling, per_status, years_between
from app.core.tax_rules import rules_for

TODAY = date(2026, 10, 7)
RULES = rules_for(2026)


def test_rules_for_unknown_year_falls_back_to_latest_known():
    assert rules_for(2099).year == max(rules_for(y).year for y in (2025, 2026))
    assert rules_for(1990).year == min(rules_for(y).year for y in (2025, 2026))


def test_years_between_is_calendar_aware():
    assert years_between(date(2021, 10, 7), date(2026, 10, 7)) == pytest.approx(5.0, abs=0.01)
    assert years_between(date(2021, 10, 8), date(2026, 10, 7)) < 5.0


def test_pea_remaining_room_and_percentage():
    status = pea_status(60_000.0, date(2019, 3, 15), [], TODAY, RULES)
    assert status["current"] == 60_000.0
    assert status["ceiling"] == RULES.pea_ceiling
    assert status["remaining"] == pytest.approx(RULES.pea_ceiling - 60_000.0)
    assert status["used_pct"] == pytest.approx(60_000.0 / RULES.pea_ceiling * 100.0)
    assert status["milestone_years"] == 5
    assert status["milestone_reached"] is True
    assert status["alerts"] == []


def test_pea_over_ceiling_never_negative_and_alerts():
    status = pea_status(RULES.pea_ceiling + 1_000.0, date(2019, 3, 15), [], TODAY, RULES)
    assert status["remaining"] == 0.0
    assert any("plafond" in a.lower() for a in status["alerts"])


def test_pea_withdrawal_before_five_years_alerts():
    status = pea_status(10_000.0, date(2024, 1, 10), [date(2025, 6, 1)], TODAY, RULES)
    assert status["milestone_reached"] is False
    assert any("5 ans" in a for a in status["alerts"])


def test_pea_withdrawal_after_five_years_is_fine():
    status = pea_status(10_000.0, date(2019, 1, 10), [date(2025, 6, 1)], TODAY, RULES)
    assert status["alerts"] == []


def test_pea_without_opening_date_does_not_crash():
    status = pea_status(10_000.0, None, [], TODAY, RULES)
    assert status["age_years"] is None
    assert status["milestone_reached"] is None
    assert any("date d'ouverture" in a.lower() for a in status["alerts"])


def test_per_ceiling_is_ten_percent_bounded_by_floor_and_cap():
    assert per_deduction_ceiling(0.0, RULES) == RULES.per_floor
    assert per_deduction_ceiling(1_000_000.0, RULES) == RULES.per_ceiling
    middle = (RULES.per_floor + RULES.per_ceiling) / 2 / RULES.per_rate
    assert per_deduction_ceiling(middle, RULES) == pytest.approx(middle * RULES.per_rate)


def test_per_status_tax_saving_is_contribution_times_tmi():
    status = per_status(3_000.0, 40_000.0, 30.0, RULES)
    deductible = min(3_000.0, status["ceiling"])
    assert status["current"] == 3_000.0
    assert status["estimated_tax_saving"] == pytest.approx(deductible * 0.30)
    assert status["remaining"] == pytest.approx(status["ceiling"] - 3_000.0)


def test_per_contribution_above_ceiling_only_deducts_the_ceiling():
    status = per_status(100_000.0, 40_000.0, 30.0, RULES)
    assert status["remaining"] == 0.0
    assert status["estimated_tax_saving"] == pytest.approx(status["ceiling"] * 0.30)
    assert status["alerts"]


def test_livret_a_room_and_overflow():
    ok = livret_a_status(10_000.0, RULES)
    assert ok["remaining"] == pytest.approx(RULES.livret_a_ceiling - 10_000.0)
    over = livret_a_status(RULES.livret_a_ceiling + 500.0, RULES)
    assert over["remaining"] == 0.0
    assert over["used_pct"] == pytest.approx((RULES.livret_a_ceiling + 500.0) / RULES.livret_a_ceiling * 100.0)


def test_av_milestone_and_allowance_by_household():
    single = av_status(date(2017, 5, 1), "single", TODAY, RULES)
    couple = av_status(date(2017, 5, 1), "couple", TODAY, RULES)
    assert single["milestone_years"] == 8
    assert single["milestone_reached"] is True
    assert single["allowance"] == RULES.av_allowance_single
    assert couple["allowance"] == RULES.av_allowance_couple


def test_av_before_eight_years_not_reached():
    status = av_status(date(2022, 5, 1), "single", TODAY, RULES)
    assert status["milestone_reached"] is False
    assert status["age_years"] == pytest.approx(4.4, abs=0.1)
```

- [ ] **Step 2: Vérifier l'échec**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_tax_rules.py -v`
Expected: FAIL (`ModuleNotFoundError: app.core.tax`).

- [ ] **Step 3: Écrire la table de règles**

Créer `backend/app/core/tax_rules.py` :

```python
"""Règles fiscales françaises chiffrées, par année. Seul fichier qui porte ces valeurs.

À VÉRIFIER chaque début d'année auprès de service-public.fr / impots.gouv.fr avant de s'y fier :
les plafonds PER dépendent du PASS de l'année N-1, et le taux des prélèvements sociaux peut évoluer.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TaxRules:
    year: int
    pea_ceiling: float            # plafond de versements cumulés du PEA
    livret_a_ceiling: float       # plafond de dépôts du Livret A
    per_rate: float               # part des revenus pro déductible au PER
    per_floor: float              # plafond de déduction minimal (10 % du PASS N-1)
    per_ceiling: float            # plafond de déduction maximal (10 % de 8 PASS N-1)
    av_allowance_single: float    # abattement annuel sur les gains de rachat d'AV > 8 ans (seul)
    av_allowance_couple: float    # idem, couple
    pfu_rate: float               # prélèvement forfaitaire unique (impôt + prélèvements sociaux)


RULES_BY_YEAR: dict[int, TaxRules] = {
    # À vérifier
    2025: TaxRules(2025, 150_000.0, 22_950.0, 0.10, 4_637.0, 37_094.0, 4_600.0, 9_200.0, 0.30),
    # À vérifier : PASS 2025 = 47 100 € ; taux PFU à confirmer pour 2026
    2026: TaxRules(2026, 150_000.0, 22_950.0, 0.10, 4_710.0, 37_680.0, 4_600.0, 9_200.0, 0.30),
}


def rules_for(year: int) -> TaxRules:
    """Règles de l'année ; à défaut, de la plus proche année connue (jamais d'erreur)."""
    if year in RULES_BY_YEAR:
        return RULES_BY_YEAR[year]
    nearest = min(RULES_BY_YEAR, key=lambda known: abs(known - year))
    return RULES_BY_YEAR[nearest]
```

- [ ] **Step 4: Écrire les calculs purs**

Créer `backend/app/core/tax.py` :

```python
"""Calculs fiscaux par enveloppe. Fonctions pures : aucune base de données, aucun appel réseau."""
from datetime import date

from app.core.tax_rules import TaxRules

PEA_MILESTONE_YEARS = 5
AV_MILESTONE_YEARS = 8


def years_between(start: date, end: date) -> float:
    """Années écoulées entre deux dates (calendaires, fractionnaires)."""
    whole = end.year - start.year - ((end.month, end.day) < (start.month, start.day))
    anniversary = date(start.year + whole, start.month, start.day if not (start.month == 2 and start.day == 29) else 28)
    next_anniversary = date(anniversary.year + 1, anniversary.month, anniversary.day)
    return whole + (end - anniversary).days / max((next_anniversary - anniversary).days, 1)


def _blank(**overrides) -> dict:
    status = {
        "current": None, "ceiling": None, "remaining": None, "used_pct": None,
        "age_years": None, "milestone_years": None, "milestone_reached": None,
        "estimated_tax_saving": None, "allowance": None, "alerts": [],
    }
    status.update(overrides)
    return status


def _room(current: float, ceiling: float) -> tuple[float, float]:
    return max(ceiling - current, 0.0), (current / ceiling * 100.0 if ceiling > 0 else 0.0)


def pea_status(contributions: float, opened_at: date | None, withdrawals: list[date], today: date, rules: TaxRules) -> dict:
    """Versements cumulés (un retrait ne restitue pas de place) et ancienneté du plan."""
    remaining, used_pct = _room(contributions, rules.pea_ceiling)
    alerts: list[str] = []
    age = reached = None
    if opened_at is None:
        alerts.append("Date d'ouverture manquante : renseigne-la dans les paramètres du compte.")
    else:
        age = years_between(opened_at, today)
        reached = age >= PEA_MILESTONE_YEARS
        if any(years_between(opened_at, w) < PEA_MILESTONE_YEARS for w in withdrawals):
            alerts.append("Retrait avant 5 ans : la fiscalité avantageuse du PEA est perdue.")
    if contributions > rules.pea_ceiling:
        alerts.append("Plafond de versements du PEA dépassé.")
    return _blank(
        current=contributions, ceiling=rules.pea_ceiling, remaining=remaining, used_pct=used_pct,
        age_years=age, milestone_years=PEA_MILESTONE_YEARS, milestone_reached=reached, alerts=alerts,
    )


def per_deduction_ceiling(prior_year_income: float, rules: TaxRules) -> float:
    """10 % des revenus pro de N-1, borné entre le plancher et le plafond de l'année."""
    return min(max(prior_year_income * rules.per_rate, rules.per_floor), rules.per_ceiling)


def per_status(contributed_this_year: float, prior_year_income: float, tmi_pct: float, rules: TaxRules) -> dict:
    """Versements de l'année civile face au plafond de déduction, économie d'impôt = déductible × TMI."""
    ceiling = per_deduction_ceiling(prior_year_income, rules)
    remaining, used_pct = _room(contributed_this_year, ceiling)
    alerts = []
    if contributed_this_year > ceiling:
        alerts.append("Versements supérieurs au plafond de déduction : l'excédent n'est pas déductible.")
    return _blank(
        current=contributed_this_year, ceiling=ceiling, remaining=remaining, used_pct=used_pct,
        estimated_tax_saving=min(contributed_this_year, ceiling) * tmi_pct / 100.0, alerts=alerts,
    )


def livret_a_status(balance: float, rules: TaxRules) -> dict:
    remaining, used_pct = _room(balance, rules.livret_a_ceiling)
    alerts = ["Solde supérieur au plafond du Livret A."] if balance > rules.livret_a_ceiling else []
    return _blank(current=balance, ceiling=rules.livret_a_ceiling, remaining=remaining, used_pct=used_pct, alerts=alerts)


def av_status(opened_at: date | None, household: str, today: date, rules: TaxRules) -> dict:
    """Ancienneté face aux 8 ans et abattement annuel applicable aux gains de rachat."""
    allowance = rules.av_allowance_couple if household == "couple" else rules.av_allowance_single
    if opened_at is None:
        return _blank(
            milestone_years=AV_MILESTONE_YEARS, allowance=allowance,
            alerts=["Date d'ouverture manquante : renseigne-la dans les paramètres du compte."],
        )
    age = years_between(opened_at, today)
    return _blank(age_years=age, milestone_years=AV_MILESTONE_YEARS, milestone_reached=age >= AV_MILESTONE_YEARS, allowance=allowance)
```

- [ ] **Step 5: Vérifier que les tests passent**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_tax_rules.py -v`
Expected: tous PASS. Si `test_years_between_is_calendar_aware` échoue d'un cheveu, corriger `years_between` (pas le test).

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/tax_rules.py backend/app/core/tax.py backend/tests/test_tax_rules.py
git commit -m "feat(fiscalite): règles par année et calculs purs des plafonds et dates clés

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Réglages, aperçu des enveloppes et router `/tax`

**Files:**
- Create: `backend/app/schemas/tax.py`
- Create: `backend/app/api/analytics/tax.py`
- Create: `backend/app/api/tax.py`
- Modify: `backend/app/main.py` (import + `protected_routers`)
- Modify: `backend/tests/test_tax_api.py`

**Interfaces:**
- Consumes: `rules_for`, `pea_status`, `per_status`, `livret_a_status`, `av_status` (Task 2) ; `app.db.system_settings.get_setting/set_setting` ; `app.api.accounts._get_balance_for_account(db, account_id) -> float`.
- Produces (`schemas/tax.py`) : `TaxSettings(tmi_pct: float = 30.0, prior_year_pro_income: float = 0.0, household: Literal["single","couple"] = "single")`, `TaxSettingsUpdate` (champs optionnels), `WrapperCard`, `TaxOverview(year: int, settings: TaxSettings, wrappers: list[WrapperCard])`.
- Produces (`api/analytics/tax.py`) : `load_tax_settings(db) -> TaxSettings`, `save_tax_settings(db, update: TaxSettingsUpdate) -> TaxSettings`, `build_overview(db, today: date) -> TaxOverview`.
- Produces (HTTP) : `GET /tax/overview`, `GET /tax/settings`, `PATCH /tax/settings`.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `backend/tests/test_tax_api.py` (en haut, ajouter `from datetime import datetime` à l'import existant, puis en bas du fichier) :

```python
def _versement(client, account_id, amount, *, date_iso, type_="versement"):
    resp = client.post("/investment-transactions", json={"account_id": account_id, "date": date_iso, "type": type_, "amount": amount})
    assert resp.status_code == 201, resp.text


def test_settings_have_defaults_then_persist(client):
    assert client.get("/tax/settings").json() == {"tmi_pct": 30.0, "prior_year_pro_income": 0.0, "household": "single"}
    resp = client.patch("/tax/settings", json={"tmi_pct": 41, "prior_year_pro_income": 52000, "household": "couple"})
    assert resp.status_code == 200
    assert client.get("/tax/settings").json() == {"tmi_pct": 41.0, "prior_year_pro_income": 52000.0, "household": "couple"}


def test_settings_reject_invalid_tmi(client):
    assert client.patch("/tax/settings", json={"tmi_pct": 80}).status_code == 422


def test_overview_empty_without_wrapper(client):
    _account(client, name="Compte sans enveloppe")
    body = client.get("/tax/overview").json()
    assert body["wrappers"] == []


def test_overview_pea_counts_contributions_and_ignores_withdrawals(client):
    pea = _account(client, name="PEA", tax_wrapper="pea", opened_at="2018-01-01")
    _versement(client, pea["id"], 20_000.0, date_iso="2024-02-01T00:00:00")
    _versement(client, pea["id"], 5_000.0, date_iso="2025-02-01T00:00:00", type_="retrait")
    card = next(w for w in client.get("/tax/overview").json()["wrappers"] if w["kind"] == "pea")
    assert card["account_id"] == pea["id"]
    assert card["current"] == 20_000.0
    assert card["remaining"] == pytest.approx(150_000.0 - 20_000.0)
    assert card["milestone_reached"] is True


def test_overview_per_counts_only_current_year_contributions(client):
    per = _account(client, name="PER", tax_wrapper="per", opened_at="2022-01-01")
    year = date.today().year
    _versement(client, per["id"], 2_000.0, date_iso=f"{year}-01-15T00:00:00")
    _versement(client, per["id"], 9_999.0, date_iso=f"{year - 1}-06-15T00:00:00")
    client.patch("/tax/settings", json={"tmi_pct": 30, "prior_year_pro_income": 40_000})
    card = next(w for w in client.get("/tax/overview").json()["wrappers"] if w["kind"] == "per")
    assert card["current"] == 2_000.0
    assert card["estimated_tax_saving"] == pytest.approx(600.0)


def test_overview_livret_a_uses_account_balance(client):
    la = _account(client, name="Livret A", type_="epargne", tax_wrapper="livret_a")
    resp = client.post("/balance-snapshots", json={"account_id": la["id"], "date": "2026-01-01T00:00:00", "current_value": 12_000.0})
    assert resp.status_code in (200, 201), resp.text
    card = next(w for w in client.get("/tax/overview").json()["wrappers"] if w["kind"] == "livret_a")
    assert card["current"] == 12_000.0
    assert card["remaining"] == pytest.approx(22_950.0 - 12_000.0)


def test_overview_wrapper_without_opening_date_alerts(client):
    _account(client, name="AV", type_="assurance_vie", tax_wrapper="assurance_vie")
    card = next(w for w in client.get("/tax/overview").json()["wrappers"] if w["kind"] == "assurance_vie")
    assert card["age_years"] is None
    assert any("date d'ouverture" in a.lower() for a in card["alerts"])


def test_tax_routes_require_authentication(db_session):
    from fastapi.testclient import TestClient
    from app.main import app

    app.dependency_overrides.clear()
    with TestClient(app) as anonymous:
        assert anonymous.get("/tax/overview").status_code in (401, 403)
```

Le corps de `balance-snapshots` doit correspondre au schéma réel : avant de lancer, lire `backend/app/schemas/balance_snapshot.py` et ajuster les champs du `client.post("/balance-snapshots", …)` (nom des champs, préfixe de route) si besoin.

- [ ] **Step 2: Vérifier l'échec**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_tax_api.py -v`
Expected: les nouveaux tests FAIL (404 sur `/tax/...`).

- [ ] **Step 3: Écrire les schémas**

Créer `backend/app/schemas/tax.py` :

```python
from typing import Literal

from pydantic import BaseModel, Field

Household = Literal["single", "couple"]


class TaxSettings(BaseModel):
    tmi_pct: float = 30.0
    prior_year_pro_income: float = 0.0
    household: Household = "single"


class TaxSettingsUpdate(BaseModel):
    tmi_pct: float | None = Field(default=None, ge=0, le=45)
    prior_year_pro_income: float | None = Field(default=None, ge=0)
    household: Household | None = None


class WrapperCard(BaseModel):
    kind: Literal["pea", "per", "cto", "assurance_vie", "livret_a"]
    account_id: int
    account_name: str
    opened_at: str | None = None
    current: float | None = None
    ceiling: float | None = None
    remaining: float | None = None
    used_pct: float | None = None
    age_years: float | None = None
    milestone_years: int | None = None
    milestone_reached: bool | None = None
    estimated_tax_saving: float | None = None
    allowance: float | None = None
    alerts: list[str] = []


class TaxOverview(BaseModel):
    year: int
    settings: TaxSettings
    wrappers: list[WrapperCard]
```

- [ ] **Step 4: Écrire l'agrégation**

Créer `backend/app/api/analytics/tax.py` :

```python
"""Page Fiscalité : réglages, aperçu des enveloppes, récap annuel du CTO."""
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.api.accounts import _get_balance_for_account
from app.core.tax import av_status, livret_a_status, pea_status, per_status
from app.core.tax_rules import rules_for
from app.db.system_settings import get_setting, set_setting
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.schemas.tax import TaxOverview, TaxSettings, TaxSettingsUpdate, WrapperCard

SETTING_KEYS = {
    "tmi_pct": "tax_tmi_pct",
    "prior_year_pro_income": "tax_prior_year_pro_income",
    "household": "tax_household",
}


def load_tax_settings(db: Session) -> TaxSettings:
    defaults = TaxSettings()
    return TaxSettings(
        tmi_pct=float(get_setting(db, SETTING_KEYS["tmi_pct"], defaults.tmi_pct)),
        prior_year_pro_income=float(get_setting(db, SETTING_KEYS["prior_year_pro_income"], defaults.prior_year_pro_income)),
        household=get_setting(db, SETTING_KEYS["household"], defaults.household),
    )


def save_tax_settings(db: Session, update: TaxSettingsUpdate) -> TaxSettings:
    for field, value in update.model_dump(exclude_unset=True).items():
        if value is not None:
            set_setting(db, SETTING_KEYS[field], str(value))
    db.commit()
    return load_tax_settings(db)


def _contributions(db: Session, account_id: int, tx_type: str, *, year: int | None = None) -> list[InvestmentTransaction]:
    query = db.query(InvestmentTransaction).filter(
        InvestmentTransaction.account_id == account_id, InvestmentTransaction.type == tx_type
    )
    if year is not None:
        query = query.filter(
            InvestmentTransaction.date >= datetime(year, 1, 1), InvestmentTransaction.date < datetime(year + 1, 1, 1)
        )
    return query.all()


def build_overview(db: Session, today: date) -> TaxOverview:
    rules = rules_for(today.year)
    settings = load_tax_settings(db)
    accounts = (
        db.query(Account)
        .filter(Account.tax_wrapper.isnot(None), Account.active.is_(True))
        .order_by(Account.id.asc())
        .all()
    )
    cards: list[WrapperCard] = []
    for account in accounts:
        kind = account.tax_wrapper
        if kind == "pea":
            versements = sum(t.amount for t in _contributions(db, account.id, "versement"))
            withdrawals = [t.date.date() for t in _contributions(db, account.id, "retrait")]
            status = pea_status(versements, account.opened_at, withdrawals, today, rules)
        elif kind == "per":
            versements = sum(t.amount for t in _contributions(db, account.id, "versement", year=today.year))
            status = per_status(versements, settings.prior_year_pro_income, settings.tmi_pct, rules)
        elif kind == "livret_a":
            status = livret_a_status(_get_balance_for_account(db, account.id), rules)
        elif kind == "assurance_vie":
            status = av_status(account.opened_at, settings.household, today, rules)
        else:  # cto : pas de plafond, seul le récap annuel compte
            status = {}
        cards.append(
            WrapperCard(
                kind=kind,
                account_id=account.id,
                account_name=account.name,
                opened_at=account.opened_at.isoformat() if account.opened_at else None,
                **status,
            )
        )
    return TaxOverview(year=today.year, settings=settings, wrappers=cards)
```

- [ ] **Step 5: Écrire le router**

Créer `backend/app/api/tax.py` :

```python
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.analytics.tax import build_overview, load_tax_settings, save_tax_settings
from app.db.session import get_db
from app.schemas.tax import TaxOverview, TaxSettings, TaxSettingsUpdate

router = APIRouter(prefix="/tax", tags=["tax"])


@router.get("/overview", response_model=TaxOverview)
def get_overview(db: Session = Depends(get_db)):
    return build_overview(db, date.today())


@router.get("/settings", response_model=TaxSettings)
def get_settings(db: Session = Depends(get_db)):
    return load_tax_settings(db)


@router.patch("/settings", response_model=TaxSettings)
def update_settings(payload: TaxSettingsUpdate, db: Session = Depends(get_db)):
    return save_tax_settings(db, payload)
```

- [ ] **Step 6: Enregistrer le router**

Dans `backend/app/main.py`, ajouter après `from app.api.holdings import router as holdings_router` :

```python
from app.api.tax import router as tax_router
```

et ajouter `tax_router,` à la fin de la liste `protected_routers` (après `diversity_router,`).

- [ ] **Step 7: Vérifier**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_tax_api.py tests/test_tax_rules.py -v`
Expected: tous PASS. Le test d'authentification vérifie que `/tax/overview` n'est pas public.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/tax.py backend/app/api/analytics/tax.py backend/app/api/tax.py backend/app/main.py backend/tests/test_tax_api.py
git commit -m "feat(fiscalite): réglages et aperçu des plafonds par enveloppe

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Récap fiscal annuel du CTO

**Files:**
- Modify: `backend/app/schemas/tax.py`
- Modify: `backend/app/api/analytics/tax.py`
- Modify: `backend/app/api/tax.py`
- Modify: `backend/tests/test_tax_api.py`

**Interfaces:**
- Consumes: `compute_portfolio(db, account, *, fetch=False, history=False)` (`core/portfolio.py`, renvoie `realized_by_year: list[{"year","realized_eur","proceeds_eur","sales"}]` et `realized_unknown_sales: int`) ; `load_dividends_eur(db, account_id) -> list[DividendRow]` (`core/dividends.py`, `row.tx.date`, `row.gross_eur`, `row.net_eur`, `row.tax_eur`).
- Produces: `async build_annual_report(db, year: int) -> AnnualReport` ; `GET /tax/annual-report?year=`.
- `AnnualReport(year, pfu_rate, accounts: list[CtoYearRow], totals: CtoYearRow-like, box_2dc: float, box_3vg: float, box_3vh: float, estimated_pfu_eur: float, warnings: list[str])`.

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à `backend/tests/test_tax_api.py`. Ces tests réutilisent le scénario de `test_portfolio.py` (inventaire, cours stockés, marché hors ligne). En haut du fichier, ajouter les imports :

```python
from datetime import datetime, timedelta

import app.core.currency as currency_mod
import app.core.market_data as market_data
```

puis en bas :

```python
@pytest.fixture()
def offline_market(monkeypatch):
    async def no_chart(client, sym, params):
        return None

    async def fake_historical_rate(db, day, currency, base="EUR"):
        return {"EUR": 1.0, "USD": 2.0}[currency]

    monkeypatch.setattr(market_data, "_fetch_chart", no_chart)
    monkeypatch.setattr(currency_mod, "get_historical_rate", fake_historical_rate)
    market_data._QUOTES_CACHE.clear()
    yield
    market_data._QUOTES_CACHE.clear()


def _iso(days_ago: int) -> str:
    return (datetime.now() - timedelta(days=days_ago)).replace(microsecond=0).isoformat()


def _cto_with_sale_and_dividend(client, db_session, *, wrapper="cto"):
    account = _account(client, name="CTO", tax_wrapper=wrapper)
    resp = client.post("/holdings/baseline", json={
        "account_id": account["id"], "date": _iso(200),
        "holdings": [{"ticker": "CW8.PA", "asset_name": "MSCI World", "quantity": 10, "buy_price_avg": 100.0, "currency": "EUR"}],
    })
    assert resp.status_code == 200, resp.text
    for days_ago, close in ((200, 100.0), (60, 130.0), (0, 120.0)):
        market_data.store_price(db_session, "CW8.PA", (datetime.now() - timedelta(days=days_ago)).date(), close, "EUR")
    db_session.commit()
    sale = client.post("/investment-transactions", json={
        "account_id": account["id"], "date": _iso(60), "type": "vente", "amount": 520.0,
        "ticker": "CW8.PA", "quantity": 4, "unit_price": 130.0,
    })
    assert sale.status_code == 201, sale.text
    dividend = client.post("/investment-transactions", json={
        "account_id": account["id"], "date": _iso(30), "type": "dividende", "amount": 35.0,
        "ticker": "CW8.PA", "withholding_tax": 15.0,
    })
    assert dividend.status_code == 201, dividend.text
    return account


def test_annual_report_groups_dividends_and_realized_gains(client, db_session, offline_market):
    account = _cto_with_sale_and_dividend(client, db_session)
    year = (datetime.now() - timedelta(days=60)).year
    report = client.get(f"/tax/annual-report?year={year}").json()

    row = next(r for r in report["accounts"] if r["account_id"] == account["id"])
    assert row["realized_eur"] == pytest.approx(120.0)   # 520 − 4 × 100
    assert row["dividends_net_eur"] == pytest.approx(35.0)
    assert row["dividends_gross_eur"] == pytest.approx(50.0)  # net + retenue
    assert report["box_2dc"] == pytest.approx(50.0)
    assert report["box_3vg"] == pytest.approx(120.0)
    assert report["box_3vh"] == 0.0
    assert report["estimated_pfu_eur"] == pytest.approx((50.0 + 120.0) * report["pfu_rate"])


def test_annual_report_ignores_non_cto_accounts(client, db_session, offline_market):
    _cto_with_sale_and_dividend(client, db_session, wrapper="pea")
    year = (datetime.now() - timedelta(days=60)).year
    report = client.get(f"/tax/annual-report?year={year}").json()
    assert report["accounts"] == []
    assert report["box_2dc"] == 0.0
    assert report["box_3vg"] == 0.0


def test_annual_report_empty_year_is_all_zero_not_an_error(client, db_session, offline_market):
    _cto_with_sale_and_dividend(client, db_session)
    report = client.get("/tax/annual-report?year=2001")
    assert report.status_code == 200
    body = report.json()
    assert body["box_2dc"] == 0.0 and body["box_3vg"] == 0.0 and body["estimated_pfu_eur"] == 0.0
    assert body["accounts"][0]["realized_eur"] == 0.0


def test_annual_report_loss_goes_to_box_3vh_and_is_not_taxed(client, db_session, offline_market):
    account = _account(client, name="CTO", tax_wrapper="cto")
    client.post("/holdings/baseline", json={
        "account_id": account["id"], "date": _iso(200),
        "holdings": [{"ticker": "CW8.PA", "asset_name": "MSCI World", "quantity": 10, "buy_price_avg": 100.0, "currency": "EUR"}],
    })
    market_data.store_price(db_session, "CW8.PA", (datetime.now() - timedelta(days=60)).date(), 80.0, "EUR")
    db_session.commit()
    client.post("/investment-transactions", json={
        "account_id": account["id"], "date": _iso(60), "type": "vente", "amount": 320.0,
        "ticker": "CW8.PA", "quantity": 4, "unit_price": 80.0,
    })
    year = (datetime.now() - timedelta(days=60)).year
    report = client.get(f"/tax/annual-report?year={year}").json()
    assert report["box_3vh"] == pytest.approx(80.0)   # 320 − 400
    assert report["box_3vg"] == 0.0
    assert report["estimated_pfu_eur"] == 0.0
```

- [ ] **Step 2: Vérifier l'échec**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_tax_api.py -k annual -v`
Expected: FAIL (404 sur `/tax/annual-report`).

- [ ] **Step 3: Ajouter les schémas**

Ajouter à `backend/app/schemas/tax.py` :

```python
class CtoYearRow(BaseModel):
    account_id: int
    account_name: str
    dividends_gross_eur: float
    dividends_net_eur: float
    withholding_eur: float
    realized_eur: float
    proceeds_eur: float
    sales: int
    unknown_cost_sales: int


class AnnualReport(BaseModel):
    year: int
    pfu_rate: float
    accounts: list[CtoYearRow]
    box_2dc: float
    box_3vg: float
    box_3vh: float
    estimated_pfu_eur: float
    warnings: list[str] = []
```

- [ ] **Step 4: Implémenter le récap**

Ajouter à `backend/app/api/analytics/tax.py` (imports en haut du fichier : `from app.core.dividends import load_dividends_eur`, `from app.core.portfolio import compute_portfolio`, et étendre l'import des schémas avec `AnnualReport, CtoYearRow`) :

```python
async def build_annual_report(db: Session, year: int) -> AnnualReport:
    """Dividendes (2DC) et plus-values réalisées (3VG gain, 3VH perte) des comptes CTO pour l'année."""
    rules = rules_for(year)
    accounts = (
        db.query(Account).filter(Account.tax_wrapper == "cto").order_by(Account.id.asc()).all()
    )
    rows: list[CtoYearRow] = []
    warnings: list[str] = []
    for account in accounts:
        portfolio = await compute_portfolio(db, account, fetch=False, history=False)
        realized = next((e for e in portfolio["realized_by_year"] if e["year"] == year), None)
        dividends = [d for d in await load_dividends_eur(db, account.id) if d.tx.date.year == year]
        unknown = portfolio["realized_unknown_sales"] if realized else 0
        if unknown:
            warnings.append(f"{account.name} : {unknown} vente(s) sans coût de revient connu, plus-value non comptée.")
        rows.append(
            CtoYearRow(
                account_id=account.id,
                account_name=account.name,
                dividends_gross_eur=round(sum(d.gross_eur for d in dividends), 2),
                dividends_net_eur=round(sum(d.net_eur for d in dividends), 2),
                withholding_eur=round(sum(d.tax_eur for d in dividends), 2),
                realized_eur=realized["realized_eur"] if realized else 0.0,
                proceeds_eur=realized["proceeds_eur"] if realized else 0.0,
                sales=realized["sales"] if realized else 0,
                unknown_cost_sales=unknown,
            )
        )
    dividends_gross = sum(r.dividends_gross_eur for r in rows)
    realized_total = sum(r.realized_eur for r in rows)
    gains, losses = max(realized_total, 0.0), max(-realized_total, 0.0)
    return AnnualReport(
        year=year,
        pfu_rate=rules.pfu_rate,
        accounts=rows,
        box_2dc=round(dividends_gross, 2),
        box_3vg=round(gains, 2),
        box_3vh=round(losses, 2),
        estimated_pfu_eur=round((dividends_gross + gains) * rules.pfu_rate, 2),
        warnings=warnings,
    )
```

Note : une perte ne compense pas les dividendes dans l'estimation ; elle est reportée en 3VH.

- [ ] **Step 5: Ajouter l'endpoint**

Dans `backend/app/api/tax.py`, étendre les imports (`build_annual_report`, `AnnualReport`) et ajouter :

```python
@router.get("/annual-report", response_model=AnnualReport)
async def get_annual_report(year: int | None = None, db: Session = Depends(get_db)):
    return await build_annual_report(db, year or date.today().year)
```

- [ ] **Step 6: Vérifier**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests/test_tax_api.py tests/test_tax_rules.py -v`
Expected: tous PASS.

Si `box_2dc` diffère de 50 : vérifier dans `core/dividends.py` si la retenue `withholding_tax` est bien additionnée au net (`gross_eur = net_eur + tax_eur`) ; c'est la définition existante, le test doit la refléter.

- [ ] **Step 7: Suite complète**

Run: `cd backend && PYTHONPATH=. python3.11 -m pytest tests -q`
Expected: tout PASS (183 tests existants + les nouveaux).

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/tax.py backend/app/api/analytics/tax.py backend/app/api/tax.py backend/tests/test_tax_api.py
git commit -m "feat(fiscalite): récap annuel du CTO (2DC, 3VG/3VH, PFU estimé)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Enveloppe et date d'ouverture dans les paramètres de compte

**Files:**
- Modify: `frontend/src/pages/Accounts.tsx` (type `Account`, formulaires de création et d'édition)

**Interfaces:**
- Consumes: `tax_wrapper` et `opened_at` sur `POST/PATCH /accounts` (Task 1).

- [ ] **Step 1: Étendre le type et les états**

Dans `frontend/src/pages/Accounts.tsx`, ajouter au type `Account` (après `valuation_mode?`) :

```tsx
  tax_wrapper?: "pea" | "per" | "cto" | "assurance_vie" | "livret_a" | null
  opened_at?: string | null
```

Ajouter, à côté de `newValuationMode`, deux états `newTaxWrapper` (`string`, défaut `"none"`) et `newOpenedAt` (`string`, défaut `""`).

- [ ] **Step 2: Constante des enveloppes**

Au niveau module, ajouter :

```tsx
const TAX_WRAPPERS = [
  { value: "pea", label: "PEA" },
  { value: "per", label: "PER" },
  { value: "cto", label: "CTO" },
  { value: "assurance_vie", label: "Assurance-vie" },
  { value: "livret_a", label: "Livret A" },
] as const
```

- [ ] **Step 3: Champs du formulaire de création**

Après le bloc « Valorisation du compte » du dialogue de création, ajouter (même structure `Label` + `Select`) un bloc affiché si `newType !== "courant"` : un `Select` « Enveloppe fiscale » (valeur `"none"` = « Aucune », puis `TAX_WRAPPERS`) et, quand une enveloppe est choisie, un `Input type="date"` « Date d'ouverture ». Texte d'aide : « Active le suivi des plafonds et des dates clés dans la page Fiscalité. »

- [ ] **Step 4: Payload de création**

Dans le payload du `POST /accounts`, ajouter :

```tsx
        tax_wrapper: newTaxWrapper === "none" ? null : newTaxWrapper,
        opened_at: newTaxWrapper === "none" || !newOpenedAt ? null : newOpenedAt,
```

et réinitialiser `newTaxWrapper`/`newOpenedAt` à leurs valeurs par défaut après la création, comme les autres états.

- [ ] **Step 5: Édition**

Reproduire le bloc dans le dialogue d'édition en lisant et écrivant `editingAccount.tax_wrapper` / `editingAccount.opened_at` (`value={editingAccount.tax_wrapper ?? "none"}`, `onValueChange={(v) => setEditingAccount({ ...editingAccount, tax_wrapper: v === "none" ? null : (v as Account["tax_wrapper"]) })}`). Ajouter les deux champs au payload du `PATCH` de l'édition : `tax_wrapper: editingAccount.tax_wrapper ?? null, opened_at: editingAccount.opened_at || null`.

- [ ] **Step 6: Vérifier le build**

Run: `cd frontend && npm run build`
Expected: 0 erreur TypeScript.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Accounts.tsx
git commit -m "feat(fiscalite): enveloppe fiscale et date d'ouverture dans les paramètres de compte

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Page « Fiscalité »

**Files:**
- Create: `frontend/src/pages/Tax.tsx`
- Modify: `frontend/src/App.tsx` (route)
- Modify: `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/components/layout/Omnibox.tsx` (navigation)

**Interfaces:**
- Consumes: `GET /tax/overview`, `GET/PATCH /tax/settings`, `GET /tax/annual-report?year=` (Tasks 3 et 4). Réponses typées localement dans la page (interfaces `TaxOverview`, `WrapperCard`, `AnnualReport` miroirs des schémas Pydantic de `schemas/tax.py`).

- [ ] **Step 1: Créer la page**

Créer `frontend/src/pages/Tax.tsx`. Structure à respecter :

- Imports : `useEffect, useState`, `api` de `@/lib/api`, `formatCurrency` de `@/lib/utils`, `Card, CardContent, CardHeader, CardTitle, CardDescription`, `Button`, `Input`, `Label`, `Select*`, `Skeleton`, `toast` de `sonner`, `Link` de `react-router-dom`, icônes `lucide-react` (`Landmark`, `ShieldCheck`, `AlertTriangle`, `Settings2`, `FileText`).
- Interfaces `WrapperCard`, `TaxSettings`, `TaxOverview`, `CtoYearRow`, `AnnualReport` : mêmes champs que `backend/app/schemas/tax.py` (`number | null` pour les optionnels).
- État : `overview`, `report`, `year` (défaut année courante), `loading`, `settingsOpen`, brouillon de réglages.
- Chargement : `useEffect` qui appelle `api.get<TaxOverview>("/tax/overview")` ; second `useEffect` dépendant de `year` pour `api.get<AnnualReport>(`/tax/annual-report?year=${year}`)`. Chaque appel dans son propre `try/catch` avec `toast.error` pour qu'un échec ne bloque pas l'autre. `Skeleton` pendant le chargement.
- En-tête : titre « Fiscalité », sous-titre « Plafonds, dates clés et déclaration de tes enveloppes. », bouton « Réglages » qui déplie un panneau avec `tmi_pct` (Select 0, 11, 30, 41, 45), `prior_year_pro_income` (Input nombre) et `household` (Select Seul / Couple) ; bouton « Enregistrer » → `api.patch("/tax/settings", draft)` puis rechargement de l'aperçu et `toast.success("Réglages enregistrés")`.
- Grille de cartes (`grid gap-4 md:grid-cols-2`) pour chaque entrée de `overview.wrappers` dont `kind !== "cto"` :
  - titre = nom du compte + libellé de l'enveloppe ;
  - si `ceiling !== null` : jauge (div de largeur `Math.min(used_pct, 100)%`, rouge au-delà de 100 %, ambre au-delà de 90 %, sinon emerald), « X sur Y » et « Place restante : Z » avec `formatCurrency` et `amount-blur` ;
  - si `milestone_years !== null` : ligne « Ancienneté : N ans / milestone_years ans » avec une coche si `milestone_reached` ;
  - si `estimated_tax_saving !== null` : « Économie d'impôt estimée : … » ;
  - si `allowance !== null` : « Abattement annuel sur les gains de rachat : … » ;
  - chaque message de `alerts` dans un bandeau ambre avec `AlertTriangle`.
- État vide (aucune carte) : icône `Landmark`, texte « Aucun compte n'a d'enveloppe fiscale. Renseigne l'enveloppe dans les paramètres d'un compte. » et `Link` vers `/accounts`.
- Section « Déclaration » : sélecteur d'année (année courante et les 5 précédentes), puis un tableau (`components/ui/table`) par compte CTO avec colonnes Compte, Dividendes bruts (2DC), Plus-values réalisées, Cessions ; ligne de totaux avec les cases 2DC / 3VG / 3VH et « Impôt estimé (PFU {pfu_rate*100} %) ». `report.warnings` en bandeau ambre. Mention fixe : « Estimation indicative : ne remplace pas ta déclaration. » Si `report.accounts` est vide : message « Aucun compte CTO configuré. »
- Tous les montants : `formatCurrency` dans un `<span className="amount-blur">`.

- [ ] **Step 2: Route**

Dans `frontend/src/App.tsx`, importer `Tax from "@/pages/Tax"` (suivre la forme des imports voisins) et ajouter après la route `/tools` :

```tsx
              <Route path="/tax" element={<Tax />} />
```

- [ ] **Step 3: Navigation**

Dans `Sidebar.tsx`, importer `Landmark` depuis `lucide-react` et ajouter dans le groupe « Patrimoine », après Investissements :

```tsx
      { name: "Fiscalité", href: "/tax", icon: Landmark },
```

Dans `Omnibox.tsx`, importer `Landmark` et ajouter après la ligne Investissements :

```tsx
  { name: "Fiscalité", href: "/tax", icon: Landmark },
```

- [ ] **Step 4: Vérifier le build**

Run: `cd frontend && npm run build`
Expected: 0 erreur TypeScript.

- [ ] **Step 5: Contrôle manuel**

Lancer `cd backend && uvicorn app.main:app --reload --port 8001` et `cd frontend && npm run dev`. Dans Comptes, attribuer une enveloppe et une date d'ouverture à un PEA, un PER, un Livret A, une AV et un CTO ; ouvrir `/tax`. Vérifier : jauges, alertes, état vide sans enveloppe, flou du mode confidentialité (œil), thème sombre, affichage mobile.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Tax.tsx frontend/src/App.tsx frontend/src/components/layout/Sidebar.tsx frontend/src/components/layout/Omnibox.tsx
git commit -m "feat(fiscalite): page Fiscalité (plafonds, dates clés, déclaration CTO)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Documentation, outil MCP et validation finale

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `.claude/skills/numera-expert/SKILL.md`
- Modify: `mcp-server/server_api.py`, `mcp-server/README.md`, `CLAUDE.md` (compteur d'outils MCP et de tests)
- Modify: `frontend/src/CLAUDE.md` (liste des routes)

- [ ] **Step 1: ARCHITECTURE.md**

Ajouter : la route `/tax` au frontend ; les routes `GET /tax/overview`, `GET/PATCH /tax/settings`, `GET /tax/annual-report` à la liste des routes API ; les colonnes `accounts.tax_wrapper` et `accounts.opened_at` au modèle de données ; une ligne sur `core/tax_rules.py` (règles par année, à vérifier) et `core/tax.py` (calculs purs).

- [ ] **Step 2: Skill numera-expert**

Ajouter une section « Fiscalité et enveloppes » dans `.claude/skills/numera-expert/SKILL.md` : PEA = versements cumulés, un retrait ne restitue pas de place ; PER = versements de l'année civile face à 10 % des revenus pro N-1 borné plancher/plafond ; Livret A = solde actuel ; AV = ancienneté et abattement (pas de calcul de part de gain) ; CTO = seul concerné par 2DC/3VG/3VH, estimation PFU indicative ; règles chiffrées uniquement dans `core/tax_rules.py`.

- [ ] **Step 3: Outil MCP**

Dans `mcp-server/server_api.py`, après `list_holdings`, ajouter dans le même style :

```python
@mcp.tool()
def get_tax_overview() -> str:
    """Plafonds, place restante et dates clés des enveloppes fiscales (PEA, PER, Livret A, assurance-vie).

    Chaque enveloppe indique le montant courant, le plafond, la place restante, l'ancienneté
    face aux 5 ans (PEA) ou 8 ans (assurance-vie) et les alertes éventuelles.
    """
    try:
        resp = api.get("/tax/overview")
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        rows = [
            {
                "compte": w["account_name"],
                "enveloppe": w["kind"],
                "courant_EUR": w["current"] if w["current"] is not None else "—",
                "plafond_EUR": w["ceiling"] if w["ceiling"] is not None else "—",
                "restant_EUR": w["remaining"] if w["remaining"] is not None else "—",
                "anciennete_ans": round(w["age_years"], 1) if w["age_years"] is not None else "—",
                "alertes": "; ".join(w["alerts"]) or "—",
            }
            for w in data["wrappers"]
        ]
        return f"🏛️ Fiscalité {data['year']} — {len(rows)} enveloppe(s) :\n\n" + format_table(rows)
    except Exception as e:
        return f"❌ Erreur : {e}"
```

Passer le compteur d'outils de 44 à 45 dans `mcp-server/README.md` (ligne « API proxy ») et dans `CLAUDE.md` (section Serveur MCP).

- [ ] **Step 4: Compteurs et routes frontend**

Dans `CLAUDE.md`, mettre à jour le nombre de tests de la suite complète (relever la valeur affichée par `pytest -q` à l'étape suivante). Dans `frontend/src/CLAUDE.md`, ajouter `/tax` à la liste des routes.

- [ ] **Step 5: Validation complète**

Run: `make validate`
Expected: tests backend PASS et `npm run build` sans erreur. Reporter le nombre de tests dans `CLAUDE.md` si besoin.

- [ ] **Step 6: Faire vérifier les valeurs réglementaires**

Demander à l'utilisateur de confirmer les valeurs de `core/tax_rules.py` pour 2026 (PASS, plancher/plafond PER, taux PFU, plafonds PEA et Livret A), puis retirer les mentions « à vérifier » correspondantes.

- [ ] **Step 7: Commit**

```bash
git add ARCHITECTURE.md .claude/skills/numera-expert/SKILL.md mcp-server/server_api.py mcp-server/README.md CLAUDE.md frontend/src/CLAUDE.md backend/app/core/tax_rules.py
git commit -m "docs(fiscalite): architecture, règles métier, outil MCP et compteurs

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
