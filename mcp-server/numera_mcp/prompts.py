"""Prompts MCP : templates d'analyse pour l'agent."""


def analyze_month(month: int, year: int) -> str:
    """Analyse complète d'un mois de budget.

    Args:
        month: Mois (1-12)
        year: Année
    """
    return f"""Analyse complète du budget pour {month:02d}/{year}.

Étapes :
1. `get_budget_summary(month={month}, year={year})` — vue d'ensemble
2. `get_expenses_by_category(month={month}, year={year})` — répartition
3. `get_top_merchants(month={month}, year={year})` — marchands principaux
4. `get_budget_alerts()` — alertes budget
5. `get_monthly_report(month={month}, year={year})` — rapport complet avec comparaison

Fournis :
- Résumé revenus / dépenses / solde
- Top 5 catégories et marchands
- Alertes budget
- Comparaison avec le mois précédent
- Recommandations d'optimisation
"""


def audit_subscriptions() -> str:
    """Audit complet des abonnements et charges récurrentes."""
    return """Audit des abonnements et charges récurrentes.

Étapes :
1. `list_recurring_transactions()` — abonnements déclarés
2. `get_subscriptions()` — analyse détectée automatiquement
3. `search_transactions("abonnement")` — rechercher dans les transactions

Pour chaque abonnement :
- Nom, montant, fréquence
- Catégorie
- Toujours pertinent ?

Synthèse :
- Coût total mensuel et annuel
- Recommandations d'optimisation
- Abonnements potentiellement oubliés
"""


def budget_review() -> str:
    """Review complète et approfondie du budget."""
    return """Review complète des finances.

Étapes :
1. `list_accounts()` — comptes et soldes
2. `get_kpi_history(months=12)` — tendances annuelles
3. `get_budget_summary()` — mois en cours
4. `get_insights()` — score de santé financière
5. `list_recurring_transactions()` — charges fixes
6. `list_savings_goals()` — objectifs d'épargne
7. `get_cashflow_projection()` — projection trésorerie

Rapport structuré :
## 1. Situation globale (soldes, évolution)
## 2. Revenus vs Dépenses (moyennes, taux d'épargne)
## 3. Top catégories (postes principaux, économies possibles)
## 4. Abonnements (total, recommandations)
## 5. Objectifs d'épargne (progression)
## 6. Projection et recommandations
"""


def categorize_uncategorized() -> str:
    """Propose des catégories pour les transactions qui n'en ont pas (sans rien modifier)."""
    return """Trouve les transactions sans catégorie et propose une catégorie pour chacune.

Étapes :
1. `list_categories()` — voir les catégories existantes
2. `list_transactions(limit=200)` — chercher les transactions sans catégorie
3. Groupe-les par marchand et propose une catégorie existante pour chaque marchand
4. Présente le résultat en tableau (marchand, nb de transactions, catégorie proposée)

Le serveur MCP est en lecture seule : l'utilisateur applique les catégories dans Numera
(Paramètres → Règles, pour une règle d'auto-catégorisation par marchand).
"""


def analyze_portfolio() -> str:
    """Analyse complète du portefeuille d'investissement : positions, performance, diversification."""
    return """Analyse complète du portefeuille d'investissement.

Étapes :
1. `list_accounts(type="investissement")` — identifier les comptes d'investissement
2. `list_holdings()` — positions actuelles avec prix live et performance
3. `get_investments_summary()` — résumé global (net investi, valeur totale, gain)
4. `get_diversity_scanner()` — décomposition ETF look-through + score de diversité + alertes
5. `list_etf_profiles()` — profils ETF connus pour contexte
6. `get_investments_allocation_advanced()` — répartition par classe d'actif, secteur, zone géo

Rapport structuré attendu :
## 1. Vue d'ensemble
- Valeur totale du portefeuille, net investi, gain total, performance %
- Nombre de positions (dont ETF vs actions directes)

## 2. Positions actuelles
- Top positions par valeur (ticker, nom, valeur, gain %)
- ETF détenus et leur poids dans le portefeuille

## 3. Analyse de diversification (look-through ETF)
- Score de diversité (X/100) avec interprétation
- Top 10 entreprises sous-jacentes réelles (directes + via ETF)
- Répartition géographique et sectorielle

## 4. Alertes & Risques
- Surconcentrations détectées
- Chevauchements / doublons d'exposition
- Biais géographiques

## 5. Recommandations de rééquilibrage
"""


def analyze_etf_lookthrough() -> str:
    """Décompose les ETF détenus pour révéler les entreprises réelles sous-jacentes et les doublons."""
    return """Décomposition ETF et analyse look-through.

Étapes :
1. `list_holdings()` — identifier les ETF dans le portefeuille (colonne etf = ✅)
2. `list_etf_profiles()` — voir les profils disponibles
3. `get_etf_profile(profile_id)` — détail de chaque profil ETF détenu (pays, secteurs, top 10)
4. `get_diversity_scanner()` — exposition réelle complète (look-through tous les ETF)

Pour chaque ETF détenu :
- Quel est son profil géographique (USA, Europe, Monde ?) ?
- Quels sont ses top holdings (Apple, Microsoft, Amazon, LVMH ?) ?
- Y a-t-il des chevauchements avec d'autres ETF ou actions directes ?

Rapport :
## 1. ETF détenus et leur poids dans le portefeuille
## 2. Décomposition de chaque ETF (top pays, secteurs, holdings)
## 3. Top 10 entreprises sous-jacentes agrégées (doublons additionnnés)
## 4. Chevauchements identifiés (titres présents dans plusieurs ETF ou en direct ET en ETF)
## 5. Recommandations (consolider, diversifier, remplacer un ETF redondant ?)
"""


PROMPTS = [
    analyze_month,
    audit_subscriptions,
    budget_review,
    categorize_uncategorized,
    analyze_portfolio,
    analyze_etf_lookthrough,
]


def register(mcp) -> None:
    for prompt in PROMPTS:
        mcp.prompt()(prompt)
