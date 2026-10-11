"""remboursements : créances, affectations et offset des transactions

Revision ID: d4f2a8c6e1b9
Revises: c3e9a1d7f5b2
"""
import sqlalchemy as sa
from alembic import op

revision = "d4f2a8c6e1b9"
down_revision = "c3e9a1d7f5b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reimbursement_claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transaction_id", sa.Integer(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("debtor", sa.String(length=120), nullable=False),
        sa.Column("expected_amount", sa.Float(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_reimbursement_claims_id", "reimbursement_claims", ["id"])
    op.create_index("ix_reimbursement_claims_transaction_id", "reimbursement_claims", ["transaction_id"])

    op.create_table(
        "reimbursement_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("reimbursement_claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entree_transaction_id", sa.Integer(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("claim_id", "entree_transaction_id", name="uq_reimbursement_allocation"),
    )
    op.create_index("ix_reimbursement_allocations_id", "reimbursement_allocations", ["id"])
    op.create_index("ix_reimbursement_allocations_claim_id", "reimbursement_allocations", ["claim_id"])
    op.create_index("ix_reimbursement_allocations_entree_transaction_id", "reimbursement_allocations", ["entree_transaction_id"])

    with op.batch_alter_table("transactions") as batch:
        batch.add_column(sa.Column("reimbursement_offset", sa.Float(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch:
        batch.drop_column("reimbursement_offset")
    op.drop_table("reimbursement_allocations")
    op.drop_table("reimbursement_claims")
