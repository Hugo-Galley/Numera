"""Règles fiscales françaises chiffrées, par année. Seul fichier qui porte ces valeurs.

Valeurs vérifiées le 2026-10-07 (sources ci-dessous). À revérifier chaque début d'année sur
service-public.fr / impots.gouv.fr : le plafond PER de l'année N dépend du PASS de N-1, et les
prélèvements sociaux évoluent avec les lois de financement de la Sécurité sociale.

Sources :
- Brochure « Principales nouveautés revenus 2025 », impots.gouv.fr (LFSS 2026, art. 12) : CSG capital 9,2 % -> 10,6 %
  (prélèvements sociaux 17,2 % -> 18,6 %) à compter des revenus 2025 déclarés en 2026 pour les revenus du patrimoine
  (dont plus-values de cession de valeurs mobilières), et à compter du 1.1.2026 pour les produits de placement
  (dividendes). Assurance-vie, revenus fonciers et plus-values immobilières restent à 17,2 %.
- PASS 2024 = 46 368 EUR, PASS 2025 = 47 100 EUR, PASS 2026 = 48 060 EUR (arrêté du 22.12.2025).
- Livret A : 22 950 EUR (hors intérêts capitalisés) ; PEA : 150 000 EUR de versements ;
  assurance-vie : abattement de 4 600 EUR (seul) / 9 200 EUR (couple) sur les gains de rachats après 8 ans.
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
    pfu_rate_dividends: float     # PFU sur les dividendes perçus dans l'année (12,8 % + prélèvements sociaux à la source)
    pfu_rate_gains: float         # PFU sur les plus-values de cession de l'année (12,8 % + prélèvements sociaux)


RULES_BY_YEAR: dict[int, TaxRules] = {
    # Plafond PER 2025 = 10 % du PASS 2024 (46 368) : plancher 4 637, maximum 37 094.
    # Dividendes perçus en 2025 : PS à 17,2 % -> 30 % ; plus-values de 2025 : PS à 18,6 % -> 31,4 %.
    2025: TaxRules(2025, 150_000.0, 22_950.0, 0.10, 4_637.0, 37_094.0, 4_600.0, 9_200.0, 0.30, 0.314),
    # Plafond PER 2026 = 10 % du PASS 2025 (47 100) : plancher 4 710, maximum 37 680. PS à 18,6 % : 31,4 %.
    2026: TaxRules(2026, 150_000.0, 22_950.0, 0.10, 4_710.0, 37_680.0, 4_600.0, 9_200.0, 0.314, 0.314),
}


def rules_for(year: int) -> TaxRules:
    """Règles de l'année ; à défaut, de la plus proche année connue (jamais d'erreur)."""
    if year in RULES_BY_YEAR:
        return RULES_BY_YEAR[year]
    nearest = min(RULES_BY_YEAR, key=lambda known: abs(known - year))
    return RULES_BY_YEAR[nearest]
