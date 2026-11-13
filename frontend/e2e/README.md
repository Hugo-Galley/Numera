# Tests E2E (Playwright)

Parcours utilisateur de bout en bout : vrai navigateur, vrai frontend (Vite), vrai backend sur une base de démo
jetable. Ils complètent Vitest + MSW (qui mocke l'API) et pytest : ils attrapent ce que les mocks ne voient pas
(contrat front ↔ back, auth JWT, redirections, HTML invalide, erreurs console).

```bash
make test-e2e                                   # toute la suite (~4 min), ou : cd frontend && npm run test:e2e
cd frontend && npx playwright test accounts     # un fichier ; -g "motif" pour un scénario ; --ui pour le mode interactif
cd frontend && npx playwright show-report       # rapport HTML ; trace : npx playwright show-trace <trace.zip>
```

Premier lancement : `cd frontend && npx playwright install chromium` (et `make backend-install` pour le backend).
En local les serveurs déjà lancés sur 8101 / 5174 sont réutilisés (itération rapide) ; en CI (`CI=true`) la pile
est toujours démarrée à neuf.

## Scénarios (par parcours)

| Fichier | Parcours |
|---|---|
| `login`, `logout` | connexion, mauvais mot de passe, retour à la page demandée, déconnexion, session expirée (401) |
| `dashboard` | KPI du mois, onglets, filtre de compte, changement de mois, thème sombre, mode confidentialité (`privacy`) |
| `accounts` | liste, fiche d'un compte, création / modification / archivage, rapprochement bancaire |
| `transactions` | saisie, modification, suppression avec confirmation, recherche et filtres, virement interne |
| `import-csv` | aperçu, import, lignes visibles, ré-import = aucun doublon (idempotence) |
| `classement`, `rules` | catégories, tags, marchands, règles de catégorisation |
| `month` | bilan du mois, comparaison, revue de fin de mois et clôture (marquer, jamais verrouiller) |
| `investments` | vue globale, compte titres (positions, recherche), Point Zéro, assurance-vie |
| `savings`, `recurring`, `loans-reimbursements` | objectifs, récurrences et calendrier, salaire, crédit, créances « on me doit » |
| `audit` | Centre d'actions, actualisation, virements internes |
| `settings` | quatre onglets, sécurité, export CSV, zone de danger, profil |
| `tools` | simulateur, fiscalité, bilan annuel |
| `omnibox` | ⌘K : navigation, comptes, fermeture |
| `responsive`, `navigation` | sidebar, 404, redirections, mobile 375 px sans débordement, **chaque route se charge** |

La **garde transversale** (fixture automatique, `fixtures.ts`) fait échouer tout scénario qui provoque une exception
JS, une erreur console applicative (dont le HTML invalide signalé par React) ou une réponse HTTP 5xx, sur
n'importe quelle page. Un scénario qui attend une erreur précise la déclare : `test.use({ ignoredErrors: [/motif/] })`.


## Fonctionnement

- `playwright.config.ts` lance le backend (`e2e/backend.sh`, port **8101**) puis Vite (port **5174**), distincts du
  dev : on peut lancer les E2E pendant un `make dev`.
- `e2e/backend.sh` régénère à chaque lancement `backend/data/e2e-demo.db` (mode démo, identifiants `demo` / `demo`,
  ignoré par git). La vraie base n'est jamais touchée. Le mode démo bloque 2FA, passkeys, jetons MCP, sauvegardes et
  notifications (non testables ici) et plafonne les écritures à 120 par minute.
- `auth.setup.ts` se connecte une fois (`storageState`), tous les scénarios réutilisent la session. Un scénario qui
  teste la connexion repart d'un navigateur vierge (`test.use({ storageState: { cookies: [], origins: [] } })`).
- Un seul worker par pile (base partagée). La CI lance **deux tranches** (`--shard=1/2`, `2/2`), chacune avec sa propre
  pile ; en échec, rapport HTML + traces + captures sont publiés en artefact `playwright-N` (7 jours). `retries: 1` en CI
  seulement.
- Les données de démo sont datées par rapport à aujourd'hui (même jour, mêmes données) : ne jamais asserter un montant
  de la démo, seulement sa présence ou sa structure. Les montants des écritures créées par le scénario, eux, sont connus.

## Écrire un scénario

1. Importer `test` / `expect` depuis `./fixtures` (jamais `@playwright/test` : on perdrait la garde et la neutralisation
   de la pop-up de clôture de mois). Helpers : `openAccount`, `openTransactionMenu`, `confirmDialog`, `visible`, `unique`.
2. Sélecteurs par rôle / libellé (`getByRole`, `getByLabel`), jamais par classe CSS ; `data-testid` seulement s'il n'y a
   aucun sélecteur accessible. Les listes ont deux mises en page (cartes mobiles / tableau) : `visible(page, texte)`.
3. Attentes explicites (`expect(...).toBeVisible()`, `waitForResponse`), jamais `waitForTimeout`.
4. Données créées avec `unique("Sujet")` (préfixe `E2E ` + suffixe horaire) : le scénario se relance sur la même base,
   et se nettoie quand l'écriture est réversible.
5. Nouvelle route dans `App.tsx` : l'ajouter à `ROUTES` dans `navigation.spec.ts`.
6. Un test qui échoue révèle un bug : ne pas écrire un test qui l'accepte ; corriger ou le marquer `test.fail` avec la raison.

## Captures du README

`npm run screenshots` régénère `docs/screenshots/*.png` (1440×900 en @2x) sur la base de démo jetable. Ignoré par `npm run test:e2e`.
