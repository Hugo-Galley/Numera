"""Instance de démonstration : jeu de données fictif (graine fixe, montants, marchands, cours)."""

from __future__ import annotations

import math
import random
from datetime import date, timedelta

DEMO_SEED = 2026
DEMO_MONTHS = 18

# ── Cours fictifs ─────────────────────────────────────────────────────────────

# ticker → (nom, isin, cours de départ, rendement annuel, volatilité annuelle)
SECURITIES = {
    "CW8.PA": ("Amundi MSCI World", "LU1681043599", 470.0, 0.09, 0.14),
    "PAEEM.PA": ("Amundi PEA MSCI Emerging Markets", "FR0013412020", 22.0, 0.05, 0.18),
    "TTE.PA": ("TotalEnergies", "FR0000120271", 58.0, 0.03, 0.20),
}


def _price_series(rng: random.Random, start: date, end: date) -> dict[str, dict[date, float]]:
    """Marche aléatoire géométrique, jours ouvrés uniquement."""
    series: dict[str, dict[date, float]] = {}
    for ticker, (_, _, price, drift, vol) in SECURITIES.items():
        daily_drift, daily_vol = drift / 252, vol / math.sqrt(252)
        points: dict[date, float] = {}
        day = start
        while day <= end:
            if day.weekday() < 5:
                price *= math.exp(daily_drift - daily_vol**2 / 2 + daily_vol * rng.gauss(0, 1))
                points[day] = round(price, 2)
            day += timedelta(days=1)
        series[ticker] = points
    return series


def _price_on(series: dict[date, float], day: date) -> float:
    while day not in series:
        day -= timedelta(days=1)
    return series[day]


EXTRA_CATEGORIES = [
    # (nom, type, groupe, plafond mensuel)
    ("Logement", "depense", "Fixe", None),
    ("Énergie", "depense", "Fixe", None),
    ("Assurances", "depense", "Fixe", None),
    ("Transport", "depense", "Vie courante", 150.0),
    ("Santé", "depense", "Vie courante", None),
    ("Shopping", "depense", "Loisirs", 150.0),
    ("Voyages", "depense", "Loisirs", None),
]
BUDGETS = {"Nourriture": 450.0, "Sortie": 220.0, "Abonnement": 80.0}

GROCERIES = ["Carrefour", "Lidl", "Monoprix", "Picard", "Biocoop", "Intermarché"]
OUTINGS = ["Le Comptoir du Marché", "Big Mamma", "Deliveroo", "UGC Ciné Cité", "Uber Eats", "Bar Le Perchoir"]
SHOPPING = ["Amazon", "Fnac", "Decathlon", "Zara", "IKEA", "Leroy Merlin"]
TRANSPORT = [("SNCF Connect", 35, 95), ("Uber", 9, 26), ("TotalEnergies Station", 40, 70)]
HEALTH = [("Pharmacie du Centre", 6, 35), ("Dr Martin — consultation", 30, 30)]

# (nom, catégorie, montant, jour, logo)
FIXED_EXPENSES = [
    ("Foncia — Loyer", "Logement", 890.0, 2, None),
    ("Navigo", "Transport", 86.40, 5, None),
    ("Free Mobile", "Abonnement", 19.99, 8, "si:free"),
    ("Netflix", "Abonnement", 13.49, 10, "si:netflix"),
    ("Spotify", "Abonnement", 11.12, 12, "si:spotify"),
    ("EDF", "Énergie", 72.0, 15, None),
    ("Basic-Fit", "Sport", 29.99, 18, None),
    ("MAIF — Assurance habitation", "Assurances", 21.40, 20, None),
]
SALARY = 2740.0
SALARY_DAY = 27
TRANSFER_DAY = 3
TO_LIVRET, TO_PEA, TO_AV = 200.0, 300.0, 100.0
