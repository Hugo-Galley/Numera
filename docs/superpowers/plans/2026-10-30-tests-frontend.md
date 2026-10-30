# Tests frontend : plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (ou superpowers:subagent-driven-development pour les lots parallèles) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Doter `frontend/` d'une suite de tests automatisés, lancée en CI, qui couvre d'abord ce qui casse le plus souvent sans que `tsc` le voie : utilitaires (formats, dates, jetons), client API (JWT, 401, erreurs), providers, redirections de routes, puis les parcours critiques (connexion, saisie de transaction, import, revue du mois).

**Non-objectifs :** aucun changement de comportement ; pas de test des primitives `components/ui/` (shadcn) ni des calculs de KPI (backend, déjà couverts par `test_analytics_snapshots.py`) ; pas d'objectif de pourcentage de couverture au départ (voir lot 8).

**Tech Stack :** Vitest (même config que Vite, alias `@/` repris) · jsdom · @testing-library/react + user-event + jest-dom · MSW (Mock Service Worker, mode Node) pour simuler l'API au niveau réseau, sans mocker `lib/api.ts` · Playwright en option pour l'E2E (lot 7).

---

## 0. Conventions (valables pour tous les lots)

- **Emplacement :** test à côté du fichier testé, `X.test.ts(x)` (ex. `lib/utils.test.ts`, `pages/AccountDetail/index.test.tsx`). Outils partagés dans `src/test/` (exclu du build Vite et du plafond de taille seulement s'il le faut).
- **Rendu :** toujours via `renderWithProviders(ui, { route, auth })` de `src/test/render.tsx` (MemoryRouter + `AuthProvider` + `UIProvider` + `ConfirmProvider` + `Toaster`), jamais un `render` nu pour un composant qui dépend d'un provider.
- **Requêtes :** par rôle et libellé français (`getByRole("button", { name: "Enregistrer" })`), pas par classe CSS ni `data-testid` sauf dernier recours.
- **API :** handlers MSW par domaine dans `src/test/handlers/<domaine>.ts` (même découpage que `lib/api/<domaine>.ts`), agrégés dans `src/test/server.ts`. Un test qui a besoin d'une réponse particulière la surcharge avec `server.use(...)`. `onUnhandledRequest: "error"` : toute requête non prévue fait échouer le test.
- **Fixtures de données :** petites fabriques typées dans `src/test/factories.ts` (`makeAccount`, `makeTransaction`…), pas de copie de la démo entière.
- **Dates :** `TZ=Europe/Paris` fixé dans la config Vitest ; `vi.useFakeTimers({ toFake: ["Date"] })` + `vi.setSystemTime` quand le test dépend d'aujourd'hui.
- **Vérifier l'effet, pas l'appel :** après une mutation, vérifier la requête reçue par MSW (corps, méthode) **et** ce qui s'affiche (toast, ligne mise à jour), comme côté backend on vérifie la base.
- **Un bug frontend corrigé = un test rouge d'abord** (même discipline que `numera-tdd`, appliquée au front une fois le lot 0 livré).

## Dépendances et répartition

```
Lot 0 (socle) ──┬── Lot 1 (lib pure)            ┐
                ├── Lot 2 (client API)          │ parallélisables :
                ├── Lot 3 (hooks + providers)   │ fichiers disjoints,
                ├── Lot 4 (routing + layout)    │ un handler MSW par domaine
                ├── Lot 5 (pages critiques) ────┤
                └── Lot 6 (formulaires métier) ─┘
Lot 7 (E2E Playwright, optionnel) : après 0, indépendant du reste
Lot 8 (cliquet de couverture) : en dernier
```

Le lot 0 est **séquentiel et bloquant**. Ensuite chaque lot (et chaque tâche des lots 5 et 6) peut partir dans sa propre session : ils ne touchent que leurs fichiers `*.test.tsx` et, au plus, leur fichier `src/test/handlers/<domaine>.ts`.

---

## Lot 0 : socle (bloquant)

- [x] **0.1 Dépendances** : `npm i -D vitest @vitest/coverage-v8 jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom msw` (versions compatibles Vite 5, épinglées dans `package-lock.json`).
- [x] **0.2 Config** : `vitest.config.ts` qui étend `vite.config.ts` (`mergeConfig`) : `environment: "jsdom"`, `setupFiles: ["src/test/setup.ts"]`, `env: { TZ: "Europe/Paris" }`, `css: false`, `restoreMocks: true`. `tsconfig` : types `vitest/globals` et `@testing-library/jest-dom` pour les fichiers de test seulement ; vérifier que `vite build` n'embarque pas `src/test/`.
- [x] **0.3 Setup jsdom** (`src/test/setup.ts`) : jest-dom, `cleanup`, polyfills manquants pour Radix et Recharts (`matchMedia`, `ResizeObserver`, `IntersectionObserver`, `scrollIntoView`, `hasPointerCapture`), `localStorage` vidé entre tests, serveur MSW `listen / resetHandlers / close`.
- [x] **0.4 Outils** : `src/test/render.tsx` (`renderWithProviders`, option `auth` qui pose un JWT valide via une fabrique `makeToken({ expInMinutes })`), `src/test/server.ts`, `src/test/handlers/` (un fichier par domaine, vide au départ sauf `auth` et `analytics` minimal), `src/test/factories.ts`.
- [x] **0.5 Test témoin** : `lib/utils.test.ts` avec un cas `formatCurrency` + un rendu `renderWithProviders(<ErrorState …/>)` qui clique « Réessayer », pour prouver jsdom + providers + user-event.
- [x] **0.6 Scripts et CI** : `package.json` → `"test": "vitest run"`, `"test:watch": "vitest"`, `"coverage": "vitest run --coverage"` ; `Makefile` → `make test-front`, et `make validate` l'appelle ; job CI `Frontend` : `npm test` avant `npm run build`.
- [x] **0.7 Documentation (même commit)** : `frontend/src/CLAUDE.md` § Vérification (« Pas de tests ni de lint frontend » devient la commande et les conventions de la section 0), `CLAUDE.md` racine (commandes), skills `numera-testing`, `numera-frontend` et `numera-finishing` (le build ne suffit plus : `npm test` aussi).

## Lot 1 : `lib/` pur (tests unitaires, aucun DOM)

- [x] **1.1 `lib/utils.ts`** : `formatCurrency` (locale fr-FR, espaces insécables, négatifs, autres devises), `formatPercent` / `formatAmountWithShare` (total à 0), `formatRate` (signe, `null`), `getTokenExpiry` / `isTokenExpired` (jeton mal formé, sans `exp`, expiré), `parsePositiveAmount` (virgule décimale, négatif, vide, texte), `errorMessage` (`ApiError` avec `detail` texte / structuré, `Error`, inconnu), `frequencyLabel`.
- [x] **1.2 `lib/dates.ts`** : `toInputValue` / `toNaiveLocal` aller-retour sans décalage UTC (le piège documenté : jamais `toISOString()`), `startOfDayParam` / `endOfDayParam`, `todayLocal` sous horloge figée près de minuit.
- [x] **1.3 `lib/quickEntry.ts`** : `parseQuickEntry` (montant seul, montant + libellé, virgule, signe, entrée invalide → `null`).
- [x] **1.4 `lib/privacyScanner.ts::looksSensitive`** : montants avec devise, milliers, décimales ; faux positifs à éviter (dates, années, pourcentages, numéros).
- [x] **1.5 Divers** : `budgetPeriod.formatPeriodRange`, `storage.safeStorage` (ne lève jamais si `localStorage` jette), `labels`, `countries`.

## Lot 2 : client API (`lib/api.ts` + `lib/api/<domaine>.ts`)

- [x] **2.1 `apiFetch`** : ajoute le Bearer ; `Content-Type: application/json` par défaut ; `API_BASE` selon le mode de build, pas l'hôte (`VITE_API_BASE` sinon dev Vite → `http://localhost:8001`, sinon `/api`, même sur localhost).
- [x] **2.2 Session** : `401` vide la session et redirige vers `/login` ; `403` idem (seulement si `detail` = « User not authorized », un 403 métier reste une erreur ordinaire) **sauf** sur `/auth/token` ; refresh appelé quand il reste moins de 15 min, pas au-delà, et pas en boucle si le refresh échoue.
- [x] **2.3 Erreurs** : `ApiError(status, message, detail)` pour un `detail` texte, un `detail` structuré (`code` / `context`), une réponse non JSON, une erreur réseau.
- [x] **2.4 `api.upload`** (pas de `Content-Type`, Bearer présent) et **`api.download`** (renvoie un `Blob`).
- [x] **2.5 `lib/api/<domaine>.ts`** : une table de cas par domaine (fonction → méthode + URL + query + corps), vérifiée via MSW. Sert aussi de garde-fou contre une route renommée côté backend (à croiser avec `backend/tests/snapshots/openapi_routes.json`, voir 2.6).
- [x] **2.6 (option)** Test qui vérifie que chaque URL appelée par `lib/api/` existe dans `openapi_routes.json` : détecte côté front une route supprimée côté back. A trouvé 2 écarts, corrigés depuis : `POST /categorization-rules` sans « / » final (création de règle du Centre d'Actions), `GET /recurring-transactions/{id}` inexistant (« Valider » du calendrier passe désormais par la liste).

## Lot 3 : hooks et providers

- [ ] **3.1 `useSubmit`** : un second clic pendant l'exécution n'appelle pas deux fois ; `busy` repasse à `false` après une erreur.
- [ ] **3.2 `useDrilldown`** : `openDrilldown` écrit les `?dd_*` dans l'URL, fermeture les retire sans toucher aux autres paramètres.
- [ ] **3.3 `useIsMobile`, `useDemoMode`** (via `matchMedia` simulé / réponse MSW).
- [ ] **3.4 `AuthProvider`** : lecture du jeton au démarrage, jeton expiré ignoré, `logout` vide le stockage.
- [ ] **3.5 `UIProvider`** : thème light / dark / system (classe `dark` sur `<html>`, persistance), bascule du mode confidentialité.
- [ ] **3.6 `ConfirmProvider`** : `await confirm()` résout `true` / `false` selon le bouton, Échap = `false`.
- [ ] **3.7 `startPrivacyScanner`** (DOM) : pose `.privacy-masked` sur un montant inséré après coup (MutationObserver), respecte `data-privacy-ignore`, nettoie à l'arrêt.

## Lot 4 : routing et layout

- [ ] **4.1 `ProtectedRoute`** : sans jeton → `/login` ; avec jeton → contenu.
- [ ] **4.2 Redirections `App.tsx`** : `/report`, `/month-review`, `/comparison`, `/calendar` vers leur nouvelle adresse **en gardant la query** (`RedirectKeepingSearch`) ; route inconnue → `/` ; anciens `?tab=` de `/settings`.
- [ ] **4.3 `ErrorBoundary`** (un composant qui jette affiche l'écran d'erreur, pas une page blanche) et **`ErrorState`** (« Réessayer » rappelle le chargement).
- [ ] **4.4 Sidebar / Omnibox** : chaque entrée de la Sidebar pointe vers une route déclarée ; ⌘K ouvre l'omnibox et une saisie rapide (`parseQuickEntry`) propose la création.

## Lot 5 : pages critiques (intégration avec MSW)

Une tâche = une page, une session possible par tâche. Chaque page : chargement (squelette), succès, **échec de chargement visible** (règle « un échec ne ressemble jamais à “pas de données” »), réponse obsolète ignorée au changement de mois / compte.

- [ ] **5.1 Login** : identifiants faux (message), succès → redirection ; étape TOTP quand `mfa_token` est renvoyé ; limite de débit (`429`) affichée.
- [ ] **5.2 AccountDetail** (`pages/AccountDetail/`) : création, édition et suppression d'une transaction (confirmation `useConfirm`, toast, liste rechargée), corps envoyé avec montant positif + `type` et date naïve sans `Z`.
- [ ] **5.3 Import CSV** : upload multipart, aperçu, catégories manquantes, commit, compte rendu des doublons.
- [ ] **5.4 MonthReview** : clôturer marque le mois (pas de verrouillage de l'UI), transaction exceptionnelle signalée.
- [ ] **5.5 Dashboard** (`useDashboardData`) : un endpoint en échec n'empêche pas les autres onglets de s'afficher (`safeLoad`).
- [ ] **5.6 Classement** : création d'une règle de catégorisation et d'un tag, suppression avec confirmation.
- [ ] **5.7 Settings** : `ProfileForm` exige le mot de passe actuel, une erreur `400` reste sur la page (pas de déconnexion).

## Lot 6 : formulaires et composants métier

Validation zod (message affiché, bouton désactivé pendant l'envoi), envoi correct, toast.

- [ ] **6.1 Récurrences** (`components/recurring/`) : fréquences, salaire / aides (`IncomeTab`).
- [ ] **6.2 Épargne** : objectifs et provisions (`components/savings/`).
- [ ] **6.3 Crédits** (`components/loans/`) : saisie, remboursement anticipé.
- [ ] **6.4 Investissements** : `SecuritySearchInput` (recherche différée, réponses obsolètes ignorées), opération d'investissement, `HoldingsTable` en mode confidentialité.
- [ ] **6.5 Remboursements** et **virements** (`components/reimbursements/`, `components/transfers/`).
- [ ] **6.6 Paramètres** : notifications, MCP (création / révocation de jeton), sauvegardes.

## Lot 7 (optionnel) : E2E Playwright

- [ ] **7.1** Playwright contre l'instance de démo (`make demo`, port 8090, données `make backend-seed-demo`) : connexion → Dashboard → ajout d'une transaction → mode confidentialité (aucun montant lisible) → thème sombre → largeur 375 px.
- [ ] **7.2** Job CI séparé, déclenché manuellement ou la nuit (lent, dépend de Docker), pour ne pas ralentir chaque push.

## Lot 8 : cliquet

- [ ] **8.1** Mesurer la couverture une fois les lots 1 à 6 livrés, fixer `coverage.thresholds` à la valeur atteinte (arrondie vers le bas) et ne jamais la baisser, sur le modèle des baselines backend.

---

## Définition de « terminé » pour chaque lot

`cd frontend && npm test && npm run build` vert, aucun test `skip` / `only` laissé, documentation à jour si une convention change, commit sur `main` (sans branche ni PR).
