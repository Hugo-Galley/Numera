"""Règles fiscales françaises chiffrées, par année. Seul fichier qui porte ces valeurs.

À VÉRIFIER chaque début d'année auprès de service-public.fr / impots.gouv.fr avant de s'y fier :
les plafonds PER dépendent du PASS de l'année N-1, et le taux des prélèvements sociaux peut évoluer.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TaxRules:
    year: int
    pea_ceiling: float            # plafond de versements cumulés du PEA
    livret_a_ceiling: float       # plafond de dépôts du Livret A
    per_rate: float               # part des revenus pro déductible au PER
    per_floor: float              # plafond de déduction minimal (10 % du PASS N-1)
    per_ceiling: float            # plafond de déduction maximal (10 % de 8 PASS N-1)
    av_allowance_single: float    # abattement annuel sur les gains de rachat d'AV > 8 ans (seul)
    av_allowance_couple: float    # idem, couple
    pfu_rate: float               # prélèvement forfaitaire unique (impôt + prélèvements sociaux)


RULES_BY_YEAR: dict[int, TaxRules] = {
    # À vérifier
    2025: TaxRules(2025, 150_000.0, 22_950.0, 0.10, 4_637.0, 37_094.0, 4_600.0, 9_200.0, 0.30),
    # À vérifier : PASS 2025 = 47 100 € ; taux PFU à confirmer pour 2026
    2026: TaxRules(2026, 150_000.0, 22_950.0, 0.10, 4_710.0, 37_680.0, 4_600.0, 9_200.0, 0.30),
}


def rules_for(year: int) -> TaxRules:
    """Règles de l'année ; à défaut, de la plus proche année connue (jamais d'erreur)."""
    if year in RULES_BY_YEAR:
        return RULES_BY_YEAR[year]
    nearest = min(RULES_BY_YEAR, key=lambda known: abs(known - year))
    return RULES_BY_YEAR[nearest]
