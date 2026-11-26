import json
from pathlib import Path

import pytest

from app.domain import etf_normalize
from app.domain.etf_normalize import country_code, is_equity_line, sector_label


@pytest.mark.parametrize(
    ("label", "code"),
    [
        ("United States", "USA"),
        ("États-Unis", "USA"),
        ("Etats-Unis", "USA"),
        ("united states of america", "USA"),
        ("Grande-Bretagne", "GBR"),
        ("United Kingdom", "GBR"),
        ("Korea (South)", "KOR"),
        ("South Korea", "KOR"),
        ("Corée du Sud", "KOR"),
        ("Taiwan", "TWN"),
        ("Taïwan", "TWN"),
        ("Hong Kong", "HKG"),
        ("Japon", "JPN"),
        ("Japan", "JPN"),
        ("  france ", "FRA"),
        ("Allemagne", "DEU"),
        ("Switzerland", "CHE"),
        ("Netherlands", "NLD"),
        ("Pays-Bas", "NLD"),
        ("Russian Federation", "RUS"),
        ("China", "CHN"),
        ("India", "IND"),
        ("Saudi Arabia", "SAU"),
        ("Arabie saoudite", "SAU"),
        ("UAE", "ARE"),
    ],
)
def test_country_code_resolves_known_labels(label: str, code: str) -> None:
    assert country_code(label) == code


@pytest.mark.parametrize("label", [None, "", "  ", "Other", "Autre", "Others", "-", "Atlantis", "N/A"])
def test_country_code_unknown_is_none(label: str | None) -> None:
    assert country_code(label) is None


def test_country_referential_is_wide_and_alpha3() -> None:
    data = json.loads(Path(etf_normalize.__file__).with_name("country_codes.json").read_text("utf-8"))
    assert len(data) >= 60
    for code in ("USA", "JPN", "FRA", "GBR", "CHN", "IND", "BRA", "ZAF", "KOR", "TWN", "HKG", "SAU", "ARE"):
        assert code in data
    assert all(len(c) == 3 and c.isupper() for c in data)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Information Technology", "Technologie"),
        ("Financials", "Finance"),
        ("Health Care", "Santé"),
        ("Industrials", "Industrie"),
        ("Consumer Discretionary", "Consommation discrétionnaire"),
        ("Consumer Staples", "Biens de consommation"),
        ("Communication", "Services de communication"),
        ("Communication Services", "Services de communication"),
        ("Energy", "Énergie"),
        ("Materials", "Matériaux"),
        ("Utilities", "Services aux collectivités"),
        ("Real Estate", "Immobilier"),
        # Yahoo assetProfile
        ("Technology", "Technologie"),
        ("Financial Services", "Finance"),
        ("Healthcare", "Santé"),
        ("Consumer Cyclical", "Consommation discrétionnaire"),
        ("Consumer Defensive", "Biens de consommation"),
        ("Basic Materials", "Matériaux"),
        # clés Yahoo topHoldings
        ("financial_services", "Finance"),
        ("consumer_cyclical", "Consommation discrétionnaire"),
        ("realestate", "Immobilier"),
        ("basic_materials", "Matériaux"),
        # justETF (français)
        ("Technologie", "Technologie"),
        ("Finance", "Finance"),
        ("Soins de santé", "Santé"),
        ("Consommation cyclique", "Consommation discrétionnaire"),
        ("Biens de consommation de base", "Biens de consommation"),
        ("Télécommunications", "Services de communication"),
        ("Matières premières", "Matériaux"),
        ("Matériaux de base", "Matériaux"),
        ("Services publics", "Services aux collectivités"),
        ("Énergie", "Énergie"),
        ("Energie", "Énergie"),
        ("Immobilier", "Immobilier"),
        ("Industrie", "Industrie"),
        ("  INFORMATION TECHNOLOGY ", "Technologie"),
    ],
)
def test_sector_label_maps_to_french(label: str, expected: str) -> None:
    assert sector_label(label) == expected


@pytest.mark.parametrize("label", [None, "", "Unknown", "Autre", "Cash and/or Derivatives"])
def test_sector_label_unknown(label: str | None) -> None:
    assert sector_label(label) == "Non renseigné"


@pytest.mark.parametrize(
    ("asset_class", "type_", "expected"),
    [
        ("Equity", None, True),
        ("Equity", "EQUITY_ORDINARY", True),
        (None, "EQUITY_ORDINARY", True),
        ("Actions", None, True),
        (None, None, True),
        ("Cash", None, False),
        ("Money Market", None, False),
        ("Futures", None, False),
        ("FX", None, False),
        ("Cash Collateral and Margins", None, False),
        ("Equity", "CASH", False),
        (None, "FX_FORWARD", False),
        (None, "FUTURE", False),
        ("Liquidités", None, False),
        ("Equity", "Cashflow Growth", True),
        ("Equity", "Liquid Assets Fund", True),
        ("Equity", "Forward Looking Equity", True),
        ("Equity", "Reporting Co", True),
        ("Bonds", None, True),
        ("Fixed Income", None, True),
        ("Dérivés", None, False),
        ("derives", None, False),
        ("Contrats à terme", None, False),
        ("Trésorerie", None, False),
        ("Swap", None, False),
        ("Margin", None, False),
        ("Repo", None, False),
        ("Currency", None, False),
        ("Derivative", None, False),
    ],
)
def test_is_equity_line(asset_class: str | None, type_: str | None, expected: bool) -> None:
    assert is_equity_line(asset_class, type_) is expected
