"""Constantes du modèle de sur-exposition (spec 2026-11-27).

Ce sont des paramètres statistiques, jamais des seuils métier par pays ou par secteur : toute sur-exposition est
jugée par écart à une référence de marché."""

# Fenêtre des rendements hebdomadaires (2 ans)
HISTORY_WEEKS = 104
# En dessous, une corrélation ou une tracking error par les cours n'est pas jugée fiable
MIN_HISTORY_WEEKS = 52
# Deux fonds sous cette tracking error annualisée répliquent le même indice (même exposition, autre enveloppe)
SAME_EXPOSURE_MAX_TRACKING_ERROR = 0.02
# Repli sans historique : similarité cosinus minimale des lignes de composition pour fusionner deux fonds
SAME_EXPOSURE_MIN_SIMILARITY = 0.95
# Deux lignes au-dessus sont regroupées dans un même bloc corrélé
BLOCK_CORRELATION = 0.8
# Sur-pondération : au moins OVERWEIGHT_RATIO × le poids du marché ET au moins OVERWEIGHT_MIN_POINTS points d'écart
OVERWEIGHT_RATIO = 1.5
OVERWEIGHT_MIN_POINTS = 5.0
# Référence de marché par défaut (indice de `domain/index_references.json`)
DEFAULT_MARKET_INDEX = "MSCI ACWI"
