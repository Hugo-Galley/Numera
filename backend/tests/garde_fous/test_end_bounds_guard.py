"""Règle 12 : `end` d'une période et `end_of_today()` sont des bornes exclusives, lues avec `<`.

Une comparaison `date <= end` / `<= at` / `<= end_of_today()` inclut le premier instant de la période
suivante (ou les saisies de demain). Les exceptions légitimes (borne **inclusive** fournie par
l'utilisateur ou date sans heure) se déclarent dans `ALLOWED` avec leur motif.
"""
import re
from pathlib import Path

APP = Path(__file__).parents[2] / "app"
LAYERS = ("repositories", "services", "domain")

# Colonne ou variable de date comparée en `<=` à une borne de fin.
INCLUSIVE_END = re.compile(r"(\bdate|date_val|\bat)\s*<=\s*(end\w*|at\b|until|end_of_today\(\))")

# fichier -> motif de l'exception
ALLOWED: dict[str, str] = {
    "repositories/comptes/financial_events.py": "bornes incluses choisies par l'utilisateur (dates sans heure)",
    "repositories/analytics/metrics.py": "average_expense : date de fin saisie par l'utilisateur, incluse",
    "repositories/analytics/investments.py": "relevés des comptes titres à une date saisie par l'utilisateur",
    "domain/loans.py": "échéances de prêt : dates sans heure, `at` est un jour inclus",
    "services/investissement/investment_transactions.py": "cutoff = date du point zéro (jour inclus)",
    "services/investissement/holdings/replay.py": "cutoff = date du point zéro (jour inclus)",
    # Dette connue, à retirer avec la PR « fix(investissement) » (audit I2) qui borne les opérations futures
    "repositories/investissement/investment_transactions.py": "`until` des rejeux d'investissement (PR investissement)",
    "repositories/investissement/portfolio.py": "`until` des relevés d'investissement (PR investissement)",
    "services/systeme/demo/data.py": "génération de démo : jours inclus",
    "domain/reports.py": "boucle sur des jours inclus (`day <= end_date`)",
    "domain/portfolio.py": "boucle sur des jours inclus",
    "services/analytics/wrapped.py": "bornes semi-ouvertes `start <= x < end`",
    "services/analytics/metrics/timeseries.py": "bornes semi-ouvertes `start <= now < end`",
    "services/budget/budget_period.py": "bornes semi-ouvertes `start <= today < end`",
    "domain/budget_period.py": "bornes semi-ouvertes `start <= x < end`",
}


def inclusive_end_comparisons(text: str) -> list[str]:
    return [
        f"{number}: {line.strip()}"
        for number, line in enumerate(text.splitlines(), 1)
        if INCLUSIVE_END.search(line) and not re.search(r"<=\s*\w+\s*<", line)
    ]


def test_detects_an_inclusive_end_bound():
    assert inclusive_end_comparisons("q.filter(Transaction.date <= end)")
    assert inclusive_end_comparisons("q.filter(Transaction.date <= end_of_today())")
    assert inclusive_end_comparisons("[v for d, v in items if date_val <= end]")
    assert not inclusive_end_comparisons("q.filter(Transaction.date < end)")
    assert not inclusive_end_comparisons("if start <= row.first < end:")


def test_no_inclusive_end_bound_outside_the_declared_exceptions():
    found = []
    for layer in LAYERS:
        for path in sorted((APP / layer).rglob("*.py")):
            relative = path.relative_to(APP).as_posix()
            if relative in ALLOWED:
                continue
            found += [f"{relative}:{hit}" for hit in inclusive_end_comparisons(path.read_text())]
    assert not found, "Borne de fin exclusive lue avec `<=` (règle 12) :\n" + "\n".join(found)


def test_every_exception_still_exists():
    stale = [name for name in ALLOWED if not (APP / name).exists()]
    assert not stale, f"Exceptions obsolètes à retirer : {stale}"
