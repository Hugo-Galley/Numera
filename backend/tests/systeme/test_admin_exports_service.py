"""Administration et export CSV : erreurs métier et rendu, sans HTTP."""
from datetime import datetime

import pytest

from app.core.errors import InvalidOperationError, NotFoundError
from app.domain.exports import csv_safe
from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.admin import McpTokenCreate
from app.services.budget import exports as export_service
from app.services.systeme import admin as admin_service


def test_wrong_current_password_is_400_not_401(db_session):
    with pytest.raises(InvalidOperationError, match="Mot de passe actuel incorrect") as exc:
        admin_service.create_mcp_token(db_session, McpTokenCreate(name="claude", current_password="faux"))
    assert exc.value.status_code == 400


def test_revoke_unknown_token_is_not_found(db_session):
    with pytest.raises(NotFoundError, match="Token introuvable"):
        admin_service.revoke_mcp_token(db_session, 1)


def test_csv_safe_prefixes_formulas():
    assert csv_safe("=HYPERLINK(\"x\")") == "'=HYPERLINK(\"x\")"
    assert csv_safe("-12") == "'-12" and csv_safe("Carrefour") == "Carrefour"


def test_export_neutralizes_formula_injection(db_session):
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.flush()
    date = datetime(2026, 9, 1, 8, 30)
    db_session.add(Transaction(account_id=account.id, date=date, month_label=month_label_from_date(date),
                               type="Sortie", merchant="=cmd|'/C calc'!A0", amount=12.5, original_amount=12.5,
                               currency="EUR", running_balance=-12.5))
    db_session.commit()
    lines = export_service.export_transactions_csv(db_session, None).splitlines()
    assert lines[0] == "Compte,Date,Mois,Type,Commercant,Categorie,Montant,Solde Compte"
    assert lines[1].startswith("Courant,01/09/2026 08:30,") and "'=cmd" in lines[1] and lines[1].endswith("12.50,-12.50")
