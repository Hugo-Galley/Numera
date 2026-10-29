"""Instance de démonstration : construction du jeu fictif (comptes, flux, PEA, assurance-vie)."""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.services.balances import recalculate_running_balances
from app.domain.finance import month_label_from_date
from app.services.investissement.holdings.rebuild import rebuild_holdings
from app.services.systeme.seeds import seed_all
from app.services.transfers import link_pair
from app.models.account import Account
from app.models.balance_snapshot import BalanceSnapshot
from app.models.category import Category
from app.models.etf_profile import EtfProfile
from app.models.investment_transaction import InvestmentTransaction
from app.models.recurring_transaction import RecurringTransaction
from app.models.savings_goal import SavingsGoal
from app.models.security_price import SecurityPrice
from app.models.system_setting import SystemSetting
from app.models.tag import Tag
from app.models.transaction import Transaction

from app.services.systeme.demo.data import (
    BUDGETS, DEMO_MONTHS, DEMO_SEED, EXTRA_CATEGORIES, FIXED_EXPENSES, GROCERIES, HEALTH, OUTINGS, SALARY,
    SALARY_DAY, SECURITIES, SHOPPING, TO_AV, TO_LIVRET, TO_PEA, TRANSFER_DAY, TRANSPORT, _price_on, _price_series,
)
from app.services.systeme.demo.guard import DEMO_STAMP_KEY


class _Builder:
    def __init__(self, db: Session, today: date) -> None:
        self.db = db
        self.today = today
        self.rng = random.Random(DEMO_SEED)
        month = today.month - DEMO_MONTHS
        year = today.year + (month - 1) // 12
        self.start = date(year, (month - 1) % 12 + 1, 1)
        self.categories: dict[str, Category] = {}

    # Petits utilitaires -------------------------------------------------------

    def _when(self, day: date, hour: int = 12) -> datetime:
        return datetime(day.year, day.month, day.day, hour, 0)

    def tx(self, account: Account, day: date, tx_type: str, merchant: str, amount: float,
           category: str | None = None, **extra) -> Transaction:
        when = self._when(day, extra.pop("hour", 12))
        amount = round(amount, 2)
        tx = Transaction(
            account_id=account.id,
            date=when,
            month_label=month_label_from_date(when),
            type=tx_type,
            merchant=merchant,
            category_id=self.categories[category].id if category else None,
            amount=amount,
            currency="EUR",
            original_amount=amount,
            running_balance=0.0,
            **extra,
        )
        self.db.add(tx)
        return tx

    def transfer(self, source: Account, target: Account, day: date, amount: float, label_out: str, label_in: str,
                 **extra) -> None:
        out = self.tx(source, day, "Sortie", label_out, amount, hour=9, **extra)
        into = self.tx(target, day, "Entree", label_in, amount, hour=9)
        self.db.flush()
        link_pair(self.db, out, into, "regular", "manual")

    def months(self):
        current = self.start
        while current <= self.today:
            yield current
            current = date(current.year + current.month // 12, current.month % 12 + 1, 1)

    def day_in(self, month: date, day: int) -> date | None:
        """Jour `day` du mois (borné à la fin du mois), ou None s'il est dans le futur."""
        next_month = date(month.year + month.month // 12, month.month % 12 + 1, 1)
        result = min(date(month.year, month.month, 1) + timedelta(days=day - 1), next_month - timedelta(days=1))
        return result if result <= self.today else None

    # Référentiel --------------------------------------------------------------

    def build_categories(self) -> None:
        self.categories = {c.name: c for c in self.db.query(Category).all()}
        for name, ctype, group, limit in EXTRA_CATEGORIES:
            if name not in self.categories:
                cat = Category(name=name, type=ctype, group=group, monthly_limit=limit)
                self.db.add(cat)
                self.categories[name] = cat
        for name, limit in BUDGETS.items():
            self.categories[name].monthly_limit = limit
        self.db.flush()

    def build_accounts(self) -> dict[str, Account]:
        opened = self.start
        accounts = {
            "courant": Account(name="Compte courant", type="courant", institution="Banque Démo", color="#0ea5e9",
                               is_main=True, opened_at=opened),
            "livret": Account(name="Livret A", type="epargne", institution="Banque Démo", color="#22c55e",
                              tax_wrapper="livret_a", opened_at=opened),
            "pea": Account(name="PEA", type="investissement", institution="Courtier Démo", color="#8b5cf6",
                           tax_wrapper="pea", valuation_mode="positions", opened_at=opened),
            "av": Account(name="Assurance-vie", type="assurance_vie", institution="Assureur Démo", color="#f59e0b",
                          tax_wrapper="assurance_vie", fonds_euros_pct=40.0, fonds_investis_pct=60.0, opened_at=opened),
        }
        self.db.add_all(accounts.values())
        self.db.flush()
        return accounts

    def build_recurring(self, courant: Account, livret: Account) -> dict[str, RecurringTransaction]:
        start = self._when(self.start, 0)
        recurring = {
            "Salaire": RecurringTransaction(
                account_id=courant.id, name="Acme Conseil — Salaire", type="Entree", amount=SALARY,
                category_id=self.categories["Salaire"].id, frequency="monthly", day_of_month=SALARY_DAY,
                start_date=start, is_active=True, auto_generate=False,
            ),
            "Livret": RecurringTransaction(
                account_id=courant.id, name="Virement Livret A", type="Sortie", amount=TO_LIVRET,
                frequency="monthly", day_of_month=TRANSFER_DAY, start_date=start, is_active=True,
                auto_generate=False, transfer_to_account_id=livret.id,
            ),
        }
        for name, category, amount, day, logo in FIXED_EXPENSES:
            recurring[name] = RecurringTransaction(
                account_id=courant.id, name=name, type="Sortie", amount=amount,
                category_id=self.categories[category].id, frequency="monthly", day_of_month=day,
                start_date=start, is_active=True, auto_generate=False, logo=logo,
            )
        self.db.add_all(recurring.values())
        self.db.flush()
        return recurring

    # Comptes ------------------------------------------------------------------

    def build_bank(self, accounts: dict[str, Account], recurring: dict[str, RecurringTransaction], vacation: Tag) -> None:
        courant, livret, av = accounts["courant"], accounts["livret"], accounts["av"]
        rng = self.rng
        self.tx(courant, self.start, "Solde Initial", "Solde initial", 2400.0, hour=0)
        self.tx(livret, self.start, "Solde Initial", "Solde initial", 6500.0, hour=0)

        salary = SALARY
        for index, month in enumerate(self.months()):
            if month.month == 1 and index:
                salary = round(salary * 1.03, 2)  # augmentation annuelle

            def recurring_tx(key: str, day: date, tx_type: str, merchant: str, amount: float, category: str | None):
                rec = recurring[key]
                rec.last_generated_date = self._when(day)
                return self.tx(courant, day, tx_type, merchant, amount, category,
                               is_recurring=True, recurring_transaction_id=rec.id)

            if day := self.day_in(month, SALARY_DAY):
                recurring_tx("Salaire", day, "Entree", "Acme Conseil — Salaire", salary, "Salaire")
            if month.month == 6 and (day := self.day_in(month, 28)):
                self.tx(courant, day, "Entree", "Acme Conseil — Prime annuelle", 1500.0, "Revenus supplementaires")

            for name, category, amount, day_number, _ in FIXED_EXPENSES:
                if day := self.day_in(month, day_number):
                    if name == "EDF":  # facture plus lourde l'hiver
                        amount = {12: 118.0, 1: 124.0, 2: 109.0, 11: 96.0}.get(month.month, 61.0)
                    recurring_tx(name, day, "Sortie", name, amount, category)

            if day := self.day_in(month, TRANSFER_DAY):
                self.transfer(courant, livret, day, TO_LIVRET, "Virement Livret A", "Virement depuis compte courant",
                              is_recurring=True, recurring_transaction_id=recurring["Livret"].id)
                recurring["Livret"].last_generated_date = self._when(day)
                self.transfer(courant, av, day, TO_AV, "Versement assurance-vie", "Versement programmé")

            for count, merchants, low, high, category in (
                (rng.randint(6, 9), GROCERIES, 18, 95, "Nourriture"),
                (rng.randint(3, 6), OUTINGS, 12, 58, "Sortie"),
                (rng.randint(1, 3), SHOPPING, 15, 110, "Shopping"),
            ):
                for _ in range(count):
                    if day := self.day_in(month, rng.randint(1, 28)):
                        self.tx(courant, day, "Sortie", rng.choice(merchants), rng.uniform(low, high), category,
                                hour=rng.randint(8, 21))
            for merchant, low, high in rng.sample(TRANSPORT, rng.randint(0, 2)):
                if day := self.day_in(month, rng.randint(1, 28)):
                    self.tx(courant, day, "Sortie", merchant, rng.uniform(low, high), "Transport")
            if rng.random() < 0.6:
                merchant, low, high = rng.choice(HEALTH)
                if day := self.day_in(month, rng.randint(1, 28)):
                    self.tx(courant, day, "Sortie", merchant, rng.uniform(low, high), "Santé")
                    if (refund := self.day_in(month, day.day + 3)) and refund.month == month.month:
                        self.tx(courant, refund, "Entree", "CPAM — Remboursement", 16.5, "Remboursement (recu)")

            # Temps forts de l'année
            if month.month == 7:
                if day := self.day_in(month, 6):
                    self.transfer(livret, courant, day, 800.0, "Virement vers compte courant", "Virement depuis Livret A")
                for day_number, merchant, amount in ((8, "Airbnb", 720.0), (8, "Air France", 386.0), (15, "Restaurant La Marée", 94.0)):
                    if day := self.day_in(month, day_number):
                        trip = self.tx(courant, day, "Sortie", merchant, amount, "Voyages")
                        trip.tags = [vacation]
            if month.month == 12:
                for day_number in (10, 16, 21):
                    if day := self.day_in(month, day_number):
                        self.tx(courant, day, "Sortie", rng.choice(["Fnac", "Nature & Découvertes", "Galeries Lafayette"]),
                                rng.uniform(40, 130), "Cadeaux (emis)")
                if day := self.day_in(month, 31):
                    self.tx(livret, day, "Interets", "Intérêts Livret A", 168.40, hour=23)
            if index == 9 and (day := self.day_in(month, 14)):
                self.tx(courant, day, "Sortie", "Apple Store", 1499.0, "Achat divers", is_exceptional=True,
                        note="Nouvel ordinateur portable")

        self.db.flush()

    def build_pea(self, pea: Account, courant: Account, prices: dict[str, dict[date, float]]) -> None:
        profiles = {p.ticker: p.id for p in self.db.query(EtfProfile).filter(EtfProfile.ticker.in_(SECURITIES)).all()}
        cash = 0.0

        def add(day: date, tx_type: str, amount: float, **extra) -> InvestmentTransaction:
            nonlocal cash
            amount = round(amount, 2)
            cash += amount if tx_type in ("versement", "dividende") else -amount
            inv = InvestmentTransaction(account_id=pea.id, date=self._when(day, 10), type=tx_type, amount=amount,
                                        currency="EUR", original_amount=amount, **extra)
            self.db.add(inv)
            return inv

        def buy(day: date, ticker: str, quantity: int) -> None:
            name, isin, *_ = SECURITIES[ticker]
            price = _price_on(prices[ticker], day)
            fees = 1.0
            add(day, "achat", quantity * price + fees, ticker=ticker, isin=isin, quantity=quantity, unit_price=price,
                price_currency="EUR", fees=fees, note=name, etf_profile_id=profiles.get(ticker))

        first = self.start
        add(first, "versement", 6000.0, note="Versement initial")
        buy(first, "CW8.PA", 9)
        buy(first, "TTE.PA", 25)

        for month in self.months():
            day = self.day_in(month, TRANSFER_DAY)
            if day is None:
                continue
            out = self.tx(courant, day, "Sortie", "Virement PEA", TO_PEA, hour=9)
            inv = add(day, "versement", TO_PEA, note="Versement mensuel")
            self.db.flush()
            link_pair(self.db, out, inv, "investment", "manual")
            buy_day = day + timedelta(days=1)
            if buy_day > self.today:
                continue
            world = int(cash * 0.8 // _price_on(prices["CW8.PA"], buy_day))
            if world:
                buy(buy_day, "CW8.PA", world)
            emerging = int((cash - 1) // _price_on(prices["PAEEM.PA"], buy_day))
            if month.month % 3 == 0 and emerging:
                buy(buy_day, "PAEEM.PA", emerging)
            if month.month in (1, 4, 6, 10) and (div_day := self.day_in(month, 20)):
                add(div_day, "dividende", 25 * 0.79, ticker="TTE.PA", isin=SECURITIES["TTE.PA"][1],
                    note="Dividende TotalEnergies")
        self.db.flush()

    def build_life_insurance(self, av: Account) -> None:
        """Valorisée par relevés mensuels (fonds euros + unités de compte)."""
        self.tx(av, self.start, "Solde Initial", "Solde initial", 8000.0, hour=0)
        value = 8000.0
        self.db.add(BalanceSnapshot(account_id=av.id, date=self._when(self.start, 0), current_value=value,
                                    note="Point zéro", is_zero_point=True))
        for month in self.months():
            if self.day_in(month, TRANSFER_DAY) is None:
                break
            value = value * (1 + self.rng.gauss(0.004, 0.012)) + TO_AV
            next_month = date(month.year + month.month // 12, month.month % 12 + 1, 1)
            snap_day = min(next_month - timedelta(days=1), self.today)
            self.db.add(BalanceSnapshot(account_id=av.id, date=self._when(snap_day, 20), current_value=round(value, 2),
                                        note="Relevé mensuel"))
        self.db.flush()

    def store_prices(self, prices: dict[str, dict[date, float]]) -> None:
        self.db.add_all(
            SecurityPrice(ticker=ticker, date=day, close=close, currency="EUR", source="demo")
            for ticker, points in prices.items()
            for day, close in points.items()
        )

    async def run(self) -> None:
        self.build_categories()
        accounts = self.build_accounts()
        recurring = self.build_recurring(accounts["courant"], accounts["livret"])
        vacation = Tag(name="Vacances", color="#f59e0b")
        self.db.add_all([vacation, Tag(name="À rembourser", color="#ef4444")])
        prices = _price_series(self.rng, self.start - timedelta(days=7), self.today)
        self.store_prices(prices)

        self.build_bank(accounts, recurring, vacation)
        self.build_pea(accounts["pea"], accounts["courant"], prices)
        self.build_life_insurance(accounts["av"])

        self.db.add_all([
            SavingsGoal(name="Épargne de précaution", target_amount=12000.0, icon="shield", color="#22c55e",
                        account_id=accounts["livret"].id),
            SavingsGoal(name="Apport immobilier", target_amount=30000.0, icon="home", color="#f59e0b",
                        account_id=accounts["av"].id, deadline=date(self.today.year + 3, 6, 30)),
        ])
        self.db.commit()

        for account in accounts.values():
            recalculate_running_balances(self.db, account.id)
        await rebuild_holdings(self.db, accounts["pea"].id)
        self.db.commit()


async def generate_demo_data(db: Session, today: date | None = None) -> None:
    """Remplit une base vide (catégories et profils ETF compris) avec le jeu de démonstration."""
    today = today or date.today()
    seed_all(db)
    await _Builder(db, today).run()
    db.merge(SystemSetting(key=DEMO_STAMP_KEY, value=today.isoformat()))
    db.commit()
