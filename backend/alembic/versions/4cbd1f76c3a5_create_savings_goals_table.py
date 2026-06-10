"""create_savings_goals_table

Revision ID: 4cbd1f76c3a5
Revises: a1b2c3d4e5f6
Create Date: 2026-05-21 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4cbd1f76c3a5'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('savings_goals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('target_amount', sa.Float(), nullable=False),
        sa.Column('keyword', sa.String(length=50), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('deadline', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_savings_goals_id'), 'savings_goals', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_savings_goals_id'), table_name='savings_goals')
    op.drop_table('savings_goals')
