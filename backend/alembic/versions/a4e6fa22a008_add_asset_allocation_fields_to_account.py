"""add asset allocation fields to account

Revision ID: a4e6fa22a008
Revises: 4cbd1f76c3a5
Create Date: 2026-05-28 20:06:40.102061

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4e6fa22a008'
down_revision: Union[str, Sequence[str], None] = '4cbd1f76c3a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('accounts', sa.Column('asset_class', sa.String(length=32), nullable=True))
    op.add_column('accounts', sa.Column('sector', sa.String(length=64), nullable=True))
    op.add_column('accounts', sa.Column('geographic_zone', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('accounts', 'geographic_zone')
    op.drop_column('accounts', 'sector')
    op.drop_column('accounts', 'asset_class')
