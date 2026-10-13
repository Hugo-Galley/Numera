"""FK des liens et récurrences : ON DELETE SET NULL comme dans les modèles

Les migrations d'origine avaient créé ces contraintes sans ON DELETE : avec
PRAGMA foreign_keys=ON, supprimer une opération d'investissement liée à un
virement (DCA récurrent) échouait en FOREIGN KEY constraint failed.

Revision ID: e5a1c7d3f9b2
Revises: d4f2a8c6e1b9
"""
from alembic import op
import sqlalchemy as sa

revision = "e5a1c7d3f9b2"
down_revision = "d4f2a8c6e1b9"
branch_labels = None
depends_on = None

NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}

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
    conn = op.get_bind()
    for table in ("transactions", "investment_transactions"):
        meta = sa.MetaData(naming_convention=NAMING_CONVENTION)
        t = sa.Table(table, meta, autoload_with=conn)
        existing_constraint_names = {c.name for c in t.constraints if c.name}

        with op.batch_alter_table(table, naming_convention=NAMING_CONVENTION) as batch_op:
            for t_name, name, column, referent in FKS:
                if t_name != table:
                    continue
                if name in existing_constraint_names:
                    batch_op.drop_constraint(name, type_="foreignkey")
                batch_op.create_foreign_key(name, referent, [column], ["id"], ondelete=ondelete)


def upgrade() -> None:
    _recreate("SET NULL")


def downgrade() -> None:
    _recreate(None)
