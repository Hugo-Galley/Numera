"""FK des liens et récurrences : ON DELETE SET NULL comme dans les modèles

Les migrations d'origine avaient créé ces contraintes sans ON DELETE : avec
PRAGMA foreign_keys=ON, supprimer une opération d'investissement liée à un
virement (DCA récurrent) échouait en FOREIGN KEY constraint failed.

Revision ID: e5a1c7d3f9b2
Revises: d4f2a8c6e1b9
"""
from alembic import op

revision = "e5a1c7d3f9b2"
down_revision = "d4f2a8c6e1b9"
branch_labels = None
depends_on = None

# (table, contrainte, colonne, table référencée)
FKS = [
    ("transactions", "fk_transactions_linked_transaction", "linked_transaction_id", "transactions"),
    ("transactions", "fk_tx_linked_itx", "linked_investment_transaction_id", "investment_transactions"),
    ("transactions", "fk_transactions_recurring_transaction_id", "recurring_transaction_id", "recurring_transactions"),
    ("transactions", "fk_transactions_merchant_id_merchants", "merchant_id", "merchants"),
    ("investment_transactions", "fk_itx_linked_tx", "linked_transaction_id", "transactions"),
    ("investment_transactions", "fk_itx_recurring_tx", "recurring_transaction_id", "recurring_transactions"),
]


def _recreate(ondelete: str | None) -> None:
    for table in ("transactions", "investment_transactions"):
        with op.batch_alter_table(table) as batch_op:
            for t, name, column, referent in FKS:
                if t != table:
                    continue
                batch_op.drop_constraint(name, type_="foreignkey")
                batch_op.create_foreign_key(name, referent, [column], ["id"], ondelete=ondelete)


def upgrade() -> None:
    _recreate("SET NULL")


def downgrade() -> None:
    _recreate(None)
