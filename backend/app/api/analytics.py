import calendar
import traceback
from datetime import date, datetime, timedelta

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.core.currency import get_exchange_rates, convert_amount
from app.db.session import get_db
from app.models.account import Account
from app.models.category import Category
from app.models.categorization_rule import CategorizationRule
from app.schemas.category import BudgetAlert
from app.schemas.insight import (
    IntelligentInsights, 
    HealthScore, 
    MetricDetail, 
    Insight, 
    MonthlyReport, 
    MonthlyComparison, 
    CashflowProjection, 
    ProjectionPoint, 
    ProjectionEvent, 
    SubscriptionsResponse, 
    SubscriptionInsight, 
    SubscriptionIgnore,
    WealthSimulationResponse,
    WealthSimulationPoint,
    MoneyFlowReport,
    MoneyFlowBlock,
    MoneyFlowItem,
    DataAuditResponse,
    DataAuditSummary,
    DataAuditIssue,
    ActionCenterResponse,
    ActionCenterSummary,
    ActionItem,
)
from app.models.balance_snapshot import BalanceSnapshot
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransaction
from app.core.finance import get_recurring_occurrences
from app.core.logging import get_logger
from app.schemas.transaction import TransactionRead

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _tx_sample(tx: Transaction) -> dict:
    return {
        "id": tx.id,
        "account_id": tx.account_id,
        "date": tx.date.date().isoformat(),
        "merchant": tx.merchant,
        "type": tx.type,
        "amount": round(float(tx.amount), 2),
        "currency": tx.currency,
    }


def _tx_read(tx: Transaction) -> dict:
    return TransactionRead.model_validate(tx).model_dump(mode="json")


def _savings_account_ids(db: Session) -> list[int]:
    return [acc.id for acc in db.query(Account).filter(Account.type == "epargne", Account.active.is_(True)).all()]


def _savings_events_by_account(db: Session, account_ids: list[int], end_date: datetime) -> dict[int, list[tuple[datetime, int, float]]]:
    events: dict[int, list[tuple[datetime, int, float]]] = {acc_id: [] for acc_id in account_ids}
    if not account_ids:
        return events

    snapshots = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id.in_(account_ids), BalanceSnapshot.date <= end_date)
        .order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc())
        .all()
    )
    for snap in snapshots:
        events[snap.account_id].append((snap.date, 1, float(snap.current_value)))

    transactions = (
        db.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids), Transaction.date <= end_date)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
        .all()
    )
    for tx in transactions:
        events[tx.account_id].append((tx.date, 0, float(tx.running_balance)))

    for acc_id, items in events.items():
        items.sort(key=lambda item: (item[0], item[1]))
        events[acc_id] = items
    return events


def _savings_total_at(db: Session, account_ids: list[int], end_date: datetime) -> float:
    events = _savings_events_by_account(db, account_ids, end_date)
    total = 0.0
    for items in events.values():
        total += items[-1][2] if items else 0.0
    return total


@router.get("/audit", response_model=DataAuditResponse)
def data_audit(db: Session = Depends(get_db)):
    now = datetime.now()
    issues: list[DataAuditIssue] = []

    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0
    active_accounts = db.query(func.count(Account.id)).filter(Account.active.is_(True)).scalar() or 0

    uncategorized_query = (
        db.query(Transaction)
        .filter(
            Transaction.category_id.is_(None),
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
        )
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    )
    uncategorized_count = uncategorized_query.count()
    if uncategorized_count:
        samples = [_tx_sample(tx) for tx in uncategorized_query.limit(5).all()]
        issues.append(DataAuditIssue(
            id="uncategorized-expenses",
            type="categorization",
            severity="high",
            title="Transactions sans categorie",
            description="Ces depenses ne sont pas prises en compte correctement dans les budgets et les analyses par categorie.",
            count=uncategorized_count,
            action_label="Voir les transactions",
            action_url="/accounts",
            samples=samples,
        ))

    missing_merchant_query = (
        db.query(Transaction)
        .filter(or_(Transaction.merchant.is_(None), func.trim(Transaction.merchant) == ""))
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    )
    missing_merchant_count = missing_merchant_query.count()
    if missing_merchant_count:
        issues.append(DataAuditIssue(
            id="missing-merchants",
            type="merchant",
            severity="medium",
            title="Transactions sans marchand",
            description="Les recherches, les top marchands et les futures regles automatiques seront moins fiables.",
            count=missing_merchant_count,
            action_label="Voir les transactions",
            action_url="/accounts",
            samples=[_tx_sample(tx) for tx in missing_merchant_query.limit(5).all()],
        ))

    unnormalized_merchant_query = (
        db.query(Transaction.merchant, func.count(Transaction.id).label("count"))
        .filter(Transaction.merchant_id.is_(None), Transaction.merchant.is_not(None), Transaction.merchant != "")
        .group_by(Transaction.merchant)
        .having(func.count(Transaction.id) >= 5)
        .order_by(func.count(Transaction.id).desc())
    )
    unnormalized_merchant_count = unnormalized_merchant_query.count()
    if unnormalized_merchant_count:
        issues.append(DataAuditIssue(
            id="unnormalized-merchants",
            type="merchant",
            severity="low",
            title="Marchands non normalisés",
            description="Certains marchands fréquents ne sont pas encore reliés à un marchand canonique.",
            count=unnormalized_merchant_count,
            action_label="Normaliser",
            action_url="/settings?tab=merchants",
            samples=[{"merchant": r.merchant, "count": r.count} for r in unnormalized_merchant_query.limit(5).all()],
        ))

    duplicate_groups = (
        db.query(
            Transaction.account_id,
            Transaction.date,
            Transaction.type,
            Transaction.merchant,
            Transaction.amount,
            Transaction.currency,
            func.count(Transaction.id).label("count"),
        )
        .filter(Transaction.is_duplicate_ignored == False)
        .group_by(
            Transaction.account_id,
            Transaction.date,
            Transaction.type,
            Transaction.merchant,
            Transaction.amount,
            Transaction.currency,
        )
        .having(func.count(Transaction.id) > 1)
        .order_by(func.count(Transaction.id).desc())
        .limit(10)
        .all()
    )
    if duplicate_groups:
        duplicate_count = sum(int(row.count) for row in duplicate_groups)
        samples = [
            {
                "account_id": row.account_id,
                "date": row.date.date().isoformat(),
                "merchant": row.merchant,
                "type": row.type,
                "amount": round(float(row.amount), 2),
                "currency": row.currency,
                "count": int(row.count),
            }
            for row in duplicate_groups[:5]
        ]
        issues.append(DataAuditIssue(
            id="duplicate-transactions",
            type="duplicates",
            severity="high",
            title="Doublons suspects",
            description="Plusieurs transactions ont exactement le meme compte, la meme date, le meme marchand et le meme montant.",
            count=duplicate_count,
            action_label="Verifier les comptes",
            action_url="/accounts",
            samples=samples,
        ))

    accounts = db.query(Account).filter(Account.active.is_(True)).order_by(Account.name.asc()).all()
    accounts_without_initial = []
    for account in accounts:
        tx_count = db.query(func.count(Transaction.id)).filter(Transaction.account_id == account.id).scalar() or 0
        if tx_count == 0:
            continue
        has_initial = (
            db.query(Transaction.id)
            .filter(Transaction.account_id == account.id, Transaction.type == "Solde Initial")
            .first()
            is not None
        )
        if not has_initial:
            accounts_without_initial.append(account)
    if accounts_without_initial:
        issues.append(DataAuditIssue(
            id="missing-initial-balances",
            type="accounts",
            severity="medium",
            title="Comptes sans solde initial",
            description="Le running balance peut etre difficile a auditer si un compte actif commence sans transaction de solde initial.",
            count=len(accounts_without_initial),
            action_label="Ouvrir les comptes",
            action_url="/accounts",
            samples=[{"id": acc.id, "name": acc.name, "type": acc.type, "currency": acc.currency} for acc in accounts_without_initial[:5]],
        ))

    stale_snapshot_accounts = []
    investment_accounts = [acc for acc in accounts if acc.type == "investissement"]
    for account in investment_accounts:
        latest_snapshot = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == account.id)
            .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
            .first()
        )
        if not latest_snapshot or (now - latest_snapshot.date).days > 45:
            stale_snapshot_accounts.append({
                "id": account.id,
                "name": account.name,
                "last_snapshot": latest_snapshot.date.date().isoformat() if latest_snapshot else None,
                "days_since_snapshot": (now - latest_snapshot.date).days if latest_snapshot else None,
            })
    if stale_snapshot_accounts:
        issues.append(DataAuditIssue(
            id="stale-investment-snapshots",
            type="investments",
            severity="medium",
            title="Snapshots investissement a mettre a jour",
            description="Les performances et le patrimoine net peuvent etre obsoletes si les valeurs de marche ne sont pas rafraichies.",
            count=len(stale_snapshot_accounts),
            action_label="Mettre a jour",
            action_url="/investments",
            samples=stale_snapshot_accounts[:5],
        ))

    unused_categories = (
        db.query(Category)
        .outerjoin(Transaction, Transaction.category_id == Category.id)
        .group_by(Category.id)
        .having(func.count(Transaction.id) == 0)
        .order_by(Category.name.asc())
        .limit(20)
        .all()
    )
    if unused_categories:
        issues.append(DataAuditIssue(
            id="unused-categories",
            type="cleanup",
            severity="low",
            title="Categories inutilisees",
            description="Ces categories ajoutent du bruit dans les formulaires et les filtres.",
            count=len(unused_categories),
            action_label="Gerer les categories",
            action_url="/settings",
            samples=[{"id": cat.id, "name": cat.name, "type": cat.type} for cat in unused_categories[:8]],
        ))

    recent_start = now - timedelta(days=180)
    possible_transfer_count = 0
    transfer_samples = []
    candidate_sorties = (
        db.query(Transaction)
        .filter(
            Transaction.type == "Sortie",
            Transaction.is_transfer.is_(False),
            Transaction.is_transfer_ignored.is_(False),
            Transaction.linked_transaction_id.is_(None),
            Transaction.linked_investment_transaction_id.is_(None),
            Transaction.date >= recent_start,
        )
        .order_by(Transaction.date.desc())
        .limit(250)
        .all()
    )
    for sortie in candidate_sorties:
        match = (
            db.query(Transaction)
            .filter(
                Transaction.id != sortie.id,
                Transaction.account_id != sortie.account_id,
                Transaction.type == "Entree",
                Transaction.currency == sortie.currency,
                Transaction.amount == sortie.amount,
                Transaction.is_transfer.is_(False),
                Transaction.is_transfer_ignored.is_(False),
                Transaction.linked_transaction_id.is_(None),
                Transaction.date >= sortie.date - timedelta(days=3),
                Transaction.date <= sortie.date + timedelta(days=3),
            )
            .first()
        )
        if match:
            possible_transfer_count += 1
            if len(transfer_samples) < 5:
                transfer_samples.append({
                    "sortie": _tx_sample(sortie),
                    "entree": _tx_sample(match),
                })
    if possible_transfer_count:
        issues.append(DataAuditIssue(
            id="unmatched-transfers",
            type="transfers",
            severity="medium",
            title="Transferts internes possibles",
            description="Ces mouvements ressemblent a des virements entre comptes et peuvent fausser les depenses s'ils ne sont pas rapproches.",
            count=possible_transfer_count,
            action_label="Rapprocher",
            action_url="/settings?tab=transfers",
            samples=transfer_samples,
        ))

    high_count = sum(1 for issue in issues if issue.severity == "high")
    medium_count = sum(1 for issue in issues if issue.severity == "medium")
    low_count = sum(1 for issue in issues if issue.severity == "low")

    return DataAuditResponse(
        summary=DataAuditSummary(
            total_issues=len(issues),
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            total_transactions=total_transactions,
            active_accounts=active_accounts,
            checked_at=now.isoformat(),
        ),
        issues=issues,
    )


@router.get("/audit/{issue_id}")
def data_audit_issue_details(issue_id: str, db: Session = Depends(get_db)):
    if issue_id == "uncategorized-expenses":
        transactions = (
            db.query(Transaction)
            .filter(
                Transaction.category_id.is_(None),
                Transaction.type == "Sortie",
                Transaction.is_transfer.is_(False),
            )
            .order_by(Transaction.date.desc(), Transaction.id.desc())
            .limit(500)
            .all()
        )
        return {"issue_id": issue_id, "transactions": [_tx_read(tx) for tx in transactions]}

    if issue_id == "missing-merchants":
        transactions = (
            db.query(Transaction)
            .filter(or_(Transaction.merchant.is_(None), func.trim(Transaction.merchant) == ""))
            .order_by(Transaction.date.desc(), Transaction.id.desc())
            .limit(500)
            .all()
        )
        return {"issue_id": issue_id, "transactions": [_tx_read(tx) for tx in transactions]}

    if issue_id == "duplicate-transactions":
        duplicate_groups = (
            db.query(
                Transaction.account_id,
                Transaction.date,
                Transaction.type,
                Transaction.merchant,
                Transaction.amount,
                Transaction.currency,
                func.count(Transaction.id).label("count"),
            )
            .filter(Transaction.is_duplicate_ignored == False)
            .group_by(
                Transaction.account_id,
                Transaction.date,
                Transaction.type,
                Transaction.merchant,
                Transaction.amount,
                Transaction.currency,
            )
            .having(func.count(Transaction.id) > 1)
            .order_by(func.count(Transaction.id).desc())
            .limit(100)
            .all()
        )
        groups = []
        for row in duplicate_groups:
            transactions = (
                db.query(Transaction)
                .filter(
                    Transaction.account_id == row.account_id,
                    Transaction.date == row.date,
                    Transaction.type == row.type,
                    Transaction.merchant == row.merchant,
                    Transaction.amount == row.amount,
                    Transaction.currency == row.currency,
                )
                .order_by(Transaction.id.asc())
                .all()
            )
            groups.append({
                "key": f"{row.account_id}-{row.date.isoformat()}-{row.type}-{row.merchant}-{row.amount}-{row.currency}",
                "count": int(row.count),
                "transactions": [_tx_read(tx) for tx in transactions],
            })
        return {"issue_id": issue_id, "duplicate_groups": groups}

    if issue_id == "unmatched-transfers":
        now = datetime.now()
        recent_start = now - timedelta(days=180)
        pairs = []
        candidate_sorties = (
            db.query(Transaction)
            .filter(
                Transaction.type == "Sortie",
                Transaction.is_transfer.is_(False),
                Transaction.is_transfer_ignored.is_(False),
                Transaction.linked_transaction_id.is_(None),
                Transaction.linked_investment_transaction_id.is_(None),
                Transaction.date >= recent_start,
            )
            .order_by(Transaction.date.desc())
            .limit(250)
            .all()
        )
        seen: set[tuple[int, int]] = set()
        for sortie in candidate_sorties:
            matches = (
                db.query(Transaction)
                .filter(
                    Transaction.id != sortie.id,
                    Transaction.account_id != sortie.account_id,
                    Transaction.type == "Entree",
                    Transaction.currency == sortie.currency,
                    Transaction.amount == sortie.amount,
                    Transaction.is_transfer.is_(False),
                    Transaction.is_transfer_ignored.is_(False),
                    Transaction.linked_transaction_id.is_(None),
                    Transaction.date >= sortie.date - timedelta(days=3),
                    Transaction.date <= sortie.date + timedelta(days=3),
                )
                .order_by(Transaction.date.asc(), Transaction.id.asc())
                .limit(5)
                .all()
            )
            for match in matches:
                key = (sortie.id, match.id)
                if key in seen:
                    continue
                seen.add(key)
                pairs.append({"sortie": _tx_read(sortie), "entree": _tx_read(match)})
                if len(pairs) >= 100:
                    return {"issue_id": issue_id, "transfer_pairs": pairs}
        return {"issue_id": issue_id, "transfer_pairs": pairs}

    raise HTTPException(status_code=404, detail="Audit issue not found or not editable")


@router.get("/actions", response_model=ActionCenterResponse)
async def get_action_center(db: Session = Depends(get_db)):
    try:
        now = datetime.now()
        actions: list[ActionItem] = []
        
        # --- 1. Audit Actions (Ported from data_audit) ---
        
        # 1.1 Uncategorized Expenses
        uncategorized_query = (
            db.query(Transaction)
            .filter(
                Transaction.category_id.is_(None),
                Transaction.type == "Sortie",
                Transaction.is_transfer.is_(False),
            )
            .order_by(Transaction.date.desc())
        )
        uncategorized_count = uncategorized_query.count()
        if uncategorized_count:
            actions.append(ActionItem(
                id="uncategorized-expenses",
                type="audit",
                severity="high",
                title="Transactions sans catégorie",
                description=f"Vous avez {uncategorized_count} dépenses sans catégorie.",
                action_label="Catégoriser",
                action_url="/audit", # Pointing to the audit/actions page
                action_type="modal_categorize",
                samples=[_tx_sample(tx) for tx in uncategorized_query.limit(5).all()],
                metadata={"issue_id": "uncategorized-expenses"}
            ))

        # 1.2 Duplicate Transactions
        duplicate_groups = (
            db.query(
                Transaction.account_id,
                Transaction.date,
                Transaction.type,
                Transaction.merchant,
                Transaction.amount,
                Transaction.currency,
                func.count(Transaction.id).label("count"),
            )
            .filter(Transaction.is_duplicate_ignored == False)
            .group_by(
                Transaction.account_id,
                Transaction.date,
                Transaction.type,
                Transaction.merchant,
                Transaction.amount,
                Transaction.currency,
            )
            .having(func.count(Transaction.id) > 1)
            .all()
        )
        if duplicate_groups:
            duplicate_count = sum(int(row.count) for row in duplicate_groups)
            actions.append(ActionItem(
                id="duplicate-transactions",
                type="audit",
                severity="high",
                title="Doublons suspects",
                description=f"{duplicate_count} transactions semblent être des doublons.",
                action_label="Vérifier",
                action_url="/audit",
                action_type="modal_categorize", # Reusing the detail modal logic
                metadata={"issue_id": "duplicate-transactions"}
            ))

        # 1.3 Missing Investment Snapshots
        stale_snapshot_accounts = []
        accounts = db.query(Account).filter(Account.active.is_(True)).all()
        investment_accounts = [acc for acc in accounts if acc.type == "investissement"]
        for account in investment_accounts:
            latest_snapshot = (
                db.query(BalanceSnapshot)
                .filter(BalanceSnapshot.account_id == account.id)
                .order_by(BalanceSnapshot.date.desc())
                .first()
            )
            if not latest_snapshot or (now - latest_snapshot.date).days > 45:
                stale_snapshot_accounts.append(account)
        
        if stale_snapshot_accounts:
            actions.append(ActionItem(
                id="stale-snapshots",
                type="audit",
                severity="medium",
                title="Soldes investissement obsolètes",
                description=f"{len(stale_snapshot_accounts)} comptes d'investissement n'ont pas de mise à jour récente.",
                action_label="Mettre à jour",
                action_url="/investments",
                action_type="link",
                metadata={"account_ids": [acc.id for acc in stale_snapshot_accounts]}
            ))

        # 1.4 Unmatched Transfers
        # (Simplified check for the action list)
        recent_start = now - timedelta(days=90)
        possible_transfer_count = 0
        candidate_sorties = (
            db.query(Transaction)
            .filter(
                Transaction.type == "Sortie",
                Transaction.is_transfer.is_(False),
                Transaction.is_transfer_ignored.is_(False),
                Transaction.linked_transaction_id.is_(None),
                Transaction.date >= recent_start,
            ).limit(100).all()
        )
        for sortie in candidate_sorties:
            match = db.query(Transaction).filter(
                Transaction.id != sortie.id,
                Transaction.account_id != sortie.account_id,
                Transaction.type == "Entree",
                Transaction.amount == sortie.amount,
                Transaction.is_transfer.is_(False),
                Transaction.date >= sortie.date - timedelta(days=3),
                Transaction.date <= sortie.date + timedelta(days=3),
            ).first()
            if match:
                possible_transfer_count += 1
        
        if possible_transfer_count:
            actions.append(ActionItem(
                id="possible-transfers",
                type="audit",
                severity="medium",
                title="Transferts non rapprochés",
                description=f"{possible_transfer_count} virements internes potentiels ont été détectés.",
                action_label="Rapprocher",
                action_url="/settings?tab=transfers",
                action_type="link",
                metadata={"issue_id": "unmatched-transfers"}
            ))

        # --- 2. Budget Actions (New) ---
        current_month = now.month
        current_year = now.year
        alerts = await budget_alerts(year=current_year, month=current_month, account_id=None, db=db)
        
        over_budget = [a for a in alerts if a.monthly_ratio and a.monthly_ratio >= 1.0]
        near_budget = [a for a in alerts if a.monthly_ratio and a.monthly_ratio >= 0.85 and a.monthly_ratio < 1.0]
        
        for alert in over_budget:
            actions.append(ActionItem(
                id=f"budget-over-{alert.category_id}",
                type="budget",
                severity="high",
                title=f"Budget dépassé : {alert.category_name}",
                description=f"Vous avez dépensé {round(alert.monthly_spent, 2)}€ pour une limite de {alert.monthly_limit}€.",
                action_label="Voir détails",
                action_url=f"/accounts", # Could be a specific category view if it existed
                action_type="link",
                metadata={"category_id": alert.category_id, "spent": alert.monthly_spent, "limit": alert.monthly_limit}
            ))
            
        for alert in near_budget:
            actions.append(ActionItem(
                id=f"budget-near-{alert.category_id}",
                type="budget",
                severity="medium",
                title=f"Budget presque atteint : {alert.category_name}",
                description=f"Vous êtes à {round(alert.monthly_ratio * 100)}% de votre limite pour {alert.category_name}.",
                action_label="Surveiller",
                action_url=f"/accounts",
                action_type="link",
                metadata={"category_id": alert.category_id, "spent": alert.monthly_spent, "limit": alert.monthly_limit}
            ))

        # --- 3. Rule Suggestions (New) ---
        # Merchants with >= 5 transactions in the last 6 months that DON'T have a rule
        six_months_ago = now - timedelta(days=180)
        top_merchants_without_rules = (
            db.query(Transaction.merchant, func.count(Transaction.id).label("tx_count"), func.max(Transaction.category_id).label("suggested_cat_id"))
            .filter(Transaction.date >= six_months_ago)
            .filter(Transaction.merchant.is_not(None), Transaction.merchant != "")
            .group_by(Transaction.merchant)
            .having(func.count(Transaction.id) >= 5)
            .all()
        )
        
        for merchant, count, suggested_cat_id in top_merchants_without_rules:
            # Check if a rule already exists for this merchant
            rule_exists = db.query(CategorizationRule).filter(
                or_(
                    func.lower(CategorizationRule.merchant_name) == func.lower(merchant),
                    func.lower(CategorizationRule.pattern) == func.lower(merchant)
                )
            ).first() is not None
            
            if not rule_exists:
                actions.append(ActionItem(
                    id=f"suggest-rule-{merchant}",
                    type="rule",
                    severity="low",
                    title=f"Nouvelle règle suggérée : {merchant}",
                    description=f"Vous avez {count} transactions chez '{merchant}'. Créer une règle d'auto-catégorisation ?",
                    action_label="Créer la règle",
                    action_url="/settings?tab=rules",
                    action_type="modal_rule",
                    metadata={"merchant": merchant, "suggested_category_id": suggested_cat_id}
                ))

        # --- 4. Merchant Normalization Suggestions ---
        unnormalized_merchants = (
            db.query(Transaction.merchant, func.count(Transaction.id).label("count"))
            .filter(Transaction.merchant_id.is_(None), Transaction.merchant.is_not(None), Transaction.merchant != "")
            .group_by(Transaction.merchant)
            .having(func.count(Transaction.id) >= 10)
            .order_by(func.count(Transaction.id).desc())
            .limit(5)
            .all()
        )
        for merchant, count in unnormalized_merchants:
            actions.append(ActionItem(
                id=f"suggest-normalization-{merchant}",
                type="merchant",
                severity="low",
                title=f"Normalisation suggérée : {merchant}",
                description=f"Le marchand '{merchant}' apparaît {count} fois. Créer un marchand canonique ?",
                action_label="Normaliser",
                action_url="/settings?tab=merchants",
                action_type="modal_merchant",
                metadata={"merchant": merchant, "count": count}
            ))

        # --- 5. Summary & Sort ---
        # Safe sort: defaults to 3 (lowest) if severity is unexpected
        actions.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.severity, 3))
        
        # Filter dismissed actions
        from app.models.dismissed_insight import DismissedInsight
        dismissed = db.query(DismissedInsight.title).all()
        dismissed_ids = {d.title for d in dismissed}
        
        actions = [a for a in actions if a.id not in dismissed_ids]

        high_count = sum(1 for a in actions if a.severity == "high")
        medium_count = sum(1 for a in actions if a.severity == "medium")
        low_count = sum(1 for a in actions if a.severity == "low")
        
        return ActionCenterResponse(
            summary=ActionCenterSummary(
                total_actions=len(actions),
                high_priority=high_count,
                medium_priority=medium_count,
                low_priority=low_count,
                checked_at=now.isoformat()
            ),
            actions=actions
        )
    except Exception as e:
        logger.error(f"Error in get_action_center: {e}", exc_info=True)
        # Raise as HTTPException to ensure it's handled by FastAPI and CORS headers are added
        raise HTTPException(status_code=500, detail=str(e))

class DismissActionRequest(BaseModel):
    id: str

@router.post("/actions/dismiss")
async def dismiss_action(request: DismissActionRequest, db: Session = Depends(get_db)):
    from app.models.dismissed_insight import DismissedInsight
    existing = db.query(DismissedInsight).filter(DismissedInsight.title == request.id).first()
    if not existing:
        new_dismissed = DismissedInsight(title=request.id)
        db.add(new_dismissed)
        db.commit()
    return {"status": "success"}



@router.get("/budget")
async def budget_analytics(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        start = None
        end = datetime.now()
        base_currency = "EUR"
        rates = await get_exchange_rates(base_currency)
        
        if month and year:
            start = datetime(year, month, 1)
            end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)

        # Get income grouped by account currency
        revenus_query_filter = ["Entree", "Interets"]
        if not month or not year:
            # Only include Solde Initial when looking at "All time"
            revenus_query_filter.append("Solde Initial")

        revenus_by_curr = db.query(
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
        ).join(Account, Transaction.account_id == Account.id).filter(
            Transaction.type.in_(revenus_query_filter),
            Transaction.is_transfer == False
        )
        if not account_id:
            # Global view: include both checking and savings accounts
            revenus_by_curr = revenus_by_curr.filter(Account.type.in_(["courant", "epargne"]))
        else:
            revenus_by_curr = revenus_by_curr.filter(Transaction.account_id == account_id)

        if start:
            revenus_by_curr = revenus_by_curr.filter(Transaction.date >= start)
        revenus_by_curr = revenus_by_curr.filter(Transaction.date < end)

        revenus_rows = revenus_by_curr.group_by(Account.currency).all()
        revenus = sum(row.total / rates.get(row.currency, 1.0) for row in revenus_rows)

        # ADD: Investment transactions as income when looking at a specific account OR if they are dividends
        itx_revenus_query = db.query(
            Account.currency,
            func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")
        ).join(Account, InvestmentTransaction.account_id == Account.id)

        if not account_id:
            itx_revenus_query = itx_revenus_query.filter(InvestmentTransaction.type == "dividende")
        else:
            itx_revenus_query = itx_revenus_query.filter(
                InvestmentTransaction.account_id == account_id,
                InvestmentTransaction.type.in_(["versement", "dividende"])
            )

        if start:
            itx_revenus_query = itx_revenus_query.filter(InvestmentTransaction.date >= start)
        itx_revenus_query = itx_revenus_query.filter(InvestmentTransaction.date < end)

        itx_revenus_rows = itx_revenus_query.group_by(Account.currency).all()
        revenus += sum(row.total / rates.get(row.currency, 1.0) for row in itx_revenus_rows)

        # Calculate "Interets" separately — restricted to courant/epargne accounts
        interets_by_curr = db.query(
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
        ).join(Account, Transaction.account_id == Account.id).outerjoin(Category, Transaction.category_id == Category.id).filter(
            ((Transaction.type == "Interets") |
             (Category.name.in_(["Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"]))),
            Transaction.is_transfer == False
        )
        if not account_id:
            interets_by_curr = interets_by_curr.filter(Account.type.in_(["courant", "epargne"]))
        else:
            interets_by_curr = interets_by_curr.filter(Transaction.account_id == account_id)

        if start:
            interets_by_curr = interets_by_curr.filter(Transaction.date >= start)
        interets_by_curr = interets_by_curr.filter(Transaction.date < end)

        interets_rows = interets_by_curr.group_by(Account.currency).all()
        interets = sum(row.total / rates.get(row.currency, 1.0) for row in interets_rows)
        # Add investment dividends to interests total as well (always dividends, even if not filtered specifically)
        itx_div_query = db.query(Account.currency, func.sum(InvestmentTransaction.amount)).join(Account, InvestmentTransaction.account_id == Account.id).filter(
            InvestmentTransaction.type == "dividende",
            InvestmentTransaction.date < end
        )
        if start:
            itx_div_query = itx_div_query.filter(InvestmentTransaction.date >= start)
        if account_id:
            itx_div_query = itx_div_query.filter(InvestmentTransaction.account_id == account_id)

        itx_div_rows = itx_div_query.group_by(Account.currency).all()
        interets += sum(row[1] / rates.get(row[0], 1.0) for row in itx_div_rows)

        # Expenses grouped by account currency
        depenses_by_curr = db.query(
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
        ).join(Account, Transaction.account_id == Account.id).filter(
            Transaction.type == "Sortie",
            Transaction.is_transfer == False
        )
        if not account_id:
            # Global view: include both checking and savings accounts
            depenses_by_curr = depenses_by_curr.filter(Account.type.in_(["courant", "epargne"]))
        else:
            depenses_by_curr = depenses_by_curr.filter(Transaction.account_id == account_id)

        if start:
            depenses_by_curr = depenses_by_curr.filter(Transaction.date >= start)
        depenses_by_curr = depenses_by_curr.filter(Transaction.date < end)

        depenses_rows = depenses_by_curr.group_by(Account.currency).all()
        depenses = sum(row.total / rates.get(row.currency, 1.0) for row in depenses_rows)

        # ADD: Investment withdrawals as expenses for individual account view
        if account_id:
            itx_exp_query = db.query(Account.currency, func.sum(InvestmentTransaction.amount)).join(Account, InvestmentTransaction.account_id == Account.id).filter(
                InvestmentTransaction.account_id == account_id,
                InvestmentTransaction.type == "retrait",
                InvestmentTransaction.date < end
            )
            if start:
                itx_exp_query = itx_exp_query.filter(InvestmentTransaction.date >= start)

            itx_exp_rows = itx_exp_query.group_by(Account.currency).all()
            depenses += sum(row[1] / rates.get(row[0], 1.0) for row in itx_exp_rows)

        # Calculate "Investissements" (Internal savings transfers) separately
        # We include both "Investissement" and "Epargne" categories here as they are not "consumption"
        investments_by_curr = (
            db.query(
                Account.currency,
                func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
            )
            .join(Account, Transaction.account_id == Account.id)
            .join(Category, Transaction.category_id == Category.id)
            .filter(Transaction.type == "Sortie", Category.name.in_(["Investissement", "Epargne"]), Transaction.is_transfer == False)
        )
        if start:
            investments_by_curr = investments_by_curr.filter(Transaction.date >= start)
        investments_by_curr = investments_by_curr.filter(Transaction.date < end)
        if account_id:
            investments_by_curr = investments_by_curr.filter(Transaction.account_id == account_id)

        investments_rows = investments_by_curr.group_by(Account.currency).all()
        investments = sum(row.total / rates.get(row.currency, 1.0) for row in investments_rows)

        # ADD: Investment versements as investments
        itx_inv_query = db.query(
            Account.currency,
            func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")
        ).join(Account, InvestmentTransaction.account_id == Account.id).filter(
            InvestmentTransaction.type == "versement"
        )
        if start:
            itx_inv_query = itx_inv_query.filter(InvestmentTransaction.date >= start)
        itx_inv_query = itx_inv_query.filter(InvestmentTransaction.date < end)
        if account_id:
            itx_inv_query = itx_inv_query.filter(InvestmentTransaction.account_id == account_id)

        itx_inv_rows = itx_inv_query.group_by(Account.currency).all()
        investments += sum(row.total / rates.get(row.currency, 1.0) for row in itx_inv_rows)

        real_depenses = depenses - investments
        remaining = revenus - depenses

        # Savings rate = (Revenus - Real Expenses) / Revenus
        if revenus <= 0:
            savings_rate = 0.0
        else:
            savings_rate = ((revenus - real_depenses) / revenus * 100.0)
            savings_rate = max(min(savings_rate, 100.0), -100.0)

        if month and year:
            now = datetime.now()
            if now.year == year and now.month == month:
                days = now.day
            else:
                days = calendar.monthrange(year, month)[1]
        else:
            # For all-time, use days between earliest tx and end
            earliest = db.query(func.min(Transaction.date)).scalar()
            if earliest:
                delta = end - earliest
                days = max(delta.days, 1)
            else:
                days = 1

        burn_rate = real_depenses / max(days, 1)

        latest_snapshots_subquery = (
            db.query(
                BalanceSnapshot.account_id.label("account_id"),
                func.max(BalanceSnapshot.date).label("max_date"),
            )
            .filter(BalanceSnapshot.date <= end)
            .group_by(BalanceSnapshot.account_id)
            .subquery()
        )

        latest_snapshots_ids = (
            db.query(func.max(BalanceSnapshot.id).label("max_id"))
            .join(
                latest_snapshots_subquery,
                (BalanceSnapshot.account_id == latest_snapshots_subquery.c.account_id)
                & (BalanceSnapshot.date == latest_snapshots_subquery.c.max_date),
            )
            .group_by(BalanceSnapshot.account_id)
            .subquery()
        )

        # Patrimoine / Solde Actuel logic
        # 1. Investments
        if account_id:
            # For a single investment account, use raw value from snapshots
            inv_acc = db.query(Account).filter(Account.id == account_id).first()
            if inv_acc and inv_acc.type == "investissement":
                latest_snap = db.query(BalanceSnapshot).filter(
                    BalanceSnapshot.account_id == account_id,
                    BalanceSnapshot.date <= end
                ).order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc()).first()
                
                if latest_snap:
                    investment_value = float(latest_snap.current_value)
                else:
                    # Fallback to Transaction table
                    last_tx = db.query(Transaction).filter(
                        Transaction.account_id == account_id,
                        Transaction.date <= end
                    ).order_by(Transaction.date.desc(), Transaction.id.desc()).first()
                    investment_value = float(last_tx.running_balance) if last_tx else 0.0
            else:
                investment_value = 0.0
        else:
            # Global view: sum snapshots for all investment accounts
            investment_accounts = db.query(Account).filter(Account.type == "investissement", Account.active == True).all()
            investment_value = 0.0
            
            # Get latest values from snapshots
            latest_values_rows = (
                db.query(BalanceSnapshot.account_id, BalanceSnapshot.current_value)
                .join(latest_snapshots_ids, BalanceSnapshot.id == latest_snapshots_ids.c.max_id)
                .all()
            )
            latest_values = {row.account_id: float(row.current_value or 0.0) for row in latest_values_rows}
            
            for acc in investment_accounts:
                val = 0.0
                if acc.id in latest_values:
                    val = latest_values[acc.id]
                else:
                    # Fallback to Transaction table
                    last_tx = db.query(Transaction).filter(
                        Transaction.account_id == acc.id,
                        Transaction.date <= end
                    ).order_by(Transaction.date.desc(), Transaction.id.desc()).first()
                    if last_tx:
                        val = float(last_tx.running_balance)
                
                investment_value += val / rates.get(acc.currency, 1.0)

        # 2. Checking / Savings balances
        # We use a subquery to get the latest transaction (max date, then max ID) for each account
        account_last_tx = (
            db.query(
                Transaction.account_id.label("account_id"),
                func.max(Transaction.date).label("max_date"),
            )
            .filter(Transaction.date <= end)
            .group_by(Transaction.account_id)
            .subquery()
        )

        latest_tx_ids = (
            db.query(func.max(Transaction.id).label("max_id"))
            .join(
                account_last_tx,
                (Transaction.account_id == account_last_tx.c.account_id) & (Transaction.date == account_last_tx.c.max_date),
            )
            .group_by(Transaction.account_id)
            .subquery()
        )

        current_accounts_query = (
            db.query(Account.id, Account.type, Account.currency, func.coalesce(func.sum(Transaction.running_balance), 0.0).label("total"))
            .join(Account, Transaction.account_id == Account.id)
            .join(latest_tx_ids, Transaction.id == latest_tx_ids.c.max_id)
        )
        if account_id:
            current_accounts_query = current_accounts_query.filter(Account.id == account_id)
        else:
            current_accounts_query = current_accounts_query.filter(Account.active == True)

        current_accounts_rows = current_accounts_query.group_by(Account.id, Account.type, Account.currency).all()

        # Aggregate balances by type for the response
        checking_bal = 0.0
        savings_bal_from_tx = 0.0
        for row in current_accounts_rows:
            # For specific account, we might want the raw value
            if account_id and row.id == account_id:
                val = row.total
            else:
                val = row.total / rates.get(row.currency, 1.0)
            
            if row.type == "courant":
                checking_bal += val
            elif row.type == "epargne":
                savings_bal_from_tx += val

        # For savings accounts, we prefer the Snapshot-based calculation if available
        # because it might include value updates not present in transactions.
        savings_account_ids = _savings_account_ids(db)
        if account_id:
            savings_account_ids = [account_id] if account_id in savings_account_ids else []

        savings_account_map = {
            acc.id: acc
            for acc in db.query(Account).filter(Account.id.in_(savings_account_ids)).all()
        } if savings_account_ids else {}

        events = _savings_events_by_account(db, savings_account_ids, end)
        savings_total = 0.0
        for acc_id, items in events.items():
            if items:
                acc = savings_account_map.get(acc_id)
                val = items[-1][2]
                if account_id and acc_id == account_id:
                    savings_total += val
                else:
                    savings_total += val / rates.get(acc.currency, 1.0) if acc else val

        # If we have savings accounts, use savings_total (snapshot-aware) instead of savings_bal_from_tx
        if not account_id:
            solde_actuel = checking_bal + savings_total + investment_value
        else:
            acc_obj = db.query(Account).filter(Account.id == account_id).first()
            if acc_obj.type == "investissement":
                solde_actuel = investment_value
            elif acc_obj.type == "epargne":
                solde_actuel = savings_total
            else:
                solde_actuel = checking_bal

        # Re-calculate revenus and depenses in account currency if account_id is provided
        if account_id:
            acc_obj = db.query(Account).filter(Account.id == account_id).first()
            if not acc_obj:
                raise HTTPException(status_code=404, detail="Account not found")

            # We need to re-query without currency conversion
            revenus_query = (
                db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
                .filter(Transaction.account_id == account_id, Transaction.type.in_(["Entree", "Solde Initial"]), Transaction.is_transfer == False)
            )
            if start:
                revenus_query = revenus_query.filter(Transaction.date >= start)
            revenus_query = revenus_query.filter(Transaction.date < end)
            revenus = float(revenus_query.scalar() or 0.0)
            
            # Add investment transactions (versement is positive flow into account)
            itx_revenus_query = (
                db.query(func.coalesce(func.sum(InvestmentTransaction.amount), 0.0))
                .filter(InvestmentTransaction.account_id == account_id, InvestmentTransaction.type == "versement")
            )
            if start:
                itx_revenus_query = itx_revenus_query.filter(InvestmentTransaction.date >= start)
            itx_revenus_query = itx_revenus_query.filter(InvestmentTransaction.date < end)
            revenus += float(itx_revenus_query.scalar() or 0.0)
            
            depenses_query = (
                db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
                .filter(Transaction.account_id == account_id, Transaction.type == "Sortie", Transaction.is_transfer == False)
            )
            if start:
                depenses_query = depenses_query.filter(Transaction.date >= start)
            depenses_query = depenses_query.filter(Transaction.date < end)
            depenses = float(depenses_query.scalar() or 0.0)
            
            itx_retrait_query = (
                db.query(func.coalesce(func.sum(InvestmentTransaction.amount), 0.0))
                .filter(InvestmentTransaction.account_id == account_id, InvestmentTransaction.type == "retrait")
            )
            if start:
                itx_retrait_query = itx_retrait_query.filter(InvestmentTransaction.date >= start)
            itx_retrait_query = itx_retrait_query.filter(InvestmentTransaction.date < end)
            depenses += float(itx_retrait_query.scalar() or 0.0)
            
            # Calculate investments for specific account
            inv_q = (
                db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
                .join(Category, Transaction.category_id == Category.id)
                .filter(
                    Transaction.account_id == account_id, 
                    Transaction.type == "Sortie", 
                    Category.name.in_(["Investissement", "Epargne"]),
                    Transaction.is_transfer == False
                )
            )
            if start:
                inv_q = inv_q.filter(Transaction.date >= start)
            inv_q = inv_q.filter(Transaction.date < end)
            investments = float(inv_q.scalar() or 0.0)
            
            # Add investment transactions (versement)
            itx_inv_q = (
                db.query(func.coalesce(func.sum(InvestmentTransaction.amount), 0.0))
                .filter(InvestmentTransaction.account_id == account_id, InvestmentTransaction.type == "versement")
            )
            if start:
                itx_inv_q = itx_inv_q.filter(InvestmentTransaction.date >= start)
            itx_inv_q = itx_inv_q.filter(InvestmentTransaction.date < end)
            investments += float(itx_inv_q.scalar() or 0.0)

            remaining = revenus - depenses
            savings_rate = (remaining / revenus * 100.0) if revenus > 0 else 0.0
            real_depenses = depenses - investments
            
            # Robust calculation of days for burn_rate
            if start:
                days_count = (end - start).days
            else:
                earliest = db.query(func.min(Transaction.date)).filter(Transaction.account_id == account_id).scalar()
                if earliest:
                    days_count = max((end - earliest).days, 1)
                else:
                    days_count = 1
            
            burn_rate = real_depenses / days_count if days_count > 0 else 0.0
            interets = 0.0 # Simplified for single account view




        return {
            "month": month,
            "year": year,
            "base_currency": base_currency,
            "revenus_totaux": round(float(revenus), 2),
            "interets_totaux": round(float(interets), 2),
            "depenses_totales": round(float(depenses), 2),
            "depenses_reelles": round(float(real_depenses), 2),
            "investissements_du_mois": round(float(investments), 2),
            "revenus_apres_depenses": round(float(remaining), 2),
            "taux_epargne": round(float(savings_rate), 2),
            "burn_rate": round(float(burn_rate), 2),
            "patrimoine_net_total": round(float(checking_bal + savings_total + investment_value), 2),
            "epargne_total": round(float(savings_total), 2),
            "solde_actuel": round(float(solde_actuel), 2),
        }
    except Exception as e:
        print(f"ERROR in budget_analytics: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags")
async def tags_analytics(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2200),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        from app.models.tag import Tag, transaction_tags
        
        start = start_date
        end = end_date or datetime.now()
        base_currency = "EUR"
        rates = await get_exchange_rates(base_currency)
        
        if month and year and not start_date:
            start = datetime(year, month, 1)
            end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)

        query = db.query(
            Tag.id,
            Tag.name,
            Tag.color,
            Account.currency,
            func.sum(Transaction.amount).label("total")
        ).join(transaction_tags, Tag.id == transaction_tags.c.tag_id) \
         .join(Transaction, Transaction.id == transaction_tags.c.transaction_id) \
         .join(Account, Transaction.account_id == Account.id) \
         .filter(Transaction.type == "Sortie", Transaction.is_transfer == False)

        if start:
            query = query.filter(Transaction.date >= start)
        query = query.filter(Transaction.date < end)
        
        if account_id:
            query = query.filter(Transaction.account_id == account_id)
        else:
            query = query.filter(Account.type.in_(["courant", "epargne"]))

        rows = query.group_by(Tag.id, Account.currency).all()

        tag_totals = {}
        for row in rows:
            if row.id not in tag_totals:
                tag_totals[row.id] = {
                    "id": row.id,
                    "name": row.name,
                    "color": row.color,
                    "total_eur": 0.0
                }
            
            val_eur = row.total / rates.get(row.currency, 1.0)
            tag_totals[row.id]["total_eur"] += val_eur

        results = sorted(tag_totals.values(), key=lambda x: x["total_eur"], reverse=True)
        for r in results:
            r["total_eur"] = round(r["total_eur"], 2)
            
        return results
    except Exception as e:
        logger.error(f"Error in tags_analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/expenses-by-category")
async def expenses_by_category(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    rates = await get_exchange_rates("EUR")

    query = (
        db.query(
            Category,
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,
        )
    )
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    
    rows = query.group_by(Category.id, Account.currency).all()

    # Aggregate by category after conversion
    category_totals = {}
    for row in rows:
        cat_id = row.Category.id
        if cat_id not in category_totals:
            category_totals[cat_id] = {"category": row.Category, "total_eur": 0.0}
        
        val_eur = row.total / rates.get(row.currency, 1.0)
        category_totals[cat_id]["total_eur"] += val_eur

    total_amount_eur = sum(item["total_eur"] for item in category_totals.values())

    # ADD: Investment versements as a virtual "Investissement" category
    itx_inv_query = db.query(
        Account.currency,
        func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total"),
    ).join(Account, InvestmentTransaction.account_id == Account.id).filter(
        InvestmentTransaction.date >= start,
        InvestmentTransaction.date < end,
        InvestmentTransaction.type == "versement",
    )
    if account_id:
        itx_inv_query = itx_inv_query.filter(InvestmentTransaction.account_id == account_id)

    itx_rows = itx_inv_query.group_by(Account.currency).all()
    if itx_rows:
        inv_cat = db.query(Category).filter(Category.name == "Investissement").first()
        if inv_cat:
            if inv_cat.id not in category_totals:
                category_totals[inv_cat.id] = {"category": inv_cat, "total_eur": 0.0}

            for row in itx_rows:
                category_totals[inv_cat.id]["total_eur"] += row.total / rates.get(row.currency, 1.0)

            # Recalculate total amount
            total_amount_eur = sum(item["total_eur"] for item in category_totals.values())

    data = []
    for item in sorted(category_totals.values(), key=lambda x: x["total_eur"], reverse=True):
        amount = item["total_eur"]
        pct = (amount / total_amount_eur * 100.0) if total_amount_eur > 0 else 0.0
        cat = item["category"]
        data.append(
            {
                "category": {
                    "id": cat.id,
                    "name": cat.name,
                    "icon": cat.icon,
                    "color": cat.color,
                    "monthly_limit": cat.monthly_limit,
                    "annual_limit": cat.annual_limit,
                },
                "total": round(amount, 2),
                "percentage": round(pct, 2),
            }
        )

    return {
        "month": month,
        "year": year,
        "total": round(total_amount_eur, 2),
        "items": data,
    }


@router.get("/top-merchants")
async def top_merchants(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    limit: int = Query(default=5, ge=1, le=50),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    from app.models.merchant import Merchant
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    rates = await get_exchange_rates("EUR")

    query = (
        db.query(
            func.coalesce(Merchant.name, Transaction.merchant).label("merchant"),
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .outerjoin(Merchant, Transaction.merchant_id == Merchant.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,
            func.coalesce(Category.name, "") != "Investissement"
        )
    )
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    
    rows = query.group_by(func.coalesce(Merchant.name, Transaction.merchant), Account.currency).all()

    # Aggregate by merchant after conversion
    merchant_totals = {}
    for row in rows:
        if row.merchant not in merchant_totals:
            merchant_totals[row.merchant] = 0.0
        val_eur = row.total / rates.get(row.currency, 1.0)
        merchant_totals[row.merchant] += val_eur

    sorted_merchants = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:limit]
    items = [{"merchant": name, "total": round(float(total), 2)} for name, total in sorted_merchants]
    return {"month": month, "year": year, "items": items}


@router.get("/investments")
async def investments_analytics(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db)
):
    # If account_id is provided, check if it's an investment account.
    # If not, ignore it to show a global investment overview on the dashboard.
    target_account = None
    if account_id:
        target_account = db.query(Account).filter(Account.id == account_id).first()
    
    query = db.query(Account).filter(Account.type == "investissement", Account.active.is_(True))
    if target_account and target_account.type == "investissement":
        query = query.filter(Account.id == account_id)
    
    investment_accounts = query.all()
    
    rates = await get_exchange_rates("EUR")

    start_date = None
    end_date = datetime.now()
    if month and year:
        start_date = datetime(year, month, 1)
        end_date = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)

    latest_snapshots_subquery = (
        db.query(
            BalanceSnapshot.account_id.label("account_id"),
            func.max(BalanceSnapshot.date).label("max_date"),
        )
        .filter(BalanceSnapshot.date <= end_date)
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_snapshots_ids = (
        db.query(func.max(BalanceSnapshot.id).label("max_id"))
        .join(
            latest_snapshots_subquery,
            (BalanceSnapshot.account_id == latest_snapshots_subquery.c.account_id)
            & (BalanceSnapshot.date == latest_snapshots_subquery.c.max_date),
        )
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_values_rows = (
        db.query(BalanceSnapshot.account_id, BalanceSnapshot.current_value)
        .join(latest_snapshots_ids, BalanceSnapshot.id == latest_snapshots_ids.c.max_id)
        .all()
    )
    latest_values = {row.account_id: float(row.current_value or 0.0) for row in latest_values_rows}

    # Fallback for accounts without snapshots
    for acc in investment_accounts:
        if acc.id not in latest_values:
            last_tx = (
                db.query(Transaction)
                .filter(Transaction.account_id == acc.id, Transaction.date <= end_date)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .first()
            )
            if last_tx:
                latest_values[acc.id] = float(last_tx.running_balance)

    items = []
    total_net_invested_eur = 0.0
    total_current_value_eur = 0.0
    
    for account in investment_accounts:
        flows = await _calculate_investment_flows(db, account, end_date, start_date=start_date, target_currency="EUR")
        net_invested_eur = flows["net_invested_target"]
        
        raw_current_value = latest_values.get(account.id)
        if raw_current_value is not None:
            current_value_eur = raw_current_value / rates.get(account.currency, 1.0)
        else:
            # Fallback: use net invested as current value if no snapshots exist
            current_value_eur = net_invested_eur
        
        gain_eur = current_value_eur - net_invested_eur
        performance_pct = (gain_eur / net_invested_eur * 100.0) if net_invested_eur > 0 else 0.0

        total_net_invested_eur += net_invested_eur
        total_current_value_eur += current_value_eur
        
        display_verse = flows["total_verse_target"]

        items.append(
            {
                "account_id": account.id,
                "account_name": account.name,
                "total_verse": round(display_verse, 2),
                "total_retire": round(flows["total_retire_target"], 2),
                "net_invested": round(net_invested_eur, 2),
                "current_value": round(current_value_eur, 2),
                "gain_eur": round(gain_eur, 2),
                "performance_pct": round(performance_pct, 2),
                "currency": account.currency
            }
        )

    total_gain_eur = total_current_value_eur - total_net_invested_eur
    total_performance_pct = (total_gain_eur / total_net_invested_eur * 100.0) if total_net_invested_eur > 0 else 0.0
    return {
        "total_net_invested": round(total_net_invested_eur, 2),
        "total_current_value": round(total_current_value_eur, 2),
        "total_gain_eur": round(total_gain_eur, 2),
        "total_performance_pct": round(total_performance_pct, 2),
        "items": items,
    }



async def _calculate_investment_flows(db: Session, account: Account, end_date: datetime, start_date: Optional[datetime] = None, target_currency: str = "EUR") -> dict:
    # 1. Determine the baseline
    # If start_date is provided, we want the value AT start_date as baseline
    # If start_date is None, we look for the latest is_zero_point snapshot
    
    baseline_date = None
    baseline_val_raw = 0.0
    
    if start_date:
        # We want the value at the beginning of the period
        # Check for latest snapshot at or before start_date
        last_snap = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == account.id, BalanceSnapshot.date < start_date)
            .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
            .first()
        )
        if last_snap:
            baseline_val_raw = float(last_snap.current_value)
            baseline_date = last_snap.date
        else:
            # Fallback to latest transaction balance before start_date
            last_tx = (
                db.query(Transaction)
                .filter(Transaction.account_id == account.id, Transaction.date < start_date)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .first()
            )
            if last_tx:
                baseline_val_raw = float(last_tx.running_balance)
                baseline_date = last_tx.date
        
        # If still nothing, it means the account started DURING or AFTER start_date
        # So baseline is 0 and we will pick up the Solde Initial/versements in the loop
    else:
        # All-time baseline: latest is_zero_point snapshot
        zero_point = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == account.id, BalanceSnapshot.is_zero_point.is_(True))
            .filter(BalanceSnapshot.date <= end_date)
            .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
            .first()
        )
        if zero_point:
            baseline_val_raw = float(zero_point.current_value)
            baseline_date = zero_point.date

    # Convert baseline value to target currency
    baseline_val_target = 0.0
    if baseline_val_raw != 0:
        baseline_val_target = await convert_amount(baseline_val_raw, account.currency, target_currency, date=baseline_date.date() if baseline_date else None, db=db)
    
    total_verse_target = 0.0
    total_retire_target = 0.0

    # Fetch flows
    itx_query = db.query(InvestmentTransaction).filter(InvestmentTransaction.account_id == account.id, InvestmentTransaction.date <= end_date)
    if start_date:
        itx_query = itx_query.filter(InvestmentTransaction.date >= start_date)
    elif baseline_date:
        # For all-time, we only take transactions strictly after the zero-point snapshot
        itx_query = itx_query.filter(InvestmentTransaction.date > baseline_date)
    
    itxs = itx_query.all()
    for tx in itxs:
        amount_target = await convert_amount(tx.original_amount, tx.currency, target_currency, date=tx.date.date(), db=db)
        if tx.type == "versement":
            total_verse_target += amount_target
        elif tx.type == "retrait":
            total_retire_target += amount_target
            
    # Regular Transactions
    rtx_query = db.query(Transaction).outerjoin(Category, Transaction.category_id == Category.id).filter(Transaction.account_id == account.id, Transaction.date <= end_date)
    if start_date:
        rtx_query = rtx_query.filter(Transaction.date >= start_date)
    elif baseline_date:
        rtx_query = rtx_query.filter(Transaction.date > baseline_date)
        
    rtxs = rtx_query.all()
    for tx in rtxs:
        merchant_lower = (tx.merchant or "").lower()
        # On investment accounts, "Solde Initial" OR "Entree" (that are NOT interests/dividends) are versements
        if tx.type == "Solde Initial" or tx.type == "Entree":
            # Exclude interests/dividends from net invested (they are gains)
            if tx.category and tx.category.name in ["Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"]:
                continue
            if "dividende" in merchant_lower:
                continue
            # "vente" is often a withdrawal or internal move, but let's be careful. 
            # Usually "Vente" on an investment account means you got cash back (retrait from the market).
            if "vente" in merchant_lower:
                amount_target = await convert_amount(tx.original_amount, tx.currency, target_currency, date=tx.date.date(), db=db)
                total_retire_target += amount_target
                continue

            amount_target = await convert_amount(tx.original_amount, tx.currency, target_currency, date=tx.date.date(), db=db)
            total_verse_target += amount_target
        elif tx.type == "Sortie":
            # Exclude fees/taxes from net invested (they are losses/expenses, but part of performance, not capital flow)
            if any(k in merchant_lower for k in ["achat", "frais", "commission", "tax"]):
                continue
            amount_target = await convert_amount(tx.original_amount, tx.currency, target_currency, date=tx.date.date(), db=db)
            total_retire_target += amount_target
            
    return {
        "baseline_val_target": baseline_val_target,
        "baseline_date": baseline_date,
        "total_verse_target": total_verse_target,
        "total_retire_target": total_retire_target,
        "net_invested_target": baseline_val_target + total_verse_target - total_retire_target
    }



@router.get("/investments/{account_id}")
async def investment_account_analytics(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.type != "investissement":
        raise HTTPException(status_code=422, detail="Account must be investissement")
    
    rates = await get_exchange_rates("EUR")

    zero_point = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id, BalanceSnapshot.is_zero_point.is_(True))
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )

    baseline_date = zero_point.date if zero_point else None
    
    # Use helper for flows in account currency
    flows = await _calculate_investment_flows(db, account, datetime.now(), target_currency=account.currency)
    net_invested = flows["net_invested_target"]
    baseline_date = flows["baseline_date"]

    tx_query = db.query(InvestmentTransaction).filter(InvestmentTransaction.account_id == account_id)
    if baseline_date is not None:
        tx_query = tx_query.filter(InvestmentTransaction.date >= baseline_date)
    txs = tx_query.order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc()).all()

    # Also include regular transactions for this account
    regular_tx_query = db.query(Transaction).outerjoin(Category, Transaction.category_id == Category.id).filter(Transaction.account_id == account_id)
    if baseline_date is not None:
        regular_tx_query = regular_tx_query.filter(Transaction.date >= baseline_date)
    regular_txs = regular_tx_query.order_by(Transaction.date.asc(), Transaction.id.asc()).all()

    latest_snapshot = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id)
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )
    if latest_snapshot:
        current_value = float(latest_snapshot.current_value)
    else:
        # Fallback 1: Sum of investment transactions (net flows)
        # We already have this in net_invested (calculated in account currency)
        current_value = net_invested
        
        # Fallback 2: Regular transactions if any (rare for investment accounts but possible)
        last_tx = db.query(Transaction).filter(Transaction.account_id == account_id).order_by(Transaction.date.desc(), Transaction.id.desc()).first()
        if last_tx:
            current_value = float(last_tx.running_balance)

    gain = current_value - net_invested
    performance_pct = (gain / net_invested * 100.0) if net_invested > 0 else 0.0

    snapshots = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id)
        .order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc())
        .all()
    )

    value_series = []
    for snap in snapshots:
        # For single account detail, we show values in account currency
        val = float(snap.current_value)
        value_series.append(
            {
                "id": snap.id,
                "date": snap.date.isoformat(),
                "current_value": round(val, 2),
                "current_value_raw": round(val, 2),
                "is_zero_point": bool(snap.is_zero_point),
                "note": snap.note,
            }
        )

    all_txs = []
    for tx in txs:
        # Convert to account currency
        amount = await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
        all_txs.append({
            "id": tx.id,
            "date": tx.date.isoformat(),
            "type": tx.type,
            "amount": round(amount, 2),
            "original_amount": round(float(tx.original_amount), 2),
            "currency": tx.currency,
            "note": tx.note,
            "asset_class": tx.asset_class,
            "sector": tx.sector,
            "geographic_zone": tx.geographic_zone,
        })
    for tx in regular_txs:
        # Convert to account currency
        amount = await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
        
        tx_type_display = "versement"
        if tx.type == "Sortie":
            tx_type_display = "retrait"
        elif tx.type == "Solde Initial":
            tx_type_display = "versement"
            
        all_txs.append({
            "id": tx.id,
            "date": tx.date.isoformat(),
            "type": tx_type_display,
            "amount": round(amount, 2),
            "original_amount": round(float(tx.original_amount), 2),
            "currency": tx.currency,
            "note": f"{tx.merchant}{' (' + tx.note + ')' if tx.note else ''}",
            "is_regular": True
        })
    all_txs.sort(key=lambda x: x["date"])

    return {
        "account_id": account.id,
        "account_name": account.name,
        "currency": account.currency,
        "baseline": {
            "date": baseline_date.isoformat() if baseline_date else None,
            "value": round(flows["baseline_val_target"], 2),
        },
        "totals": {
            "total_verse": round(flows["total_verse_target"], 2),
            "total_retire": round(flows["total_retire_target"], 2),
            "net_invested": round(net_invested, 2),
            "current_value": round(current_value, 2),
            "gain_eur": round(gain, 2),
            "performance_pct": round(performance_pct, 2),
        },
        "transactions": all_txs,
        "value_series": value_series,
    }


@router.get("/investments/{account_id}/performance-history")
async def investment_performance_history(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.type != "investissement":
        raise HTTPException(status_code=422, detail="Account must be investissement")

    zero_point = (
        db.query(BalanceSnapshot)
        .filter(BalanceSnapshot.account_id == account_id, BalanceSnapshot.is_zero_point.is_(True))
        .order_by(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc())
        .first()
    )
    baseline_date = zero_point.date if zero_point else None
    baseline_value_raw = float(zero_point.current_value) if zero_point else 0.0
    
    # Baseline in account currency
    baseline_value = await convert_amount(baseline_value_raw, account.currency, account.currency, date=baseline_date.date() if baseline_date else None, db=db)

    txs = db.query(InvestmentTransaction).filter(InvestmentTransaction.account_id == account_id)
    rtxs = db.query(Transaction).filter(Transaction.account_id == account_id)
    snaps = db.query(BalanceSnapshot).filter(BalanceSnapshot.account_id == account_id)
    if baseline_date is not None:
        txs = txs.filter(InvestmentTransaction.date >= baseline_date)
        rtxs = rtxs.filter(Transaction.date >= baseline_date)
        snaps = snaps.filter(BalanceSnapshot.date >= baseline_date)

    txs = txs.order_by(InvestmentTransaction.date.asc(), InvestmentTransaction.id.asc()).all()
    rtxs = rtxs.order_by(Transaction.date.asc(), Transaction.id.asc()).all()
    snaps = snaps.order_by(BalanceSnapshot.date.asc(), BalanceSnapshot.id.asc()).all()

    tx_events_by_day: dict[str, dict[str, float]] = {}
    for tx in txs:
        key = tx.date.date().isoformat()
        if key not in tx_events_by_day:
            tx_events_by_day[key] = {"versement_target": 0.0, "retrait_target": 0.0}
        if tx.type == "dividende":
            continue
            
        amount_target = await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
        if tx.type == "versement":
            tx_events_by_day[key]["versement_target"] += amount_target
        elif tx.type == "retrait":
            tx_events_by_day[key]["retrait_target"] += amount_target
    
    rtx_q = db.query(Transaction).outerjoin(Category, Transaction.category_id == Category.id).filter(Transaction.account_id == account_id)
    if baseline_date:
        rtx_q = rtx_q.filter(Transaction.date >= baseline_date)
    for tx in rtx_q.all():
        key = tx.date.date().isoformat()
        if key not in tx_events_by_day:
            tx_events_by_day[key] = {"versement_target": 0.0, "retrait_target": 0.0}
        
        merchant_lower = (tx.merchant or "").lower()
        if tx.type in ["Entree", "Solde Initial"]:
            if tx.type == "Entree":
                if tx.category and tx.category.name in ["Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"]:
                    continue
                if "vente" in merchant_lower or "dividende" in merchant_lower:
                    continue
            amount_target = await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
            tx_events_by_day[key]["versement_target"] += amount_target
        elif tx.type == "Sortie":
            if any(k in merchant_lower for k in ["achat", "frais", "commission", "tax"]):
                continue
            amount_target = await convert_amount(tx.original_amount, tx.currency, account.currency, date=tx.date.date(), db=db)
            tx_events_by_day[key]["retrait_target"] += amount_target

    # We need to collect ALL events and snapshots dates to calculate cumulative flows correctly
    all_dates = sorted(set(tx_events_by_day.keys()) | {s.date.date().isoformat() for s in snaps})
    
    running_verse = 0.0
    running_retire = 0.0
    series = []
    
    # Map snapshots by day for easy lookup
    snaps_by_day = {s.date.date().isoformat(): s for s in snaps}

    for day_str in all_dates:
        event = tx_events_by_day.get(day_str, {"versement_target": 0.0, "retrait_target": 0.0})
        running_verse += event["versement_target"]
        running_retire += event["retrait_target"]
        
        snap = snaps_by_day.get(day_str)
        if snap:
            net_invested = baseline_value + running_verse - running_retire
            current_value = float(snap.current_value)
            gain = current_value - net_invested
            performance_pct = (gain / net_invested * 100.0) if net_invested > 0 else 0.0
            series.append(
                {
                    "date": snap.date.isoformat(),
                    "net_invested": round(net_invested, 2),
                    "current_value": round(current_value, 2),
                    "gain_eur": round(gain, 2), # Named gain_eur but in account currency
                    "performance_pct": round(performance_pct, 2),
                    "is_zero_point": bool(snap.is_zero_point),
                }
            )

    return {"items": series}


@router.get("/subscriptions", response_model=SubscriptionsResponse)
async def get_subscriptions_analytics(
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Analyzes subscriptions and fixed charges.
    """
    subscriptions: List[SubscriptionInsight] = []
    
    # 1. Explicit recurring transactions
    recur_query = db.query(RecurringTransaction).filter(RecurringTransaction.type == "Sortie")
    if account_id:
        recur_query = recur_query.filter(RecurringTransaction.account_id == account_id)
    
    recurring_defs = recur_query.all()
    for rd in recurring_defs:
        monthly_cost = 0.0
        annual_cost = 0.0
        if rd.frequency == "monthly":
            monthly_cost = float(rd.amount)
            annual_cost = float(rd.amount) * 12
        elif rd.frequency == "annual":
            monthly_cost = float(rd.amount) / 12
            annual_cost = float(rd.amount)
        elif rd.frequency == "weekly":
            monthly_cost = float(rd.amount) * 4.33
            annual_cost = float(rd.amount) * 52
        elif rd.frequency == "quarterly":
            monthly_cost = float(rd.amount) / 3
            annual_cost = float(rd.amount) * 4

        # Find last occurrence in real transactions
        last_tx = db.query(Transaction).filter(
            Transaction.recurring_transaction_id == rd.id
        ).order_by(Transaction.date.desc()).first()
        
        last_occ = last_tx.date.isoformat() if last_tx else None
        
        # Next occurrence
        next_occs = get_recurring_occurrences(rd, datetime.now(), datetime.now() + timedelta(days=60))
        next_occ = next_occs[0].isoformat() if next_occs else None

        subscriptions.append(SubscriptionInsight(
            name=rd.name,
            category_name=rd.category.name if rd.category else "Abonnement",
            amount=float(rd.amount),
            frequency=rd.frequency,
            monthly_cost=round(monthly_cost, 2),
            annual_cost=round(annual_cost, 2),
            last_occurrence=last_occ,
            next_occurrence=next_occ,
            is_recurring_entity=True,
            status="active" if rd.is_active else "paused"
        ))

    # 2. Detect potential subscriptions (Repeated transactions same merchant + same amount)
    limit_date = datetime.now() - timedelta(days=90)
    potential_query = db.query(
        Transaction.merchant,
        Transaction.amount,
        Category.name.label("category_name"),
        func.count(Transaction.id).label("count"),
        func.max(Transaction.date).label("last_date")
    ).join(Category, Transaction.category_id == Category.id, isouter=True) \
     .filter(Transaction.type == "Sortie") \
     .filter(Transaction.date >= limit_date) \
     .filter(Transaction.recurring_transaction_id == None) \
     .filter(Transaction.is_subscription_ignored == False) \
     .group_by(Transaction.merchant, Transaction.amount, Category.id) \
     .having(func.count(Transaction.id) >= 2)
    
    if account_id:
        potential_query = potential_query.filter(Transaction.account_id == account_id)
        
    potentials = potential_query.all()
    for p in potentials:
        if any(s.name.lower() == p.merchant.lower() for s in subscriptions):
            continue
            
        monthly_cost = float(p.amount)
        subscriptions.append(SubscriptionInsight(
            name=p.merchant,
            category_name=p.category_name or "Abonnement",
            amount=float(p.amount),
            frequency="monthly (detected)",
            monthly_cost=round(monthly_cost, 2),
            annual_cost=round(monthly_cost * 12, 2),
            last_occurrence=p.last_date.isoformat(),
            next_occurrence=None,
            is_recurring_entity=False,
            status="potential"
        ))

    total_monthly = sum(s.monthly_cost for s in subscriptions)
    total_annual = sum(s.annual_cost for s in subscriptions)

    return SubscriptionsResponse(
        subscriptions=subscriptions,
        total_monthly=round(total_monthly, 2),
        total_annual=round(total_annual, 2)
    )


@router.post("/subscriptions/ignore")
async def ignore_subscription_detection(
    data: SubscriptionIgnore,
    db: Session = Depends(get_db),
):
    """
    Marks all matching transactions as ignored for subscription detection.
    """
    db.query(Transaction).filter(
        Transaction.merchant == data.merchant,
        Transaction.amount == data.amount,
        Transaction.recurring_transaction_id == None
    ).update({"is_subscription_ignored": True}, synchronize_session=False)
    
    db.commit()
    return {"status": "ok"}


@router.get("/kpi-history")
async def kpi_history(
    months_count: int = Query(default=6, ge=1, le=24), 
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db)
):
    # Returns history of KPIs for sparklines
    now = datetime.now()
    savings_account_ids = _savings_account_ids(db)
    if account_id:
        savings_account_ids = [account_id] if account_id in savings_account_ids else []
    
    savings_account_map = {
        acc.id: acc
        for acc in db.query(Account).filter(Account.id.in_(savings_account_ids)).all()
    } if savings_account_ids else {}
    base_currency = "EUR"
    rates = await get_exchange_rates(base_currency)

    # Find the earliest transaction date to avoid showing empty future or past months
    earliest_tx_query = db.query(func.min(Transaction.date))
    if account_id:
        earliest_tx_query = earliest_tx_query.filter(Transaction.account_id == account_id)
    earliest_tx = earliest_tx_query.scalar()
    
    if not earliest_tx:
        return []

    results = []
    for i in range(months_count - 1, -1, -1):
        total_months = now.year * 12 + (now.month - 1) - i
        y = total_months // 12
        m = (total_months % 12) + 1

        start = datetime(y, m, 1)
        end = datetime(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)

        # Only include if month is NOT in the future AND there's data after the earliest tx
        if start > now:
            continue

        rev_query = db.query(Account.currency, func.coalesce(func.sum(Transaction.amount), 0.0).label("total")).select_from(Transaction).join(Account, Transaction.account_id == Account.id).filter(
            Transaction.date >= start, Transaction.date < end, Transaction.type.in_(["Entree", "Interets"])
        )
        if not account_id:
            rev_query = rev_query.filter(Account.type.in_(["courant", "epargne"]))
        else:
            rev_query = rev_query.filter(Transaction.account_id == account_id)
        
        rev_rows = rev_query.group_by(Account.currency).all()
        rev = sum(row.total / rates.get(row.currency, 1.0) for row in rev_rows)

        # ADD: Investment dividends
        itx_rev_query = db.query(Account.currency, func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")).join(Account, InvestmentTransaction.account_id == Account.id).filter(
            InvestmentTransaction.date >= start, InvestmentTransaction.date < end, InvestmentTransaction.type == "dividende"
        )
        if account_id:
            itx_rev_query = itx_rev_query.filter(InvestmentTransaction.account_id == account_id)
        
        itx_rev_rows = itx_rev_query.group_by(Account.currency).all()
        rev += sum(row.total / rates.get(row.currency, 1.0) for row in itx_rev_rows)

        inte_query = db.query(Account.currency, func.coalesce(func.sum(Transaction.amount), 0.0).label("total")).select_from(Transaction).join(Account, Transaction.account_id == Account.id).outerjoin(Category, Transaction.category_id == Category.id).filter(
            Transaction.date >= start, Transaction.date < end,
            (Transaction.type == "Interets") |
            (Category.name.in_(["Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"]))
        )
        if not account_id:
            inte_query = inte_query.filter(Account.type.in_(["courant", "epargne"]))
        else:
            inte_query = inte_query.filter(Transaction.account_id == account_id)
            
        inte_rows = inte_query.group_by(Account.currency).all()
        inte = sum(row.total / rates.get(row.currency, 1.0) for row in inte_rows)
        # Add investment dividends to interests too
        inte += sum(row.total / rates.get(row.currency, 1.0) for row in itx_rev_rows)

        dep_query = db.query(Account.currency, func.coalesce(func.sum(Transaction.amount), 0.0).label("total")).select_from(Transaction).join(Account, Transaction.account_id == Account.id).filter(
            Transaction.date >= start, Transaction.date < end, Transaction.type == "Sortie"
        )
        if not account_id:
            dep_query = dep_query.filter(Account.type.in_(["courant", "epargne"]))
        else:
            dep_query = dep_query.filter(Transaction.account_id == account_id)
            
        dep_rows = dep_query.group_by(Account.currency).all()
        dep = sum(row.total / rates.get(row.currency, 1.0) for row in dep_rows)

        inv_query = db.query(Account.currency, func.coalesce(func.sum(Transaction.amount), 0.0).label("total")).select_from(Transaction).join(Account, Transaction.account_id == Account.id).join(Category, Transaction.category_id == Category.id).filter(
            Transaction.date >= start, Transaction.date < end, Transaction.type == "Sortie", Category.name.in_(["Investissement", "Epargne"])
        )
        if account_id:
            inv_query = inv_query.filter(Transaction.account_id == account_id)
            
        inv_rows = inv_query.group_by(Account.currency).all()
        inv = sum(row.total / rates.get(row.currency, 1.0) for row in inv_rows)

        # ADD: Investment versements
        itx_inv_query = db.query(Account.currency, func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")).join(Account, InvestmentTransaction.account_id == Account.id).filter(
            InvestmentTransaction.date >= start, InvestmentTransaction.date < end, InvestmentTransaction.type == "versement"
        )
        if account_id:
            itx_inv_query = itx_inv_query.filter(InvestmentTransaction.account_id == account_id)
            
        itx_inv_rows = itx_inv_query.group_by(Account.currency).all()
        inv += sum(row.total / rates.get(row.currency, 1.0) for row in itx_inv_rows)

        # If no revenue and no expense, and it's not the current month, skip to keep chart tight
        if rev == 0 and dep == 0 and not (now.year == y and now.month == m):
            continue

        # Epargne totale at end of month
        events = _savings_events_by_account(db, savings_account_ids, end)
        epargne_total = 0.0
        for acc_id, items in events.items():
            if items:
                acc = savings_account_map.get(acc_id)
                val = items[-1][2]
                epargne_total += val / rates.get(acc.currency, 1.0) if acc else val
        
        real_dep = dep - inv
        results.append({
            "month": m,
            "year": y,
            "label": f"{m}/{y}",
            "base_currency": base_currency,
            "revenus": round(float(rev), 2),
            "interets": round(float(inte), 2),
            "depenses": round(float(dep), 2),
            "investissements": round(float(inv), 2),
            "epargne": round(float(epargne_total), 2),
            "epargne_flow": round(float(rev - real_dep), 2),
            "cash_flow": round(float(rev - dep), 2)
        })
        
    return results


@router.get("/investments-allocation")
async def investments_allocation(account_id: int | None = Query(default=None), db: Session = Depends(get_db)):
    query = db.query(Account).filter(Account.type == "investissement", Account.active.is_(True))
    if account_id:
        query = query.filter(Account.id == account_id)
    
    investment_accounts = query.all()
    rates = await get_exchange_rates("EUR")
    now = datetime.now()
    
    latest_snapshots_subquery = (
        db.query(
            BalanceSnapshot.account_id.label("account_id"),
            func.max(BalanceSnapshot.date).label("max_date"),
        )
        .filter(BalanceSnapshot.date <= now)
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_snapshots_ids = (
        db.query(func.max(BalanceSnapshot.id).label("max_id"))
        .join(
            latest_snapshots_subquery,
            (BalanceSnapshot.account_id == latest_snapshots_subquery.c.account_id)
            & (BalanceSnapshot.date == latest_snapshots_subquery.c.max_date),
        )
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_values_rows = (
        db.query(BalanceSnapshot.account_id, BalanceSnapshot.current_value)
        .join(latest_snapshots_ids, BalanceSnapshot.id == latest_snapshots_ids.c.max_id)
        .all()
    )
    current_by_account = {row.account_id: float(row.current_value or 0.0) for row in latest_values_rows}
    
    # Fallback for accounts without snapshots: use last running_balance from Transaction table
    for acc in investment_accounts:
        if acc.id not in current_by_account:
            last_tx = (
                db.query(Transaction)
                .filter(Transaction.account_id == acc.id, Transaction.date <= now)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .first()
            )
            if last_tx:
                current_by_account[acc.id] = float(last_tx.running_balance)

    total_current_value_eur = 0.0
    total_net_invested_eur = 0.0

    items = []
    for acc in investment_accounts:
        # Net invested converted with historical rates
        flows = await _calculate_investment_flows(db, acc, now, target_currency="EUR")
        net_invested_eur = flows["net_invested_target"]
        total_net_invested_eur += net_invested_eur

        raw_value = current_by_account.get(acc.id)
        if raw_value is not None:
            # Current value converted with latest rates
            value_eur = raw_value / rates.get(acc.currency, 1.0)
        else:
            # Fallback: use net invested as current value
            value_eur = net_invested_eur
            
        total_current_value_eur += value_eur

        items.append(
            {
                "account_id": acc.id,
                "account_name": acc.name,
                "current_value": round(value_eur, 2),
                "net_invested": round(net_invested_eur, 2),
                "gain_eur": round(value_eur - net_invested_eur, 2),
                "currency": acc.currency,
            }
        )

    # Re-calculate percentages based on EUR values
    for item in items:
        item["percentage"] = round((item["current_value"] / total_current_value_eur * 100.0), 2) if total_current_value_eur > 0 else 0.0

    total_gain_eur = total_current_value_eur - total_net_invested_eur
    total_perf_pct = (total_gain_eur / total_net_invested_eur * 100.0) if total_net_invested_eur > 0 else 0.0

    items.sort(key=lambda i: i["current_value"], reverse=True)
    return {
        "total_current_value": round(total_current_value_eur, 2),
        "total_net_invested": round(total_net_invested_eur, 2),
        "total_gain_eur": round(total_gain_eur, 2),
        "total_performance_pct": round(total_perf_pct, 2),
        "items": items
    }


@router.get("/investments-allocation-advanced")
async def investments_allocation_advanced(db: Session = Depends(get_db)):
    """
    Returns advanced asset allocation: by asset class, sector and geographic zone.
    """
    investment_accounts = db.query(Account).filter(Account.type == "investissement", Account.active.is_(True)).all()
    rates = await get_exchange_rates("EUR")
    now = datetime.now()
    
    latest_snapshots_subquery = (
        db.query(
            BalanceSnapshot.account_id.label("account_id"),
            func.max(BalanceSnapshot.date).label("max_date"),
        )
        .filter(BalanceSnapshot.date <= now)
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_snapshots_ids = (
        db.query(func.max(BalanceSnapshot.id).label("max_id"))
        .join(
            latest_snapshots_subquery,
            (BalanceSnapshot.account_id == latest_snapshots_subquery.c.account_id)
            & (BalanceSnapshot.date == latest_snapshots_subquery.c.max_date),
        )
        .group_by(BalanceSnapshot.account_id)
        .subquery()
    )

    latest_values_rows = (
        db.query(BalanceSnapshot.account_id, BalanceSnapshot.current_value)
        .join(latest_snapshots_ids, BalanceSnapshot.id == latest_snapshots_ids.c.max_id)
        .all()
    )
    current_by_account = {row.account_id: float(row.current_value or 0.0) for row in latest_values_rows}
    
    # Fallback for accounts without snapshots
    for acc in investment_accounts:
        if acc.id not in current_by_account:
            last_tx = (
                db.query(Transaction)
                .filter(Transaction.account_id == acc.id, Transaction.date <= now)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .first()
            )
            if last_tx:
                current_by_account[acc.id] = float(last_tx.running_balance)

    # Aggregations
    # Structure: { "Category Name": { "value": 0.0, "items": { account_id: { name: "", value: 0.0 } } } }
    by_asset_class = {}
    by_sector = {}
    by_zone = {}
    total_value_eur = 0.0

    def _add_to_agg(agg_dict, cat_name, val, acc):
        if cat_name not in agg_dict:
            agg_dict[cat_name] = {"value": 0.0, "items": {}}
        
        agg_dict[cat_name]["value"] += val
        
        acc_id = acc.id
        if acc_id not in agg_dict[cat_name]["items"]:
            agg_dict[cat_name]["items"][acc_id] = {"account_id": acc_id, "account_name": acc.name, "value": 0.0}
        
        agg_dict[cat_name]["items"][acc_id]["value"] += val

    for acc in investment_accounts:
        raw_val = current_by_account.get(acc.id, 0.0)
        val_eur = raw_val / rates.get(acc.currency, 1.0)
        total_value_eur += val_eur

        txs_with_allocation = db.query(InvestmentTransaction).filter(
            InvestmentTransaction.account_id == acc.id,
            InvestmentTransaction.asset_class.isnot(None)
        ).all()

        if txs_with_allocation:
            total_tx_amount = sum(abs(tx.amount) for tx in txs_with_allocation)
            if total_tx_amount > 0:
                for tx in txs_with_allocation:
                    weight = abs(tx.amount) / total_tx_amount
                    tx_val_eur = val_eur * weight
                    
                    _add_to_agg(by_asset_class, tx.asset_class or "Non classé", tx_val_eur, acc)
                    _add_to_agg(by_sector, tx.sector or "Non classé", tx_val_eur, acc)
                    _add_to_agg(by_zone, tx.geographic_zone or "Non classé", tx_val_eur, acc)
            else:
                _add_to_agg(by_asset_class, acc.asset_class or "Non classé", val_eur, acc)
                _add_to_agg(by_sector, acc.sector or "Non classé", val_eur, acc)
                _add_to_agg(by_zone, acc.geographic_zone or "Non classé", val_eur, acc)
        else:
            _add_to_agg(by_asset_class, acc.asset_class or "Non classé", val_eur, acc)
            _add_to_agg(by_sector, acc.sector or "Non classé", val_eur, acc)
            _add_to_agg(by_zone, acc.geographic_zone or "Non classé", val_eur, acc)

    def _format_agg(agg_dict):
        result = []
        for name, data in agg_dict.items():
            val = data["value"]
            pct = (val / total_value_eur * 100.0) if total_value_eur > 0 else 0.0
            
            # Format items and sort them by value
            items = []
            for item in data["items"].values():
                item_pct = (item["value"] / val * 100.0) if val > 0 else 0.0
                items.append({
                    "account_id": item["account_id"],
                    "account_name": item["account_name"],
                    "value": round(item["value"], 2),
                    "percentage_of_group": round(item_pct, 2)
                })
            items.sort(key=lambda x: x["value"], reverse=True)

            result.append({
                "name": name,
                "value": round(val, 2),
                "percentage": round(pct, 2),
                "items": items
            })
        return sorted(result, key=lambda x: x["value"], reverse=True)

    return {
        "total_value_eur": round(total_value_eur, 2),
        "by_asset_class": _format_agg(by_asset_class),
        "by_sector": _format_agg(by_sector),
        "by_geographic_zone": _format_agg(by_zone)
    }


@router.get("/asset-allocation/suggestions")
def get_asset_allocation_suggestions(db: Session = Depends(get_db)):
    """
    Returns unique values for asset classes, sectors and geographic zones
    to be used for autocompletion in the frontend.
    """
    # Unique values from accounts
    acc_classes = db.query(Account.asset_class).filter(Account.asset_class.isnot(None)).distinct().all()
    acc_sectors = db.query(Account.sector).filter(Account.sector.isnot(None)).distinct().all()
    acc_zones = db.query(Account.geographic_zone).filter(Account.geographic_zone.isnot(None)).distinct().all()
    
    # Unique values from investment transactions
    tx_classes = db.query(InvestmentTransaction.asset_class).filter(InvestmentTransaction.asset_class.isnot(None)).distinct().all()
    tx_sectors = db.query(InvestmentTransaction.sector).filter(InvestmentTransaction.sector.isnot(None)).distinct().all()
    tx_zones = db.query(InvestmentTransaction.geographic_zone).filter(InvestmentTransaction.geographic_zone.isnot(None)).distinct().all()
    
    # Flatten and unique
    classes = sorted(list(set([c[0] for c in acc_classes + tx_classes if c[0]])))
    sectors = sorted(list(set([s[0] for s in acc_sectors + tx_sectors if s[0]])))
    zones = sorted(list(set([z[0] for z in acc_zones + tx_zones if z[0]])))
    
    # Default common values
    default_classes = ["Actions", "Obligations", "Immobilier", "Liquidités", "Crypto", "Or & Matières Premières", "Private Equity"]
    default_sectors = ["Tech", "Santé", "Finance", "Energie", "Industrie", "Consommation", "Télécoms", "Luxe", "SaaS", "E-commerce", "Tourisme"]
    default_zones = ["Europe", "USA", "Asie", "Marchés Émergents", "France", "Monde", "Chine", "Japon"]
    
    return {
        "asset_classes": sorted(list(set(classes + default_classes))),
        "sectors": sorted(list(set(sectors + default_sectors))),
        "geographic_zones": sorted(list(set(zones + default_zones)))
    }


@router.get("/wealth-simulation", response_model=WealthSimulationResponse)
async def wealth_simulation(
    initial_capital: float = Query(ge=0),
    monthly_contribution: float = Query(ge=0),
    annual_return_pct: float = Query(ge=-100, le=1000),
    years: int = Query(ge=1, le=50, default=15),
):
    """
    Simulates wealth growth over time with monthly contributions and compounded interest.
    """
    items = []
    current_total = initial_capital
    cumulative_contributions = 0.0
    cumulative_interest = 0.0
    
    # Monthly rate from annual rate: (1 + r_annual)^(1/12) - 1
    annual_rate_decimal = annual_return_pct / 100.0
    monthly_rate = (1 + annual_rate_decimal) ** (1/12) - 1 if annual_rate_decimal > -1 else -1.0

    # Year 0 point
    items.append(WealthSimulationPoint(
        year=0,
        initial_capital=round(initial_capital, 2),
        total_contributions=0.0,
        total_interest=0.0,
        total_value=round(initial_capital, 2)
    ))

    for y in range(1, years + 1):
        for m in range(1, 13):
            # 1. Add interest to current total
            interest_this_month = current_total * monthly_rate
            current_total += interest_this_month
            cumulative_interest += interest_this_month
            
            # 2. Add monthly contribution
            current_total += monthly_contribution
            cumulative_contributions += monthly_contribution

        # Add data point for the end of the year
        items.append(WealthSimulationPoint(
            year=y,
            initial_capital=round(initial_capital, 2),
            total_contributions=round(cumulative_contributions, 2),
            total_interest=round(cumulative_interest, 2),
            total_value=round(current_total, 2)
        ))

    return WealthSimulationResponse(
        items=items,
        total_final=round(current_total, 2),
        total_interest=round(cumulative_interest, 2),
        total_contributions=round(cumulative_contributions, 2)
    )


def _apply_account_level(acc, val_eur, by_asset_class, by_sector, by_zone):
    # Asset Class
    ac = acc.asset_class or "Non classé"
    by_asset_class[ac] = by_asset_class.get(ac, 0.0) + val_eur

    # Sector
    sec = acc.sector or "Non classé"
    by_sector[sec] = by_sector.get(sec, 0.0) + val_eur

    # Zone
    zone = acc.geographic_zone or "Non classé"
    by_zone[zone] = by_zone.get(zone, 0.0) + val_eur


@router.get("/timeseries")
async def timeseries_analytics(
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    now = datetime.now()
    monthly = []
    
    # Check if there's any transaction for the year to avoid empty charts
    any_tx = db.query(Transaction).filter(func.strftime("%Y", Transaction.date) == str(year))
    if account_id:
        any_tx = any_tx.filter(Transaction.account_id == account_id)
    
    if not any_tx.first():
        # If no data for the year, return empty instead of 12 zeros
        return {
            "year": year,
            "account_id": account_id,
            "monthly_flows": [],
            "balance_points": [],
            "salary_series": [],
        }

    rates = await get_exchange_rates("EUR")

    for month in range(1, 13):
        start = datetime(year, month, 1)
        end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)

        # Don't show future months
        if start > now:
            continue

        # Correctly handle multi-currency for global view
        income_by_curr = db.query(
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
        ).join(Account, Transaction.account_id == Account.id).filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type.in_(["Entree", "Interets"]),
        )
        
        expense_by_curr = db.query(
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total")
        ).join(Account, Transaction.account_id == Account.id).filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
        )

        if account_id is not None:
            income_by_curr = income_by_curr.filter(Transaction.account_id == account_id)
            expense_by_curr = expense_by_curr.filter(Transaction.account_id == account_id)
        else:
            income_by_curr = income_by_curr.filter(Account.type.in_(["courant", "epargne"]))
            expense_by_curr = expense_by_curr.filter(Account.type.in_(["courant", "epargne"]))

        income_rows = income_by_curr.group_by(Account.currency).all()
        income = sum(row.total / rates.get(row.currency, 1.0) for row in income_rows)
        
        # ADD: Investment dividends
        itx_inc_query = db.query(Account.currency, func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")).join(Account, InvestmentTransaction.account_id == Account.id).filter(
            InvestmentTransaction.date >= start, InvestmentTransaction.date < end, InvestmentTransaction.type == "dividende"
        )
        if account_id:
            itx_inc_query = itx_inc_query.filter(InvestmentTransaction.account_id == account_id)
        
        itx_inc_rows = itx_inc_query.group_by(Account.currency).all()
        income += sum(row.total / rates.get(row.currency, 1.0) for row in itx_inc_rows)

        expense_rows = expense_by_curr.group_by(Account.currency).all()
        expense = sum(row.total / rates.get(row.currency, 1.0) for row in expense_rows)

        # ADD: Investment versements (if looking at this account, they are outflows of cash part?)
        # Actually, for global view, versements are already Sortie on bank accounts.
        # But if specifically on investment account, we might want to see them as "expense" of the budget?
        # Let's include versements in 'expense' only if account_id is specifically an investment account.
        if account_id:
            acc_obj = db.query(Account).filter(Account.id == account_id).first()
            if acc_obj and acc_obj.type == "investissement":
                itx_exp_query = db.query(Account.currency, func.coalesce(func.sum(InvestmentTransaction.amount), 0.0).label("total")).join(Account, InvestmentTransaction.account_id == Account.id).filter(
                    InvestmentTransaction.date >= start, InvestmentTransaction.date < end, InvestmentTransaction.type == "versement"
                ).filter(InvestmentTransaction.account_id == account_id)
                itx_exp_rows = itx_exp_query.group_by(Account.currency).all()
                expense += sum(row.total / rates.get(row.currency, 1.0) for row in itx_exp_rows)
        
        # Only add month if it has data or is the current month
        if income > 0 or expense > 0 or (now.year == year and now.month == month):
            days = calendar.monthrange(year, month)[1]
            if now.year == year and now.month == month:
                days = now.day
                
            monthly.append(
                {
                    "month": month,
                    "income": round(float(income), 2),
                    "expense": round(float(expense), 2),
                    "burn_rate": round(float(expense) / max(days, 1), 2),
                }
            )

    # For balance points, if it's a global view, we should probably aggregate them or not show them.
    # But if account_id is provided, it's definitely fine.
    balance_points_query = db.query(Transaction).order_by(Transaction.date.asc(), Transaction.id.asc())
    if account_id is not None:
        balance_points_query = balance_points_query.filter(Transaction.account_id == account_id)
        balance_points = [
            {
                "date": tx.date.isoformat(),
                "running_balance": round(float(tx.running_balance), 2),
                "account_id": tx.account_id,
            }
            for tx in balance_points_query.all()
        ]
    else:
        # For global view, balance points are less meaningful if just interleaved.
        # Maybe we should return empty or aggregate them by day?
        # For now, let's keep it as is but it's a known limitation for global charts.
        balance_points = []

    salary_rows_query = (
        db.query(
            func.strftime("%m", Transaction.date).label("month"),
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            func.strftime("%Y", Transaction.date) == str(year),
            Category.name == "Salaire",
            Transaction.type == "Entree",
        )
        .group_by(func.strftime("%m", Transaction.date), Account.currency)
    )
    if account_id is not None:
        salary_rows_query = salary_rows_query.filter(Transaction.account_id == account_id)

    salary_data = salary_rows_query.all()
    salary_by_month = {}
    for row in salary_data:
        m = int(row.month)
        val_eur = row.total / rates.get(row.currency, 1.0)
        salary_by_month[m] = salary_by_month.get(m, 0.0) + val_eur
    
    salary_series = []
    for month in range(1, 13):
        # Only add to salary series if month has data and is not in future
        if datetime(year, month, 1) <= now and (salary_by_month.get(month, 0) > 0):
             salary_series.append({"month": month, "salary": salary_by_month.get(month, 0.0)})

    return {
        "year": year,
        "account_id": account_id,
        "monthly_flows": monthly,
        "balance_points": balance_points,
        "salary_series": salary_series,
    }


@router.get("/budget-alerts", response_model=list[BudgetAlert])
async def budget_alerts(
    year: int = Query(...),
    month: int = Query(...),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    categories = db.query(Category).filter(
        (Category.monthly_limit.isnot(None)) | (Category.annual_limit.isnot(None))
    ).all()

    if not categories:
        return []

    rates = await get_exchange_rates("EUR")
    start_month = datetime(year, month, 1)
    end_month = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    start_year = datetime(year, 1, 1)
    end_year = datetime(year + 1, 1, 1)

    # Monthly spending per category in EUR
    monthly_query = (
        db.query(Transaction.category_id, Account.currency, func.sum(Transaction.amount))
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,
            Transaction.date >= start_month,
            Transaction.date < end_month,
        )
    )
    if account_id:
        monthly_query = monthly_query.filter(Transaction.account_id == account_id)

    monthly_rows = monthly_query.group_by(Transaction.category_id, Account.currency).all()

    monthly_spent_map = {}
    for cat_id, curr, amount in monthly_rows:
        if cat_id not in monthly_spent_map:
            monthly_spent_map[cat_id] = 0.0
        monthly_spent_map[cat_id] += amount / rates.get(curr, 1.0)

    # Annual spending per category in EUR
    annual_query = (
        db.query(Transaction.category_id, Account.currency, func.sum(Transaction.amount))
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,
            Transaction.date >= start_year,
            Transaction.date < end_year,
        )
    )
    if account_id:
        annual_query = annual_query.filter(Transaction.account_id == account_id)

    annual_rows = annual_query.group_by(Transaction.category_id, Account.currency).all()    
    annual_spent_map = {}
    for cat_id, curr, amount in annual_rows:
        if cat_id not in annual_spent_map:
            annual_spent_map[cat_id] = 0.0
        annual_spent_map[cat_id] += amount / rates.get(curr, 1.0)

    # ADD: Investment versements into "Investissement" category for alerts
    inv_cat = db.query(Category).filter(Category.name == "Investissement").first()
    if inv_cat:
        # Monthly Investment Transactions
        itx_monthly_query = db.query(Account.currency, func.sum(InvestmentTransaction.amount)).join(Account, InvestmentTransaction.account_id == Account.id).filter(
            InvestmentTransaction.type == "versement",
            InvestmentTransaction.date >= start_month,
            InvestmentTransaction.date < end_month,
        )
        if account_id:
            itx_monthly_query = itx_monthly_query.filter(InvestmentTransaction.account_id == account_id)

        itx_monthly_rows = itx_monthly_query.group_by(Account.currency).all()
        for curr, amount in itx_monthly_rows:
            if inv_cat.id not in monthly_spent_map:
                monthly_spent_map[inv_cat.id] = 0.0
            monthly_spent_map[inv_cat.id] += amount / rates.get(curr, 1.0)

        # Annual Investment Transactions
        itx_annual_query = db.query(Account.currency, func.sum(InvestmentTransaction.amount)).join(Account, InvestmentTransaction.account_id == Account.id).filter(
            InvestmentTransaction.type == "versement",
            InvestmentTransaction.date >= start_year,
            InvestmentTransaction.date < end_year,
        )
        if account_id:
            itx_annual_query = itx_annual_query.filter(InvestmentTransaction.account_id == account_id)

        itx_annual_rows = itx_annual_query.group_by(Account.currency).all()
        for curr, amount in itx_annual_rows:
            if inv_cat.id not in annual_spent_map:
                annual_spent_map[inv_cat.id] = 0.0
            annual_spent_map[inv_cat.id] += amount / rates.get(curr, 1.0)

    results = []
    for cat in categories:
        monthly_spent = monthly_spent_map.get(cat.id, 0.0)
        annual_spent = annual_spent_map.get(cat.id, 0.0)

        monthly_ratio = (monthly_spent / cat.monthly_limit) if cat.monthly_limit else None
        annual_ratio = (annual_spent / cat.annual_limit) if cat.annual_limit else None

        results.append(BudgetAlert(
            category_id=cat.id,
            category_name=cat.name,
            category_icon=cat.icon,
            category_color=cat.color,
            monthly_limit=cat.monthly_limit,
            annual_limit=cat.annual_limit,
            monthly_spent=round(monthly_spent, 2),
            annual_spent=round(annual_spent, 2),
            monthly_ratio=monthly_ratio,
            annual_ratio=annual_ratio,
        ))

    # Sort by ratio (highest first)
    results.sort(key=lambda a: max(
        a.monthly_ratio or 0,
        a.annual_ratio or 0,
    ), reverse=True)

    return results


async def get_subscription_total_for_period(month: int, year: int, db: Session) -> float:
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    rates = await get_exchange_rates("EUR")

    rows = (
        db.query(
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,
            Category.name == "Abonnement",
        )
        .group_by(Account.currency)
        .all()
    )

    total_eur = 0.0
    for row in rows:
        total_eur += row.total / rates.get(row.currency, 1.0)
    
    return total_eur


@router.get("/insights", response_model=IntelligentInsights)
async def get_intelligent_insights(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    rates = await get_exchange_rates("EUR")
    start_month = datetime(year, month, 1)
    end_month = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    
    # 1. Fetch current month data for Score
    budget_data = await budget_analytics(month=month, year=year, account_id=account_id, db=db)
    revenus = budget_data["revenus_totaux"]
    depenses_reelles = budget_data["depenses_reelles"]
    epargne_total = budget_data["epargne_total"]
    burn_rate = budget_data["burn_rate"]
    investissements = budget_data["investissements_du_mois"]
    
    # --- Health Score Calculation ---
    metrics = []
    
    # A. Savings Rate (30 pts)
    # Target: 20%
    savings_rate = budget_data["taux_epargne"]
    sr_score = min(max(savings_rate / 20.0 * 30.0, 0.0), 30.0)
    metrics.append(MetricDetail(
        name="Taux d'Épargne",
        score=round(sr_score, 1),
        max_score=30.0,
        value=round(savings_rate, 1),
        unit="%",
        status="good" if savings_rate >= 20 else "warning" if savings_rate >= 10 else "critical"
    ))

    # B. Runway / Safety Fund (30 pts)
    # Target: 6 months of burn rate
    runway_months = (epargne_total / burn_rate / 30.5) if (burn_rate > 0 and epargne_total > 0) else 0.0
    runway_score = min(runway_months / 6.0 * 30.0, 30.0)
    metrics.append(MetricDetail(
        name="Fonds de Sécurité",
        score=round(runway_score, 1),
        max_score=30.0,
        value=round(runway_months, 1),
        unit="mois",
        status="good" if runway_months >= 6 else "warning" if runway_months >= 3 else "critical"
    ))

    # C. Positive Cashflow (20 pts)
    # Target: Revenus > Depenses Reelles
    cashflow = revenus - depenses_reelles
    cf_score = 20.0 if cashflow > 0 else 0.0
    metrics.append(MetricDetail(
        name="Flux de Trésorerie",
        score=cf_score,
        max_score=20.0,
        value=round(cashflow, 2),
        unit="€",
        status="good" if cashflow > 0 else "critical"
    ))

    # D. Investment Ratio (20 pts)
    # Target: 10% of income
    inv_ratio = (investissements / revenus * 100.0) if revenus > 0 else 0.0
    inv_score = min(inv_ratio / 10.0 * 20.0, 20.0)
    metrics.append(MetricDetail(
        name="Ratio d'Investissement",
        score=round(inv_score, 1),
        max_score=20.0,
        value=round(inv_ratio, 1),
        unit="%",
        status="good" if inv_ratio >= 10 else "warning" if inv_ratio >= 5 else "critical"
    ))

    total_score = sum(m.score for m in metrics)
    health_score = HealthScore(total_score=round(total_score, 1), metrics=metrics)

    # --- Anomalies Detection ---
    insights = []

    # 1. Subscription increase
    # Compare with previous month
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    
    current_subs_total = await get_subscription_total_for_period(month=month, year=year, db=db)
    prev_subs_total = await get_subscription_total_for_period(month=prev_month, year=prev_year, db=db)
    
    if current_subs_total > prev_subs_total:
        diff = current_subs_total - prev_subs_total
        insights.append(Insight(
            type="anomaly",
            title="Hausse des abonnements",
            description=f"Vos abonnements ont augmenté de {round(diff, 2)}€ par rapport au mois dernier.",
            severity="medium",
            value=diff
        ))

    # 2. Large isolated transactions
    # Threshold: any transaction > 10% of monthly income OR > 500€
    large_tx_query = db.query(Transaction, Account.currency).join(Account).filter(
        Transaction.date >= start_month,
        Transaction.date < end_month,
        Transaction.type == "Sortie",
        Transaction.is_transfer == False
    )
    if account_id:
        large_tx_query = large_tx_query.filter(Transaction.account_id == account_id)
    
    all_txs = large_tx_query.all()
    for tx, curr in all_txs:
        val_eur = tx.amount / rates.get(curr, 1.0)
        # Exclude internal transfers or investments already tracked
        if tx.category and tx.category.name == "Investissement":
            continue
            
        threshold = max(revenus * 0.1, 500.0)
        if val_eur > threshold:
            insights.append(Insight(
                type="anomaly",
                title="Grosse dépense isolée",
                description=f"La transaction '{tx.merchant}' de {round(val_eur, 2)}€ est exceptionnellement élevée.",
                severity="high" if val_eur > revenus * 0.3 else "medium",
                value=val_eur
            ))

    # 3. Category spending anomalies (Sprint 4: > 2x average of last 3 months)
    # Get current month category totals
    current_cat_data = await expenses_by_category(month=month, year=year, account_id=account_id, db=db)
    current_cat_totals = {item["category"]["id"]: item["total"] for item in current_cat_data["items"]}
    
    # Get last 3 months averages
    last_3_months = []
    for i in range(1, 4):
        m_idx = month - i
        y_idx = year
        if m_idx <= 0:
            m_idx += 12
            y_idx -= 1
        last_3_months.append((m_idx, y_idx))
    
    cat_histories = {} # cat_id -> [totals]
    for m_idx, y_idx in last_3_months:
        hist_data = await expenses_by_category(month=m_idx, year=y_idx, account_id=account_id, db=db)
        for item in hist_data["items"]:
            cat_id = item["category"]["id"]
            if cat_id not in cat_histories:
                cat_histories[cat_id] = []
            cat_histories[cat_id].append(item["total"])
            
    for cat_id, current_total in current_cat_totals.items():
        history = cat_histories.get(cat_id, [])
        if len(history) >= 2: # Need at least 2 months to have a meaningful average
            avg = sum(history) / len(history)
            if avg > 20 and current_total > (avg * 2.0): # Only alert if avg > 20€ and 2x increase
                cat_obj = db.query(Category).filter(Category.id == cat_id).first()
                insights.append(Insight(
                    type="anomaly",
                    title=f"Alerte catégorie : {cat_obj.name}",
                    description=f"Vos dépenses en '{cat_obj.name}' ({round(current_total, 2)}€) sont plus de 2x supérieures à votre moyenne habituelle ({round(avg, 2)}€).",
                    severity="medium",
                    value=current_total
                ))

    # 4. Positive Insights
    if savings_rate > 30:
        insights.append(Insight(
            type="positive",
            title="Excellent taux d'épargne",
            description="Félicitations ! Vous épargnez plus de 30% de vos revenus ce mois-ci.",
            severity="low",
            value=savings_rate
        ))
    
    if runway_months > 12:
        insights.append(Insight(
            type="positive",
            title="Sérénité financière",
            description="Votre fonds de sécurité couvre plus d'un an de dépenses. Vous êtes très bien protégé.",
            severity="low",
            value=runway_months
        ))

    from app.models.dismissed_insight import DismissedInsight
    dismissed = db.query(DismissedInsight.title).all()
    dismissed_titles = {d.title for d in dismissed}
    
    final_insights = [i for i in insights if i.title not in dismissed_titles]

    return IntelligentInsights(health_score=health_score, insights=final_insights)

from pydantic import BaseModel
class DismissInsightRequest(BaseModel):
    title: str

@router.post("/insights/dismiss")
async def dismiss_insight(request: DismissInsightRequest, db: Session = Depends(get_db)):
    from app.models.dismissed_insight import DismissedInsight
    existing = db.query(DismissedInsight).filter(DismissedInsight.title == request.title).first()
    if not existing:
        new_dismissed = DismissedInsight(title=request.title)
        db.add(new_dismissed)
        db.commit()
    return {"status": "success"}

@router.get("/calendar")
async def calendar_analytics(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    start_month = datetime(year, month, 1)
    # End of month is start of next month
    if month == 12:
        end_month = datetime(year + 1, 1, 1)
    else:
        end_month = datetime(year, month + 1, 1)
        
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    sim_start = min(start_month, today)
    
    # 1. Fetch real transactions
    tx_query = db.query(Transaction).filter(
        Transaction.date >= sim_start,
        Transaction.date < end_month
    )
    inv_tx_query = db.query(InvestmentTransaction).filter(
        InvestmentTransaction.date >= sim_start,
        InvestmentTransaction.date < end_month
    )
    
    if account_id:
        tx_query = tx_query.filter(Transaction.account_id == account_id)
        inv_tx_query = inv_tx_query.filter(InvestmentTransaction.account_id == account_id)
    
    real_txs = tx_query.all()
    real_inv_txs = inv_tx_query.all()
    
    # 2. Fetch recurring transactions and project them
    recur_query = db.query(RecurringTransaction).filter(RecurringTransaction.is_active == True)
    if account_id:
        recur_query = recur_query.filter(RecurringTransaction.account_id == account_id)
    
    recurring_defs = recur_query.all()
    projected_events = []
    
    # Create a set of (recurring_id, date) for real transactions to deduplicate
    # We use date.date() to ignore time
    realized_recurrences = {
        (tx.recurring_transaction_id, tx.date.date()) 
        for tx in real_txs 
        if tx.recurring_transaction_id is not None
    }
    # Also include investment transactions
    for tx in real_inv_txs:
        if hasattr(tx, "recurring_transaction_id") and tx.recurring_transaction_id is not None:
            realized_recurrences.add((tx.recurring_transaction_id, tx.date.date()))
    
    for rd in recurring_defs:
        # Project for the whole month, but deduplicate
        occurrences = get_recurring_occurrences(rd, sim_start, end_month)
        for occ in occurrences:
            proj_date = occ
            proj_amount = rd.amount
            proj_note = rd.name
            
            # Check if it's a salary/TR recurrence
            from app.models.salary_config import SalaryConfig
            from app.models.salary_month import SalaryMonth
            from app.models.telecommuting_day import TelecommutingDay
            from app.core.finance import month_label_from_date
            
            salary_config = db.query(SalaryConfig).filter(
                (SalaryConfig.salary_recurring_id == rd.id) | 
                (SalaryConfig.ticket_recurring_id == rd.id)
            ).first()
            
            if salary_config:
                month_label = month_label_from_date(occ)
                if rd.id == salary_config.ticket_recurring_id and occ.day < 15:
                    work_month_date = occ - timedelta(days=20)
                    salary_month_label = f"{work_month_date.year}-{work_month_date.month:02d}"
                else:
                    salary_month_label = f"{occ.year}-{occ.month:02d}"
                salary_month = db.query(SalaryMonth).filter(
                    SalaryMonth.salary_config_id == salary_config.id,
                    SalaryMonth.month_label == salary_month_label
                ).first()
                
                tt_days_count = 0
                if salary_month:
                    tt_days_count = db.query(TelecommutingDay).filter(
                        TelecommutingDay.salary_config_id == salary_config.id,
                        TelecommutingDay.month_label == salary_month_label
                    ).count()
                    
                    if rd.id == salary_config.salary_recurring_id and salary_month.salary_date:
                        proj_date = datetime.combine(salary_month.salary_date, datetime.min.time())
                    if rd.id == salary_config.ticket_recurring_id and salary_month.ticket_date:
                        proj_date = datetime.combine(salary_month.ticket_date, datetime.min.time())
                
                if rd.id == salary_config.salary_recurring_id:
                    deduction = tt_days_count * salary_config.ticket_employee_share
                    proj_amount = salary_config.net_salary - deduction
                    proj_note = f"Salaire ({month_label})"
                elif rd.id == salary_config.ticket_recurring_id:
                    proj_amount = tt_days_count * salary_config.ticket_value
                    proj_note = f"Tickets Restaurant ({month_label})"
                    
            # Skip if already realized (we check month and recurring_id instead of exact date for salary to be safe)
            # Or just check exact date with the overriden proj_date
            if (rd.id, proj_date.date()) in realized_recurrences:
                continue
                
            projected_events.append({
                "id": f"proj_{rd.id}_{proj_date.isoformat()}",
                "date": proj_date.isoformat(),
                "name": proj_note,
                "amount": proj_amount,
                "type": rd.type,
                "category_id": rd.category_id,
                "is_projected": True,
                "recurring_id": rd.id,
                "currency": rd.currency,
                "account_id": rd.account_id
            })

    # 3. Format real transactions
    formatted_real = []
    for tx in real_txs:
        formatted_real.append({
            "id": f"tx_{tx.id}",
            "date": tx.date.isoformat(),
            "name": tx.merchant,
            "amount": tx.amount,
            "type": tx.type,
            "category_id": tx.category_id,
            "is_projected": False,
            "currency": tx.currency,
            "account_id": tx.account_id,
            "running_balance": getattr(tx, "running_balance", None)
        })
    
    for tx in real_inv_txs:
        formatted_real.append({
            "id": f"inv_{tx.id}",
            "date": tx.date.isoformat(),
            "name": f"[{tx.type.capitalize()}] {tx.note or 'Investissement'}",
            "amount": tx.amount,
            "type": tx.type,
            "category_id": None,
            "is_projected": False,
            "currency": tx.currency,
            "account_id": tx.account_id
        })
        
    # 4. Calculate daily balance projections
    daily_balances = []
    rates = await get_exchange_rates("EUR")
    
    # Initialize balances per account
    account_balances = {}
    active_accounts = db.query(Account).all()
    account_currencies = {acc.id: acc.currency for acc in active_accounts}
    
    if account_id:
        last_tx_before = db.query(Transaction).filter(
            Transaction.account_id == account_id,
            Transaction.date < sim_start
        ).order_by(Transaction.date.desc(), Transaction.id.desc()).first()
        account_balances[account_id] = last_tx_before.running_balance if last_tx_before else 0.0
    else:
        active_only = [a for a in active_accounts if a.active]
        for acc in active_only:
            last_tx_before = db.query(Transaction).filter(
                Transaction.account_id == acc.id,
                Transaction.date < sim_start
            ).order_by(Transaction.date.desc(), Transaction.id.desc()).first()
            account_balances[acc.id] = last_tx_before.running_balance if last_tx_before else 0.0

    # We simulate day by day
    all_events = sorted(formatted_real + projected_events, key=lambda x: x["date"])
    event_idx = 0
    
    temp_date = sim_start
    while temp_date < end_month:
        # Apply events for this day
        while event_idx < len(all_events) and datetime.fromisoformat(all_events[event_idx]["date"]).date() == temp_date.date():
            ev = all_events[event_idx]
            acc_id = ev.get("account_id")
            
            if acc_id is not None:
                if acc_id not in account_balances:
                    account_balances[acc_id] = 0.0

                positive_types = ["Entree", "Interets", "Solde Initial", "versement", "dividende"]
                negative_types = ["Sortie", "retrait"]
                
                # If it's a real transaction with a running_balance, we sync it exactly
                if not ev.get("is_projected") and ev.get("running_balance") is not None:
                    account_balances[acc_id] = ev["running_balance"]
                else:
                    amt = ev["amount"]
                    if ev["type"] == "Solde Initial":
                        account_balances[acc_id] = amt
                    elif ev["type"] in positive_types:
                        account_balances[acc_id] += amt
                    elif ev["type"] in negative_types:
                        account_balances[acc_id] -= amt

            event_idx += 1
            
        # Calculate daily total
        if account_id:
            current_bal = account_balances.get(account_id, 0.0)
        else:
            current_bal = 0.0
            for a_id, bal in account_balances.items():
                curr = account_currencies.get(a_id, "EUR")
                current_bal += bal / rates.get(curr, 1.0)

        if temp_date >= start_month:
            daily_balances.append({
                "date": temp_date.date().isoformat(),
                "balance": round(current_bal, 2)
            })
        temp_date += timedelta(days=1)

    return {
        "month": month,
        "year": year,
        "events": [ev for ev in sorted(formatted_real + projected_events, key=lambda x: x["date"]) if datetime.fromisoformat(ev["date"]) >= start_month],
        "daily_balances": daily_balances
    }


@router.get("/cashflow-projection", response_model=CashflowProjection)
async def get_cashflow_projection(
    days: int = Query(default=30, ge=7, le=365),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Projects balance for the next X days based on current balance and recurring transactions.
    """
    now = datetime.now()
    end_date = now + timedelta(days=days)
    rates = await get_exchange_rates("EUR")

    # 1. Current balance
    current_bal = 0.0
    if account_id:
        acc = db.query(Account).filter(Account.id == account_id).first()
        if not acc:
            raise HTTPException(status_code=404, detail="Account not found")
        last_tx = (
            db.query(Transaction)
            .filter(Transaction.account_id == account_id)
            .order_by(Transaction.date.desc(), Transaction.id.desc())
            .first()
        )
        if last_tx:
            current_bal = float(last_tx.running_balance)
    else:
        active_accounts = db.query(Account).filter(Account.active == True).all()
        for acc in active_accounts:
            last_tx = (
                db.query(Transaction)
                .filter(Transaction.account_id == acc.id)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .first()
            )
            if last_tx:
                current_bal += float(last_tx.running_balance) / rates.get(acc.currency, 1.0)

    # 2. Collect future occurrences
    projected_events_list: List[ProjectionEvent] = []
    
    recur_query = db.query(RecurringTransaction).filter(RecurringTransaction.is_active == True)
    if account_id:
        recur_query = recur_query.filter(RecurringTransaction.account_id == account_id)
    
    recurring_defs = recur_query.all()
    
    for rd in recurring_defs:
        occurrences = get_recurring_occurrences(rd, now, end_date)
        for occ in occurrences:
            is_income = rd.type in ["Entree", "Interets", "versement", "dividende"]
            
            proj_amount = rd.amount
            
            # Check if it's a salary/TR recurrence
            from app.models.salary_config import SalaryConfig
            from app.models.salary_month import SalaryMonth
            from app.models.telecommuting_day import TelecommutingDay
            from app.core.finance import month_label_from_date
            
            salary_config = db.query(SalaryConfig).filter(
                (SalaryConfig.salary_recurring_id == rd.id) | 
                (SalaryConfig.ticket_recurring_id == rd.id)
            ).first()
            
            if salary_config:
                if rd.id == salary_config.ticket_recurring_id and occ.day < 15:
                    work_month_date = occ - timedelta(days=20)
                    salary_month_label = f"{work_month_date.year}-{work_month_date.month:02d}"
                else:
                    salary_month_label = f"{occ.year}-{occ.month:02d}"
                salary_month = db.query(SalaryMonth).filter(
                    SalaryMonth.salary_config_id == salary_config.id,
                    SalaryMonth.month_label == salary_month_label
                ).first()
                
                tt_days_count = 0
                if salary_month:
                    tt_days_count = db.query(TelecommutingDay).filter(
                        TelecommutingDay.salary_config_id == salary_config.id,
                        TelecommutingDay.month_label == salary_month_label
                    ).count()
                
                if rd.id == salary_config.salary_recurring_id:
                    deduction = tt_days_count * salary_config.ticket_employee_share
                    proj_amount = salary_config.net_salary - deduction
                elif rd.id == salary_config.ticket_recurring_id:
                    proj_amount = tt_days_count * salary_config.ticket_value

            # Convert amount to EUR if global view
            amount_target = float(proj_amount)
            if not account_id and rd.currency != "EUR":
                amount_target = amount_target / rates.get(rd.currency, 1.0)
                
            projected_events_list.append(ProjectionEvent(
                date=occ.isoformat(),
                name=rd.name,
                amount=amount_target,
                type="recurring",
                is_income=is_income
            ))

    # 3. Simulate day by day
    points: List[ProjectionPoint] = []
    simulated_bal = current_bal
    
    # Sort events by date
    projected_events_list.sort(key=lambda x: x.date)
    event_idx = 0
    
    low_point = current_bal
    low_point_date = now.date().isoformat()
    
    temp_date = now
    while temp_date <= end_date:
        daily_change = 0.0
        while event_idx < len(projected_events_list) and datetime.fromisoformat(projected_events_list[event_idx].date).date() == temp_date.date():
            ev = projected_events_list[event_idx]
            
            # Amount conversion for global view
            # Note: We don't have account currency here in ProjectionEvent, but we can assume EUR for now or fetch it
            # To be precise, we'd need rd.currency. Let's assume EUR if no account_id.
            # For simplicity, we'll re-fetch or use a more complex event structure.
            
            # Re-fetch rd currency if needed? No, let's keep it simple for now.
            # In a real app, I'd want the currency in ProjectionEvent.
            
            amt = ev.amount
            if ev.is_income:
                simulated_bal += amt
                daily_change += amt
            else:
                simulated_bal -= amt
                daily_change -= amt
            
            event_idx += 1
            
        if simulated_bal < low_point:
            low_point = simulated_bal
            low_point_date = temp_date.date().isoformat()
            
        points.append(ProjectionPoint(
            date=temp_date.date().isoformat(),
            balance=round(simulated_bal, 2),
            change=round(daily_change, 2)
        ))
        temp_date += timedelta(days=1)

    return CashflowProjection(
        points=points,
        events=projected_events_list,
        current_balance=round(current_bal, 2),
        projected_balance=round(simulated_bal, 2),
        low_point=round(low_point, 2),
        low_point_date=low_point_date,
        days=days
    )


@router.get("/monthly-report", response_model=MonthlyReport)
async def get_monthly_report(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Consolidates data for a comprehensive monthly smart report.
    Compares with previous month and provides insights.
    """
    # 1. Current month data
    current_budget = await budget_analytics(month=month, year=year, account_id=account_id, db=db)
    
    # 2. Previous month data for comparison
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    prev_budget = await budget_analytics(month=prev_month, year=prev_year, account_id=account_id, db=db)
    
    # 3. Insights (Anomalies, Score, etc.)
    insights_data = await get_intelligent_insights(month=month, year=year, account_id=account_id, db=db)
    
    # 4. Top categories
    cat_data = await expenses_by_category(month=month, year=year, account_id=account_id, db=db)
    top_categories = []
    # Sort items by total descending
    sorted_items = sorted(cat_data["items"], key=lambda x: x["total"], reverse=True)
    for item in sorted_items[:5]:
        top_categories.append({
            "name": item["category"]["name"],
            "total": item["total"],
            "icon": item["category"]["icon"],
            "color": item["category"]["color"]
        })
    
    # 5. Top merchants
    merch_data = await top_merchants(month=month, year=year, limit=5, account_id=account_id, db=db)
    
    # 6. Comparison logic
    def calc_diff(curr, prev):
        diff = curr - prev
        pct = (diff / prev * 100) if prev != 0 else 0
        return diff, pct

    inc_diff, inc_pct = calc_diff(current_budget["revenus_totaux"], prev_budget["revenus_totaux"])
    exp_diff, exp_pct = calc_diff(current_budget["depenses_reelles"], prev_budget["depenses_reelles"])
    sav_diff, sav_pct = calc_diff(current_budget["revenus_apres_depenses"], prev_budget["revenus_apres_depenses"])
    
    # Net worth change
    nw_change = current_budget["patrimoine_net_total"] - prev_budget["patrimoine_net_total"]

    # 7. Money Flow (Integrated)
    flow_data = await get_money_flow(month=month, year=year, account_id=account_id, db=db)
    
    return MonthlyReport(
        month=month,
        year=year,
        income=current_budget["revenus_totaux"],
        expenses=current_budget["depenses_totales"],
        real_expenses=current_budget["depenses_reelles"],
        savings=current_budget["revenus_apres_depenses"],
        savings_rate=current_budget["taux_epargne"],
        burn_rate=current_budget["burn_rate"],
        net_worth=current_budget["patrimoine_net_total"],
        net_worth_change=round(nw_change, 2),
        top_categories=top_categories,
        top_merchants=merch_data["items"],
        comparison=MonthlyComparison(
            income_diff=round(inc_diff, 2),
            income_diff_pct=round(inc_pct, 1),
            expenses_diff=round(exp_diff, 2),
            expenses_diff_pct=round(exp_pct, 1),
            savings_diff=round(sav_diff, 2),
            savings_diff_pct=round(sav_pct, 1)
        ),
        insights=insights_data.insights,
        health_score=insights_data.health_score,
        money_flow=flow_data
    )


async def _calculate_money_flow_data(month: int, year: int, db: Session, account_id: int | None = None):
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    rates = await get_exchange_rates("EUR")
    
    # 1. Income (Filtered to checking accounts by default if account_id is None)
    # We re-implement a lean version here or call budget_analytics with type filter if supported.
    # To be precise and follow user instruction: we only want cash flowing INTO checking accounts.
    
    income_query = (
        db.query(Account.currency, func.sum(Transaction.amount).label("total"))
        .join(Account, Transaction.account_id == Account.id)
        .filter(Transaction.date >= start, Transaction.date < end)
        .filter(Transaction.type.in_(["Entree", "Interets", "Solde Initial"]))
        .filter(Transaction.is_transfer == False)
    )
    
    if account_id:
        income_query = income_query.filter(Transaction.account_id == account_id)
    else:
        # Focus on CHECKING accounts only
        income_query = income_query.filter(Account.type == "courant")
        
    income_rows = income_query.group_by(Account.currency).all()
    income = sum(row.total / rates.get(row.currency, 1.0) for row in income_rows)
    
    # 2. Expenses (Sortie, is_transfer=False) from CHECKING accounts
    tx_query = (
        db.query(Transaction, Category.name.label("cat_name"))
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(Transaction.date >= start, Transaction.date < end)
        .filter(Transaction.is_transfer == False)
    )
    
    if account_id:
        tx_query = tx_query.filter(Transaction.account_id == account_id)
    else:
        tx_query = tx_query.filter(Account.type == "courant")
        
    transactions = tx_query.all()
    
    fixed_charges = 0.0
    variable_expenses = 0.0
    savings = 0.0
    investments = 0.0
    
    top_fixed_map = {}
    top_variable_map = {}
    top_savings_map = {}
    top_investments_map = {}
    
    for row in transactions:
        tx = row.Transaction
        cat_name = row.cat_name or "Sans catégorie"
        
        amount_eur = tx.amount / rates.get(tx.currency, 1.0)
        
        if tx.type == "Sortie":
            if cat_name in ["Epargne", "Épargne"]:
                savings += amount_eur
                top_savings_map[tx.merchant] = top_savings_map.get(tx.merchant, 0) + amount_eur
            elif cat_name in ["Investissement"]:
                investments += amount_eur
                top_investments_map[tx.merchant] = top_investments_map.get(tx.merchant, 0) + amount_eur
            elif tx.is_recurring:
                fixed_charges += amount_eur
                key = f"{tx.merchant} ({cat_name})"
                top_fixed_map[key] = top_fixed_map.get(key, 0) + amount_eur
            else:
                variable_expenses += amount_eur
                key = cat_name
                top_variable_map[key] = top_variable_map.get(key, 0) + amount_eur
                
    # 3. Investment Transactions
    # We REMOVE the direct query to InvestmentTransaction because for the "Checking Account" perspective,
    # these flows are already captured as 'Sortie' (Transferts) in the Transactions table of the checking account.
    # Including them again would double count the outflows.
    
    remainder = income - (fixed_charges + variable_expenses + savings + investments)
    
    return {
        "income": income,
        "fixed_charges": fixed_charges,
        "variable_expenses": variable_expenses,
        "savings": savings,
        "investments": investments,
        "remainder": remainder,
        "top_fixed": sorted([{"name": k, "amount": v} for k, v in top_fixed_map.items()], key=lambda x: x["amount"], reverse=True)[:5],
        "top_variable": sorted([{"name": k, "amount": v} for k, v in top_variable_map.items()], key=lambda x: x["amount"], reverse=True)[:5],
        "top_savings": sorted([{"name": k, "amount": v} for k, v in top_savings_map.items()], key=lambda x: x["amount"], reverse=True)[:5],
        "top_investments": sorted([{"name": k, "amount": v} for k, v in top_investments_map.items()], key=lambda x: x["amount"], reverse=True)[:5]
    }


@router.get("/money-flow", response_model=MoneyFlowReport)
async def get_money_flow(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Returns a detailed flow of where the money went during a month.
    """
    # 1. Current month
    curr = await _calculate_money_flow_data(month, year, db, account_id)
    
    # 2. Previous month
    prev_m = month - 1 if month > 1 else 12
    prev_y = year if month > 1 else year - 1
    prev = await _calculate_money_flow_data(prev_m, prev_y, db, account_id)
    
    def make_block(val_curr, val_prev, income):
        diff = val_curr - val_prev
        diff_pct = (diff / val_prev * 100) if val_prev != 0 else 0
        pct_inc = (val_curr / income * 100) if income != 0 else 0
        return MoneyFlowBlock(
            amount=round(val_curr, 2),
            percentage=round(pct_inc, 1),
            diff_prev_month=round(diff, 2),
            diff_prev_month_pct=round(diff_pct, 1)
        )

    return MoneyFlowReport(
        month=month,
        year=year,
        income=curr["income"],
        fixed_charges=make_block(curr["fixed_charges"], prev["fixed_charges"], curr["income"]),
        variable_expenses=make_block(curr["variable_expenses"], prev["variable_expenses"], curr["income"]),
        savings=make_block(curr["savings"], prev["savings"], curr["income"]),
        investments=make_block(curr["investments"], prev["investments"], curr["income"]),
        remainder=make_block(curr["remainder"], prev["remainder"], curr["income"]),
        top_fixed=[MoneyFlowItem(**x, is_recurring=True) for x in curr["top_fixed"]],
        top_variable=[MoneyFlowItem(**x) for x in curr["top_variable"]],
        top_savings=[MoneyFlowItem(**x) for x in curr["top_savings"]],
        top_investments=[MoneyFlowItem(**x) for x in curr["top_investments"]]
    )


@router.get("/sankey")
async def sankey_analytics(
    month: int = Query(ge=1, le=12),
    year: int = Query(ge=2000, le=2200),
    account_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    # 1. Prepare time and rates
    start = datetime(year, month, 1)
    end = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    rates = await get_exchange_rates("EUR")
    budget_data = await budget_analytics(month=month, year=year, account_id=account_id, db=db)
    
    # 2. Fetch all expenses by category (excluding internal transfers/savings/investments)
    exp_query = (
        db.query(
            Category,
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type == "Sortie",
            Transaction.is_transfer == False,
            # We filter out Investment/Savings categories because they have their own logic below
            ~Category.name.in_(["Investissement", "Epargne"])
        )
    )
    if account_id:
        exp_query = exp_query.filter(Transaction.account_id == account_id)

    exp_rows = exp_query.group_by(Category.id, Account.currency).all()

    # Aggregate expenses by category
    cat_expenses = {} # cat_id -> {obj, total}
    for row in exp_rows:
        cid = row.Category.id
        if cid not in cat_expenses:
            cat_expenses[cid] = {"obj": row.Category, "total": 0.0}
        cat_expenses[cid]["total"] += row.total / rates.get(row.currency, 1.0)

    # 3. Fetch Income sources
    inc_query = (
        db.query(
            Category,
            Account.currency,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total"),
        )
        .join(Account, Transaction.account_id == Account.id)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.type.in_(["Entree", "Interets", "Solde Initial"]), # Include Solde Initial for better flow visualization
            Transaction.is_transfer == False
        )
    )
    if account_id:
        inc_query = inc_query.filter(Transaction.account_id == account_id)

    inc_rows = inc_query.group_by(Category.id, Account.currency).all()

    income_sources = [] # list of {name, total, color}
    total_income = 0.0
    for row in inc_rows:
        name = row.Category.name if row.Category else "Autres Revenus"
        color = row.Category.color if row.Category else "#10b981"
        val = row.total / rates.get(row.currency, 1.0)
        if val > 0:
            income_sources.append({"name": name, "total": val, "color": color})
            total_income += val

    # Add investment dividends to income
    itx_div_query = db.query(Account.currency, func.sum(InvestmentTransaction.amount)).join(Account, InvestmentTransaction.account_id == Account.id).filter(
        InvestmentTransaction.type == "dividende",
        InvestmentTransaction.date >= start,
        InvestmentTransaction.date < end
    )
    if account_id:
        itx_div_query = itx_div_query.filter(InvestmentTransaction.account_id == account_id)

    div_total = 0.0
    for curr, amt in itx_div_query.group_by(Account.currency).all():
        div_total += amt / rates.get(curr, 1.0)

    if div_total > 0:
        income_sources.append({"name": "Dividendes", "total": div_total, "color": "#10b981"})
        total_income += div_total

    # 4. Build Nodes and Links
    nodes = []
    links = []

    def add_node(name, color=None):
        idx = len(nodes)
        nodes.append({"name": name, "color": color})
        return idx

    # Aggregator Node
    total_revenus_idx = add_node("Budget", "#94a3b8")

    # STAGE 1: Income -> Budget
    for src in income_sources:
        src_idx = add_node(src["name"], src["color"])
        links.append({"source": src_idx, "target": total_revenus_idx, "value": round(src["total"], 2), "color": src["color"]})

    # STAGE 2 & 3: Budget -> Groups -> Categories
    groups = {} # group_name -> {idx, total, color}

    # Investment "Group"
    invest_total = budget_data["investissements_du_mois"]
    if invest_total > 0:
        inv_idx = add_node("Investissements", "#6366f1")
        links.append({"source": total_revenus_idx, "target": inv_idx, "value": round(invest_total, 2), "color": "#6366f1"})

    # Savings "Group"
    savings_total = budget_data["revenus_apres_depenses"]
    if savings_total > 0:
        sav_idx = add_node("Épargne", "#10b981")
        links.append({"source": total_revenus_idx, "target": sav_idx, "value": round(savings_total, 2), "color": "#10b981"})
    elif savings_total < 0:
        # Spending more than income: add a 'Deficit' node as an incoming flow to Budget
        def_idx = add_node("Déficit / Trésorerie", "#f43f5e")
        links.append({"source": def_idx, "target": total_revenus_idx, "value": round(abs(savings_total), 2), "color": "#fecdd3"})
        total_income += abs(savings_total)

    # Expenses logic: we need to ensure Budget node doesn't leak
    # If income is higher than total shown outflows, the difference is "Epargne"
    # (already handled via savings_total which is remaining = income - total_expenses)

    # Expense Groups and Categories
    for cid, data in cat_expenses.items():
        cat = data["obj"]
        total = data["total"]
        if total <= 0: continue

        if cat.group:
            group_name = cat.group
            if group_name not in groups:
                # Add a slightly different color for groups to distinguish from categories
                g_idx = add_node(group_name, "#64748b") 
                groups[group_name] = {"idx": g_idx, "total": 0.0}
                links.append({"source": total_revenus_idx, "target": g_idx, "value": 0.0, "color": "#cbd5e1"})

            groups[group_name]["total"] += total

            # Link Group -> Category
            cat_idx = add_node(cat.name, cat.color)
            links.append({"source": groups[group_name]["idx"], "target": cat_idx, "value": round(total, 2), "color": cat.color})
        else:
            # Direct link Budget -> Category (no intermediate group)
            cat_idx = add_node(cat.name, cat.color)
            links.append({"source": total_revenus_idx, "target": cat_idx, "value": round(total, 2), "color": cat.color})

    # Update Group link values (they were 0.0 placeholder)
    for g_name, g_data in groups.items():
        for link in links:
            if link["source"] == total_revenus_idx and link["target"] == g_data["idx"]:
                link["value"] = round(g_data["total"], 2)

    # Final check: if the Budget node is still unbalanced (more income than total links out),
    # it might be due to rounding or untracked flows. We balance it with a small "Ajustement" if needed.
    total_out = sum(l["value"] for l in links if l["source"] == total_revenus_idx)
    diff = total_income - total_out
    if diff > 1.0: # Only if significant (> 1 EUR)
        adj_idx = add_node("Reliquat / Ajustement", "#94a3b8")
        links.append({"source": total_revenus_idx, "target": adj_idx, "value": round(diff, 2), "color": "#cbd5e1"})

    return {"nodes": nodes, "links": links}
