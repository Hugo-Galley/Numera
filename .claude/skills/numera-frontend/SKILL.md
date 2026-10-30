---
name: numera-frontend
description: Procédures et standards UI/UX pour le frontend Numera (React, Tailwind, shadcn/ui, Recharts) : ajouter une page, un onglet du dashboard, un graphique, un formulaire, gérer le mode confidentialité. À charger dès qu'on édite frontend/src/.
---

# Numera frontend — procédures et design

Conventions techniques : `frontend/src/CLAUDE.md` (à lire d'abord).

## Identité visuelle

Esthétique sobre « entreprise légère », Tailwind + shadcn. Palette : Slate (neutre), Emerald (revenus, gains), Rose (dépenses, pertes), Amber (alertes), primaire bleu/slate profond (`--primary`). Titres et valeurs KPI en `font-black`. Contenu principal centré en `max-w-7xl`, espacements `gap-4`/`gap-6`, `space-y-4`. Thèmes clair/sombre via `UIProvider` : palettes inversées par variables CSS, donc pas de variantes `dark:` (voir `frontend/src/CLAUDE.md`).

## Présentation des données financières

- `formatCurrency(amount, currency)` partout ; montants colorés (Emerald/Rose) plutôt que seulement signés ; alignés à droite dans les tables.
- Classe `amount-blur` sur tout montant sensible (mode confidentialité).
- `Card` pour grouper, `Badge` pour statuts/catégories, `Button` variants `default|outline|ghost|destructive`, icônes `lucide-react` (`h-4 w-4` en ligne, `h-5 w-5` en carte).
- États : `Skeleton` au chargement, état vide (icône + bouton d'action), `toast` (sonner) après chaque mutation.
- Mobile-first : masquer/adapter colonnes de tables et grilles avec les classes responsive.

## Ajouter une page

1. `src/pages/<Nom>.tsx` ; au-delà de 350 lignes, dossier `src/pages/<Nom>/` : `index.tsx` (composition, retours anticipés), hooks `use<Nom>*.ts` (état, chargement, actions), un composant par section ou dialogue recevant `ctx` (modèle : `pages/AccountDetail/`).
2. Route dans `App.tsx` (à l'intérieur du bloc `ProtectedRoute`/`AppLayout`).
3. Entrée dans la Sidebar (`components/layout/Sidebar.tsx`) et dans l'Omnibox (`components/layout/Omnibox/`, ⌘K) pour qu'elle soit découvrable.
4. Données via les fonctions de `lib/api/<domaine>.ts` (une par route, ex. `getAccounts<Account[]>()`, `patchAccountsById(id, body)`, `getTransactions<T>("?limit=10")`) ; une route nouvelle y ajoute sa fonction. `api.download` pour les fichiers. Jamais de calcul de KPI dans le composant.

## Ajouter un onglet au Dashboard

Créer `components/dashboard/tabs/<Nom>Tab.tsx` (onglets actuels : Overview, History, Budgets, Insights, Investments, Merchants, Projections, Subscriptions), brancher les données dans `useDashboardData.ts` (un `safeLoad` par endpoint) et déclarer l'onglet dans `pages/Dashboard.tsx`.

## Ajouter un graphique

`recharts`, couleurs de la palette, `Tooltip` et légende toujours présents, valeurs formatées via `formatCurrency`. Rendre les éléments cliquables pour naviguer vers la vue filtrée quand elle existe. Sankey / treemap / simulateur : `components/analytics/`.

## Pages à connaître

- `Tools.tsx` : gestion du salaire (`SalaryManager`) et calendrier de télétravail (`TelecommutingCalendar`).
- `Settings.tsx` : vrais réglages seulement, 4 onglets (Général, Notifications, Sécurité, Données), cartes dans `components/settings/`. Ce qui se manipule souvent n'y va pas.
- `Classement.tsx` (`/classement`, groupe Gestion) : catégories, tags, marchands, règles (`components/classement/`).
- Import CSV : `components/import/ImportFlow` dans `ImportDialog`, ouvert depuis la page d'un compte (ou `/accounts?import=1`).
- `Audit.tsx` : Centre d'Actions (voir `docs/ACTION_CENTER.md`) ; `?vue=virements` = revue des virements internes (`components/audit/TransferReview`).
- `Accounts.tsx` : liste des comptes avec `AccountVerificationBanner` (met à jour `last_verified_at`).
- `Investments.tsx` : vue globale, `HoldingsTable`, `DiversityScanner`, `PointZeroModal`, `CustomEtfModal`, `SecuritySearchInput`.

## Validation

`cd frontend && npm test && npm run build` (Vitest, puis `tsc` app + tests et `vite build`, 0 erreur de types actuellement) ; `npm run typecheck` pour tsc seul. Un composant ou un bug corrigé reçoit son test `X.test.tsx` (conventions : `frontend/src/CLAUDE.md` § Vérification, procédures : skill `numera-testing`). Puis contrôle manuel : mode confidentialité, thème sombre, largeur mobile.
