# Frontend — conventions (React 18 / Vite / TypeScript / Tailwind / shadcn)

Complète le `CLAUDE.md` racine. Procédures : skill `numera-frontend`. Le frontend est **purement présentatif** : aucun KPI calculé ici, tout vient de `/analytics/*`.

## Structure

- `App.tsx` : react-router v7. `/login` public ; le reste sous `ProtectedRoute` + `AppLayout` (Sidebar, Omnibox). Routes : `/`, `/accounts`, `/accounts/:id`, `/savings`, `/investments`, `/comparison`, `/report` (page `MonthlyReport.tsx`, composant `IntelligentReport`), `/calendar`, `/recurring`, `/audit` (Centre d'Actions), `/tools`, `/tax` (Fiscalité), `/settings`. Route inconnue → `/`.
- `providers/` : `AuthProvider` (token en `localStorage`, `useAuth()`), `UIProvider` (thème, mode confidentialité `isPrivacyMode`, état de l'omnibox).
- `lib/api.ts` : `api.get/post/put/patch/delete` + `apiFetch`. Ajoute le Bearer ; sur `401` (ou `403` hors `/auth/token`) vide la session et redirige vers `/login`. `API_BASE` : `http://localhost:8001` sur `localhost`, sinon `/api` (reverse proxy nginx en prod → `backend:8001`). Erreurs levées en `ApiError(status, message, detail)`.
- `types/` (un seul fichier : `diversity.ts`) et `hooks/` (vide) : les types d'API sont majoritairement définis localement dans les pages/composants.
- `lib/utils.ts` : `formatCurrency(value, currency="EUR")` (locale `fr-FR`), `cn()`, `isTokenExpired()`.
- `components/ui/` : primitives shadcn/Radix (`button`, `card`, `dialog`, `table`, `tabs`, `select`, `sheet`, `sonner`, `skeleton`…). Ne pas les modifier sans nécessité. Ajouter un composant : `components.json` est configuré pour shadcn.
- `components/<domaine>/` : `investments` (dont `PortfolioSummary` valeur calculée / rapprochement, `DividendsCard`, `HoldingsTable`), `dashboard` (KPI, header, `tabs/` = Overview, History, Budgets, Insights, Investments, Merchants, Projections, Subscriptions), `investments`, `settings`, `tools`, `analytics`, `layout`.

## Règles

- Alias d'import `@/` → `src/`.
- Appels API uniquement via `api` de `@/lib/api` (le JWT et la gestion du 401 y sont centralisés). Uploads multipart : `api.upload(endpoint, formData)` (n'envoie pas `Content-Type`, le navigateur fixe le boundary, mais ajoute le Bearer). Téléchargements de fichiers : `api.download(endpoint)` → `Blob` (jamais `window.location`, qui n'envoie pas le JWT). Les helpers `api.*` ont `T = any` par défaut : typer le générique quand le payload est connu.
- Récupération de données : dans la page, ou dans un hook dédié quand elle est lourde (`components/dashboard/useDashboardData.ts` charge tout le Dashboard avec un `safeLoad` par endpoint pour qu'un échec n'en bloque pas d'autres). Les sous-composants reçoivent des props.
- TypeScript strict. Le code existant utilise encore `any` pour les réponses API ; dans du code nouveau, déclarer des types (`interface`) pour les payloads.
- Montants : toujours `formatCurrency`. Tout montant sensible porte la classe **`amount-blur`** (définie dans `styles.css`, active quand `body.privacy-enabled`, se dévoile au survol). Ne pas utiliser `.amount-value` (n'existe pas).
- Retours utilisateur : `toast.success` / `toast.error` (`sonner`) après chaque mutation ; `Skeleton` pendant le chargement ; état vide avec icône + action.
- Icônes `lucide-react`. Graphiques `recharts` (palette Slate / Emerald / Rose / Amber ; tooltips et légendes obligatoires ; éléments cliquables pour drill-down quand une vue filtrée existe). Sankey/treemap dans `components/analytics`.
- Formulaires : `react-hook-form` + `zod` (+ `@hookform/resolvers`) avec `components/ui/form`.
- Nouvelle fonctionnalité navigable → l'ajouter à la Sidebar et à l'Omnibox (⌘K).

## Vérification

Pas de tests ni de lint frontend. Seul garde-fou : `cd frontend && npm run build` = `tsc --noEmit && vite build` (les erreurs de types bloquent le build ; `npm run typecheck` pour tsc seul). Le projet est à 0 erreur TypeScript : ne pas en introduire. Types manquants : `types/react-simple-maps.d.ts`. Contrôle manuel : mode confidentialité (œil), thème sombre, responsive mobile.
