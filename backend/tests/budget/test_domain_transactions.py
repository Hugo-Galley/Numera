from app.domain.transactions import net_amount
from app.models.transaction import Transaction


def test_net_amount_subtracts_reimbursement_offset():
    assert net_amount(Transaction(amount=100.0, reimbursement_offset=30.0)) == 70.0


def test_net_amount_without_offset_is_gross_amount():
    assert net_amount(Transaction(amount=42.5, reimbursement_offset=None)) == 42.5
