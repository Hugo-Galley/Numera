"""Identité des expositions : fusion des positions d'un même titre ou d'un même indice (spec sur-exposition § 1)."""

import pytest

from app.domain.exposure.identity import Holding, Kind, group_exposures


def _holding(
    id: int,
    ticker: str,
    value_eur: float,
    *,
    kind: Kind = "fund",
    account_id: int = 1,
    isin: str | None = None,
    name: str | None = None,
    profile_id: int | None = None,
    exposure_profile_id: int | None = None,
    index_name: str | None = None,
) -> Holding:
    return Holding(
        id=id,
        account_id=account_id,
        ticker=ticker,
        isin=isin,
        name=name or ticker,
        value_eur=value_eur,
        kind=kind,
        profile_id=profile_id,
        exposure_profile_id=exposure_profile_id,
        index_name=index_name,
    )


def test_same_crypto_on_two_accounts_is_one_exposure():
    groups = group_exposures(
        [
            _holding(1, "BTC-USD", 207.04, kind="crypto", account_id=8, name="Bitcoin"),
            _holding(2, "btc-usd ", 460.56, kind="crypto", account_id=9, name="Bitcoin"),
        ]
    )

    assert len(groups) == 1
    group = groups[0]
    assert group.value_eur == pytest.approx(667.60)
    assert len(group.holdings) == 2
    assert group.kind == "crypto"
    assert group.key == "exp:BTC-USD"
    assert [h.id for h in group.holdings] == [2, 1]


def test_same_isin_with_different_tickers_merges():
    groups = group_exposures(
        [
            _holding(1, "CW8.PA", 100.0, isin="LU1681043599"),
            _holding(2, "CW8", 50.0, isin="LU1681043599"),
        ]
    )

    assert len(groups) == 1


def test_two_funds_same_index_merge():
    groups = group_exposures(
        [
            _holding(
                1,
                "WPEA.PA",
                4729.18,
                name="iShares MSCI World Swap PEA UCI",
                profile_id=10,
                index_name="MSCI World",
            ),
            _holding(2, "CW8.PA", 3806.58, name="Amundi MSCI World", profile_id=11, index_name="MSCI World"),
        ]
    )

    assert len(groups) == 1
    assert groups[0].name == "iShares MSCI World Swap PEA UCI"
    assert groups[0].key == "exp:WPEA.PA"
    assert groups[0].value_eur == pytest.approx(8535.76)


def test_same_profile_merges():
    groups = group_exposures([_holding(1, "A", 10.0, profile_id=3), _holding(2, "B", 20.0, profile_id=3)])

    assert len(groups) == 1


def test_synthetic_merges_with_its_physical_reference():
    groups = group_exposures(
        [
            _holding(1, "A", 100.0, profile_id=1),
            _holding(2, "B", 200.0, profile_id=2, exposure_profile_id=1),
        ]
    )

    assert len(groups) == 1


def test_two_synthetics_on_same_reference_merge():
    groups = group_exposures(
        [
            _holding(1, "A", 100.0, profile_id=1, exposure_profile_id=5),
            _holding(2, "B", 200.0, profile_id=2, exposure_profile_id=5),
        ]
    )

    assert len(groups) == 1


def test_sp500_and_world_stay_apart_by_default():
    holdings = [
        _holding(1, "SP5", 100.0, profile_id=1, index_name="S&P 500"),
        _holding(2, "CW8", 200.0, profile_id=2, index_name="MSCI World"),
    ]

    assert len(group_exposures(holdings)) == 2
    # Deux indices connus et différents : jamais la même exposition, quoi que dise la règle de repli
    assert len(group_exposures(holdings, same_fund=lambda a, b: True)) == 2


def test_unknown_index_on_one_side_lets_the_fallback_decide():
    holdings = [
        _holding(1, "SP5", 100.0, profile_id=1, index_name="S&P 500"),
        _holding(2, "XYZ", 200.0, profile_id=2, index_name=None),
    ]

    assert len(group_exposures(holdings)) == 2
    assert len(group_exposures(holdings, same_fund=lambda a, b: True)) == 1


def test_direct_stock_never_merges_with_fund():
    groups = group_exposures(
        [
            _holding(1, "AAPL", 100.0, kind="direct", index_name="MSCI World"),
            _holding(2, "CW8", 200.0, index_name="MSCI World"),
        ],
        same_fund=lambda a, b: True,
    )

    assert len(groups) == 2


def test_zero_value_holding_ignored():
    groups = group_exposures([_holding(1, "AAPL", 0.0, kind="direct"), _holding(2, "MSFT", 50.0, kind="direct")])

    assert len(groups) == 1
    assert [h.id for h in groups[0].holdings] == [2]


def test_groups_sorted_by_value_desc():
    groups = group_exposures(
        [
            _holding(1, "AAPL", 10.0, kind="direct"),
            _holding(2, "MSFT", 30.0, kind="direct"),
            _holding(3, "NVDA", 20.0, kind="direct"),
        ]
    )

    assert [g.key for g in groups] == ["exp:MSFT", "exp:NVDA", "exp:AAPL"]


def test_empty_portfolio():
    assert group_exposures([]) == []
