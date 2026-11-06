"""Audit des données (`/analytics/audit`) : anomalies de qualité et détail éditable d'une anomalie."""
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.i18n import tr
from app.domain.transactions import tx_read, tx_sample
from app.domain.transfers import strict_matches
from app.models.transaction import Transaction
from app.repositories.analytics import audit as repo
from app.repositories.comptes import balances
from app.schemas.insight import DataAuditIssue, DataAuditResponse, DataAuditSummary
from app.services.audit.context import unallocated_reimbursements_query


def compute_data_audit(db: Session) -> DataAuditResponse:
    now = datetime.now()
    total_transactions = repo.transaction_count(db)
    active_accounts = repo.active_account_count(db)
    accounts = balances.active_accounts(db, by_name=True)
    checks = [
        _uncategorized(db), _missing_merchants(db), _unnormalized_merchants(db), _duplicates(db),
        _missing_initial_balances(db, accounts), _stale_snapshots(db, accounts, now), _unused_categories(db),
        _unmatched_transfers(db, now), _unallocated_reimbursements(db, now),
    ]
    issues = [issue for issue in checks if issue is not None]
    return DataAuditResponse(
        summary=DataAuditSummary(
            total_issues=len(issues),
            high_count=sum(1 for issue in issues if issue.severity == "high"),
            medium_count=sum(1 for issue in issues if issue.severity == "medium"),
            low_count=sum(1 for issue in issues if issue.severity == "low"),
            total_transactions=total_transactions,
            active_accounts=active_accounts,
            checked_at=now.isoformat(),
        ),
        issues=issues,
    )


def _uncategorized(db: Session) -> DataAuditIssue | None:
    query = repo.uncategorized_expenses(db).order_by(Transaction.date.desc(), Transaction.id.desc())
    count = query.count()
    if not count:
        return None
    return DataAuditIssue(
        id="uncategorized-expenses",
        type="categorization",
        severity="high",
        title=tr("audit.data.uncategorized.title"),
        description=tr("audit.data.uncategorized.description"),
        count=count,
        action_label=tr("audit.data.uncategorized.action"),
        action_url="/accounts",
        samples=[tx_sample(tx) for tx in query.limit(5).all()],
    )


def _missing_merchants(db: Session) -> DataAuditIssue | None:
    query = repo.missing_merchants(db)
    count = query.count()
    if not count:
        return None
    return DataAuditIssue(
        id="missing-merchants",
        type="merchant",
        severity="medium",
        title=tr("audit.data.missing_merchants.title"),
        description=tr("audit.data.missing_merchants.description"),
        count=count,
        action_label=tr("audit.data.missing_merchants.action"),
        action_url="/accounts",
        samples=[tx_sample(tx) for tx in query.limit(5).all()],
    )


def _unnormalized_merchants(db: Session) -> DataAuditIssue | None:
    query = (
        repo.unnormalized_merchant_counts(db)
        .having(func.count(Transaction.id) >= 5)
        .order_by(func.count(Transaction.id).desc())
    )
    count = query.count()
    if not count:
        return None
    return DataAuditIssue(
        id="unnormalized-merchants",
        type="merchant",
        severity="low",
        title=tr("audit.data.unnormalized_merchants.title"),
        description=tr("audit.data.unnormalized_merchants.description"),
        count=count,
        action_label=tr("audit.data.unnormalized_merchants.action"),
        action_url="/classement?tab=merchants",
        samples=[{"merchant": r.merchant, "count": r.count} for r in query.limit(5).all()],
    )


def _duplicates(db: Session) -> DataAuditIssue | None:
    groups = repo.duplicate_groups(db).order_by(func.count(Transaction.id).desc()).limit(10).all()
    if not groups:
        return None
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
        for row in groups[:5]
    ]
    return DataAuditIssue(
        id="duplicate-transactions",
        type="duplicates",
        severity="high",
        title=tr("audit.data.duplicates.title"),
        description=tr("audit.data.duplicates.description"),
        count=sum(int(row.count) for row in groups),
        action_label=tr("audit.data.duplicates.action"),
        action_url="/accounts",
        samples=samples,
    )


def _missing_initial_balances(db: Session, accounts: list) -> DataAuditIssue | None:
    missing = [
        account for account in accounts
        if repo.transaction_count(db, account.id) and not repo.has_initial_balance(db, account.id)
    ]
    if not missing:
        return None
    return DataAuditIssue(
        id="missing-initial-balances",
        type="accounts",
        severity="medium",
        title=tr("audit.data.initial_balances.title"),
        description=tr("audit.data.initial_balances.description"),
        count=len(missing),
        action_label=tr("audit.data.initial_balances.action"),
        action_url="/accounts",
        samples=[{"id": acc.id, "name": acc.name, "type": acc.type, "currency": acc.currency} for acc in missing[:5]],
    )


def _stale_snapshots(db: Session, accounts: list, now: datetime) -> DataAuditIssue | None:
    stale = []
    for account in accounts:
        if account.type != "investissement":
            continue
        last = repo.latest_snapshot_date(db, account.id, id_tiebreak=True)
        if not last or (now - last).days > 45:
            stale.append({
                "id": account.id,
                "name": account.name,
                "last_snapshot": last.date().isoformat() if last else None,
                "days_since_snapshot": (now - last).days if last else None,
            })
    if not stale:
        return None
    return DataAuditIssue(
        id="stale-investment-snapshots",
        type="investments",
        severity="medium",
        title=tr("audit.data.investment_snapshots.title"),
        description=tr("audit.data.investment_snapshots.description"),
        count=len(stale),
        action_label=tr("audit.data.investment_snapshots.action"),
        action_url="/investments",
        samples=stale[:5],
    )


def _unused_categories(db: Session) -> DataAuditIssue | None:
    unused = repo.unused_categories(db)
    if not unused:
        return None
    return DataAuditIssue(
        id="unused-categories",
        type="cleanup",
        severity="low",
        title=tr("audit.data.unused_categories.title"),
        description=tr("audit.data.unused_categories.description"),
        count=len(unused),
        action_label=tr("audit.data.unused_categories.action"),
        action_url="/classement?tab=categories",
        samples=[{"id": cat.id, "name": cat.name, "type": cat.type} for cat in unused[:8]],
    )


def _transfer_candidates(db: Session, now: datetime) -> tuple[list[Transaction], dict[float, list[Transaction]]]:
    """Sorties récentes non rapprochées et leurs entrées candidates (une requête chacune), indexées par montant."""
    sorties = repo.recent_unlinked_sorties(db, now - timedelta(days=180), strict=True, limit=250)
    entrees: dict[float, list[Transaction]] = {}
    for entree in repo.strict_transfer_candidates(db, sorties):
        entrees.setdefault(entree.amount, []).append(entree)
    return sorties, entrees


def _unmatched_transfers(db: Session, now: datetime) -> DataAuditIssue | None:
    count = 0
    samples = []
    sorties, entrees = _transfer_candidates(db, now)
    for sortie in sorties:
        matches = strict_matches(sortie, entrees)
        if matches:
            count += 1
            if len(samples) < 5:
                samples.append({"sortie": tx_sample(sortie), "entree": tx_sample(matches[0])})
    if not count:
        return None
    return DataAuditIssue(
        id="unmatched-transfers",
        type="transfers",
        severity="medium",
        title=tr("audit.data.transfers.title"),
        description=tr("audit.data.transfers.description"),
        count=count,
        action_label=tr("audit.data.transfers.action"),
        action_url="/audit?vue=virements",
        samples=samples,
    )


def _unallocated_reimbursements(db: Session, now: datetime) -> DataAuditIssue | None:
    query = unallocated_reimbursements_query(db, now)
    unallocated = query.all() if query is not None else []
    if not unallocated:
        return None
    return DataAuditIssue(
        id="unallocated-reimbursements",
        type="reimbursements",
        severity="low",
        title=tr("audit.data.reimbursements.title"),
        description=tr("audit.data.reimbursements.description"),
        count=len(unallocated),
        action_label=tr("audit.data.reimbursements.action"),
        action_url="/reimbursements",
        samples=[tx_sample(t) for t in unallocated[:5]],
    )


# --- Détail éditable d'une anomalie (`/analytics/audit/{issue_id}`) ---

def compute_data_audit_issue(db: Session, issue_id: str) -> dict:
    if issue_id == "uncategorized-expenses":
        query = repo.uncategorized_expenses(db).order_by(Transaction.date.desc(), Transaction.id.desc())
        return {"issue_id": issue_id, "transactions": [tx_read(tx) for tx in query.limit(500).all()]}
    if issue_id == "missing-merchants":
        return {"issue_id": issue_id, "transactions": [tx_read(tx) for tx in repo.missing_merchants(db).limit(500).all()]}
    if issue_id == "duplicate-transactions":
        return {"issue_id": issue_id, "duplicate_groups": _duplicate_groups(db)}
    if issue_id == "unmatched-transfers":
        return {"issue_id": issue_id, "transfer_pairs": _transfer_pairs(db, datetime.now())}
    if issue_id == "unallocated-reimbursements":
        query = unallocated_reimbursements_query(db, datetime.now())
        transactions = query.limit(200).all() if query is not None else []
        return {"issue_id": issue_id, "transactions": [tx_read(tx) for tx in transactions]}
    raise NotFoundError(tr("errors.audit_issue_not_found"))


def _duplicate_groups(db: Session) -> list[dict]:
    rows = repo.duplicate_groups(db).order_by(func.count(Transaction.id).desc()).limit(100).all()
    return [
        {
            "key": f"{row.account_id}-{row.date.isoformat()}-{row.type}-{row.merchant}-{row.amount}-{row.currency}",
            "count": int(row.count),
            "transactions": [tx_read(tx) for tx in repo.duplicate_group_transactions(db, row)],
        }
        for row in rows
    ]


def _transfer_pairs(db: Session, now: datetime) -> list[dict]:
    pairs = []
    seen: set[tuple[int, int]] = set()
    sorties, entrees = _transfer_candidates(db, now)
    for sortie in sorties:
        for match in strict_matches(sortie, entrees)[:5]:
            key = (sortie.id, match.id)
            if key in seen:
                continue
            seen.add(key)
            pairs.append({"sortie": tx_read(sortie), "entree": tx_read(match)})
            if len(pairs) >= 100:
                return pairs
    return pairs
