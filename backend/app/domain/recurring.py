"""Règles pures des récurrences."""

INVESTMENT_ACCOUNT_TYPES = ("investissement", "assurance_vie")


def investment_leg_type(rule_type: str, account_type: str, has_ticker: bool, has_transfer: bool) -> tuple[bool, str]:
    """(l'échéance est-elle une opération d'investissement, type d'opération titres correspondant).

    Une règle sur un compte investissement, ou un achat de titre sans virement, produit une opération
    d'investissement ; `achat`/`vente` deviennent `versement`/`retrait`, de même qu'Entrée/Sortie.
    """
    is_investment_account = account_type in INVESTMENT_ACCOUNT_TYPES
    is_inv = is_investment_account or (has_ticker and not has_transfer)
    inv_type = rule_type.lower()
    if inv_type in ("achat", "vente"):
        inv_type = "versement" if inv_type == "achat" else "retrait"
    elif is_investment_account and inv_type in ("entree", "sortie"):
        # Règle posée sur le compte investissement lui-même : une Entrée y fait entrer l'argent
        inv_type = "versement" if inv_type == "entree" else "retrait"
    elif inv_type in ("sortie", "entree"):
        # Achat programmé depuis un compte bancaire (ticker) : la Sortie finance l'achat
        inv_type = "versement" if inv_type == "sortie" else "retrait"
    return is_inv, inv_type
