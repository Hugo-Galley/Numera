# Phase 4 — Portefeuille : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sortir de `core/` et des controllers toute la logique d'investissement (opérations, positions, dividendes, cours, profils ETF, valorisation, diversification) vers `services/`, `repositories/`, `domain/` et `integrations/`, avec **zéro écart de chiffres**, jusqu'à vider la baseline de taille de ses 13 entrées backend.

**Architecture:** La tâche 1 fige la sortie JSON des routes du portefeuille (instantanés à date figée, dossier séparé de ceux de la phase 3). Les tâches 2 à 5 démontent les modules `core/` du bas vers le haut du graphe de dépendances (`market_data` → `etf_analyzer` → `dividends`/`holdings` → `portfolio`) ; les tâches 6 à 9 amincissent les controllers. Après chaque tâche, les deux tests d'instantanés passent à l'identique.

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic v2, pytest (Python 3.11), `freezegun`, `httpx`.

**Spec:** `docs/superpowers/specs/2026-10-28-architecture-en-couches-design.md` · plan maître : `docs/superpowers/plans/2026-10-28-architecture-en-couches.md` (§ Phase 4) · plan de la phase précédente (conventions et pièges, section 0) : `docs/superpowers/plans/2026-10-28-phase-3-analytics.md`.

---

## 0. Reprendre ce plan dans une nouvelle conversation

```text
On reprend la phase 4 de la migration de Numera vers une architecture en couches.
Lis d'abord docs/superpowers/plans/2026-10-29-phase-4-portefeuille.md (en entier, surtout la section 0),
puis la section 0 de docs/superpowers/plans/2026-10-28-phase-3-analytics.md (pièges 1 à 9) et le ledger
.superpowers/sdd/2026-10-29-phase-4-portefeuille/progress.md (une tâche « complete » n'est pas refaite).
Exécute la suite toi-même (skill superpowers:executing-plans). Commits directement sur main, sans push.
```

- Conventions de l'utilisateur, correspondance des erreurs, pièges 1 à 9 : **section 0 du plan de la phase 3**, inchangées.
- Ledger : `.superpowers/sdd/2026-10-29-phase-4-portefeuille/progress.md` (dossier ignoré par git) ; `Task N: complete (commits a..b, tests: …)` et `Task N: Ruling: <décision> — <pourquoi> — <coût si faux>`.
- État au départ (commit `bbab11b`) : suite ≈ 880 tests ; `tests/architecture_baseline.txt` vide ; `scripts/code_size_baseline.json` = 34 entrées dont 13 backend, **toutes** dans le périmètre (`core/portfolio.py` 670 + `compute_portfolio` 395, `core/market_data.py` 482 + `get_market_quotes` 96 + `search_market_assets` 86, `core/seeds_etf.py` 445, `core/holdings.py::replay_account` 100 + `estimate_baseline_costs` 94, `controllers/analytics/diversity.py` 453 + `diversity_scanner` 369, `controllers/analytics/dividends.py::get_dividends` 101, `controllers/investment_transactions.py::create_…` 83 + `update_…` 95).

### Pièges propres à la phase 4

10. **Patchs réseau des tests.** Huit fichiers de test patchent `market_data._fetch_chart` / `get_price_on` / `get_market_quotes` / `get_exchange_rates`, `etf_analyzer.fetch_yahoo_composition`, `app.core.portfolio.get_market_quotes`. Le code appelant doit appeler l'intégration **par attribut de module** (`yahoo_finance.fetch_chart(...)`, `market_quotes.get_market_quotes(...)`) pour que le patch, repointé vers le nouveau module, reste effectif. Le blocage réseau (`block_network`) fait échouer bruyamment un patch oublié : corriger le test, jamais le blocage.
11. **État global de module.** `_QUOTES_CACHE`, `_HISTORY_ATTEMPTS`, `_yahoo_auth` sont des dictionnaires globaux vidés ou lus par des tests (`market_data._QUOTES_CACHE.clear()`). Un seul module propriétaire chacun ; tous les `clear()` des tests repointés.
12. **Commits cachés.** `get_market_quotes` et `fetch_price_history` font `db.commit()` ; `refresh_etf_profile`, `auto_decompose_and_create_profile` et la route diversité (rattachement des profils) commitent aussi. Ces commits restent dans le **service** (jamais dans un repository) et au même moment du déroulé : un `commit` déplacé avant un `rebuild_holdings` ou après une lecture change ce qui est persisté.
13. **Cycle `holdings` → `dividends` → `market_data`.** `estimate_baseline_costs` importe `match_dividend_ticker` en local pour éviter un cycle. Une fois `match_dividend_ticker` et `extract_asset_clean_name` dans `domain/`, l'import local devient un import de module.
14. **Associativité flottante dans `compute_portfolio`.** Les totaux (`value_eur_positions`, `unrealized_eur`, `fx_effect_eur`, `cost_known_eur`, `realized_total`, `fees_eur`) se cumulent ligne à ligne dans un ordre précis ; une étape extraite renvoie le total cumulé dans le même ordre, jamais une somme de sous-totaux.
15. **Données de démo sans Point Zéro.** Le PEA de démo n'a ni `holdings_baseline_date` ni inventaire : la courbe, le TWR et le rapprochement de `compute_portfolio` ne sont exercés que par le compte complémentaire de la tâche 1.

## Périmètre

| Module actuel | Destination |
|---|---|
| `core/market_data.py` | `integrations/yahoo_finance.py` (HTTP), `repositories/security_prices.py`, `domain/market.py` (pur), `services/market/` (`quotes.py`, `search.py`, `suggestions.py`) |
| `core/etf_analyzer.py`, `core/seeds_etf.py` | `integrations/yahoo_finance.py` (composition), `domain/etf_profiles.py`, `domain/etf_presets.json` + `domain/etf_presets.py`, `repositories/etf_profiles.py`, `services/etf_profiles.py` |
| `core/dividends.py` | `domain/dividends.py`, `services/dividends.py` |
| `core/holdings.py` | `domain/holdings.py`, `repositories/holdings.py`, `services/holdings/` (`replay.py`, `rebuild.py`, `cost_estimates.py`) |
| `core/portfolio.py` | `domain/performance.py` (`xirr`, `twr`), `domain/portfolio.py`, `repositories/portfolio.py`, `services/portfolio/` |
| controllers `market`, `etf_profiles`, `investment_transactions`, `holdings`, `analytics/portfolio`, `analytics/dividends`, `analytics/diversity` | services correspondants ; controllers sans `db.query`, `commit`, `HTTPException` métier ni import de `app.models` |

Hors périmètre : `FORBIDDEN["app.core"]` (durci en phase 6), regroupement par domaine (phase 6), frontend (phase 5), toute correction de comportement (une anomalie va au ledger en `minor (deferred)`).

## Global Constraints

- **Zéro écart** : `tests/test_analytics_snapshots.py` (phase 3, jamais régénéré) et `tests/test_portfolio_snapshots.py` (tâche 1, jamais régénéré après elle) passent à l'identique après chaque tâche. Seule modification permise à ces fichiers de test : repointer un patch ou un `clear()` vers le nouveau module (piège 10).
- Mêmes routes, paramètres, codes et corps de réponse ; MCP et frontend inchangés.
- `main` vert après chaque tâche : suite complète, `make check-size`, `tests/architecture_baseline.txt` vide.
- Fin de tâche : les entrées de `scripts/code_size_baseline.json` des fichiers touchés ont **disparu** ; aucune nouvelle entrée.
- Module `core/` déplacé : `git mv` vers sa destination principale puis édition ; supprimé à la fin de sa tâche ; aucun ré-export ; tous les importeurs mis à jour (absolus, locaux, tests, `monkeypatch.setattr` par chaîne `"app.core.…"`).
- Docs mises à jour dans le commit de la tâche quand un emplacement cité change (`ARCHITECTURE.md`, `CLAUDE.md`, `backend/CLAUDE.md`, skills `numera-*`, commentaires des modèles `etf_profile.py`, `holding_baseline_item.py`).
- Commit par tâche, en français, sur `main`, terminé par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

### Recette (tâches 2 à 9)

1. Requêtes → `repositories/<domaine>.py` (pas de `commit`, `flush` permis). 2. Calculs sans `Session` → `domain/<domaine>.py`, testés sans base. 3. Orchestration, `await` des conversions, `commit`, erreurs métier → `services/`. 4. Appels HTTP → `integrations/yahoo_finance.py`. 5. Controller : signature inchangée + un appel de service. 6. Vérifier : `PYTHONPATH=. python3.11 -m pytest tests/test_analytics_snapshots.py tests/test_portfolio_snapshots.py -q` → identiques ; suite complète au premier plan (`> ledger/tN-suite.log 2>&1`) ; `make check-size` ; `grep -rn "app.core.<module>" backend docs CLAUDE.md .claude --include='*.py' --include='*.md'` vide hors `docs/superpowers/`.

## Review Focus

- **Cours périmé / absent** : sans réponse Yahoo, une position garde le dernier cours stocké (`stale=True`) et le portefeuille l'indique ; sans aucun cours, valorisation au coût. Couvert par les instantanés (aucun appel réseau n'aboutit en test) et `tests/test_holdings_rebuild.py`.
- **Vente au-delà de la position / opération antérieure au Point Zéro** : vente ignorée avec avertissement journalisé ; 422 avec le même message à la création. Couvert par `tests/test_holdings_rebuild.py` et `tests/test_investment_transactions*.py` ; ajouter le test de l'étape 1 de la tâche 6 si absent.
- **Yahoo injoignable pendant l'actualisation d'un profil** : 502 `"Yahoo Finance est injoignable, réessayez plus tard"` (route unitaire), arrêt sans erreur (tâche de fond). Couvert par `tests/test_etf_composition.py`.
- **Profil ETF créé à la volée par le scanner de diversité** : effet de bord persistant (rattachement des positions) ; l'ordre des routes dans l'instantané de la tâche 1 le fige (diversité avant `/etf-profiles`).
- **Conversion de devise indisponible** : une conversion datée sans taux donne `None` (FxBook, rejeu) et non une erreur ; le compte complémentaire de la tâche 1 porte un titre en USD avec taux historiques stockés pour couvrir le chemin FX.

---

### Task 1 : Instantanés des routes du portefeuille

**Files:**
- Create: `backend/tests/test_portfolio_snapshots.py`, `backend/tests/snapshots/portfolio/*.json`
- Modify: rien d'autre (la fixture et les helpers de `tests/test_analytics_snapshots.py` sont importés tels quels)

**Interfaces:**
- Réutilise `snapshot_client` (fixture), `_normalize`, `_first_diff`, `FROZEN_NOW` de `tests/test_analytics_snapshots.py` (import `from test_analytics_snapshots import …`, `tests/` est sur le `sys.path` de pytest ; la fixture est réexportée dans le module pour être découverte).
- `_add_portfolio_cases(db) -> dict[str, int]` : ajoute un compte `CTO Instantané` (`investissement`, `valuation_mode="positions"`, EUR) avec `holdings_baseline_date = 2025-06-02`, un inventaire (`ESE.PA` 10 parts PRU 400, `AAPL` 5 parts PRU 150 USD), un snapshot Point Zéro au 2025-06-02 et trois snapshots postérieurs (dont un écart > 2 % pour `flagged`), des cours `security_prices` hebdomadaires de 2025-05-01 à 2026-06-15 pour les deux titres, des taux `historical_exchange_rates` USD hebdomadaires sur la même période, un versement, un achat `CW8.PA`, une vente partielle `AAPL` (plus-value réalisée), des frais, un dividende `CW8.PA` avec retenue ; puis `rebuild_holdings` et `commit`. Renvoie `{"cto": id}`.
- `PORTFOLIO_ROUTES` (nom, chemin, paramètres), **dans cet ordre** : `/analytics/portfolio` ; `/analytics/portfolio/{id}` pour PEA, assurance-vie et CTO ; `/analytics/dividends` (défaut, `months=12`, `account_id=pea`, `account_id=cto`) ; `/holdings` (tous, PEA, CTO) ; `/holdings/estimate-costs?account_id=cto` ; `/investment-transactions?account_id=cto` ; `/analytics/diversity-scanner` (tous, PEA) ; `/etf-profiles` ; `/analytics/investments/{cto}` et `/performance-history` ; `/analytics/actions` (la règle `broker_reconciliation` doit y produire une action). Les ids d'objets créés en base sont figés par l'ordre d'insertion ; les champs `created_at`/`updated_at` sont figés par `freezegun`.
- Patch réseau de la composition ETF : `monkeypatch.setattr(etf_analyzer, "fetch_yahoo_composition", none)` (renvoie `None`), repointé en tâche 3.
- Régénération : `UPDATE_SNAPSHOTS=1` ne réécrit que `tests/snapshots/portfolio/` ; orphelins signalés comme dans la phase 3.

- [ ] **Step 1 : Écrire le test**, générer (`UPDATE_SNAPSHOTS=1 PYTHONPATH=. python3.11 -m pytest tests/test_portfolio_snapshots.py`), relire `portfolio_cto.json` : `history` non nul, `twr_pct` et `xirr_pct` non nuls, `reconciliation` avec un `flagged: true`, `realized_eur ≠ 0`, `fx_effect_eur` non nul, `withholding_eur > 0` ; `actions.json` contient `reconciliation-gap`. Compléter les données sinon.
- [ ] **Step 2 : Stabilité** : deux passages sans la variable → PASS ; `tests/test_analytics_snapshots.py` toujours PASS ; suite complète verte.
- [ ] **Step 3 : Preuve** : modifier temporairement `RECONCILIATION_THRESHOLD_PCT = 2.0` → `3.0` → échec sur `portfolio_cto.json` ; annuler. Consigner au ledger.
- [ ] **Step 4 : Commit** — `test: instantanés des routes du portefeuille (compte titres avec Point Zéro)`

### Task 2 : Données de marché

**Files:** `git mv backend/app/core/market_data.py backend/app/services/market/quotes.py` puis découpe ; Create `backend/app/integrations/yahoo_finance.py`, `backend/app/repositories/security_prices.py`, `backend/app/repositories/etf_profiles.py`, `backend/app/domain/market.py`, `backend/app/domain/etf_profiles.py`, `backend/app/services/market/{__init__,search,suggestions}.py`, `backend/tests/test_domain_market.py` ; Modify `controllers/market.py`, `controllers/holdings.py`, `controllers/analytics/{dividends,diversity}.py`, `core/{portfolio,dividends}.py`, `services/recurring.py`, `main.py`, et les 8 tests du piège 10.

**Interfaces:**
- `integrations/yahoo_finance.py` : `HEADERS`, `client(timeout: float) -> httpx.AsyncClient`, `async fetch_chart(client, sym, params) -> dict | None` (ex-`_fetch_chart`), `async search_quotes(query: str) -> list[dict]` (liste brute `quotes` de Yahoo, `[]` si statut ≠ 200 ; les exceptions remontent, le service les journalise comme avant).
- `domain/market.py` : `QUOTE_SUFFIX_CURRENCIES`, `guess_quote_currency(symbol) -> str`, `normalize_price(price, raw_currency) -> tuple[float, str]`, `to_eur(price, currency, rates) -> float | None` (garde son `logger.warning`), `extract_asset_clean_name(note) -> str | None`.
- `domain/etf_profiles.py` : `match_profile(profiles: list[EtfProfile], symbol, isin=None, name=None) -> EtfProfile | None` (corps de `_match_etf_profile` sans la requête), `profile_matches_query(profile, q_lower) -> bool` (filtre local de la recherche).
- `repositories/security_prices.py` : `store_price(db, ticker, day, close, currency, source="yahoo")`, `latest(db, ticker, on_or_before=None)`, `latest_demo(db, sym)`, `series(db, ticker) -> list[tuple[date, float, str]]` (pour `PriceBook`, tâche 5), `held_tickers(db) -> list[str]`.
- `repositories/etf_profiles.py` : `all_profiles(db) -> list[EtfProfile]` (ordre de la requête actuelle, sans `order_by`).
- `services/market/quotes.py` : `_QUOTES_CACHE`, `CACHE_TTL`, `get_market_quotes(symbols, db=None)` (découpée : `_cached_or_demo(...)`, `_fetch_quote(client, sym, rates, now, db) -> dict | None`, `_fallback_quote(db, sym, rates, now) -> dict`), `fetch_price_history`, `get_price_on`, `refresh_held_prices`. `_demo_stored_quote` sans `db` (appelants `/market/quote`, `/market/validate`) ouvre et ferme lui-même une `SessionLocal` comme aujourd'hui (le test d'architecture n'interdit pas `app.db` aux services), la requête passant par `repositories/security_prices.latest_demo`.
- `services/market/search.py` : `search_market_assets(query, db=None)` (< 80 : `_local_matches(db, cleaned)`, `_yahoo_matches(db, cleaned, seen)`), `validate_symbol(db, term) -> dict` (corps de la route `/market/validate`), `match_etf_profile(db, symbol, isin=None, name=None)` (repository + `domain.match_profile`).
- `services/market/suggestions.py` : `suggest_holdings_from_notes(db, account_id)`.
- `services/market/__init__.py` : vide (pas de ré-export ; les importeurs visent les sous-modules).
- `tests/test_business_fixes.py:279` importe `match_etf_profile` depuis `app.services.market.search`.

- [ ] **Step 1 : Tests de domaine** (`tests/test_domain_market.py`) : `test_guess_quote_currency` (reprend les 4 cas de `test_holdings_rebuild.py:237-240`, qui est alors supprimé de ce fichier), `test_normalize_price_pence` (`(1234.0, "GBp") → (12.34, "GBP")`), `test_extract_asset_clean_name` (`"Achat Apple" → "Apple"`, `"x" → None`), `test_match_profile_by_alias_and_name` (profils en mémoire) → FAIL.
- [ ] **Step 2 : Découper**, repointer importeurs et patchs (`monkeypatch.setattr(yahoo_finance, "fetch_chart", …)`, `quotes._QUOTES_CACHE.clear()`, `monkeypatch.setattr(quotes, "get_price_on", …)` dans `test_recurring_transfers.py` avec `services/recurring.py` appelant `quotes.get_price_on` par attribut).
- [ ] **Step 3 : Vérifier** (recette, étape 6) ; entrées `core/market_data.py*` absentes de la baseline ; `controllers/market.py` n'appelle que `services.market`.
- [ ] **Step 4 : Commit** — `refactor(market): données de marché en intégration Yahoo, repository des cours et services/market`

### Task 3 : Profils ETF et composition

**Files:** `git mv backend/app/core/etf_analyzer.py backend/app/services/etf_profiles.py` puis édition ; `git rm backend/app/core/seeds_etf.py` après extraction ; Create `backend/app/domain/etf_presets.json`, `backend/app/domain/etf_presets.py` ; Modify `integrations/yahoo_finance.py`, `domain/etf_profiles.py`, `repositories/etf_profiles.py`, `controllers/etf_profiles.py`, `controllers/analytics/diversity.py`, `services/seeds.py`, `main.py`, `models/etf_profile.py` (commentaire), `tests/test_etf_composition.py`, `tests/test_diversity_scanner.py`, `tests/test_portfolio_snapshots.py` (patch).

**Interfaces:**
- `integrations/yahoo_finance.py` += `YahooUnavailable`, `YAHOO_SECTOR_LABELS`, `QUOTE_SUMMARY_URL`, `_yahoo_auth`, `ensure_crumb(client, force=False)`, `parse_top_holdings(top) -> dict`, `async fetch_composition(symbol) -> dict | None`.
- `domain/etf_profiles.py` += `SOURCE_YAHOO/PRESET/MANUAL`, `COMPOSITION_FIELDS`, `YAHOO_FIELDS`, `REFRESH_INTERVAL`, `load_sources(profile) -> dict`, `apply_composition(profile, composition) -> list[str]`, `to_read(profile) -> EtfProfileRead` (ex-`_to_read_model`), `new_profile(payload) -> EtfProfile` et `apply_update(profile, payload) -> None` (champs + sources `manual`).
- `domain/etf_presets.py` : `SYSTEM_ETF_PRESETS: list[dict]` chargé depuis `etf_presets.json` (même contenu, même ordre ; vérifié par `tests/test_etf_presets.py::test_presets_match_legacy_data` écrit **avant** la suppression de `seeds_etf.py` en comparant les deux, puis réduit à `test_presets_shape` : 5 profils, champs `name/ticker/isin/aliases/countries/sectors/top_holdings`).
- `repositories/etf_profiles.py` += `list_ordered(db)`, `get(db, id)`, `find_by_ticker_or_name(db, ticker, name)`, `find_by_symbol_or_alias(db, sym)`, `find_by_name(db, name)`, `held_profiles(db)`, `attach_to_holdings(db, sym, profile_id)`, `add(db, profile)`, `delete(db, profile)`.
- `services/etf_profiles.py` : `list_profiles`, `get_profile` (`NotFoundError("ETF profile not found")`), `create_profile` (`InvalidOperationError("An ETF profile with this name or ticker already exists")`), `update_profile`, `delete_profile` (`InvalidOperationError("Cannot delete system preset ETF profiles")`), `refresh_profile(db, id)` (`ExternalServiceError("Yahoo Finance est injoignable, réessayez plus tard")`), `refresh_held_etf_profiles(db, force=False)`, `refresh_etf_profile(db, profile)`, `auto_decompose_and_create_profile(db, symbol, name=None, isin=None)`, `auto_decompose(db, payload)` (`InvalidOperationError("Could not decompose ETF profile online")`), `seed_etf_profiles(db)`. Tous renvoient des `EtfProfileRead` côté routes. Appels Yahoo par attribut (`yahoo_finance.fetch_composition`).

- [ ] **Step 1 : Tests** : `tests/test_etf_presets.py::test_presets_match_legacy_data` (compare `domain.etf_presets.SYSTEM_ETF_PRESETS` à `core.seeds_etf.SYSTEM_ETF_PRESETS`) → FAIL ; générer le JSON (`json.dumps(…, ensure_ascii=False, indent=1)`) → PASS ; `tests/test_domain_etf_profiles.py::test_apply_composition_keeps_manual_fields` → FAIL.
- [ ] **Step 2 : Déplacer et découper**, repointer `tests/test_etf_composition.py` (`yahoo_finance.fetch_composition`, `yahoo_finance.parse_top_holdings`, `yahoo_finance.YahooUnavailable`) ; puis réduire le test de présets à `test_presets_shape` et supprimer `core/seeds_etf.py`.
- [ ] **Step 3 : Vérifier** ; `core/seeds_etf.py` absent de la baseline ; aucun `HTTPException` dans `controllers/etf_profiles.py`.
- [ ] **Step 4 : Commit** — `refactor(etf): profils ETF dans services/, composition Yahoo en intégration, préréglages en JSON`

### Task 4 : Dividendes et positions (rejeu, reconstruction, estimation du PRU)

**Files:** `git mv backend/app/core/holdings.py backend/app/services/holdings/replay.py`, `git mv backend/app/core/dividends.py backend/app/services/dividends.py`, puis découpe ; Create `backend/app/domain/holdings.py`, `backend/app/domain/dividends.py`, `backend/app/repositories/holdings.py`, `backend/app/repositories/investment_transactions.py`, `backend/app/services/holdings/{__init__,rebuild,cost_estimates}.py`, `backend/tests/test_domain_holdings.py`, `backend/tests/test_domain_dividends.py` ; Modify tous les importeurs (`grep -rn "core.holdings\|core.dividends" backend`), `models/holding_baseline_item.py` (commentaire).

**Interfaces:**
- `domain/holdings.py` : `BUY_TYPES`, `SELL_TYPES`, `TRADE_TYPES`, `EPSILON`, `normalize_ticker`, `is_trade`, `RealizedSale`, `Replay`, `Position` (ex-`_Position`, renommé : il est importé hors du module), `CostEstimate`, `buy_cost_average(...)` / `sell_ratio(...)` si l'extraction du rejeu en dégage (calculs sur une `Position` sans conversion).
- `domain/dividends.py` : `DIVIDEND_TYPE`, `CRYPTO_ALIASES`, `match_dividend_ticker`, `DividendRow`, `HoldingDividends`, `summarize_by_holding`.
- `repositories/holdings.py` : `baseline_items(db, account_id, order_by_id=False)`, `baseline_item(db, account_id, ticker)`, `account_holdings(db, account_id)` (ordre `id`), `holdings_by_ticker(db, account_id) -> dict`, `delete_holding(db, h)`, `add_holding(db, h)`.
- `repositories/investment_transactions.py` : `trades(db, account_id, until=None)` (filtres et tri actuels de `replay_account` / `estimate_baseline_costs`), `buys(db, account_id)`, `dividends(db, account_id=None)`, `delete_reinvestments(db, dividend_id)`, `account_currencies(db) -> dict[int, str]`.
- `services/holdings/replay.py` : `replay_account(db, account_id) -> Replay` (< 80 : `_load_baseline(...)`, `_apply_buy(...)`, `_apply_sell(...)`), `trade_cutoff(db, account_id, ticker)`, `convert(db, amount, from_cur, to_cur, when)` (ex-`_convert`).
- `services/holdings/rebuild.py` : `rebuild_holdings(db, account_id)` (ne commit pas, `flush`).
- `services/holdings/cost_estimates.py` : `estimate_baseline_costs(db, account_id) -> list[CostEstimate]` (< 80 : `_amount_only_buys(...)`, `_estimate_item(...)`).
- `services/holdings/__init__.py` : vide.
- `services/dividends.py` : `load_dividends_eur(db, account_id=None)`, `sync_reinvestment(db, dividend)`.
- Les appels de conversion restent par attribut de module si un test patche `convert_amount` (vérifier `grep -rn "convert_amount" backend/tests`).

- [ ] **Step 1 : Tests de domaine** : `test_is_trade` (achat sans quantité → False), `test_match_dividend_ticker_crypto_alias` (« Dividende Bitcoin » + `BTC-EUR` → `BTC-EUR`), `test_match_dividend_ticker_ambiguous_is_none`, `test_summarize_by_holding_last_12m` (deux lignes à 400 et 10 jours de la date passée) → FAIL. Les tests existants de `test_dividends.py` qui importent `match_dividend_ticker` visent `app.domain.dividends`.
- [ ] **Step 2 : Découper** ; l'import local de `estimate_baseline_costs` (piège 13) devient un import de module.
- [ ] **Step 3 : Vérifier** ; entrées `core/holdings.py*` absentes de la baseline.
- [ ] **Step 4 : Commit** — `refactor(holdings): rejeu des positions et dividendes dans services/, règles pures dans domain/`

### Task 5 : Valorisation du portefeuille (`compute_portfolio`)

**Files:** `git mv backend/app/core/portfolio.py backend/app/services/portfolio/compute.py` puis découpe ; Create `backend/app/domain/performance.py`, `backend/app/domain/portfolio.py`, `backend/app/repositories/portfolio.py`, `backend/app/services/portfolio/{__init__,books,cash,positions,opening,history,income}.py`, `backend/tests/test_domain_performance.py` ; Modify importeurs (`services/analytics/{portfolio,investments/*,budget/summary}.py`, `services/{wealth,tax}.py`, `services/audit/rules/broker_reconciliation.py`, `repositories/analytics/investments.py`), `tests/test_portfolio.py` (imports `twr`/`xirr` → `app.domain.performance` ; patch `get_exchange_rates`), `tests/test_tax_api.py:257` (patch par chaîne).

**Interfaces:**
- `domain/performance.py` : `xirr(flows) -> float | None`, `twr(points) -> float | None` (corps inchangés ; `twr` importe `EPSILON` de `domain/holdings`).
- `domain/portfolio.py` : `RECONCILIATION_THRESHOLD_PCT`, `SNAPSHOT_MATCH_DAYS`, `PRE_INVENTORY_RATIO`, `MIN_XIRR_DAYS`, `INTEREST_CATEGORIES`, `FEE_KEYWORDS`, `CashEvent`, `classify_regular_flow(tx)`, `sample_days(start, end, extra)`, `uses_positions(account, replay)`, `history_point(day, value, invested) -> dict` (dictionnaire de point de courbe, arrondis actuels), `reconciliation_line(snapshot_date, snapshot_value, computed) -> dict`.
- `repositories/portfolio.py` : `price_series` n'y est pas (c'est `security_prices.series`) ; `latest_zero_point(db, account_id)`, `snapshot_near(db, account_id, before)`, `snapshots_before(db, account_id, day)`, `snapshots_since(db, account_id, day)`, `latest_snapshot(db, account_id)`, `investment_transactions(db, account_id)` (tri date, id), `regular_transactions(db, account_id, transfers_only)`, `only_transfer_legs(query)` (importé par `repositories/analytics/investments.py`), `holdings_meta(db, account_id) -> dict[str, PortfolioHolding]`.
- `services/portfolio/books.py` : `PriceBook` (charge via `security_prices.series`), `FxBook`, `ensure_history(db, book, tickers, start, fetch)`, `_HISTORY_ATTEMPTS`, `HISTORY_RETRY` (appel `quotes.fetch_price_history` par attribut).
- `services/portfolio/cash.py` : `cash_events(db, account_id, after) -> tuple[list[CashEvent], bool]`.
- `services/portfolio/positions.py` : `value_positions(db, replay, quotes, fx, holdings_meta) -> PositionsValuation` (dataclass : `lines`, `value_eur`, `unrealized_eur`, `unrealized_cost_eur`, `fx_effect_eur`, `cost_known_eur`, `unpriced`, `stale`), cumul dans l'ordre actuel des tickers (piège 14).
- `services/portfolio/opening.py` : `opening_value(db, account, replay, book, fx, currency) -> tuple[float, float, bool]` (valeur, espèces, approximation).
- `services/portfolio/history.py` : `history_series(...) -> tuple[list[dict], float | None, list[dict]]` (points, TWR, rapprochement).
- `services/portfolio/income.py` : `realized_summary(replay) -> tuple[dict, float, int]`, `dividend_totals(db, account_id, today) -> tuple[float, float, float]`, `fees_eur(db, account_id, baseline_date, currency, fx) -> float`.
- `services/portfolio/compute.py` : `compute_portfolio(db, account, *, fetch=True, history=True) -> dict` (orchestration < 80, sortie identique, clé `_xirr_flows_eur` comprise), `positions_values_eur(db, accounts)`.
- `services/portfolio/__init__.py` : exporte `compute_portfolio`, `positions_values_eur` (API publique du package) ; les autres importeurs visent les sous-modules ou `domain`.

- [ ] **Step 1 : Tests de domaine** (`tests/test_domain_performance.py`) : `test_xirr_doubling_in_one_year` (−100 au 2025-01-01, +200 au 2026-01-01 → ≈ 1.0 à 1e-6), `test_xirr_single_sign_is_none`, `test_twr_ignores_flows` ((j0, 100, 0), (j1, 210, 100) → 0.1), `test_sample_days_includes_bounds_and_extra` ; les tests `xirr`/`twr` de `test_portfolio.py` déplacés ici → FAIL.
- [ ] **Step 2 : Découper** étape par étape (positions, puis espèces/ouverture, puis revenus, puis courbe), instantanés après chacune.
- [ ] **Step 3 : Vérifier** ; entrées `core/portfolio.py*` absentes ; `ls backend/app/core` = `config errors logging login_events login_rate_limit mcp_tokens migrations security time totp` (+ `__init__`).
- [ ] **Step 4 : Commit** — `refactor(portfolio): valorisation des comptes titres découpée en services/portfolio, XIRR/TWR dans domain/`

### Task 6 : Opérations d'investissement

**Files:** Create `backend/app/services/investment_transactions.py` ; Modify `repositories/investment_transactions.py`, `controllers/investment_transactions.py` ; Test `backend/tests/test_investment_transactions_service.py`.

**Interfaces:**
- `services/investment_transactions.py` : `VALID_TYPES`, `TRADE_FIELDS`, `DIVIDEND_FIELDS`, `TYPE_ERROR` ; `list_transactions(db, account_id, skip, limit)`, `link_dividends(db, account_id, dry_run) -> dict`, `create_transaction(db, payload) -> InvestmentTransaction`, `update_transaction(db, id, payload)`, `delete_transaction(db, id)` ; étapes < 80 : `_validate_new(db, account, tx_type, payload)`, `_check_zero_point(db, account_id, day)`, `_amount_in_account_currency(db, account, amount, currency, day)`, `_normalize_update(db, tx, account, data)`, `_persist(db, tx, account_id, *, sync_dividend, flag)` (flush → `sync_reinvestment` → `rebuild_holdings` → `_flag_distributing` → `commit` → `refresh`, dans cet ordre, piège 12).
- Erreurs : 404 `NotFoundError("Account not found" | "Investment transaction not found")` ; 422 `BusinessRuleError(<message actuel>)` ; 409 `ConflictError(<message actuel>)`. Messages copiés à l'identique.
- `repositories/investment_transactions.py` += `list_for(db, account_id, skip, limit)`, `get(db, id)`, `dividend_link_candidates(db, account_id) -> dict[str, str]` (ordre : positions, inventaire, opérations), `unlinked_dividends(db, account_id)`, `linked_bank_transactions(db, tx_id)`, `holding(db, account_id, ticker)`, `add(db, tx)`, `delete(db, tx)`.

- [ ] **Step 1 : Tests de service** : `test_trade_before_baseline_is_rejected` (`BusinessRuleError`, message commençant par « Opération sur CW8.PA antérieure au Point Zéro »), `test_reinvested_purchase_cannot_be_deleted` (`ConflictError`), `test_dividend_requires_ticker` → FAIL (module absent).
- [ ] **Step 2 : Déplacer** ; le controller ne contient plus que les signatures.
- [ ] **Step 3 : Vérifier** ; entrées `controllers/investment_transactions.py*` absentes ; `grep -nE "db\.|HTTPException|app\.models" backend/app/controllers/investment_transactions.py` vide.
- [ ] **Step 4 : Commit** — `refactor(investment-transactions): opérations d'investissement dans services/`

### Task 7 : Positions et inventaire Point Zéro (controller `holdings`)

**Files:** Create `backend/app/services/holdings/{inventory,enrich}.py` ; Modify `repositories/holdings.py`, `controllers/holdings.py` ; Test `backend/tests/test_holdings_service.py`.

**Interfaces:**
- `services/holdings/enrich.py` : `enrich_holding(holding, quotes, rates, divs) -> PortfolioHoldingRead` (le calcul pur gain / rendement total va dans `domain/holdings.py::holding_returns(quantity, price_eur, cost_basis_eur, buy_price_avg, fx, dividends_total) -> dict`), `enrich_all(db, holdings)`.
- `services/holdings/inventory.py` : `list_holdings(db, account_id)`, `suggestions(db, account_id)`, `cost_estimates(db, account_id) -> list[CostEstimateRead]`, `apply_costs(db, payload)`, `set_baseline(db, payload)`, `create_holding(db, payload)`, `update_holding(db, id, payload)`, `delete_holding(db, id)`. Erreurs aux messages actuels (`NotFoundError("Account not found" | "Holding not found")`, `BusinessRuleError` pour les 422, `ConflictError` pour le 409).
- `repositories/holdings.py` += `list_all(db, account_id=None)`, `get(db, id)`, `delete_baseline(db, account_id, ticker=None)`, `later_trade_exists(db, account_id, ticker, cutoff) -> bool`.

- [ ] **Step 1 : Tests de service** : `test_update_quantity_without_baseline_is_rejected` (`BusinessRuleError`), `test_delete_holding_with_later_trade_conflicts` (`ConflictError`), `test_holding_returns_include_dividends` (domaine : coût 100, valeur 120, dividendes 5 → `total_return_pct == 25.0`) → FAIL.
- [ ] **Step 2 : Déplacer.**
- [ ] **Step 3 : Vérifier** (instantanés `holdings_*`, `estimate_costs_*`) ; controller sans `db.`, `HTTPException`, `app.models`.
- [ ] **Step 4 : Commit** — `refactor(holdings): inventaire Point Zéro et positions enrichies dans services/holdings`

### Task 8 : Routes analytics du portefeuille et des dividendes

**Files:** Create `backend/app/services/analytics/dividends.py` ; Modify `services/analytics/portfolio.py`, `domain/dividends.py`, `controllers/analytics/{portfolio,dividends}.py`, `repositories/holdings.py` ; Test `backend/tests/test_domain_dividends.py`.

**Interfaces:**
- `services/analytics/portfolio.py` += `portfolio_account(db, account_id) -> PortfolioRead` (`NotFoundError("Account not found")`, `BusinessRuleError("Account must be investissement or assurance_vie")`).
- `domain/dividends.py` += `month_keys(end, months) -> list[str]`, `aggregate_dividends(rows, since) -> DividendAggregates` (totaux, par mois, par année, par titre, non rattachés : boucle actuelle), `position_values(holdings, quotes) -> dict[str, dict]`, `dividend_tickers(by_ticker, positions) -> list[DividendTicker]` (tri par total décroissant).
- `services/analytics/dividends.py` : `compute_dividends(db, account_id, months) -> DividendSummary` (< 80).
- `repositories/holdings.py` += `held_positions(db, account_id=None)` (quantité > 0).

- [ ] **Step 1 : Tests** : `test_month_keys_wraps_year` (`end=2026-02`, 3 mois → `["2025-12", "2026-01", "2026-02"]`), `test_aggregate_dividends_unlinked` → FAIL.
- [ ] **Step 2 : Déplacer.**
- [ ] **Step 3 : Vérifier** ; entrée `get_dividends` absente ; les deux controllers sans `db.`/`HTTPException`/`app.models`.
- [ ] **Step 4 : Commit** — `refactor(analytics): portefeuille par compte et dividendes dans services/analytics`

### Task 9 : Scanner de diversification

**Files:** Create `backend/app/services/analytics/diversity.py`, `backend/app/domain/diversity.py`, `backend/app/repositories/analytics/diversity.py`, `backend/tests/test_domain_diversity.py` ; Modify `controllers/analytics/diversity.py`.

**Interfaces:**
- `domain/diversity.py` : `UNKNOWN_LABEL`, `normalize_company_key(ticker, name)`, `spread_weights(target, weights_json, value_eur)`, `hhi_score(weights) -> float`, `score_label(score) -> str`, `look_through(valued_holdings, profile_for) -> LookThrough` (sociétés, pays, secteurs, ETF, compositions ; `profile_for` = fonction ticker → profil, résolue par le service), `exposure_rows(values, total_stocks, total_wealth) -> list[dict]`, `top_companies(companies, total_stocks, total_wealth) -> list[dict]`, `diversity_alerts(companies, countries, sectors) -> list[dict]` (messages copiés à l'identique).
- `repositories/analytics/diversity.py` : `holdings(db, account_id)`, `active_accounts(db)`, `latest_snapshot(db, account_id)`, `last_transaction(db, account_id)`.
- `services/analytics/diversity.py` : `compute_diversity(db, account_id) -> dict` (< 80) ; étapes `_value_holdings(db, holdings, quotes, rates)` (dont rattachement/création de profil et son `commit`/`rollback`, piège 12), `_wealth_context(db, rates) -> dict`. `rates` est lu **deux fois** comme aujourd'hui (`fx_rates` puis `rates`) : garder les deux appels.

- [ ] **Step 1 : Tests de domaine** : `test_hhi_score_single_asset_is_low` (`[100.0] → 10.0`), `test_hhi_score_empty_is_50`, `test_spread_weights_uncovered_goes_to_unknown` (poids 60 % → 40 % en « Non renseigné »), `test_normalize_company_key_strips_suffix` (`(None, "Apple Inc") → "NAME:apple"`) → FAIL ; les tests équivalents de `test_diversity_scanner.py` qui importent les fonctions privées sont repointés.
- [ ] **Step 2 : Déplacer.**
- [ ] **Step 3 : Vérifier** ; entrées `controllers/analytics/diversity.py*` absentes ; `scripts/code_size_baseline.json` ne contient plus aucune clé `backend/`.
- [ ] **Step 4 : Commit** — `refactor(analytics): scanner de diversification dans services/ et domain/`

### Task 10 : Clôture de la phase 4

**Files:** `ARCHITECTURE.md`, `CLAUDE.md`, `backend/CLAUDE.md`, skills `numera-backend` / `numera-expert` / `numera-testing`, plan maître.

- [ ] **Step 1 : Périmètre** : `grep -rnE "db\.(query|add|commit|get|delete)|HTTPException|from app\.models" backend/app/controllers/{investment_transactions,holdings,etf_profiles,market}.py backend/app/controllers/analytics/{portfolio,dividends,diversity}.py` → vide ; `ls backend/app/core` = transverse seul.
- [ ] **Step 2 : Docs** : arborescence et § Couches de `ARCHITECTURE.md` (ligne 42 : plus de modules de phase 4 dans `core/`) ; tous les emplacements cités (`grep -rnE "core/(portfolio|holdings|dividends|market_data|etf_analyzer|seeds_etf)" --include='*.md' . | grep -v docs/superpowers`) ; skill `numera-testing` : les deux tests d'instantanés ; plan maître : phase 4 terminée, section « Reprendre la phase 5 » sur le modèle de la section 0 ci-dessus.
- [ ] **Step 3 : Suite complète, `make check-size`, `cd frontend && npm run build`.**
- [ ] **Step 4 : Relecture finale** (Review Focus point par point), rulings et `minor (deferred)` rapportés à l'utilisateur.
- [ ] **Step 5 : Commit** — `docs: phase 4 de la migration en couches terminée`
