"""stockage des cours, inventaire Point Zéro des positions, frais et devise de prix des opérations

Revision ID: b4e1c7d2a9f3
Revises: 7d3f9a21c8b4
Create Date: 2026-10-07 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b4e1c7d2a9f3"
down_revision: Union[str, None] = "7d3f9a21c8b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Copie figée de market_data.QUOTE_SUFFIX_CURRENCIES (une migration ne doit pas dépendre du code applicatif)
_EUR_SUFFIXES = (".PA", ".AS", ".BR", ".DE", ".F", ".SG", ".MU", ".DU", ".HM", ".BE", ".MI", ".MC", ".VI", ".LS", ".HE", ".IR")


def _guess_currency(ticker: str) -> str:
    t = ticker.upper()
    if t.endswith(("-EUR",)) or t.endswith(_EUR_SUFFIXES):
        return "EUR"
    if t.endswith(".SW"):
        return "CHF"
    if t.endswith(".L"):
        return "GBP"
    return "USD"


def upgrade() -> None:
    op.create_table(
        "security_prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("ticker", "date", name="uq_security_prices_ticker_date"),
    )
    op.create_index("ix_security_prices_id", "security_prices", ["id"])
    op.create_index("ix_security_prices_ticker", "security_prices", ["ticker"])
    op.create_index("ix_security_prices_date", "security_prices", ["date"])

    op.create_table(
        "holding_baseline_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("baseline_date", sa.DateTime(), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("isin", sa.String(length=20), nullable=True),
        sa.Column("asset_name", sa.String(length=120), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("buy_price_avg", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("etf_profile_id", sa.Integer(), sa.ForeignKey("etf_profiles.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_holding_baseline_items_id", "holding_baseline_items", ["id"])
    op.create_index("ix_holding_baseline_items_account_id", "holding_baseline_items", ["account_id"])
    op.create_index("ix_holding_baseline_items_ticker", "holding_baseline_items", ["ticker"])

    with op.batch_alter_table("accounts") as batch:
        batch.add_column(sa.Column("holdings_baseline_date", sa.DateTime(), nullable=True))
    with op.batch_alter_table("portfolio_holdings") as batch:
        batch.add_column(sa.Column("cost_basis_eur", sa.Float(), nullable=True))
    with op.batch_alter_table("investment_transactions") as batch:
        batch.add_column(sa.Column("price_currency", sa.String(length=3), nullable=True))
        batch.add_column(sa.Column("fees", sa.Float(), nullable=True))

    bind = op.get_bind()

    # Devise des lignes sans PRU : on prend la devise de cotation déduite du suffixe du ticker
    # (la recherche devinait « USD » pour toute place hors d'une courte liste, ex. Stuttgart .SG).
    for hid, ticker in bind.execute(sa.text("SELECT id, ticker FROM portfolio_holdings WHERE buy_price_avg IS NULL")).fetchall():
        bind.execute(
            sa.text("UPDATE portfolio_holdings SET currency = :c WHERE id = :id"),
            {"c": _guess_currency(ticker), "id": hid},
        )

    # Les positions existantes deviennent l'inventaire Point Zéro de leur compte, daté du dernier
    # changement connu : les opérations déjà appliquées ne seront pas rejouées.
    accounts = bind.execute(
        sa.text(
            """
            SELECT h.account_id,
                   MAX(h.updated_at),
                   (SELECT MAX(t.date) FROM investment_transactions t
                     WHERE t.account_id = h.account_id AND t.ticker IS NOT NULL AND t.quantity > 0)
            FROM portfolio_holdings h
            GROUP BY h.account_id
            """
        )
    ).fetchall()
    for account_id, last_update, last_trade in accounts:
        cutoff = max(str(d) for d in (last_update, last_trade) if d is not None)
        bind.execute(
            sa.text("UPDATE accounts SET holdings_baseline_date = :d WHERE id = :id"),
            {"d": cutoff, "id": account_id},
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO holding_baseline_items
                    (account_id, baseline_date, ticker, isin, asset_name, quantity, buy_price_avg, currency, etf_profile_id)
                SELECT account_id, :d, ticker, isin, asset_name, quantity, buy_price_avg, currency, etf_profile_id
                FROM portfolio_holdings WHERE account_id = :id AND quantity > 0
                """
            ),
            {"d": cutoff, "id": account_id},
        )


def downgrade() -> None:
    with op.batch_alter_table("investment_transactions") as batch:
        batch.drop_column("fees")
        batch.drop_column("price_currency")
    with op.batch_alter_table("portfolio_holdings") as batch:
        batch.drop_column("cost_basis_eur")
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("holdings_baseline_date")
    op.drop_table("holding_baseline_items")
    op.drop_table("security_prices")
