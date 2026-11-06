from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.i18n import tr
from app.core.time import utcnow_naive
from app.models.account import Account
from app.repositories.comptes import accounts as repo
from app.schemas.account import (
    AccountCreate,
    AccountUpdate,
    ReconcileHint,
    ReconcileRequest,
    ReconcileResult,
    ReconcileTransaction,
)
from app.services.comptes import reconciliation
from app.services.comptes.wealth import account_values


async def account_balance(db: Session, account_id: int) -> float:
    """Solde affiché d'un compte : sa valeur par `account_values` (source unique du patrimoine)."""
    account = _require(db, account_id)
    return (await account_values(db, [account]))[account_id].value


def _require(db: Session, account_id: int) -> Account:
    account = repo.get(db, account_id)
    if not account:
        raise NotFoundError(tr("errors.account_not_found"), code="account_not_found", context={"account_id": account_id})
    return account


async def _with_balances(db: Session, accounts: list[Account]) -> list[Account]:
    values = await account_values(db, accounts)
    for account in accounts:
        account.balance = values[account.id].value
    return accounts


async def list_accounts(db: Session) -> list[Account]:
    return await _with_balances(db, repo.list_all(db))


async def get_account(db: Session, account_id: int) -> Account:
    return (await _with_balances(db, [_require(db, account_id)]))[0]


def create_account(db: Session, payload: AccountCreate) -> Account:
    account = Account(
        name=payload.name,
        type=payload.type,
        currency=payload.currency,
        color=payload.color,
        asset_class=payload.asset_class,
        sector=payload.sector,
        geographic_zone=payload.geographic_zone,
        institution=payload.institution,
        logo=payload.logo,
        is_main=payload.is_main,
        fonds_euros_pct=payload.fonds_euros_pct,
        fonds_investis_pct=payload.fonds_investis_pct,
        tax_wrapper=payload.tax_wrapper,
        opened_at=payload.opened_at,
        # assurance-vie : relevés par défaut tant que le mode n'est pas choisi explicitement
        valuation_mode=payload.valuation_mode if "valuation_mode" in payload.model_fields_set or payload.type != "assurance_vie" else "snapshot",
    )
    repo.add(db, account)
    db.commit()
    db.refresh(account)
    account.balance = 0.0
    return account


async def update_account(db: Session, account_id: int, payload: AccountUpdate) -> Account:
    account = _require(db, account_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_main") is True:
        repo.clear_main_flag(db, except_id=account_id)
    for key, value in data.items():
        setattr(account, key, value)
    db.commit()
    db.refresh(account)
    return (await _with_balances(db, [account]))[0]


async def verify_account(db: Session, account_id: int) -> Account:
    account = _require(db, account_id)
    account.last_verified_at = utcnow_naive()
    db.commit()
    db.refresh(account)
    return (await _with_balances(db, [account]))[0]


def reconcile_account(db: Session, account_id: int, payload: ReconcileRequest) -> ReconcileResult:
    """Compare le solde affiché par la banque à celui de Numera et propose les causes d'un écart.

    Lecture seule, sauf : un écart nul marque le compte vérifié (comme « Rien n'a bougé »).
    """
    account = _require(db, account_id)
    currency = account.currency or "EUR"
    result = reconciliation.reconcile(db, account_id, payload.date, payload.bank_balance, currency)
    if result.matches:
        account.last_verified_at = utcnow_naive()
        db.commit()
    return ReconcileResult(
        account_id=account_id,
        date=payload.date,
        currency=currency,
        bank_balance=round(payload.bank_balance, 2),
        numera_balance=result.numera_balance,
        gap=result.gap,
        matches=result.matches,
        verified=result.matches,
        hints=[_reconcile_hint(h) for h in result.hints],
    )


def _reconcile_hint(hint) -> ReconcileHint:
    return ReconcileHint(
        kind=hint.kind,
        message=hint.message,
        transactions=[
            ReconcileTransaction(
                id=tx.id,
                date=tx.date.date().isoformat(),
                merchant=tx.merchant,
                type=tx.type,
                amount=round(float(tx.amount), 2),
            )
            for tx in hint.transactions
        ],
    )


def archive_account(db: Session, account_id: int) -> None:
    account = _require(db, account_id)
    account.active = False
    db.commit()
