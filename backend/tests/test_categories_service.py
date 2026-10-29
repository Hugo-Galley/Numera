"""Services catégories et tags, sans HTTP."""
from datetime import datetime

import pytest

from app.core.errors import ConflictError, InvalidOperationError, NotFoundError
from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.categorization_rule import CategorizationRule
from app.models.category import Category
from app.models.merchant import Merchant
from app.models.salary_config import SalaryConfig
from app.models.tag import Tag
from app.models.transaction import Transaction
from app.schemas.category import CategoryCreate
from app.schemas.tag import TagCreate, TagUpdate
from app.services.budget import categories as category_service
from app.services.budget import tags as tag_service


def test_delete_category_detaches_every_reference(db_session):
    db = db_session
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    category = Category(name="Courses", type="depense")
    db.add_all([account, category])
    db.flush()
    date = datetime(2026, 10, 1)
    tx = Transaction(account_id=account.id, date=date, month_label=month_label_from_date(date), type="Sortie",
                     merchant="CARREFOUR", amount=10.0, original_amount=10.0, currency="EUR",
                     running_balance=-10.0, category_id=category.id)
    rule = CategorizationRule(pattern="CARREFOUR", category_id=category.id)
    merchant = Merchant(name="Carrefour", category_id=category.id)
    salary = SalaryConfig(salary_account_id=account.id, net_salary=2500.0,
                          salary_category_id=category.id, ticket_category_id=category.id)
    db.add_all([tx, rule, merchant, salary])
    db.commit()

    category_service.delete_category(db, category.id)
    db.expire_all()

    assert db.get(Category, category.id) is None
    assert db.get(Transaction, tx.id).category_id is None
    assert db.get(CategorizationRule, rule.id).category_id is None
    assert db.get(Merchant, merchant.id).category_id is None
    salary = db.get(SalaryConfig, salary.id)
    assert salary.salary_category_id is None and salary.ticket_category_id is None


def test_create_duplicate_category_is_conflict(db_session):
    category_service.create_category(db_session, CategoryCreate(name="Loisirs", type="depense"))
    with pytest.raises(ConflictError) as exc:
        category_service.create_category(db_session, CategoryCreate(name="Loisirs", type="depense"))
    assert exc.value.to_content()["detail"]["code"] == "category_already_exists"


def test_delete_unknown_category_is_structured_not_found(db_session):
    with pytest.raises(NotFoundError) as exc:
        category_service.delete_category(db_session, 404)
    assert exc.value.to_content()["detail"]["context"] == {"category_id": 404}


def test_duplicate_tag_name_is_invalid_operation(db_session):
    tag_service.create_tag(db_session, TagCreate(name="Vacances", color="#123456"))
    with pytest.raises(InvalidOperationError, match="Tag name already exists"):
        tag_service.create_tag(db_session, TagCreate(name="Vacances", color="#654321"))


def test_renaming_tag_to_existing_name_is_invalid_operation(db_session):
    tag_service.create_tag(db_session, TagCreate(name="A", color="#123456"))
    b = tag_service.create_tag(db_session, TagCreate(name="B", color="#123456"))
    with pytest.raises(InvalidOperationError):
        tag_service.update_tag(db_session, b.id, TagUpdate(name="A"))


def test_unknown_tag_is_not_found(db_session):
    with pytest.raises(NotFoundError, match="Tag not found"):
        tag_service.delete_tag(db_session, 1)
    assert db_session.query(Tag).count() == 0
