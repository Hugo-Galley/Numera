"""Coût des récurrences, classement essentiel / non essentiel et reste à vivre (calcul pur)."""
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

# Multiplicateurs (coût mensuel, coût annuel) par fréquence de récurrence
MONTHS_PER_PERIOD_FACTOR = {
    "daily": {"monthly": 30.0, "annual": 365.0},
    "weekly": {"monthly": 4.33, "annual": 52.0},
    "monthly": {"monthly": 1.0, "annual": 12.0},
    "quarterly": {"monthly": 1 / 3, "annual": 4.0},
    "yearly": {"monthly": 1 / 12, "annual": 1.0},
    "annual": {"monthly": 1 / 12, "annual": 1.0},  # ancien libellé
}


def recurring_costs(amount: float, frequency: str, rate: float) -> tuple[float, float]:
    """Coût mensuel et annuel en EUR d'une récurrence (montant dans sa devise, `rate` = taux EUR→devise)."""
    factor = MONTHS_PER_PERIOD_FACTOR.get(frequency)
    monthly_cost = float(amount) * factor["monthly"] / rate if factor else 0.0
    annual_cost = float(amount) * factor["annual"] / rate if factor else 0.0
    return monthly_cost, annual_cost


SAVINGS_CATEGORIES = ("Investissement", "Epargne")


def subscription_kind(category_name: str | None, flow_type: str) -> str:
    """Onglet d'une récurrence : alimentation d'épargne/investissement, autre flux que Sortie, sinon abonnement."""
    if category_name in SAVINGS_CATEGORIES:
        return "investments"
    return "subscriptions" if flow_type == "Sortie" else "other"


def counted_in_kind_total(kind: str, status: str, counts_in_total: bool, is_recurring_entity: bool) -> bool:
    """Une récurrence entre dans le total de son onglet : confirmée, et active (plans d'investissement) ou comptée (le reste)."""
    if not is_recurring_entity:
        return False
    return status == "active" if kind == "investments" else counts_in_total


# Catégories essentielles par défaut (mots normalisés : minuscules, sans accents).
# Mot entier, ou début de mot pour les racines (« assur » couvre assurance, assurances…).
_ESSENTIAL_WORDS = frozenset({
    "sante", "logement", "loyer", "loyers", "charge", "charges", "gaz", "eau", "mobile", "internet", "box", "fibre",
    "credit", "credits", "pret", "prets", "emprunt", "emprunts", "edf", "engie",
})
_ESSENTIAL_ROOTS = ("assur", "mutuel", "energ", "electri", "telephon", "medic", "medec", "pharma", "habitat")

EssentialSource = Literal["auto", "manual"]


def _words(text: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", plain)


def default_is_essential(category_name: str | None) -> bool:
    """Essentiel par défaut : assurance, santé/mutuelle, logement (loyer, charges), énergie, téléphonie/internet, crédit."""
    return any(w in _ESSENTIAL_WORDS or w.startswith(_ESSENTIAL_ROOTS) for w in _words(category_name or ""))


def effective_essential(is_essential: bool | None, category_name: str | None) -> tuple[bool, EssentialSource]:
    """Choix de l'utilisateur s'il existe, sinon valeur déduite de la catégorie."""
    if is_essential is None:
        return default_is_essential(category_name), "auto"
    return is_essential, "manual"


INCOME_FLOW_TYPES = ("Entree", "Interets")


@dataclass(frozen=True)
class RecurringLine:
    flow_type: str
    kind: str
    in_kind_total: bool
    is_essential: bool
    monthly_cost: float


@dataclass(frozen=True)
class ResteAVivre:
    revenus_recurrents: float
    charges_essentielles: float
    charges_non_essentielles: float
    reste_a_vivre_essentiel: float
    reste_a_vivre_total: float


def reste_a_vivre(lines: list[RecurringLine]) -> ResteAVivre:
    """Revenus récurrents − charges récurrentes, ramenés au mois.

    Seules les récurrences comptées dans le total de leur onglet entrent (`in_kind_total` : actives, encore
    prélevées, hors virement interne et alimentation d'épargne). Charges = onglet abonnements ;
    revenus = entrées et intérêts de l'onglet « autres ». Les flux titres (achat, versement…) n'entrent pas.
    """
    counted = [line for line in lines if line.in_kind_total]
    income = sum(line.monthly_cost for line in counted if line.kind == "other" and line.flow_type in INCOME_FLOW_TYPES)
    charges = [line for line in counted if line.kind == "subscriptions"]
    essential = sum(line.monthly_cost for line in charges if line.is_essential)
    optional = sum(line.monthly_cost for line in charges if not line.is_essential)
    return ResteAVivre(
        revenus_recurrents=round(income, 2),
        charges_essentielles=round(essential, 2),
        charges_non_essentielles=round(optional, 2),
        reste_a_vivre_essentiel=round(income - essential, 2),
        reste_a_vivre_total=round(income - essential - optional, 2),
    )
