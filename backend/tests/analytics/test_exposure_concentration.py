"""Nombre de paris indépendants et blocs de lignes corrélées (domain/exposure/concentration.py)."""

from app.domain.exposure.concentration import Block, correlation_blocks, effective_bets


def _identity(n: int) -> list[list[float | None]]:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def test_independent_lines_count_as_inverse_hhi() -> None:
    assert effective_bets([1, 1, 1, 1], _identity(4)) == 4.0


def test_everything_moving_together_is_one_bet() -> None:
    rho: list[list[float | None]] = [[1.0] * 4 for _ in range(4)]
    assert effective_bets([1, 1, 1, 1], rho) == 1.0


def test_two_equal_weights_half_correlated() -> None:
    assert effective_bets([1, 1], [[1, 0.5], [0.5, 1]]) == 1.33


def test_empty_portfolio_has_no_bet() -> None:
    assert effective_bets([], []) == 0.0


def test_zero_weights_have_no_bet() -> None:
    assert effective_bets([0, 0], _identity(2)) == 0.0


def test_single_line_is_one_bet() -> None:
    assert effective_bets([5], [[1]]) == 1.0


def test_negative_correlation_counts_as_zero() -> None:
    assert effective_bets([1, 1], [[1, -0.9], [-0.9, 1]]) == 2.0


def test_unknown_correlation_counts_as_zero_and_diagonal_is_one() -> None:
    assert effective_bets([1, 1], [[None, None], [None, 0.2]]) == 2.0


def _crypto_tech() -> tuple[list[str], list[float], list[list[float | None]]]:
    keys = ["BTC", "ETH", "AAPL", "MSFT"]
    weights = [4.0, 3.0, 2.0, 1.0]
    rho: list[list[float | None]] = [
        [1.0, 0.86, 0.3, 0.3],
        [0.86, 1.0, 0.3, 0.3],
        [0.3, 0.3, 1.0, 0.82],
        [0.3, 0.3, 0.82, 1.0],
    ]
    return keys, weights, rho


def test_blocks_crypto_and_tech() -> None:
    keys, weights, rho = _crypto_tech()

    blocks = correlation_blocks(keys, weights, rho)

    assert blocks == [
        Block(("BTC", "ETH"), weight_pct=70.0, mean_rho=0.86),
        Block(("AAPL", "MSFT"), weight_pct=30.0, mean_rho=0.82),
    ]


def test_average_linkage_does_not_chain() -> None:
    rho: list[list[float | None]] = [[1.0, 0.9, 0.5], [0.9, 1.0, 0.9], [0.5, 0.9, 1.0]]

    blocks = correlation_blocks(["A", "B", "C"], [1.0, 1.0, 1.0], rho)

    assert [block.keys for block in blocks] == [("A", "B")]
    assert blocks[0].mean_rho == 0.9


def test_unknown_correlation_counts_as_zero_in_linkage() -> None:
    rho: list[list[float | None]] = [[1.0, 0.9, None], [0.9, 1.0, 0.9], [None, 0.9, 1.0]]

    blocks = correlation_blocks(["A", "B", "C"], [1.0, 1.0, 1.0], rho)

    assert [block.keys for block in blocks] == [("A", "B")]


def test_threshold_is_configurable() -> None:
    keys, weights, rho = _crypto_tech()

    blocks = correlation_blocks(keys, weights, rho, threshold=0.25)

    assert len(blocks) == 1
    assert set(blocks[0].keys) == {"BTC", "ETH", "AAPL", "MSFT"}
    assert blocks[0].weight_pct == 100.0


def test_single_exposure_has_no_block() -> None:
    assert correlation_blocks(["A"], [1.0], [[1.0]]) == []


def test_empty_portfolio_has_no_block() -> None:
    assert correlation_blocks([], [], []) == []
