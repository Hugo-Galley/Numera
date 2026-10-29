"""Money-flow : où est passé l'argent du mois (charges fixes, dépenses variables, épargne, investissements)."""
from sqlalchemy.orm import Session

from app.domain.reports import money_flow_block, top_items
from app.domain.transactions import net_amount
from app.integrations.currency import get_exchange_rates
from app.repositories.analytics import reports as repo
from app.repositories.analytics.common import ticket_restaurant_account_ids
from app.schemas.insight import MoneyFlowItem, MoneyFlowReport
from app.services.analytics.budget import compute_budget
from app.services.budget_period import period_bounds


async def compute_money_flow(db: Session, month: int, year: int, account_id: int | None = None) -> MoneyFlowReport:
    curr = await _calculate_money_flow_data(month, year, db, account_id)
    prev_m = month - 1 if month > 1 else 12
    prev_y = year if month > 1 else year - 1
    prev = await _calculate_money_flow_data(prev_m, prev_y, db, account_id)
    income = curr["income"]
    return MoneyFlowReport(
        month=month,
        year=year,
        income=income,
        fixed_charges=money_flow_block(curr["fixed_charges"], prev["fixed_charges"], income),
        variable_expenses=money_flow_block(curr["variable_expenses"], prev["variable_expenses"], income),
        savings=money_flow_block(curr["savings"], prev["savings"], income),
        investments=money_flow_block(curr["investments"], prev["investments"], income),
        remainder=money_flow_block(curr["remainder"], prev["remainder"], income),
        top_fixed=[MoneyFlowItem(**x, is_recurring=True) for x in curr["top_fixed"]],
        top_variable=[MoneyFlowItem(**x) for x in curr["top_variable"]],
        top_savings=[MoneyFlowItem(**x) for x in curr["top_savings"]],
        top_investments=[MoneyFlowItem(**x) for x in curr["top_investments"]]
    )


async def _calculate_money_flow_data(month: int, year: int, db: Session, account_id: int | None = None) -> dict:
    start, end = period_bounds(db, year, month)
    rates = await get_exchange_rates("EUR")
    # Définition unique du revenu : celle du budget (courant, ou catégorie « revenu » ailleurs, dividendes inclus)
    income = float((await compute_budget(month=month, year=year, account_id=account_id, db=db))["revenus_totaux"])
    tr_accounts = set() if account_id else ticket_restaurant_account_ids(db)
    flows = _classify(repo.money_flow_rows(db, start, end, account_id, tr_accounts), rates)

    # Versements alimentés par un virement interne lié : la sortie du courant est un virement
    # (is_transfer, donc absente ci-dessus) mais l'argent a bien quitté le budget. Mêmes versements
    # que `investissements_du_mois` du budget, sans double compte avec les sorties catégorisées.
    if not account_id:
        for amount, currency, account_name in repo.budget_versements(db, start, end):
            amount_eur = float(amount) / rates.get(currency, 1.0)
            flows["investments"] += amount_eur
            flows["top_investments"][account_name] = flows["top_investments"].get(account_name, 0) + amount_eur

    remainder = income - (flows["fixed_charges"] + flows["variable_expenses"] + flows["savings"] + flows["investments"])
    return {
        "income": income,
        "fixed_charges": flows["fixed_charges"],
        "variable_expenses": flows["variable_expenses"],
        "savings": flows["savings"],
        "investments": flows["investments"],
        "remainder": remainder,
        "top_fixed": top_items(flows["top_fixed"]),
        "top_variable": top_items(flows["top_variable"]),
        "top_savings": top_items(flows["top_savings"]),
        "top_investments": top_items(flows["top_investments"]),
    }


def _classify(rows: list, rates: dict) -> dict:
    """Répartit les sorties : épargne, investissement, charges fixes (récurrentes), dépenses variables."""
    flows = {"fixed_charges": 0.0, "variable_expenses": 0.0, "savings": 0.0, "investments": 0.0,
             "top_fixed": {}, "top_variable": {}, "top_savings": {}, "top_investments": {}}
    for row in rows:
        tx = row.Transaction
        if tx.type != "Sortie":
            continue
        cat_name = row.cat_name or "Sans catégorie"
        # `amount` est déjà dans la devise du compte : convertir avec celle-ci, pas la devise de saisie
        amount_eur = net_amount(tx) / rates.get(row.acc_currency, 1.0)
        if cat_name in ["Epargne", "Épargne"]:
            flows["savings"] += amount_eur
            flows["top_savings"][tx.merchant] = flows["top_savings"].get(tx.merchant, 0) + amount_eur
        elif cat_name in ["Investissement"]:
            flows["investments"] += amount_eur
            flows["top_investments"][tx.merchant] = flows["top_investments"].get(tx.merchant, 0) + amount_eur
        elif tx.is_recurring:
            flows["fixed_charges"] += amount_eur
            key = f"{tx.merchant} ({cat_name})"
            flows["top_fixed"][key] = flows["top_fixed"].get(key, 0) + amount_eur
        else:
            flows["variable_expenses"] += amount_eur
            # Dépense découpée : chaque part va à sa catégorie, remboursement réparti au prorata
            shares = (
                [(part.category.name if part.category else "Sans catégorie", part.amount / tx.amount) for part in tx.splits]
                if tx.splits and tx.amount
                else [(cat_name, 1.0)]
            )
            for key, ratio in shares:
                flows["top_variable"][key] = flows["top_variable"].get(key, 0) + amount_eur * ratio
    return flows
