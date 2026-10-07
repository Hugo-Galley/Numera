"""align recurring transactions currency with their account currency

Revision ID: 7d3f9a21c8b4
Revises: 8cf9c97ea492
Create Date: 2026-10-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "7d3f9a21c8b4"
down_revision: Union[str, None] = "8cf9c97ea492"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Les récurrences d'investissement (DCA) ont pu hériter de la devise du titre (USD)
    # au lieu de celle du compte : on réaligne sur la devise du compte.
    op.execute(
        """
        UPDATE recurring_transactions
        SET currency = (SELECT currency FROM accounts WHERE accounts.id = recurring_transactions.account_id)
        WHERE currency != (SELECT currency FROM accounts WHERE accounts.id = recurring_transactions.account_id)
        """
    )


def downgrade() -> None:
    pass
