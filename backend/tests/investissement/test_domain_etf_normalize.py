import json
from pathlib import Path

import pytest

from app.domain import etf_normalize
from app.domain.etf_normalize import INDEX_NAMES, country_code, index_for_fund_name, is_equity_line, sector_label
from app.domain.isin import is_valid_isin


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
        ("Collateral", None, False),
        ("Liquidity Fund", None, False),
        ("FX FORWARD", None, False),
        ("Forward", None, False),
        ("Non-Deliverable Forward", None, False),
        ("Forward Looking Equity", None, True),
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


@pytest.mark.parametrize(
    ("name", "index"),
    [
        ("Amundi MSCI World Swap UCITS ETF EUR Acc", "MSCI World"),
        ("iShares MSCI World Swap PEA UCITS ETF", "MSCI World"),
        ("Lyxor PEA Monde (MSCI World) UCITS ETF", "MSCI World"),
        ("State Street® SPDR® MSCI World UCITS ETF (Acc)", "MSCI World"),
        ("Amundi PEA S&P 500 UCITS ETF Acc", "S&P 500"),
        ("BNP Paribas Easy S&P 500 UCITS ETF EUR C", "S&P 500"),
        ("State Street® SPDR® S&P® 500 UCITS ETF (Dist)", "S&P 500"),
        ("Amundi Nasdaq-100 Swap UCITS ETF EUR Acc", "Nasdaq 100"),
        ("Amundi PEA Nasdaq 100 UCITS ETF", "Nasdaq 100"),
        ("Amundi PEA MSCI Emerging Markets UCITS ETF", "MSCI Emerging Markets"),
        ("iShares Core MSCI EM UCITS ETF USD (Acc)", "MSCI Emerging Markets"),
        ("Amundi Core Stoxx Europe 600 UCITS ETF Acc", "STOXX Europe 600"),
        ("Amundi CAC 40 UCITS ETF Dist", "CAC 40"),
        ("iShares MSCI ACWI UCITS ETF", "MSCI ACWI"),
        ("Amundi MSCI Europe UCITS ETF Acc", "MSCI Europe"),
        ("Xtrackers MSCI USA Swap UCITS ETF 1C", "MSCI USA"),
        ("iShares S&P 500 EUR Hedged UCITS ETF (Acc)", "S&P 500"),
    ],
)
def test_index_for_fund_name(name, index):
    assert index_for_fund_name(name) == index


@pytest.mark.parametrize(
    "name",
    [
        "iShares MSCI World Small Cap UCITS ETF",
        "Amundi MSCI World ESG Leaders UCITS ETF",
        "Amundi MSCI World SRI Climate Paris Aligned UCITS ETF",
        "Amundi MSCI World Information Technology UCITS ETF",
        "Xtrackers MSCI World ex USA UCITS ETF",
        "iShares S&P 500 Information Technology Sector UCITS ETF",
        "Invesco S&P 500 Equal Weight UCITS ETF",
        "Amundi ETF Leveraged MSCI USA Daily UCITS ETF",
        "Amundi Nasdaq-100 Daily (2x) Leveraged UCITS ETF",
        "Amundi CAC 40 Daily (-1x) Inverse UCITS ETF",
        "iShares Core MSCI Emerging Markets IMI UCITS ETF",
        "iShares MSCI ACWI IMI UCITS ETF",
        "Carmignac Patrimoine A EUR Acc",
        "MSCI",
        "",
    ],
)
def test_index_for_fund_name_refuses_variants_of_an_index(name):
    """Un indice dérivé (taille, secteur, ESG, levier…) n'a pas la composition de l'indice de base."""
    assert index_for_fund_name(name) is None


def test_every_index_has_one_reference_fund_and_no_figure():
    references = json.loads((Path(__file__).parents[2] / "app" / "domain" / "index_references.json").read_text(encoding="utf-8"))
    assert set(references) == set(INDEX_NAMES)
    assert all(is_valid_isin(isin) for isin in references.values())
