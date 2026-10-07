"""mode de valorisation d'un compte : positions × cours ou relevés (snapshots)

Revision ID: d6a3e9f4c2b5
Revises: c5f2d8e3b1a4
Create Date: 2026-10-07 21:00:00.000000

"""
import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d6a3e9f4c2b5"
down_revision: Union[str, None] = "c5f2d8e3b1a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CRYPTO_PAIR = re.compile(r"^[A-Z0-9]{2,10}-(EUR|USD|USDT|USDC|GBP|CHF|BTC|ETH)$")


def upgrade() -> None:
    with op.batch_alter_table("accounts") as batch:
        batch.add_column(sa.Column("valuation_mode", sa.String(length=12), nullable=False, server_default="positions"))

    # Les comptes qui ne contiennent que des paires crypto (BTC-EUR…) restent valorisés par relevés
    conn = op.get_bind()
    for name in ("coinbase", "ledger", "binance", "kraken", "bitpanda"):
        conn.execute(
            sa.text("UPDATE accounts SET valuation_mode = 'snapshot' WHERE type = 'investissement' AND lower(name) LIKE :n"),
            {"n": f"%{name}%"},
        )
    tickers: dict[int, list[str]] = {}
    for account_id, ticker in conn.execute(sa.text("SELECT account_id, ticker FROM portfolio_holdings")):
        tickers.setdefault(account_id, []).append((ticker or "").upper())
    for account_id, symbols in tickers.items():
        if symbols and all(CRYPTO_PAIR.match(s) for s in symbols):
            conn.execute(sa.text("UPDATE accounts SET valuation_mode = 'snapshot' WHERE id = :id"), {"id": account_id})


def downgrade() -> None:
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("valuation_mode")
