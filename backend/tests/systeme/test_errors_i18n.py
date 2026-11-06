"""Erreurs métier dans la langue de l'interface (Accept-Language)."""
import pytest

from app.core.errors import BusinessRuleError
from app.core.i18n import set_language
from app.domain.csv_import import parse_csv

EN = {"Accept-Language": "en"}


@pytest.fixture(autouse=True)
def _reset_language():
    set_language("fr")
    yield
    set_language("fr")


def test_not_found_follows_language(client):
    assert client.get("/accounts/9999").json()["detail"]["detail"] == "Compte introuvable"
    res = client.get("/accounts/9999", headers=EN)
    assert res.status_code == 404 and res.json()["detail"]["detail"] == "Account not found"


def test_login_error_follows_language(client):
    data = {"username": "nobody", "password": "wrong-password"}
    assert client.post("/auth/token", data=data).json()["detail"] == "Identifiant ou mot de passe incorrect"
    assert client.post("/auth/token", data=data, headers=EN).json()["detail"] == "Incorrect username or password"


def test_english_origin_message_now_french_by_default(client):
    assert client.post("/tags", json={"name": "a"}).status_code in (200, 201)
    assert client.post("/tags", json={"name": "a"}).json()["detail"] == "Ce nom de tag existe déjà"
    assert client.post("/tags", json={"name": "a"}, headers=EN).json()["detail"] == "Tag name already exists"


def test_message_with_variables_in_both_languages():
    content = b"Foo;Bar\n1;2\n"
    with pytest.raises(BusinessRuleError) as fr:
        parse_csv(content)
    assert fr.value.detail.startswith("Colonnes manquantes dans le fichier : ")
    set_language("en")
    with pytest.raises(BusinessRuleError) as en:
        parse_csv(content)
    assert en.value.detail.startswith("Missing columns in the file: ")
    assert "Expected columns: Date, Commercant, Montant" in en.value.detail
