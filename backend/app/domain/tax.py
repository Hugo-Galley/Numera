"""Calculs fiscaux par enveloppe. Fonctions pures : aucune base de données, aucun appel réseau."""
import re
import unicodedata
from datetime import date
from typing import NamedTuple

from app.domain.tax_rules import TaxRules

_CAPITALISED_INTEREST_ALERT = "Plafond de versements du {name} atteint : les intérêts capitalisés peuvent légitimement le dépasser."
PEA_MILESTONE_YEARS = 5
AV_MILESTONE_YEARS = 8


def years_between(start: date, end: date) -> float:
    """Années écoulées entre deux dates (calendaires, fractionnaires)."""
    whole = end.year - start.year - ((end.month, end.day) < (start.month, start.day))
    day = 28 if (start.month == 2 and start.day == 29) else start.day
    anniversary = date(start.year + whole, start.month, day)
    next_anniversary = date(anniversary.year + 1, anniversary.month, day)
    return whole + (end - anniversary).days / max((next_anniversary - anniversary).days, 1)


def _blank(**overrides) -> dict:
    status = {
        "current": None, "ceiling": None, "remaining": None, "used_pct": None,
        "age_years": None, "milestone_years": None, "milestone_reached": None,
        "estimated_tax_saving": None, "allowance": None, "total_contributed": None,
        "blocked": None, "available": None, "next_unlock_date": None, "alerts": [],
    }
    status.update(overrides)
    return status


def _room(current: float, ceiling: float) -> tuple[float, float]:
    return max(ceiling - current, 0.0), (current / ceiling * 100.0 if ceiling > 0 else 0.0)


def pea_status(contributions: float, opened_at: date | None, withdrawals: list[date], today: date, rules: TaxRules) -> dict:
    """Versements cumulés (un retrait ne restitue pas de place) et ancienneté du plan."""
    remaining, used_pct = _room(contributions, rules.pea_ceiling)
    alerts: list[str] = []
    age = reached = None
    if opened_at is None:
        alerts.append("Date d'ouverture manquante : renseigne-la dans les paramètres du compte.")
    else:
        age = years_between(opened_at, today)
        reached = age >= PEA_MILESTONE_YEARS
        if any(years_between(opened_at, w) < PEA_MILESTONE_YEARS for w in withdrawals):
            alerts.append("Retrait avant 5 ans : la fiscalité avantageuse du PEA est perdue.")
    if contributions > rules.pea_ceiling:
        alerts.append("Plafond de versements du PEA dépassé.")
    return _blank(
        current=contributions, ceiling=rules.pea_ceiling, remaining=remaining, used_pct=used_pct,
        age_years=age, milestone_years=PEA_MILESTONE_YEARS, milestone_reached=reached, alerts=alerts,
    )


def per_deduction_ceiling(prior_year_income: float, rules: TaxRules) -> float:
    """10 % des revenus pro de N-1, borné entre le plancher et le plafond de l'année."""
    return min(max(prior_year_income * rules.per_rate, rules.per_floor), rules.per_ceiling)


def per_status(contributed_this_year: float, prior_year_income: float, tmi_pct: float, rules: TaxRules) -> dict:
    """Versements de l'année civile face au plafond de déduction, économie d'impôt = déductible × TMI."""
    ceiling = per_deduction_ceiling(prior_year_income, rules)
    remaining, used_pct = _room(contributed_this_year, ceiling)
    alerts = []
    if contributed_this_year > ceiling:
        alerts.append("Versements supérieurs au plafond de déduction : l'excédent n'est pas déductible.")
    return _blank(
        current=contributed_this_year, ceiling=ceiling, remaining=remaining, used_pct=used_pct,
        estimated_tax_saving=min(contributed_this_year, ceiling) * tmi_pct / 100.0, alerts=alerts,
    )


def livret_a_status(balance: float, rules: TaxRules) -> dict:
    remaining, used_pct = _room(balance, rules.livret_a_ceiling)
    alerts = [_CAPITALISED_INTEREST_ALERT.format(name="Livret A")] if balance > rules.livret_a_ceiling else []
    return _blank(current=balance, ceiling=rules.livret_a_ceiling, remaining=remaining, used_pct=used_pct, alerts=alerts)


def livret_jeune_status(balance: float, rules: TaxRules) -> dict:
    remaining, used_pct = _room(balance, rules.livret_jeune_ceiling)
    alerts = [_CAPITALISED_INTEREST_ALERT.format(name="Livret Jeune")] if balance > rules.livret_jeune_ceiling else []
    return _blank(current=balance, ceiling=rules.livret_jeune_ceiling, remaining=remaining, used_pct=used_pct, alerts=alerts)


def ldds_status(balance: float, rules: TaxRules) -> dict:
    remaining, used_pct = _room(balance, rules.ldds_ceiling)
    alerts = [_CAPITALISED_INTEREST_ALERT.format(name="LDDS")] if balance > rules.ldds_ceiling else []
    return _blank(current=balance, ceiling=rules.ldds_ceiling, remaining=remaining, used_pct=used_pct, alerts=alerts)


def lep_status(balance: float, rules: TaxRules) -> dict:
    remaining, used_pct = _room(balance, rules.lep_ceiling)
    alerts = [_CAPITALISED_INTEREST_ALERT.format(name="LEP")] if balance > rules.lep_ceiling else []
    alerts.append("Le LEP est réservé aux foyers sous un plafond de revenus : à revérifier chaque année (non contrôlé ici).")
    return _blank(current=balance, ceiling=rules.lep_ceiling, remaining=remaining, used_pct=used_pct, alerts=alerts)


class PeeLot(NamedTuple):
    """Un versement au PEE ; `employer` = abondement de l'employeur (hors plafond des versements volontaires)."""

    date: date
    amount: float
    employer: bool


def _add_years(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:  # 29 février
        return day.replace(year=day.year + years, day=28)


def pee_status(lots: list[PeeLot], withdrawn: float, gross_annual_salary: float, today: date, rules: TaxRules) -> dict:
    """Total versé, part bloquée / disponible (retraits imputés sur les plus anciens), plafond des versements volontaires."""
    remaining_withdrawal = withdrawn
    open_lots: list[tuple[date, float]] = []
    for lot in sorted(lots, key=lambda item: item.date):
        taken = min(lot.amount, remaining_withdrawal)
        remaining_withdrawal -= taken
        if lot.amount - taken > 0:
            open_lots.append((lot.date, lot.amount - taken))
    unlock = [(_add_years(day, rules.pee_lock_years), amount) for day, amount in open_lots]
    blocked_lots = [(when, amount) for when, amount in unlock if when > today]
    blocked = sum(amount for _, amount in blocked_lots)
    available = sum(amount for when, amount in unlock if when <= today)
    voluntary = sum(lot.amount for lot in lots if not lot.employer and lot.date.year == today.year)

    alerts: list[str] = []
    ceiling = remaining = used_pct = None
    if gross_annual_salary > 0:
        ceiling = gross_annual_salary * rules.pee_voluntary_rate
        remaining, used_pct = _room(voluntary, ceiling)
        if voluntary > ceiling:
            alerts.append("Versements volontaires supérieurs au plafond de 25 % de la rémunération brute annuelle.")
    else:
        alerts.append("Renseigne ton salaire brut annuel dans les réglages pour suivre le plafond des versements volontaires.")
    return _blank(
        current=voluntary, ceiling=ceiling, remaining=remaining, used_pct=used_pct,
        total_contributed=sum(lot.amount for lot in lots), blocked=blocked, available=available,
        next_unlock_date=min(when for when, _ in blocked_lots).isoformat() if blocked_lots else None,
        alerts=alerts,
    )


def av_status(opened_at: date | None, household: str, today: date, rules: TaxRules) -> dict:
    """Ancienneté face aux 8 ans et abattement annuel applicable aux gains de rachat."""
    allowance = rules.av_allowance_couple if household == "couple" else rules.av_allowance_single
    if opened_at is None:
        return _blank(
            milestone_years=AV_MILESTONE_YEARS, allowance=allowance,
            alerts=["Date d'ouverture manquante : renseigne-la dans les paramètres du compte."],
        )
    age = years_between(opened_at, today)
    return _blank(age_years=age, milestone_years=AV_MILESTONE_YEARS, milestone_reached=age >= AV_MILESTONE_YEARS, allowance=allowance)


# Libellés courants → enveloppe. Ordre important : « PEA-PME » avant « PEE », « PERCO » avant « PER ».
_WRAPPER_PATTERNS: list[tuple[str, str]] = [
    (r"\bpea\b", "pea"),
    (r"\b(pee|peg|peeg|pei)\b|epargne salariale", "pee"),
    (r"\b(per|perin|perco|percol|pero)\b|epargne retraite", "per"),
    (r"\bcto\b|compte titres?", "cto"),
    (r"assurance vie|\bav\b", "assurance_vie"),
    (r"livret jeune", "livret_jeune"),
    (r"\bldds\b|livret (de )?developpement durable", "ldds"),
    (r"\blep\b|livret (d )?epargne populaire", "lep"),
    (r"livret a\b", "livret_a"),
]


def guess_tax_wrapper(name: str, account_type: str | None = None) -> str | None:
    """Enveloppe probable d'un compte d'après son nom (et son type pour l'assurance-vie), ou None.

    Sert uniquement à proposer l'enveloppe : rien n'est enregistré sans validation.
    """
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    text = " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())
    for pattern, kind in _WRAPPER_PATTERNS:
        if re.search(pattern, text):
            return kind
    return "assurance_vie" if account_type == "assurance_vie" else None


# Livrets réglementés, du plus intéressant au moins intéressant (le LEP rapporte le plus, le Livret Jeune est plafonné bas)
_LIVRET_ORDER = ("lep", "livret_a", "ldds", "livret_jeune")
_LIVRET_NAMES = {"lep": "LEP", "livret_a": "Livret A", "ldds": "LDDS", "livret_jeune": "Livret Jeune"}
PRECAUTION_MIN_MONTHS = 3
PRECAUTION_TARGET_MONTHS = 6
PER_MIN_TMI_PCT = 30


def _fr(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def allocation_advice(cards: list[dict], months_of_expenses: float | None, tmi_pct: float | None) -> list[dict]:
    """Ordre de remplissage conseillé : précaution sur livret, PEA, PER si TMI ≥ 30 %, assurance-vie, CTO.

    `cards` : cartes d'enveloppes (`kind`, `account_id`, `account_name`, `remaining`). Une étape sans compte
    existant propose d'en ouvrir un (`account_id = None`). Règle fixe et explicable, aucun taux codé en dur.
    """
    by_kind: dict[str, list[dict]] = {}
    for card in cards:
        by_kind.setdefault(card["kind"], []).append(card)
    with_room = lambda kind: next((c for c in by_kind.get(kind, []) if (c.get("remaining") or 0) > 0), None)  # noqa: E731
    steps: list[dict] = []

    def add(kind: str, card: dict | None, reason: str, name: str | None = None) -> None:
        steps.append({
            "rank": len(steps) + 1, "kind": kind, "account_id": card["account_id"] if card else None,
            "account_name": card["account_name"] if card else name, "reason": reason,
            "remaining": card.get("remaining") if card else None,
        })

    if months_of_expenses is None or months_of_expenses < PRECAUTION_TARGET_MONTHS:
        if months_of_expenses is None:
            situation = f"Constitue d'abord {PRECAUTION_MIN_MONTHS} à {PRECAUTION_TARGET_MONTHS} mois de dépenses d'épargne de précaution"
        elif months_of_expenses < PRECAUTION_MIN_MONTHS:
            situation = f"Ton épargne de précaution couvre {_fr(months_of_expenses)} mois de dépenses, sous le minimum de {PRECAUTION_MIN_MONTHS} mois"
        else:
            situation = f"Ton épargne de précaution couvre {_fr(months_of_expenses)} mois de dépenses, l'objectif est {PRECAUTION_TARGET_MONTHS} mois"
        livret = next((card for kind in _LIVRET_ORDER if (card := with_room(kind))), None)
        has_livret = any(kind in by_kind for kind in _LIVRET_ORDER)
        if livret:
            add(livret["kind"], livret, f"{situation} : verse sur ton {_LIVRET_NAMES[livret['kind']]}, disponible à tout moment et sans impôt.")
        elif not has_livret:
            add("livret_a", None, f"{situation} : ouvre un livret réglementé (LEP si tu y as droit, sinon Livret A).", "Livret A à ouvrir")

    pea = with_room("pea")
    if pea:
        add("pea", pea, "Actions sur le long terme : le PEA est exonéré d'impôt sur les gains après 5 ans (hors prélèvements sociaux).")
    elif "pea" not in by_kind:
        add("pea", None, "Ouvre un PEA, même avec un petit versement, pour lancer le compteur des 5 ans de fiscalité avantageuse.", "PEA à ouvrir")

    if tmi_pct is not None and tmi_pct >= PER_MIN_TMI_PCT:
        per = with_room("per")
        if per:
            add("per", per, f"Avec une tranche à {tmi_pct:.0f} %, chaque versement au PER réduit ton impôt (argent bloqué jusqu'à la retraite).")
        elif "per" not in by_kind:
            add("per", None, f"Avec une tranche à {tmi_pct:.0f} %, un PER réduirait ton impôt (argent bloqué jusqu'à la retraite).", "PER à ouvrir")

    if "assurance_vie" not in by_kind:
        add("assurance_vie", None, "Ouvre une assurance-vie pour prendre date : la fiscalité s'allège après 8 ans.", "Assurance-vie à ouvrir")
    else:
        cto = (by_kind.get("cto") or [None])[0]
        add("cto", cto, "Enveloppes avantageuses remplies ou ouvertes : le compte-titres n'a pas de plafond.", None if cto else "Compte-titres")
    return steps
