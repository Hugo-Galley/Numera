# Phase 5 — Frontend : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (exécution native, choisie par l'utilisateur) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Découper les 21 fichiers `frontend/src` qui dépassent le plafond de 350 lignes (baseline `scripts/code_size_baseline.json`) jusqu'à vider la baseline, **sans aucun changement de comportement, d'interface ni d'appel API**.

**Architecture:** Découpage pur, page par page. Une page devient un dossier `pages/<Page>/` (`index.tsx` = composition, un composant par section et par dialogue, hooks `use*.ts` pour l'état et le chargement) ; un gros composant devient un dossier `components/<domaine>/<Composant>/` dont `index.tsx` exporte le même nom (les imports existants ne changent pas). Le code est **déplacé**, pas réécrit : blocs contigus, dans l'ordre d'origine, pour garder l'ordre des hooks et des effets. Les appels typés `lib/api/<domaine>.ts` font l'objet d'une tâche transversale à la fin (tâche 12), pour ne pas mélanger déplacement et réécriture.

**Tech Stack:** React 18, Vite, TypeScript strict (`tsc --noEmit`), Tailwind, shadcn/Radix, Recharts ; aperçu navigateur intégré (outils `mcp__Claude_Browser__*`) sur l'instance de démo.

**Spec:** `docs/superpowers/specs/2026-10-28-architecture-en-couches-design.md` (§ Couches frontend, § Limites de taille) · plan maître : `docs/superpowers/plans/2026-10-28-architecture-en-couches.md` (§ Phase 5) · conventions d'exécution : section 0 de `docs/superpowers/plans/2026-10-28-phase-3-analytics.md`.

---

## 0. Reprendre ce plan dans une nouvelle conversation

### Message à coller pour démarrer

```text
On reprend la phase 5 (frontend) de la migration de Numera vers une architecture en couches.
Lis d'abord, dans cet ordre : docs/superpowers/plans/2026-10-29-phase-5-frontend.md (en entier, surtout la section 0),
puis frontend/src/CLAUDE.md et le skill numera-frontend. Relis le ledger
.superpowers/sdd/2026-10-29-phase-5-frontend/progress.md (une tâche « complete » n'est pas refaite).
Exécute toi-même (skill superpowers:executing-plans) la prochaine tâche non cochée, puis les suivantes
si le budget le permet. Commits directement sur main, sans push.
```

### État (mis à jour à chaque tâche)

- **Fait** : tâches 1 à 6 (`AccountDetail`, `RecurringTransactions`, `WealthSimulator`, `Accounts`, `Audit`, `Investments` + `Savings`), un commit « refactor(frontend): découpe de … » par fichier. Baseline : **14 entrées**.
- **Fait aussi** : tâche 7, première moitié (`HoldingsTable`). Baseline : **13 entrées**.
- **Prochaine tâche** : tâche 7, seconde moitié (`PointZeroModal`).
- Aucune tâche entamée à moitié.

### Conventions de l'utilisateur (sans redemander)

- Échanges en français, concis. Commits **directement sur `main`**, sans branche ni PR, **un commit par tâche**, message en français terminé par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Ne jamais pousser.
- Exécution native (l'agent fait lui-même, sans sous-agent sauf demande).
- Ledger : `.superpowers/sdd/2026-10-29-phase-5-frontend/progress.md` (non versionné). Une ligne `Task N: complete` par tâche, une ligne `Task N: Ruling: <décision> — <pourquoi> — <coût si faux>` par écart au plan.
- Budget limité : une tâche est soit finie et commitée, soit pas commencée. Si le budget manque en cours de tâche, `git checkout -- frontend/` + supprimer le dossier créé, et noter dans « État » où reprendre.

### Outillage déjà prêt (dans `.superpowers/sdd/2026-10-29-phase-5-frontend/`)

- `run-backend.sh` / `run-frontend.sh` : backend sur une **copie** de `backend/data/demo.db` (`DEMO_MODE=true`, port 8011, `SECRET_KEY` aléatoire, identifiants `demo`/`demo` via un `env.sh` à créer : `ADMIN_USERNAME=demo` + `ADMIN_PASSWORD_HASH` bcrypt de `demo`) et Vite (`VITE_API_BASE=http://localhost:8011`, port 5173). Copier les scripts dans le scratchpad de la session, corriger les chemins, et pointer `.claude/launch.json` dessus **sans committer `launch.json`** (`git checkout -- .claude/launch.json` avant le commit). Démarrer avec `preview_start {name: "backend-demo"}` puis `{name: "frontend"}`. La page de connexion a les champs déjà remplis : cliquer seulement « Entrer dans la démo ».
- `splitlib.py` : version générique du générateur (classe `Split` : `hooks`, `comp`, `index` ; ignore commentaires et chaînes pour choisir les imports). Une config courte par fichier (ex. `split-recurring.py`, tâche 2) ; la lancer sur une copie du fichier d'origine (`git show HEAD:… > scratchpad`).
- `split-accountdetail.py` : le générateur utilisé pour la tâche 1. À adapter (plages de lignes) pour chaque gros fichier, il :
  1. lit les imports d'origine et n'émet, dans chaque nouveau fichier, que ceux dont l'identifiant y apparaît (alias `as` et `import type` conservés) ;
  2. découpe le corps du composant en **hooks** sur des blocs contigus, dans l'ordre d'origine ; chaque hook reçoit l'union des retours des hooks précédents (`p: ReturnType<typeof useA> & …`), déstructure ce qu'il utilise et retourne tout ce qu'il déclare ; il signale toute **référence en avant** (un nom utilisé avant le bloc qui le déclare) — la résoudre en déplaçant la déclaration pure (ex. un formateur) dans un bloc antérieur ;
  3. un hook `use<Page>.ts` assemble les hooks et exporte `<Page>Ctx` / `<Page>View` (contexte une fois les données non nulles) ;
  4. découpe le JSX en composants `({ ctx }: { ctx: <Page>View })` qui déstructurent les noms du contexte qu'ils utilisent ; les sous-composants imbriqués sont insérés par `<Enfant ctx={ctx} />` ;
  5. `index.tsx` (écrit par le script) garde les retours anticipés (chargement, introuvable) et la composition.
- Repérer les plages : `awk` sur l'indentation (lignes du JSX à ≤ 10 espaces) et `grep -n "^  const \[\|^  const [a-z]* = \|^  useEffect\|<Dialog "` pour l'état et les dialogues.

### Filet de non-régression (pas de tests frontend)

Pour chaque tâche, **avant** de toucher au code puis **après** :

1. `cd frontend && npm run build` (= `tsc --noEmit && vite build`) : vert. Le projet est à 0 erreur TypeScript.
2. `make check-size` : vert, entrée de baseline retirée (`scripts/code_size_baseline.json`), aucun nouveau fichier ≥ 350 lignes.
3. Aperçu navigateur sur la démo (préférer `javascript_tool` / `get_page_text` / `read_network_requests` aux captures) : pour chaque écran concerné (chaque onglet, chaque type de compte…), relever avec le snippet ci-dessous **longueur + empreinte du texte de `<main>`, nombre et statut des requêtes vers :8011, nombre de boutons**. Après découpe : valeurs **identiques**. (En dev, StrictMode double les requêtes : comparer avant/après dans les mêmes conditions.) Les `logos/img/si:*:0` sont des images tierces, déjà en statut 0 avant.

   ```js
   await new Promise(r=>setTimeout(r,3000));const txt=document.querySelector('main')?.innerText||document.body.innerText;let h=0;for(const c of txt)h=(h*31+c.charCodeAt(0))|0;const api=performance.getEntriesByType('resource').filter(e=>e.name.includes(':8011')).map(e=>e.name.replace('http://localhost:8011','')+':'+e.responseStatus).sort();JSON.stringify({url:location.pathname,len:txt.length,hash:h,napi:api.length,bad:api.filter(a=>!a.endsWith(':200')),btn:document.querySelectorAll('button').length})
   ```
4. Dialogues et actions principales : ouvrir chaque dialogue (clic JS sur le déclencheur, lire `[role=dialog]` `innerText`, Échap), un menu Radix via `PointerEvent('pointerdown')`, un formulaire d'édition pré-rempli (valeurs des `input`). **Aucune soumission** de formulaire sur la démo sauf si la tâche l'exige.
5. Une seule capture, mobile 375 px + thème sombre (`resize_window {preset: "mobile", colorScheme: "dark"}`), avec le mode confidentialité testé en JS (nombre de `.privacy-masked` > 0 une fois activé) et `scrollWidth <= innerWidth`. Remettre `preset: "desktop"` ensuite.
6. Console : aucune erreur nouvelle (`read_console_messages {onlyErrors: true}`).

### Pièges

1. **Cache Vite après déplacement** : quand `pages/X.tsx` devient `pages/X/index.tsx`, le serveur de dev garde l'ancien chemin (« Failed to fetch dynamically imported module ») → redémarrer le serveur `frontend` (`preview_stop` puis `preview_start`). Ce n'est pas une régression.
2. **Déclarations à un seul élément** (`const [handleBulkUpdate] = useSubmit(…)`, `const [searchParams] = …`) : le générateur doit les reconnaître, sinon le nom manque au contexte (tsc le signale).
3. **Références en avant** : dans un composant, une fonction peut utiliser une constante déclarée plus bas ; en hooks séparés, non. Déplacer la déclaration pure plus haut (aucun effet sur l'ordre des hooks React), ne jamais déplacer un `useEffect`.
4. **Ordre des effets** : les effets s'exécutent dans l'ordre de déclaration ; garder les blocs dans l'ordre d'origine.
5. **Retours anticipés** (`if (loading) return …`) : ils restent dans `index.tsx`, après l'appel de tous les hooks ; les valeurs calculées après eux (`isInvestment`, `currentBalance`…) entrent dans le contexte « vue ».
6. `tsconfig` n'active pas `noUnusedLocals` : une déstructuration en trop ne casse pas le build, mais en garder le moins possible.
7. Ne pas committer `.claude/launch.json` (chemins de scratchpad).

---

## Global Constraints

- Plafond bloquant : **350 lignes** par fichier `.ts`/`.tsx` de `frontend/src` hors `components/ui` (cible ~200).
- Découpage pur : même DOM, mêmes classes, mêmes textes, mêmes requêtes HTTP (mêmes URL, même ordre de déclenchement), même gestion d'erreurs et de toasts.
- Pas de modification de `components/ui/`, ni du backend, ni du serveur MCP.
- La baseline de taille ne peut que diminuer ; une entrée repassée sous le plafond **doit** être retirée.
- Les imports existants vers un composant découpé restent valides (dossier + `index.tsx` du même nom).

## Review Focus

- Une page qui change de compte / de mois ignore les réponses obsolètes (drapeaux `cancelled`, `txRequestId`) : vérifier que la référence (`useRef`) reste dans le même hook que les requêtes qui la lisent.
- Les dialogues dont l'`onOpenChange` réinitialise le formulaire : ouvrir, fermer, rouvrir → champs vides.
- Les paramètres d'URL qui ouvrent un dialogue au chargement (`?edit=`, `?tab=`, `?import=1`) : effet conservé et toujours déclenché une seule fois.
- Mode confidentialité et thème sombre : aucune classe déplacée hors de son élément.
- Mobile 375 px : les variantes `md:hidden` / `hidden md:block` des listes restent sur le même élément.

---

## Tâches

Chaque tâche suit les mêmes étapes :

- [ ] Relever l'état de référence (filet, points 3-4) pour chaque écran du fichier.
- [ ] Découper (générateur adapté, plages relues), fichiers < 350 lignes.
- [ ] `npm run build` vert ; retirer l'entrée de baseline ; `make check-size` vert.
- [ ] Redémarrer Vite si un fichier est devenu dossier ; refaire le relevé : identique ; dialogues et capture mobile sombre.
- [ ] Mettre à jour la section 0 (« État ») et cocher la tâche ; commit `refactor(frontend): découpe de <X>` ; ledger `Task N: complete`.

### Task 1: `pages/AccountDetail.tsx` (2 773) ✅

Fait. `pages/AccountDetail/` : `index.tsx` (composition, retours anticipés), `types.ts`, hooks `useAccountDetail.ts` (assemblage, types `AccountDetailCtx` / `AccountDetailView`), `useAccountDetailState.ts`, `useAccountForms.ts`, `useAccountDetailData.ts`, `useTransactionActions.ts`, `useInvestmentActions.ts`, `useTransactionView.tsx` ; composants `AccountHeader`, `TransactionDialog`, `InvestmentTxDialog`, `SnapshotDialog`, `ZeroPointDialog`, `FilterBar`, `AccountKpis`, `AccountCharts`, `TransactionsSection` (`TransactionsToolbar`, `TransactionsMobileList`, `TransactionsTable`), `InvestmentSection` (`InvestmentFlowsCard`, `SnapshotsCard`), `BulkActionsBar`, `BulkEditDialog`, `AccountDialogs`. Plus gros fichier : 253 lignes. Vérifié sur les comptes 1 à 4 de la démo (courant, épargne, PEA, assurance-vie) : texte, requêtes et boutons identiques ; 7 dialogues + menu d'actions + édition pré-remplie ; mobile sombre ; confidentialité.

### Task 2: `pages/RecurringTransactions.tsx` (1 548) ✅

Fait. `pages/RecurringTransactions/` : `index.tsx` (onglets, calendrier en `lazy`, `IncomeTab`, `InvestmentFlowDialog`), `types.ts`, hooks `useRecurringTransactions.ts` (assemblage), `useRecurringState.ts`, `useRecurringForm.ts`, `useRecurringActions.ts` ; composants `RecurringHeader`, `RecurringListTab`, `SubscriptionsTab`, `RecurringFormDialog` (`FormMainFields`, `FormSecurityFields`, `FormAmountFields`, `FormScheduleFields`). Plus gros fichier : 262 lignes. Vérifié : vue analyse, vue liste, `?tab=calendar`, `?tab=salary` (texte, requêtes, boutons identiques) ; dialogue création ×2 (vide à la réouverture) et édition pré-remplie ×2 ; mobile sombre, confidentialité.

Écrans : chaque onglet `?tab=` (dont `calendar` et `salary`, qui embarquent `Calendar.tsx` et `SalaryManager` : ne pas les toucher ici). Dossier `pages/RecurringTransactions/`.

### Task 3: `components/analytics/WealthSimulator.tsx` (1 169) ✅

Fait. `components/analytics/WealthSimulator/` : `index.tsx` (export nommé `WealthSimulator`, mêmes props ; import de `pages/Tools.tsx` inchangé), `types.ts`, hooks `useWealthSimulator.ts` (reçoit `initialCapitalDefault`), `useSimulatorState.ts`, `useSimulatorActions.tsx` (dont l'infobulle) ; composants `BaseTab`, `AllocationTab`, `AdvancedTab`, `EventsTab`, `DetailTable`, `SimulatorKpis`, `SimulatorChart`, `AssetDialog`. Plus gros fichier : 172 lignes. Vérifié sur `/tools` → « Mode avancé » (volatilité nulle : déterministe) : texte des 4 onglets, boutons et requête `/analytics/wealth-simulation` identiques. `splitlib.py` accepte des props (`hooks(..., args=[(nom, type)])`, `index(..., head=, call_args=, default=False)`).

Dossier `components/analytics/WealthSimulator/`. Écran : `/tools` (et tout autre consommateur : `grep -rn WealthSimulator frontend/src`). Le simulateur Monte-Carlo est aléatoire avec volatilité : comparer avec volatilité nulle ou ne comparer que les champs déterministes.

### Task 4: `pages/Accounts.tsx` (1 057) ✅

Fait. `pages/Accounts/` : `index.tsx` (en-tête, crédit, archivés, import), `types.ts`, hooks `useAccounts.ts`, `useAccountsState.ts` (dont les effets `?import=1` / `?new=loan`), `useAccountsActions.tsx` ; composants `CreateAccountDialog`, `EditAccountDialog`, `AccountsList`. Plus gros fichier : 241 lignes. Vérifié : texte, requêtes, boutons ; création ×2 (vide), édition pré-remplie (courant, assurance-vie), crédit, `?import=1` ouvre l'import et nettoie l'URL.

Écrans : `/accounts`, `/accounts?import=1` (dialogue d'import), bannière de vérification.

### Task 5: `pages/Audit.tsx` (1 030) ✅

Fait. `pages/Audit/` : `index.tsx` (`ActionCenter`, retours anticipés : `?vue=virements`, chargement, erreur, détail), `types.ts` (types, constantes, `sampleLabel`), `TransactionEditor.tsx` et `CreatorModals.tsx` (sous-composants autonomes déplacés tels quels), hooks `useAudit.ts` / `useActionCenterData.ts` ; composants `ActionDetail`, `ActionList`. Plus gros fichier : 264 lignes. Vérifié : `/audit` (texte identique hors horodatage « Dernière analyse », requêtes, boutons, Sidebar), clic sur chaque action (liens), `?vue=virements`. La démo n'a pas d'action `modal_*` : `ActionDetail` et les modales sont vérifiés par tsc seulement. `splitlib.py` : `module()` (déplacer des déclarations de premier niveau), `comp(..., exclude=, prelude=)` (valeur rétrécie après un retour anticipé, ex. `ctx.data!`).

Écrans : `/audit`, `/audit?vue=virements`. Le compteur d'actions de la Sidebar ne doit pas changer.

### Task 6: `pages/Investments.tsx` (775) et `pages/Savings.tsx` (761) ✅

Deux commits (un par page). `Investments` : modales `PointZeroModal`, `CustomEtfModal` ouvrables (sans les découper ici).

- [x] `Investments` : `pages/Investments/` : `index.tsx` (retour anticipé de chargement, sections), `types.ts` (constantes), hook `useInvestmentsData.ts` (dont `chartData`, calcul pur remonté avant le retour anticipé), composants `InvestmentsKpis`, `AccountsAllocation`, `PerformanceSection`, `AdvancedCharts`, `TopCompanies`, `EtfCompositions`, `DrillDownDialog`. Plus gros fichier : 156 lignes. Relevé identique (texte, requêtes, boutons, longueur du HTML de `<main>`). La page n'utilise ni `PointZeroModal` ni `CustomEtfModal` (aucun import).
- [x] `Savings` : `pages/Savings/` : `index.tsx` (états erreur / chargement / contenu, `ProvisionsSection`), `types.ts`, hook `useSavingsData.ts` ; composants `SavingsHeader`, `BalanceSection`, `FlowsSection`, `GoalsHeader` (dialogue d'objectif), `GoalsGrid`. Plus gros fichier : 155 lignes. Relevé identique ; dialogue création ×2 (vide) et édition pré-remplie.

### Task 7: `components/investments/HoldingsTable.tsx` (749) et `PointZeroModal.tsx` (602)

Écrans : `/investments`, `/accounts/3` (PEA de la démo). Deux commits.

- [x] `HoldingsTable` : `components/investments/HoldingsTable/` (export nommé et props inchangés) : `index.tsx`, `types.ts`, hooks `useHoldingsTable.ts` (reçoit les props) / `useHoldingsState.ts` ; composants `HoldingsHeader`, `HoldingsMobileList`, `HoldingsDesktopTable`. Plus gros fichier : 260 lignes. Vérifié sur `/accounts/3` : texte, requêtes, boutons, HTML ; point zéro (valeurs pré-remplies), filtre ETF puis réinitialisation. `splitlib.py` recale les imports relatifs d'origine (`./X` → `../X`).
- [ ] `PointZeroModal`.

### Task 8: `components/dashboard/tabs/OverviewTab.tsx` (622)

Écran : `/` onglet Vue d'ensemble (données via `useDashboardData`, inchangé).

### Task 9: `pages/Calendar.tsx` (519), `components/classement/MerchantsTab.tsx` (511), `CategoriesTab.tsx` (510), `components/layout/Omnibox.tsx` (509)

Un commit par fichier. Omnibox : ⌘K, recherche, navigation clavier (vérifier par `KeyboardEvent`).

### Task 10: `pages/Tax.tsx` (478), `components/tools/SalaryManager.tsx` (450), `components/import/ImportFlow.tsx` (405), `components/savings/ProvisionsSection.tsx` (386)

Un commit par fichier. ImportFlow : aller jusqu'à l'aperçu d'un CSV **sans valider l'import**.

### Task 11: `components/tools/WealthForecast.tsx` (377), `components/wrapped/WrappedStory.tsx` (373), `components/analytics/SankeyFlow.tsx` (371)

Petits dépassements : souvent un sous-composant ou un utilitaire à sortir suffit. Un commit par fichier.

### Task 12: appels typés `lib/api/<domaine>.ts` et clôture

- Créer `lib/api/<domaine>.ts` (au-dessus de `lib/api.ts`, qui reste) pour les domaines des pages découpées (`accounts`, `transactions`, `investments`, `recurring`, `analytics`…) : une fonction typée par appel, mêmes URL et paramètres ; remplacer les `api.get(...)` des hooks par ces fonctions. Vérification : relevé réseau identique (URL et ordre).
- Baseline de taille **vide** ; `make validate` vert.
- Mettre à jour `ARCHITECTURE.md` (§ frontend), `frontend/src/CLAUDE.md` (structure dossiers de pages, `lib/api/`), skill `numera-frontend` (« Ajouter une page » : dossier `pages/<Page>/`), et le plan maître (§ Phase 5 terminée, § Phase 6 : baseline vide).
