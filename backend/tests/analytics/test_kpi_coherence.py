"""Une seule définition par KPI : mêmes données → mêmes chiffres partout (audit PR 8)."""
from datetime import datetime

from app.domain.finance import month_label_from_date
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.category import Category
from app.models.transaction import Transaction


def _account(db, name, type_):
    acc = Account(name=name, type=type_, currency="EUR", active=True)
    db.add(acc)
    db.commit()
    return acc


def _tx(db, acc, type_, amount, date, merchant="X", category=None, **extra):
    t = Transaction(
        account_id=acc.id, date=date, month_label=month_label_from_date(date), type=type_, merchant=merchant,
        amount=amount, original_amount=amount, currency="EUR", running_balance=0.0,
        category_id=category.id if category else None, **extra,
    )
    db.add(t)
    db.commit()
    return t


def test_depenses_reelles_ignore_les_sorties_categorisees_hors_courant_et_epargne(client, db_session):
    """Sortie « Investissement » d'une assurance-vie : ni dépense ni retranchement (M8)."""
    courant = _account(db_session, "Courant", "courant")
    av = _account(db_session, "AV", "assurance_vie")
    invest = Category(name="Investissement", type="depense")
    db_session.add(invest)
    db_session.commit()
    _tx(db_session, courant, "Entree", 3000.0, datetime(2026, 10, 5), "SALAIRE")
    _tx(db_session, courant, "Sortie", 1000.0, datetime(2026, 10, 6), "LOYER")
    _tx(db_session, av, "Sortie", 800.0, datetime(2026, 10, 7), "Rachat", category=invest)

    data = client.get("/analytics/budget", params={"period": "month", "year": 2026, "month": 10}).json()
    kpi = data.get("kpis", data)
    assert kpi["depenses_totales"] == 1000.0
    assert kpi["depenses_reelles"] == 1000.0
    assert kpi["taux_epargne"] == 66.67


def test_capital_net_investi_identique_partout_avec_une_vente(client, db_session):
    """Entree « Vente fonds » = retrait : /investments, /investments/{id} et la courbe donnent le même capital (I6)."""
    av = _account(db_session, "AV releves", "assurance_vie")
    db_session.add_all([
        BalanceSnapshot(account_id=av.id, date=datetime(2026, 1, 1), current_value=10000.0, is_zero_point=True),
        BalanceSnapshot(account_id=av.id, date=datetime(2026, 4, 1), current_value=9000.0),
    ])
    db_session.commit()
    _tx(db_session, av, "Entree", 500.0, datetime(2026, 2, 10), "Virement")
    _tx(db_session, av, "Entree", 2000.0, datetime(2026, 3, 10), "Vente fonds X")

    totals = client.get(f"/analytics/investments/{av.id}").json()["totals"]
    overview = next(i for i in client.get("/analytics/investments").json()["items"] if i["account_id"] == av.id)
    history = client.get(f"/analytics/investments/{av.id}/performance-history").json()["items"]
    assert totals["net_invested"] == overview["net_invested"] == history[-1]["net_invested"] == 8500.0


def test_rapport_mensuel_vue_compte_une_seule_definition_du_taux_d_epargne(client, db_session):
    """Sans dépense exceptionnelle, taux « hors exceptionnel » == taux officiel (M9)."""
    courant = _account(db_session, "Courant", "courant")
    epargne_cat = Category(name="Epargne", type="depense")
    loyer = Category(name="Loyer", type="depense")
    db_session.add_all([epargne_cat, loyer])
    db_session.commit()
    _tx(db_session, courant, "Entree", 3000.0, datetime(2026, 10, 5), "SALAIRE")
    _tx(db_session, courant, "Sortie", 1500.0, datetime(2026, 10, 6), "LOYER", category=loyer)
    _tx(db_session, courant, "Sortie", 500.0, datetime(2026, 10, 7), "VERS EPARGNE", category=epargne_cat)

    report = client.get("/analytics/monthly-report", params={"month": 10, "year": 2026, "account_id": courant.id}).json()
    assert report["savings_rate_excl_exceptional"] == report["savings_rate"]
    assert report["savings"] == round(report["savings_rate"] / 100 * 3000.0, 2)


def test_ecarter_un_insight_ne_masque_que_ce_mois_et_cet_objet(client, db_session):
    """La clé d'un insight inclut le mois et l'objet : « Grosse dépense isolée » d'un mois n'éteint pas les autres (M18)."""
    courant = _account(db_session, "Courant", "courant")
    _tx(db_session, courant, "Entree", 3000.0, datetime(2026, 9, 2), "SALAIRE")
    _tx(db_session, courant, "Entree", 3000.0, datetime(2026, 10, 2), "SALAIRE")
    _tx(db_session, courant, "Sortie", 900.0, datetime(2026, 9, 10), "TV")
    _tx(db_session, courant, "Sortie", 900.0, datetime(2026, 10, 10), "VELO")
    _tx(db_session, courant, "Sortie", 900.0, datetime(2026, 10, 11), "FOUR")

    def large(month):
        items = client.get("/analytics/insights", params={"month": month, "year": 2026}).json()["insights"]
        return [i for i in items if i["title"] == "Grosse dépense isolée"]

    oct_items = large(10)
    assert len(oct_items) == 2 and len({i["key"] for i in oct_items}) == 2
    client.post("/analytics/insights/dismiss", json={"key": oct_items[0]["key"]})
    assert len(large(10)) == 1
    assert len(large(9)) == 1
