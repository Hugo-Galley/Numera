from sqlalchemy.orm import Session

from app.services.budget import reimbursements as remb
from app.core.errors import NotFoundError
from app.models.categorization_rule import CategorizationRule
from app.models.transaction import Transaction
from app.repositories.budget import categorization_rules as repo
from app.schemas.categorization_rule import CategorizationRuleCreate, CategorizationRuleUpdate
from app.services.budget.balances import recalculate_running_balances


def _require(db: Session, rule_id: int) -> CategorizationRule:
    rule = repo.get(db, rule_id)
    if not rule:
        raise NotFoundError("Rule not found")
    return rule


def list_rules(db: Session) -> list[CategorizationRule]:
    return repo.list_by_priority(db)


def create_rule(db: Session, payload: CategorizationRuleCreate) -> CategorizationRule:
    rule = CategorizationRule(**payload.model_dump())
    repo.add(db, rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(db: Session, rule_id: int, payload: CategorizationRuleUpdate) -> CategorizationRule:
    rule = _require(db, rule_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("pattern", "") is None:  # colonne NOT NULL : un `null` explicite est ignoré
        del data["pattern"]
    if data.get("priority", 0) is None:
        del data["priority"]
    for key, value in data.items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule_id: int) -> None:
    repo.delete(db, _require(db, rule_id))
    db.commit()


def _apply_rule(db: Session, tx: Transaction, rule: CategorizationRule) -> tuple[bool, bool]:
    """Applique une règle à une transaction : (modifiée, solde à recalculer)."""
    changed = balance_changed = False
    if rule.category_id and tx.category_id is None:
        tx.category_id = rule.category_id
        changed = True
    # Une transaction qui porte des remboursements garde son type (cf. services/reimbursements.py)
    if rule.transaction_type and tx.type != rule.transaction_type and not remb.has_reimbursement(db, tx.id):
        tx.type = rule.transaction_type
        changed = balance_changed = True
    if rule.merchant_name and tx.merchant != rule.merchant_name:
        tx.merchant = rule.merchant_name
        changed = True
    return changed, balance_changed


def _first_matching_rule(tx: Transaction, rules: list[CategorizationRule]) -> CategorizationRule | None:
    for rule in rules:
        pattern = rule.pattern.strip().lower()
        if pattern and (pattern in (tx.merchant or "").lower() or pattern in (tx.note or "").lower()):
            return rule
    return None


def apply_rules_to_transactions(db: Session) -> dict:
    """Applique les règles aux transactions existantes.

    Une catégorie déjà posée n'est jamais écrasée ; les « Solde Initial » et les virements internes
    ne sont pas touchés. Changements et recalcul des soldes sont validés ensemble (rollback sinon).
    """
    rules = repo.list_for_application(db)
    if not rules:
        return {"modified_count": 0}

    modified_count = 0
    affected_balance_account_ids = set()
    for tx in repo.categorizable_transactions(db):
        rule = _first_matching_rule(tx, rules)  # seule la première règle par priorité s'applique
        if rule is None:
            continue
        changed, balance_changed = _apply_rule(db, tx, rule)
        modified_count += changed
        if balance_changed:
            affected_balance_account_ids.add(tx.account_id)

    try:
        db.flush()
        for acc_id in affected_balance_account_ids:
            recalculate_running_balances(db, acc_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"modified_count": modified_count}
