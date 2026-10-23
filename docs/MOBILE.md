# Refonte mobile : règles

Cible : téléphone 375 × 812 (aussi 360 px), usage une main, pouce. Breakpoint : `md` (768 px) ; le bureau ne doit **pas** changer visuellement (préfixer le mobile par défaut, le bureau par `md:`).

## Socle (déjà en place, ne pas refaire)
- `AppLayout` : `h-dvh`, pas de scroll horizontal, en-tête mobile (marque, œil, recherche), `MobileNav` = barre d'onglets fixe en bas (Accueil, Mois, Comptes, Placements, Plus) ; `<main>` réserve déjà 4 rem + safe-area en bas.
- `DialogContent` / `SheetContent` : bornés à la hauteur de l'écran, scroll interne.

## Règles pour chaque page
1. **Aucun scroll horizontal de la page** à 375 px. Les tableaux larges : soit conteneur `overflow-x-auto` assumé, soit (préféré pour les listes de transactions, comptes, échéances) une **vue en cartes empilées** en dessous de `md` (`hidden md:block` tableau / `md:hidden` cartes). Jamais de colonne coupée sans moyen de la voir.
2. **Cibles tactiles ≥ 40 px** (boutons icône `h-10 w-10` mini, lignes cliquables `min-h-11`). Espacer les actions rapprochées.
3. **Grilles** : `grid-cols-1` par défaut, `sm:grid-cols-2`, `lg:`/`xl:` pour la suite. KPI : 2 colonnes max sur mobile.
4. **En-têtes de page** : titre + actions qui passent à la ligne (`flex-col gap-3 sm:flex-row sm:items-center sm:justify-between`) ; boutons d'action pleine largeur ou icône seule sous `sm`.
5. **Onglets** (`Tabs`) : liste scrollable horizontalement (`overflow-x-auto`, pas de retour à la ligne), l'onglet actif visible.
6. **Formulaires / dialogues** : champs pleine largeur, `text-base` (16 px) sur les `input` pour éviter le zoom iOS, boutons du pied empilés (`flex-col-reverse sm:flex-row`), clavier : le bouton principal reste atteignable (le dialogue scrolle).
7. **Graphiques Recharts** : `ResponsiveContainer` hauteur ≤ 260 px sur mobile, moins d'étiquettes d'axe (`interval="preserveStartEnd"`, `tick` 11 px), légende sous le graphique, tooltips lisibles. Pas de graphique plus large que l'écran.
8. **Textes** : `truncate` / `break-words` sur les libellés de marchands, `min-w-0` sur les enfants flex qui contiennent du texte long. Montants : jamais coupés (`whitespace-nowrap tabular-nums`).
9. **Menus déroulants / popovers** : tenir dans l'écran (`collisionPadding`, `max-h` + scroll).
10. Padding de page : le conteneur applique `p-4` ; ne pas ajouter de marges négatives qui débordent.
11. Mode confidentialité, thème sombre, `formatCurrency` : inchangés (voir `frontend/src/CLAUDE.md`). Aucun KPI calculé côté frontend.

## Vérification (obligatoire)
- Backend de démo : `http://localhost:8011` (base jetable), frontend : `http://localhost:5173` (déjà lancés, `VITE_API_BASE` pointe sur 8011). Login `admin` / `demo1234`. Ne pas lancer d'autre serveur, ne pas toucher au port 8001.
- Navigateur intégré : `resize_window` en 375 × 812 (`preset: mobile`), ouvrir chaque écran de ton périmètre **y compris ses dialogues et onglets**, screenshot, et corriger. Mesure le débordement : `document.documentElement.scrollWidth > window.innerWidth` doit être `false`.
- `cd frontend && npm run typecheck` sans erreur. Remettre le viewport en `desktop` en fin de travail et vérifier qu'une page du bureau n'a pas bougé.
- Ne modifier que les fichiers de ton périmètre (pas `components/layout`, `components/ui`, ni `docs/MOBILE.md`). Si un correctif commun est nécessaire, le décrire dans ton rapport au lieu de le faire.
- Pas de commit : le commit est fait par l'agent principal.
