# Tests E2E (Playwright)

Parcours critiques de bout en bout : vrai navigateur, vrai frontend (Vite), vrai backend.
Ils complètent Vitest + MSW (qui mocke l'API) et les tests pytest : ils attrapent ce que les mocks ne voient pas
(contrat front ↔ back, auth JWT, redirections).

```bash
make test-e2e                 # ou : cd frontend && npm run test:e2e
cd frontend && npx playwright test login --ui    # un scénario, en mode interactif
cd frontend && npx playwright show-report        # rapport (CI) ; trace : npx playwright show-trace <trace.zip>
```

Premier lancement : `cd frontend && npx playwright install chromium`.

## Fonctionnement

- `playwright.config.ts` lance deux serveurs : le backend (`e2e/backend.sh`) sur **8101** et Vite sur **5174**
  (ports distincts du dev, on peut lancer les E2E pendant un `make dev`).
- `e2e/backend.sh` régénère à chaque lancement `backend/data/e2e-demo.db` (mode démo, identifiants `demo` / `demo`,
  fichier ignoré par git). La vraie base n'est jamais touchée. `E2E_PYTHON=...` force l'interpréteur.
- `auth.setup.ts` se connecte une fois ; les scénarios réutilisent la session. Un scénario qui teste la connexion
  repart d'un navigateur vierge (`test.use({ storageState: { cookies: [], origins: [] } })`).
- Un seul worker : les scénarios qui écrivent partagent la même base.

## Écrire un scénario

- Sélecteurs par rôle / libellé (`getByRole`, `getByLabel`), jamais par classe CSS.
- Attentes explicites (`expect(...).toBeVisible()`), pas de `waitForTimeout`.
- Données créées par le scénario avec un préfixe `E2E ` ; dates relatives à aujourd'hui.
- Peu de scénarios, uniquement des parcours critiques ; pas de captures d'écran de référence.
