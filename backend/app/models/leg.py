"""Jambe d'un virement interne : une transaction bancaire ou une opération d'investissement."""
from app.models.investment_transaction import InvestmentTransaction
from app.models.transaction import Transaction

Leg = Transaction | InvestmentTransaction
