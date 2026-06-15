# Numera — Frontend Expert Skill

Ce guide contient les instructions spécifiques pour le développement du frontend React de Numera.

## 1. Structure des Composants
- **UI Atomique** : Utiliser `@/components/ui/` pour les composants de base (shadcn). Ne pas les modifier directement sauf nécessité absolue.
- **Layout** : `src/components/layout/` contient la structure globale (Sidebar, AppLayout).
- **Pages** : `src/pages/` contient les vues principales. Garder la logique de fetch dans les pages et passer les données aux sous-composants.

## 2. Appel API & Devises
- **`apiFetch`** : Toujours utiliser le wrapper `api` de `@/lib/api` qui gère automatiquement les headers JWT et les erreurs `401`.
- **Formatage** : Utiliser `formatCurrency(amount, currency)` de `@/lib/utils.ts`.
- **Privacy Mode** : S'assurer que les montants sensibles utilisent la classe CSS `.amount-value` ou respectent l'état `isPrivacyMode` du `UIProvider`.

## 3. Visualisation (Recharts)
- **Consistance** : Utiliser les couleurs définies dans `tailwind.config.js` ou les couleurs thématiques du projet (Slate, Emerald, Rose, Amber).
- **Accessibilité** : Toujours fournir des tooltips et des légendes claires.
- **Drill-down** : Préférer rendre les éléments de graphe cliquables pour naviguer vers les données filtrées.

## 4. Gestion de l'État
- **Providers** : 
    - `AuthProvider` : Authentification et profil.
    - `UIProvider` : Mode sombre/clair, mode confidentialité, état de la barre de recherche.
- **Local State** : Utiliser `useState` et `useEffect` pour les données spécifiques à une page. Préférer `useMemo` pour les calculs lourds côté client.

## 5. Formulaires & Validation
- **Composants** : Utiliser les composants `Input`, `Select`, `Checkbox` de la bibliothèque UI.
- **Feedback** : Utiliser `sonner` (`toast.success`, `toast.error`) pour informer l'utilisateur du résultat des actions.
