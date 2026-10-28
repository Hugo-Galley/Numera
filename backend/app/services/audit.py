"""Centre d'Actions : agrégation des alertes d'audit, de budget et de suivi."""
import re
import unicodedata
from datetime import date, datetime, timedelta
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.core.backup import backup_status
from app.models.account import Account
from app.models.category import Category
from app.models.categorization_rule import CategorizationRule
from app.schemas.insight import ActionCenterResponse, ActionCenterSummary, ActionItem
from app.models.balance_snapshot import BalanceSnapshot
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction
from app.core import reimbursements as remb
from app.core.logging import get_logger
from app.models.reimbursement import ReimbursementClaim
from app.domain.transactions import tx_sample
from app.core.errors import InternalError
from app.services.analytics.budget import compute_budget_alerts

logger = get_logger(__name__)

_MONTH_NAMES = ("janvier", "février", "mars", "avril", "mai", "juin",
                "juillet", "août", "septembre", "octobre", "novembre", "décembre")


def merchant_key(label: str) -> str:
    """Clé de rapprochement d'un libellé : sans accents, casse, chiffres ni ponctuation."""
    text = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z]+", " ", text).split())


def month_name(label: str) -> str:
    """« 2026-10 » → « octobre 2026 » (FRENCH_MONTHS, sans accents, sert aux libellés stockés)."""
    year, month = label.split("-")
    return f"{_MONTH_NAMES[int(month) - 1]} {year}"


def unallocated_reimbursements_query(db: Session, now: datetime):
    """Remboursements reçus (catégorie « Remboursement… ») non affectés, s'il existe une créance ouverte."""
    has_open_claim = any(
        remb.claim_received(db, claim.id) < claim.expected_amount - remb.EPS
        for claim in db.query(ReimbursementClaim).all()
    )
    if not has_open_claim:
        return None
    return (
        db.query(Transaction)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.type == "Entree",
            Category.name.ilike("Remboursement%"),
            Transaction.reimbursement_offset == 0,
            Transaction.is_transfer.is_(False),
            Transaction.date >= now - timedelta(days=180),
        )
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    )


async def compute_action_center(db: Session) -> ActionCenterResponse:
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
                samples=[tx_sample(tx) for tx in uncategorized_query.limit(5).all()],
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

        # 1.4 Salaire attendu absent (mois non renseigné dans le gestionnaire de salaire)
        from app.core.salary import find_missing_salary_months
        missing_salary_months = find_missing_salary_months(db, now.date())
        if missing_salary_months:
            labels = ", ".join(month_name(label) for label in missing_salary_months)
            actions.append(ActionItem(
                id=f"missing-salary-{missing_salary_months[-1]}",
                type="audit",
                severity="high",
                title="Salaire absent",
                description=(
                    f"Aucun salaire pour {labels}. Renseigne le mois dans le gestionnaire de salaire, "
                    "ou désactive la configuration si tu ne perçois plus ce salaire."
                ),
                action_label="Ouvrir le salaire",
                action_url="/recurring?tab=salary",
                action_type="link",
                metadata={"months": missing_salary_months},
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
                action_url="/audit?vue=virements",
                action_type="link",
                metadata={"issue_id": "unmatched-transfers"}
            ))

        # 1.5 Remboursements reçus non affectés à une créance
        unallocated_query = unallocated_reimbursements_query(db, now)
        unallocated_count = unallocated_query.count() if unallocated_query is not None else 0
        if unallocated_count:
            actions.append(ActionItem(
                id="unallocated-reimbursements",
                type="audit",
                severity="low",
                title="Remboursements à affecter",
                description=f"{unallocated_count} remboursement(s) reçu(s) ne sont rattachés à aucune créance ouverte.",
                action_label="Affecter",
                action_url="/reimbursements",
                action_type="link",
                samples=[tx_sample(tx) for tx in unallocated_query.limit(5).all()],
                metadata={"issue_id": "unallocated-reimbursements"}
            ))

        # --- 2. Budget Actions (New) ---
        current_month = now.month
        current_year = now.year
        alerts = await compute_budget_alerts(year=current_year, month=current_month, account_id=None, db=db)
        
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

        # --- 3. Rule Suggestions ---
        # Une règle ne s'applique qu'à l'import (et via « appliquer à tout ») : elle n'apporte quelque chose
        # que si le marchand a encore des transactions sans catégorie. Virements et récurrences (qui portent
        # leur propre catégorie) ne comptent pas.
        six_months_ago = now - timedelta(days=180)
        candidate_rows = (
            db.query(Transaction.merchant, Transaction.category_id, func.count(Transaction.id))
            .filter(
                Transaction.date >= six_months_ago,
                Transaction.merchant.is_not(None), Transaction.merchant != "",
                Transaction.is_transfer.is_(False),
                Transaction.recurring_transaction_id.is_(None),
                Transaction.type.in_(["Sortie", "Entree"]),
            )
            .group_by(Transaction.merchant, Transaction.category_id)
            .all()
        )
        by_merchant: dict[str, dict] = {}
        for merchant, category_id, count in candidate_rows:
            stats = by_merchant.setdefault(merchant, {"total": 0, "uncategorized": 0, "categories": {}})
            stats["total"] += count
            if category_id is None:
                stats["uncategorized"] += count
            else:
                stats["categories"][category_id] = stats["categories"].get(category_id, 0) + count

        for merchant, stats in sorted(by_merchant.items(), key=lambda kv: -kv[1]["uncategorized"]):
            if stats["total"] < 5 or stats["uncategorized"] == 0:
                continue
            rule_exists = db.query(CategorizationRule).filter(
                or_(
                    func.lower(CategorizationRule.merchant_name) == func.lower(merchant),
                    func.lower(CategorizationRule.pattern) == func.lower(merchant)
                )
            ).first() is not None
            if rule_exists:
                continue
            suggested_cat_id = max(stats["categories"], key=stats["categories"].get) if stats["categories"] else None
            actions.append(ActionItem(
                id=f"suggest-rule-{merchant}",
                type="rule",
                severity="low",
                title=f"Nouvelle règle suggérée : {merchant}",
                description=(
                    f"{stats['uncategorized']} transaction(s) sans catégorie chez '{merchant}' "
                    f"(sur {stats['total']}). Une règle les catégoriserait, ainsi que les prochains imports."
                ),
                action_label="Créer la règle",
                action_url="/classement?tab=rules",
                action_type="modal_rule",
                metadata={"merchant": merchant, "suggested_category_id": suggested_cat_id}
            ))

        # --- 4. Merchant Normalization Suggestions ---
        # Un marchand canonique sert à regrouper plusieurs écritures d'un même commerçant : on ne le propose
        # que si le même nom apparaît sous au moins deux libellés (casse, accents, chiffres, ponctuation).
        unnormalized = (
            db.query(Transaction.merchant, func.count(Transaction.id))
            .filter(Transaction.merchant_id.is_(None), Transaction.merchant.is_not(None), Transaction.merchant != "")
            .group_by(Transaction.merchant)
            .all()
        )
        variants: dict[str, list[tuple[str, int]]] = {}
        for merchant, count in unnormalized:
            key = merchant_key(merchant)
            if key:
                variants.setdefault(key, []).append((merchant, count))
        groups = sorted(
            (sorted(labels, key=lambda lc: -lc[1]) for labels in variants.values() if len(labels) >= 2),
            key=lambda labels: -sum(c for _, c in labels),
        )
        for labels in groups[:5]:
            main_label, _ = labels[0]
            total = sum(c for _, c in labels)
            actions.append(ActionItem(
                id=f"suggest-normalization-{main_label}",
                type="merchant",
                severity="low",
                title=f"Normalisation suggérée : {main_label}",
                description=(
                    f"{len(labels)} écritures pour le même marchand ({', '.join(repr(l) for l, _ in labels[:4])}), "
                    f"{total} transactions. Les regrouper sous un marchand canonique ?"
                ),
                action_label="Normaliser",
                action_url="/classement?tab=merchants",
                action_type="modal_merchant",
                metadata={"merchant": main_label, "count": total, "variants": [l for l, _ in labels]}
            ))

        # --- 4b. Dividendes (comptes titres) ---
        from app.models.portfolio_holding import PortfolioHolding
        account_names = {a.id: a.name for a in db.query(Account.id, Account.name).all()}

        unlinked_rows = (
            db.query(InvestmentTransaction.account_id, func.count(InvestmentTransaction.id))
            .filter(InvestmentTransaction.type == "dividende", InvestmentTransaction.ticker.is_(None))
            .group_by(InvestmentTransaction.account_id)
            .all()
        )
        for acc_id, count in unlinked_rows:
            actions.append(ActionItem(
                id=f"dividends-unlinked-{acc_id}",
                type="investments",
                severity="medium",
                title=f"Dividendes à rattacher à un titre : {account_names.get(acc_id, acc_id)}",
                description=f"{count} dividende(s) ne sont rattachés à aucun titre : rendement et plus-value totale par ligne sont incomplets.",
                action_label="Rattacher",
                action_url=f"/accounts/{acc_id}",
                action_type="link",
                metadata={"account_id": acc_id, "count": count},
            ))

        # Titre distribuant sans dividende depuis plus de 13 mois (réglage manuel, aucun appel externe)
        stale_before = now - timedelta(days=395)
        last_dividend = {
            (acc_id, ticker.upper()): last
            for acc_id, ticker, last in db.query(
                InvestmentTransaction.account_id, InvestmentTransaction.ticker, func.max(InvestmentTransaction.date)
            )
            .filter(InvestmentTransaction.type == "dividende", InvestmentTransaction.ticker.isnot(None))
            .group_by(InvestmentTransaction.account_id, InvestmentTransaction.ticker)
            .all()
        }
        for h in db.query(PortfolioHolding).filter(PortfolioHolding.pays_dividends.is_(True), PortfolioHolding.quantity > 0).all():
            reference = last_dividend.get((h.account_id, h.ticker.upper())) or h.created_at
            if reference < stale_before:
                actions.append(ActionItem(
                    id=f"dividend-missing-{h.account_id}-{h.ticker}",
                    type="investments",
                    severity="low",
                    title=f"Dividende attendu : {h.asset_name}",
                    description=f"Aucun dividende saisi sur {h.ticker} depuis plus de 13 mois. En as-tu reçu un ?",
                    action_label="Saisir un dividende",
                    action_url=f"/accounts/{h.account_id}",
                    action_type="link",
                    metadata={"account_id": h.account_id, "ticker": h.ticker},
                ))

        # --- 4c. Rapprochement : dernier relevé du courtier vs valeur calculée par Numera ---
        from app.core.holdings import replay_account
        from app.core.portfolio import RECONCILIATION_THRESHOLD_PCT, compute_portfolio, uses_positions
        for account in db.query(Account).filter(Account.type == "investissement", Account.active.is_(True)).all():
            try:
                if not uses_positions(account, await replay_account(db, account.id)):
                    continue
                portfolio = await compute_portfolio(db, account, fetch=False)
            except Exception as exc:  # une règle d'audit ne doit jamais casser le Centre d'Actions
                logger.warning(f"Reconciliation skipped for account {account.id}: {exc}")
                continue
            latest = (portfolio["reconciliation"] or [None])[-1]
            if latest and latest["flagged"]:
                actions.append(ActionItem(
                    id=f"reconciliation-gap-{account.id}-{latest['date'][:10]}",
                    type="investments",
                    severity="medium",
                    title=f"Écart avec le relevé du courtier : {account.name}",
                    description=(
                        f"Le relevé du {latest['date'][:10]} indique {latest['snapshot_value']:.2f} {account.currency}, "
                        f"Numera calcule {latest['computed_value']:.2f} ({latest['gap_pct']:+.1f} %, seuil {RECONCILIATION_THRESHOLD_PCT:.0f} %). "
                        "Une opération, des frais ou un dividende manquent probablement."
                    ),
                    action_label="Vérifier le compte",
                    action_url=f"/accounts/{account.id}",
                    action_type="link",
                    metadata={"account_id": account.id, **latest},
                ))

        # --- 4b. Hausses de prix des abonnements ---
        try:
            from app.core.subscription_prices import detect_price_changes, price_change_id

            freq_label = {"monthly": "mois", "quarterly": "trimestre", "yearly": "an"}
            for change in detect_price_changes(db):
                actions.append(ActionItem(
                    id=price_change_id(change),
                    type="subscription",
                    severity="medium",
                    title=f"Hausse de prix : {change.name}",
                    description=(
                        f"Passé de {change.old_amount:.2f} à {change.new_amount:.2f} {change.currency} "
                        f"par {freq_label.get(change.frequency, 'échéance')} le {change.changed_on.strftime('%d/%m/%Y')} "
                        f"({change.delta_pct:+.1f} %), soit {change.annual_impact:.2f} {change.currency} de plus par an. "
                        "Toujours utile à ce prix ?"
                    ),
                    action_label="Voir les abonnements",
                    action_url="/recurring?tab=subscriptions",
                    action_type="link",
                    metadata={
                        "account_id": change.account_id,
                        "old_amount": change.old_amount,
                        "new_amount": change.new_amount,
                        "annual_impact": change.annual_impact,
                    },
                ))
        except Exception as exc:  # une règle d'audit ne doit jamais casser le Centre d'Actions
            logger.warning(f"Subscription price check skipped: {exc}")

        # --- 4bis. Sauvegardes : en retard ou en échec (seulement si elles sont en place) ---
        try:
            backup = backup_status()
            if backup["configured"] and (backup["stale"] or backup["last_error"]):
                last = backup["last_backup_at"]
                when = last.astimezone().strftime("%d/%m/%Y") if last else "jamais"
                description = (
                    f"Dernière sauvegarde réussie : {when}."
                    + (f" Dernière erreur : {backup['last_error']}" if backup["last_error"] else "")
                )
                actions.append(ActionItem(
                    # L'id change avec la dernière sauvegarde : masquer l'alerte ne la fait pas taire pour toujours
                    id=f"backup-failing-{last.strftime('%Y%m%d') if last else 'never'}",
                    type="audit",
                    severity="high",
                    title="Sauvegarde en retard" if backup["stale"] else "Dernière sauvegarde en échec",
                    description=description,
                    action_label="Voir les sauvegardes",
                    action_url="/settings?tab=data",
                    action_type="link",
                ))
        except Exception as exc:  # une règle d'audit ne doit jamais casser le Centre d'Actions
            logger.warning(f"Backup status check skipped: {exc}")

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
        raise InternalError(str(e))
