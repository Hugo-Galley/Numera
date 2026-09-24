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
from .budget import budget_analytics, budget_alerts

logger = get_logger(__name__)

router = APIRouter()

from .utils import (
    _tx_sample,
    _tx_read,
    _savings_account_ids,
    _savings_events_by_account,
    _savings_total_at,
    _get_ticket_restaurant_account_ids,
)


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


