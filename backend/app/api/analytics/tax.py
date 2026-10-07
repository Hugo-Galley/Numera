"""Page Fiscalité : réglages, aperçu des enveloppes, récap annuel du CTO."""
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.api.accounts import _get_balance_for_account
from app.core.dividends import load_dividends_eur
from app.core.portfolio import compute_portfolio
from app.core.tax import av_status, livret_a_status, pea_status, per_status
from app.core.tax_rules import rules_for
from app.db.system_settings import get_setting, set_setting
from app.models.account import Account
from app.models.investment_transaction import InvestmentTransaction
from app.schemas.tax import AnnualReport, CtoYearRow, TaxOverview, TaxSettings, TaxSettingsUpdate, WrapperCard

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


async def build_annual_report(db: Session, year: int) -> AnnualReport:
    """Dividendes (2DC) et plus-values réalisées (3VG gain, 3VH perte) des comptes CTO pour l'année."""
    rules = rules_for(year)
    accounts = db.query(Account).filter(Account.tax_wrapper == "cto").order_by(Account.id.asc()).all()
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
