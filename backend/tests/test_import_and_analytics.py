from datetime import datetime
import csv
import io

from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.category import Category
from app.models.investment_transaction import InvestmentTransaction


def test_import_solde_initial_and_duplicates(client):
    account_resp = client.post(
        "/accounts",
        json={"name": "Compte courant", "type": "courant", "currency": "EUR", "color": None},
    )
    assert account_resp.status_code == 201
    account_id = account_resp.json()["id"]

    csv_content = "\n".join(
        [
            "Date;Mois;Type;Commercant;Categorie;Montant;Solde Compte",
            "01/01/2026 00:00;Janvier;Type;Solde initial;;1000,00;1000,00",
            "02/01/2026 00:00;Janvier;Entrée;Salaire;Salaire;2000,00;3000,00",
            "03/01/2026 00:00;Janvier;Sortie;KFC;Nourriture;20,00;2980,00",
        ]
    )

    files = {"file": ("import.csv", csv_content.encode("utf-8"), "text/csv")}
    data = {"account_id": str(account_id), "create_missing_categories": "true"}

    first = client.post("/import/commit", data=data, files=files)
    assert first.status_code == 200
    body = first.json()
    assert body["imported"] == 3
    assert body["errors"] == 0

    files2 = {"file": ("import.csv", csv_content.encode("utf-8"), "text/csv")}
    second = client.post("/import/commit", data=data, files=files2)
    assert second.status_code == 200
    body2 = second.json()
    assert body2["imported"] == 0
    assert body2["skipped"] == 3

    jan_budget = client.get("/analytics/budget", params={"month": 1, "year": 2026})
    assert jan_budget.status_code == 200
    budget = jan_budget.json()
    assert budget["revenus_totaux"] == 2000.0
    assert budget["depenses_totales"] == 20.0
    assert budget["revenus_apres_depenses"] == 1980.0


def test_investment_and_top_merchants_analytics(client, db_session):
    current = Account(name="Courant", type="courant", currency="EUR", active=True)
    invest = Account(name="PEA", type="investissement", currency="EUR", active=True)
    db_session.add_all([current, invest])

    cat_food = Category(name="Nourriture", type="depense")
    db_session.add(cat_food)
    db_session.flush()

    client.post(
        "/transactions",
        json={
            "account_id": current.id,
            "date": "2026-01-02T12:00:00",
            "type": "Sortie",
            "merchant": "KFC",
            "category_id": cat_food.id,
            "amount": 25,
            "note": None,
        },
    )
    client.post(
        "/transactions",
        json={
            "account_id": current.id,
            "date": "2026-01-03T12:00:00",
            "type": "Sortie",
            "merchant": "KFC",
            "category_id": cat_food.id,
            "amount": 10,
            "note": None,
        },
    )
    client.post(
        "/transactions",
        json={
            "account_id": current.id,
            "date": "2026-01-04T12:00:00",
            "type": "Sortie",
            "merchant": "CGR",
            "category_id": cat_food.id,
            "amount": 30,
            "note": None,
        },
    )

    db_session.add_all(
        [
            InvestmentTransaction(account_id=invest.id, date=datetime(2026, 1, 2, 10, 0), type="versement", amount=1000, original_amount=1000, currency="EUR"),
            InvestmentTransaction(account_id=invest.id, date=datetime(2026, 1, 3, 10, 0), type="versement", amount=500, original_amount=500, currency="EUR"),
            InvestmentTransaction(account_id=invest.id, date=datetime(2026, 1, 4, 10, 0), type="retrait", amount=200, original_amount=200, currency="EUR"),
            BalanceSnapshot(account_id=invest.id, date=datetime(2026, 1, 5, 10, 0), current_value=1500, is_zero_point=False),
        ]
    )

    db_session.commit()

    merchants = client.get("/analytics/top-merchants", params={"month": 1, "year": 2026, "limit": 5})
    assert merchants.status_code == 200
    items = merchants.json()["items"]
    assert items[0]["merchant"] == "KFC"
    assert items[0]["total"] == 35.0

    investments = client.get("/analytics/investments")
    assert investments.status_code == 200
    body = investments.json()
    assert body["total_net_invested"] == 1300.0
    assert body["total_current_value"] == 1500.0
    assert body["total_gain_eur"] == 200.0

    timeseries = client.get("/analytics/timeseries", params={"year": 2026, "account_id": current.id})
    assert timeseries.status_code == 200
    ts = timeseries.json()
    assert len(ts["monthly_flows"]) > 0
    assert ts["monthly_flows"][0]["expense"] == 65.0

def test_patch_investment_transaction_and_snapshot(client):
    account = client.post(
        "/accounts",
        json={"name": "Assurance Vie", "type": "investissement", "currency": "EUR", "color": None},
    ).json()

    tx = client.post(
        "/investment-transactions",
        json={"account_id": account["id"], "date": "2026-02-01T10:00:00", "type": "versement", "amount": 1000, "note": None},
    ).json()
    patched_tx = client.patch(f"/investment-transactions/{tx['id']}", json={"amount": 1200, "type": "retrait"})
    assert patched_tx.status_code == 200
    assert patched_tx.json()["amount"] == 1200.0
    assert patched_tx.json()["type"] == "retrait"

    snap_a = client.post(
        "/balance-snapshots",
        json={"account_id": account["id"], "date": "2026-02-02T10:00:00", "current_value": 1400, "is_zero_point": True},
    ).json()
    snap_b = client.post(
        "/balance-snapshots",
        json={"account_id": account["id"], "date": "2026-02-03T10:00:00", "current_value": 1500, "is_zero_point": False},
    ).json()

    patched_snap = client.patch(f"/balance-snapshots/{snap_b['id']}", json={"is_zero_point": True})
    assert patched_snap.status_code == 200
    snapshots = client.get("/balance-snapshots", params={"account_id": account["id"]}).json()
    zero_points = [s for s in snapshots if s["is_zero_point"]]
    assert len(zero_points) == 1
    assert zero_points[0]["id"] == snap_b["id"]


def test_investment_detailed_tracking_and_set_zero_point(client):
    account = client.post(
        "/accounts",
        json={"name": "PEA Long Terme", "type": "investissement", "currency": "EUR", "color": None},
    ).json()

    client.post(
        "/balance-snapshots",
        json={"account_id": account["id"], "date": "2026-01-01T09:00:00", "current_value": 1000, "is_zero_point": True},
    )
    client.post(
        "/investment-transactions",
        json={"account_id": account["id"], "date": "2026-01-02T09:00:00", "type": "versement", "amount": 200, "note": None},
    )
    client.post(
        "/investment-transactions",
        json={"account_id": account["id"], "date": "2026-01-03T09:00:00", "type": "retrait", "amount": 50, "note": None},
    )
    client.post(
        "/balance-snapshots",
        json={"account_id": account["id"], "date": "2026-01-10T09:00:00", "current_value": 1400, "is_zero_point": False},
    )

    detail = client.get(f"/analytics/investments/{account['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["baseline"]["value"] == 1000.0
    assert body["totals"]["total_verse"] == 200.0
    assert body["totals"]["total_retire"] == 50.0
    assert body["totals"]["net_invested"] == 1150.0
    assert body["totals"]["current_value"] == 1400.0

    reset = client.post(
        "/balance-snapshots/set-zero-point",
        json={"account_id": account["id"], "current_value": 1400, "date": "2026-01-15T09:00:00", "note": "Reset base"},
    )
    assert reset.status_code == 201
    snapshots = client.get("/balance-snapshots", params={"account_id": account["id"]}).json()
    zero_points = [s for s in snapshots if s["is_zero_point"]]
    assert len(zero_points) == 1
    assert zero_points[0]["current_value"] == 1400.0

    perf_history = client.get(f"/analytics/investments/{account['id']}/performance-history")
    assert perf_history.status_code == 200
    perf_items = perf_history.json()["items"]
    assert len(perf_items) >= 1
    assert perf_items[-1]["is_zero_point"] is True

    allocation = client.get("/analytics/investments-allocation")
    assert allocation.status_code == 200
    assert allocation.json()["total_current_value"] >= 1400.0


def test_investments_analytics_filtering(client):
    account = client.post(
        "/accounts",
        json={"name": "PEA Filter", "type": "investissement", "currency": "EUR", "color": None},
    ).json()

    # Transaction in January
    client.post(
        "/investment-transactions",
        json={"account_id": account["id"], "date": "2026-01-15T10:00:00", "type": "versement", "amount": 1000, "note": None},
    )
    # Transaction in February
    client.post(
        "/investment-transactions",
        json={"account_id": account["id"], "date": "2026-02-15T10:00:00", "type": "versement", "amount": 500, "note": None},
    )

    # All transactions
    all_resp = client.get("/analytics/investments")
    item = next(i for i in all_resp.json()["items"] if i["account_id"] == account["id"])
    assert item["total_verse"] == 1500.0

    # January only
    jan_resp = client.get("/analytics/investments", params={"month": 1, "year": 2026})
    item_jan = next(i for i in jan_resp.json()["items"] if i["account_id"] == account["id"])
    assert item_jan["total_verse"] == 1000.0

    # February only
    feb_resp = client.get("/analytics/investments", params={"month": 2, "year": 2026})
    item_feb = next(i for i in feb_resp.json()["items"] if i["account_id"] == account["id"])
    assert item_feb["total_verse"] == 500.0


def test_investment_transaction_rejected_before_zero_point(client):
    account = client.post(
        "/accounts",
        json={"name": "CTO", "type": "investissement", "currency": "EUR", "color": None},
    ).json()

    client.post(
        "/balance-snapshots",
        json={"account_id": account["id"], "date": "2026-03-10T10:00:00", "current_value": 2000, "is_zero_point": True},
    )

    rejected = client.post(
        "/investment-transactions",
        json={"account_id": account["id"], "date": "2026-03-01T10:00:00", "type": "versement", "amount": 100, "note": None},
    )
    assert rejected.status_code == 422
    assert "before active zero point" in rejected.json()["detail"]


def test_export_csv_numbers_compatibility(client):
    account = client.post(
        "/accounts",
        json={"name": "Compte export", "type": "courant", "currency": "EUR", "color": None},
    ).json()

    client.post(
        "/transactions",
        json={
            "account_id": account["id"],
            "date": "2026-04-01T10:00:00",
            "type": "Solde Initial",
            "merchant": "Banque",
            "category_id": None,
            "amount": 1000,
            "note": None,
        },
    )

    response = client.get("/export/transactions.csv", params={"account_ids": str(account["id"])})
    assert response.status_code == 200
    reader = csv.reader(io.StringIO(response.text))
    rows = list(reader)
    assert rows[0] == ["Compte", "Date", "Mois", "Type", "Commercant", "Categorie", "Montant", "Solde Compte"]
    assert rows[1][0] == "Compte export"
    assert rows[1][3] == "Type"
    assert rows[1][6] == "1000.00"


def test_export_csv_multiple_accounts(client):
    acc1 = client.post(
        "/accounts",
        json={"name": "Compte 1", "type": "courant", "currency": "EUR", "color": None},
    ).json()
    acc2 = client.post(
        "/accounts",
        json={"name": "Compte 2", "type": "courant", "currency": "EUR", "color": None},
    ).json()

    r1 = client.post(
        "/transactions",
        json={
            "account_id": acc1["id"],
            "date": "2026-04-01T10:00:00",
            "type": "Sortie",
            "merchant": "Merchant 1",
            "category_id": None,
            "amount": 10,
            "note": None,
        },
    )
    assert r1.status_code == 201

    r2 = client.post(
        "/transactions",
        json={
            "account_id": acc2["id"],
            "date": "2026-04-02T10:00:00",
            "type": "Sortie",
            "merchant": "Merchant 2",
            "category_id": None,
            "amount": 20,
            "note": None,
        },
    )
    assert r2.status_code == 201

    # Export both
    ids = f"{acc1['id']},{acc2['id']}"
    response = client.get("/export/transactions.csv", params={"account_ids": ids})
    assert response.status_code == 200
    reader = csv.reader(io.StringIO(response.text))
    rows = list(reader)
    
    # Header + 2 rows
    assert len(rows) == 3
    # Check account names
    account_names = [row[0] for row in rows[1:]]
    assert "Compte 1" in account_names
    assert "Compte 2" in account_names


def test_export_csv_includes_investments(client):
    acc = client.post(
        "/accounts",
        json={"name": "Compte Titres", "type": "investissement", "currency": "EUR", "color": None},
    ).json()

    # Regular transactions use /transactions
    # Investment transactions use /investment-transactions
    inv_r = client.post(
        "/investment-transactions",
        json={
            "account_id": acc["id"],
            "date": "2026-04-10T10:00:00",
            "type": "versement",
            "amount": 500,
            "note": "Achat ETF",
        },
    )
    assert inv_r.status_code == 201

    response = client.get("/export/transactions.csv", params={"account_ids": str(acc["id"])})
    assert response.status_code == 200
    reader = csv.reader(io.StringIO(response.text))
    rows = list(reader)
    
    # Header + 1 row
    assert len(rows) == 2
    assert rows[1][0] == "Compte Titres"
    assert rows[1][3] == "versement"
    assert rows[1][4] == "Investissement"
    assert rows[1][6] == "500.00"


def test_timeseries_empty_year_defaults(client):
    account = client.post(
        "/accounts",
        json={"name": "Compte vide", "type": "courant", "currency": "EUR", "color": None},
    ).json()
    response = client.get("/analytics/timeseries", params={"year": 2030, "account_id": account["id"]})
    assert response.status_code == 200
    body = response.json()
    assert len(body["monthly_flows"]) == 0
    assert body["balance_points"] == []


def test_calc_diff_with_negative_values():
    from app.api.analytics.reports import calc_diff

    # From negative (-500) to positive (+200): +700 improvement -> +140%
    diff, pct = calc_diff(200.0, -500.0)
    assert diff == 700.0
    assert pct == 140.0

    # Deficit decreased: from -200 to -100 (+100 improvement) -> +50%
    diff, pct = calc_diff(-100.0, -200.0)
    assert diff == 100.0
    assert pct == 50.0

    # Deficit increased: from -200 to -300 (-100 worsening) -> -50%
    diff, pct = calc_diff(-300.0, -200.0)
    assert diff == -100.0
    assert pct == -50.0


def test_kpi_history_endpoint(client, db_session):
    account = Account(name="KPI Account", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.commit()

    # Add transactions in two months
    client.post(
        "/transactions",
        json={
            "account_id": account.id,
            "date": "2026-01-10T12:00:00",
            "type": "Entree",
            "merchant": "Salary",
            "amount": 3000,
        },
    )
    client.post(
        "/transactions",
        json={
            "account_id": account.id,
            "date": "2026-01-15T12:00:00",
            "type": "Sortie",
            "merchant": "Groceries",
            "amount": 800,
        },
    )
    client.post(
        "/transactions",
        json={
            "account_id": account.id,
            "date": "2026-02-10T12:00:00",
            "type": "Entree",
            "merchant": "Salary",
            "amount": 3200,
        },
    )
    client.post(
        "/transactions",
        json={
            "account_id": account.id,
            "date": "2026-02-20T12:00:00",
            "type": "Sortie",
            "merchant": "Rent",
            "amount": 1000,
        },
    )

    response = client.get("/analytics/kpi-history", params={"months_count": 12})
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) >= 2

    # Check Jan 2026 and Feb 2026 items
    jan_item = next((i for i in items if i["year"] == 2026 and i["month"] == 1), None)
    assert jan_item is not None
    assert jan_item["revenus"] == 3000.0
    assert jan_item["depenses"] == 800.0
    assert jan_item["cash_flow"] == 2200.0

    feb_item = next((i for i in items if i["year"] == 2026 and i["month"] == 2), None)
    assert feb_item is not None
    assert feb_item["revenus"] == 3200.0
    assert feb_item["depenses"] == 1000.0
    assert feb_item["cash_flow"] == 2200.0


def test_fk_set_null_on_delete_category_and_recurring(client, db_session):
    from app.models.recurring_transaction import RecurringTransaction
    from app.models.transaction import Transaction

    account = Account(name="FK Account", type="courant", currency="EUR", active=True)
    cat = Category(name="TempCat", type="depense")
    db_session.add_all([account, cat])
    db_session.commit()

    rec = RecurringTransaction(
        account_id=account.id,
        category_id=cat.id,
        name="Sub",
        amount=50,
        type="Sortie",
        frequency="monthly",
        day_of_month=1,
        start_date=datetime(2026, 1, 1),
    )
    db_session.add(rec)
    db_session.commit()

    tx = Transaction(
        account_id=account.id,
        date=datetime(2026, 1, 1),
        month_label="Janvier",
        type="Sortie",
        merchant="Sub",
        amount=50,
        original_amount=50,
        currency="EUR",
        category_id=cat.id,
        recurring_transaction_id=rec.id,
        running_balance=100,
    )
    db_session.add(tx)
    db_session.commit()

    # Delete category via API
    del_cat = client.delete(f"/categories/{cat.id}")
    assert del_cat.status_code == 204

    # Delete recurring transaction via API
    del_rec = client.delete(f"/recurring-transactions/{rec.id}")
    assert del_rec.status_code == 200

    # Verify transaction still exists and its foreign keys were set to NULL
    db_session.refresh(tx)
    assert tx.category_id is None
    assert tx.recurring_transaction_id is None
