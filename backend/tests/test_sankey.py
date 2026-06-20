from datetime import datetime
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction

def _tx(account_id: int, date: datetime, merchant: str, amount: float, type: str, category_id: int | None = None):
    return Transaction(
        account_id=account_id,
        date=date,
        month_label="Janvier 2026",
        type=type,
        merchant=merchant,
        category_id=category_id,
        amount=amount,
        original_amount=amount,
        currency="EUR",
        running_balance=1000.0,
        is_transfer=False
    )

def test_sankey_flow_nodes_grouping_and_sorting(client, db_session):
    # 1. Create a current account
    account = Account(name="Courant", type="courant", currency="EUR", active=True)
    db_session.add(account)
    db_session.flush()

    # 2. Create Categories with Groups
    # Group: Fixe
    cat_transport = Category(name="Transports", type="depense", group="Fixe", color="#ff0000")
    cat_abonnement = Category(name="Abonnement", type="depense", group="Fixe", color="#00ff00")
    # Group: Loisirs
    cat_cadeaux = Category(name="Cadeaux", type="depense", group="Loisirs", color="#0000ff")
    cat_sortie = Category(name="Sortie", type="depense", group="Loisirs", color="#ffff00")
    # No Group
    cat_nourriture = Category(name="Nourriture", type="depense", group=None, color="#ff00ff")

    db_session.add_all([cat_transport, cat_abonnement, cat_cadeaux, cat_sortie, cat_nourriture])
    db_session.flush()

    # 3. Create Transactions for January 2026
    # Income (to have a budget flow)
    t_income = _tx(account.id, datetime(2026, 1, 1, 10, 0), "Salaire", 1000.0, "Entree")
    # Expenses for "Fixe" (Total: 195 + 19 = 214)
    t_transp = _tx(account.id, datetime(2026, 1, 2, 10, 0), "Train", 195.0, "Sortie", cat_transport.id)
    t_abon = _tx(account.id, datetime(2026, 1, 3, 10, 0), "Netflix", 19.0, "Sortie", cat_abonnement.id)
    # Expenses for "Loisirs" (Total: 104 + 52 = 156)
    t_cad = _tx(account.id, datetime(2026, 1, 4, 10, 0), "FNAC", 104.0, "Sortie", cat_cadeaux.id)
    t_sort = _tx(account.id, datetime(2026, 1, 5, 10, 0), "Cinema", 52.0, "Sortie", cat_sortie.id)
    # Ungrouped expense
    t_nour = _tx(account.id, datetime(2026, 1, 6, 10, 0), "KFC", 57.0, "Sortie", cat_nourriture.id)

    db_session.add_all([t_income, t_transp, t_abon, t_cad, t_sort, t_nour])
    db_session.commit()

    # 4. Call Sankey Endpoint
    resp = client.get("/analytics/sankey", params={"month": 1, "year": 2026})
    assert resp.status_code == 200
    data = resp.json()

    # Get node list and links
    nodes = data["nodes"]
    links = data["links"]

    # Verify nodes structure
    node_names = [n["name"] for n in nodes]
    
    # "Budget" must be present
    assert "Budget" in node_names
    # Groups must be present
    assert "Fixe" in node_names
    assert "Loisirs" in node_names
    # Categories must be present
    assert "Transports" in node_names
    assert "Abonnement" in node_names
    assert "Cadeaux" in node_names
    assert "Sortie" in node_names
    assert "Nourriture" in node_names

    # Check relative positioning of grouped categories.
    # Group "Fixe" is larger (214.0) than Group "Loisirs" (156.0).
    # Since we sort groups by value descending, "Fixe" should appear before "Loisirs".
    # And categories under each group must be adjacent and sorted by value descending:
    # "Transports" (195.0) then "Abonnement" (19.0)
    # "Cadeaux" (104.0) then "Sortie" (52.0)
    
    fixe_idx = node_names.index("Fixe")
    loisirs_idx = node_names.index("Loisirs")
    
    transports_idx = node_names.index("Transports")
    abonnement_idx = node_names.index("Abonnement")
    cadeaux_idx = node_names.index("Cadeaux")
    sortie_idx = node_names.index("Sortie")
    nourriture_idx = node_names.index("Nourriture")

    # Categories under "Fixe" must be grouped together
    assert transports_idx < abonnement_idx
    # Categories under "Loisirs" must be grouped together
    assert cadeaux_idx < sortie_idx
    
    # Since "Fixe" comes before "Loisirs", its categories should come before "Loisirs"'s categories
    assert abonnement_idx < cadeaux_idx

    # Check link values
    # Budget -> Fixe link
    budget_idx = node_names.index("Budget")
    budget_to_fixe_links = [l for l in links if l["source"] == budget_idx and l["target"] == fixe_idx]
    assert len(budget_to_fixe_links) == 1
    assert budget_to_fixe_links[0]["value"] == 214.0

    # Budget -> Loisirs link
    budget_to_loisirs_links = [l for l in links if l["source"] == budget_idx and l["target"] == loisirs_idx]
    assert len(budget_to_loisirs_links) == 1
    assert budget_to_loisirs_links[0]["value"] == 156.0

    # Budget -> Nourriture link (direct link)
    budget_to_nourriture_links = [l for l in links if l["source"] == budget_idx and l["target"] == nourriture_idx]
    assert len(budget_to_nourriture_links) == 1
    assert budget_to_nourriture_links[0]["value"] == 57.0
