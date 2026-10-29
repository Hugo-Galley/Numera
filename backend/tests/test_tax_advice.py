"""LDDS, LEP et conseil « où placer ton prochain euro »."""
from app.domain.tax import allocation_advice, ldds_status, lep_status
from app.domain.tax_rules import rules_for


def _card(kind, remaining, account_id=1, name=None):
    return {"kind": kind, "account_id": account_id, "account_name": name or kind.upper(), "remaining": remaining}


def test_ldds_lep_ceilings():
    rules = rules_for(2026)
    assert rules.ldds_ceiling == 12_000
    assert rules.lep_ceiling == 10_000
    assert rules_for(2025).ldds_ceiling == 12_000


def test_ldds_and_lep_status_room():
    rules = rules_for(2026)
    ldds = ldds_status(9_000, rules)
    assert ldds["remaining"] == 3_000 and ldds["ceiling"] == 12_000 and ldds["alerts"] == []
    lep = lep_status(10_200, rules)
    assert lep["remaining"] == 0
    assert any("intérêts capitalisés" in a for a in lep["alerts"])
    assert any("revenus" in a for a in lep_status(500, rules)["alerts"])  # rappel de la condition de revenus


def test_advice_low_buffer_prefers_lep():
    advice = allocation_advice([_card("livret_a", 20_000, 1), _card("lep", 4_000, 2), _card("pea", 50_000, 3)], 1.0, 30)
    assert advice[0]["kind"] == "lep" and advice[0]["account_id"] == 2 and advice[0]["rank"] == 1
    assert [a["rank"] for a in advice] == list(range(1, len(advice) + 1))
    assert "1" in advice[0]["reason"]  # le nombre de mois est cité


def test_advice_skips_full_livrets():
    advice = allocation_advice([_card("lep", 0, 1), _card("livret_a", 0, 2), _card("ldds", 500, 3)], 2.0, 11)
    assert advice[0]["kind"] == "ldds"


def test_advice_buffer_ok_goes_to_pea():
    advice = allocation_advice([_card("livret_a", 5_000, 1), _card("pea", 80_000, 2)], 8.0, 11)
    assert advice[0]["kind"] == "pea" and advice[0]["account_id"] == 2
    assert all(a["kind"] != "livret_a" for a in advice)


def test_advice_no_pea_suggests_opening():
    advice = allocation_advice([_card("livret_a", 5_000, 1)], 8.0, 11)
    pea = next(a for a in advice if a["kind"] == "pea")
    assert pea["account_id"] is None and "5 ans" in pea["reason"]


def test_advice_per_only_high_tmi():
    cards = [_card("pea", 10_000, 1), _card("assurance_vie", None, 2)]
    assert all(a["kind"] != "per" for a in allocation_advice(cards, 8.0, 11))
    assert any(a["kind"] == "per" for a in allocation_advice(cards, 8.0, 30))


def test_advice_ends_with_av_or_cto():
    assert allocation_advice([_card("pea", 0, 1)], 8.0, 11)[-1]["kind"] == "assurance_vie"
    last = allocation_advice([_card("pea", 0, 1), _card("assurance_vie", None, 2), _card("cto", None, 3)], 8.0, 11)[-1]
    assert last["kind"] == "cto" and last["account_id"] == 3


def test_overview_exposes_advice_and_ldds_card(client):
    resp = client.post("/accounts", json={"name": "LDDS", "type": "epargne", "currency": "EUR", "tax_wrapper": "ldds"})
    assert resp.status_code == 201, resp.text
    overview = client.get("/tax/overview").json()
    assert any(w["kind"] == "ldds" and w["ceiling"] == 12_000 for w in overview["wrappers"])
    assert overview["allocation_advice"], overview
    assert overview["allocation_advice"][0]["rank"] == 1
