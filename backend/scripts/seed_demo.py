from datetime import datetime

from app.core.finance import apply_transaction_to_balance, month_label_from_date
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.name == "Compte courant").first()
        if not account:
            account = Account(name="Compte courant", type="courant", currency="EUR", color="#0ea5e9")
            db.add(account)
            db.flush()

        defaults = [
            ("Salaire", "revenu"),
            ("Nourriture", "depense"),
            ("Abonnement", "depense"),
            ("Sortie", "depense"),
        ]
        categories = {c.name: c for c in db.query(Category).all()}
        for name, ctype in defaults:
            if name not in categories:
                cat = Category(name=name, type=ctype)
                db.add(cat)
                db.flush()
                categories[name] = cat

        if db.query(Transaction).filter(Transaction.account_id == account.id).count() > 0:
            db.commit()
            print("Demo seed skipped: transactions already exist.")
            return

        tx_rows = [
            (datetime(2026, 1, 1, 0, 0), "Solde Initial", "Banque", None, 666.0),
            (datetime(2026, 1, 2, 9, 0), "Entree", "Entreprise", categories["Salaire"].id, 2200.0),
            (datetime(2026, 1, 5, 12, 0), "Sortie", "Intermarche", categories["Nourriture"].id, 85.35),
            (datetime(2026, 1, 6, 8, 0), "Sortie", "YouTube Premium", categories["Abonnement"].id, 12.99),
            (datetime(2026, 1, 8, 21, 0), "Sortie", "CGR", categories["Sortie"].id, 18.0),
        ]

        balance = 0.0
        for date, tx_type, merchant, category_id, amount in tx_rows:
            balance = apply_transaction_to_balance(balance, tx_type, amount)
            db.add(
                Transaction(
                    account_id=account.id,
                    date=date,
                    month_label=month_label_from_date(date),
                    type=tx_type,
                    merchant=merchant,
                    category_id=category_id,
                    amount=amount,
                    currency="EUR",
                    original_amount=amount,
                    running_balance=balance,
                    note="Demo seed",
                )
            )

        db.commit()
        print("Demo seed completed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
