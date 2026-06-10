"""add asset allocation fields to investment transactions

Revision ID: 0143092e142d
Revises: a4e6fa22a008
Create Date: 2026-05-28 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0143092e142d'
down_revision: Union[str, Sequence[str], None] = 'a4e6fa22a008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('investment_transactions', sa.Column('asset_class', sa.String(length=32), nullable=True))
    op.add_column('investment_transactions', sa.Column('sector', sa.String(length=64), nullable=True))
    op.add_column('investment_transactions', sa.Column('geographic_zone', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('investment_transactions', 'geographic_zone')
    op.drop_column('investment_transactions', 'sector')
    op.drop_column('investment_transactions', 'asset_class')
