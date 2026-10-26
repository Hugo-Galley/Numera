# Crédits, plafonds d'épargne, actions ⌘K, notifications — conception

Date : 2026-10-26. Quatre fonctionnalités indépendantes, livrées dans cet ordre, un commit chacune sur `main`.

## Pourquoi

Numera couvre déjà budget, investissement, fiscalité et alertes, mais :
- un futur crédit (immobilier, auto) n'aurait nulle part où vivre et le patrimoine affiché serait brut, pas net ;
- la page Fiscalité ignore le LDDS et le LEP et ne dit pas *où* placer l'argent ;
- ⌘K sait chercher mais pas agir ;
- les alertes du Centre d'Actions n'existent que si l'on ouvre l'app.

Pas de crédit en cours aujourd'hui : la fonctionnalité doit être prête sans être encombrante (rien ne s'affiche tant qu'aucun crédit n'existe).

Anti-objectifs : aucun KPI calculé côté frontend ; aucune donnée vers un tiers autre que le canal de notification choisi ; pas de spam (une alerte = un message).

---

## 1. Crédits et emprunts

**Modèle (décidé).** Nouveau type de compte `credit` + table `loans` (1-1 avec le compte, `account_id` unique, suppression en cascade) :
`principal` (capital emprunté), `annual_rate_pct` (taux nominal), `duration_months`, `start_date` (date de la 1re échéance), `insurance_monthly` (assurance, défaut 0), `kind` (`immobilier|auto|consommation|etudiant|autre`), `prepayments` (remboursements anticipés réels, table `loan_prepayments` : `date`, `amount`, `mode` = `reduce_duration|reduce_payment`).

**Calcul (`core/loans.py`, pur, testé).**
- Échéancier à mensualité constante : `m = P·r / (1 − (1+r)^−n)`, `r = taux/12` ; taux 0 → `P/n`. Lignes : n°, date, mensualité, intérêts, capital, assurance, capital restant dû. Arrondi au centime par ligne, dernière ligne absorbe l'écart.
- Les remboursements anticipés enregistrés recalculent la suite (durée ou mensualité selon `mode`).
- `remaining_principal(loan, at)` = CRD après la dernière échéance ≤ `at` (avant la 1re échéance : `principal`).
- Simulation (sans enregistrer) : montant + date + mode → intérêts économisés, nouvelle date de fin ou nouvelle mensualité, indemnités de remboursement anticipé estimées (plafond légal : min(6 mois d'intérêts sur le montant, 3 % du CRD), affichées comme maximum, champ libre pour la valeur du contrat — mon choix).

**Patrimoine (décidé).** `core/wealth.py::account_values` : un compte `credit` vaut `−remaining_principal(at)` (source `loan`). Tous les totaux de patrimoine deviennent nets sans autre changement. Le solde de compte affiché (`AccountRead.balance`) vaut aussi `−CRD`. Les transactions ne sont pas saisies sur un compte crédit ; les mensualités restent des `Sortie` sur le courant.
- Allocation du patrimoine : les crédits sortent du camembert (valeurs négatives illisibles) et apparaissent comme une ligne « Dettes » + « Patrimoine net » sous le total. Mon choix.
- Les filtres existants `type in (courant, epargne)` excluent naturellement `credit` des KPI revenus/dépenses : rien à changer.

**API (`api/loans.py`, protégé)** : CRUD prêt (création = compte `credit` + prêt dans une seule requête), `GET /loans/{id}/schedule`, `POST /loans/{id}/simulate-prepayment`, CRUD remboursements anticipés. Routes de lecture reprises dans `mcp-server/server_api.py`.

**UI.** Page Comptes : bouton « Ajouter un crédit » (formulaire dédié). Le détail d'un compte crédit remplace la liste de transactions par : résumé (mensualité, CRD, % remboursé, date de fin, coût total des intérêts), courbe CRD dans le temps, tableau d'amortissement (année repliable), simulateur de remboursement anticipé. Mode confidentialité respecté.

## 2. Plafonds d'épargne : LDDS, LEP, ordre de remplissage

**LDDS et LEP.** `TaxWrapper` gagne `ldds` et `lep` ; `TaxRules` gagne `ldds_ceiling = 12 000` et `lep_ceiling = 10 000` (2025 et 2026, sources ajoutées dans l'en-tête de `tax_rules.py`). Cartes de la page Fiscalité calquées sur le Livret A (intérêts capitalisés autorisés à dépasser). LEP : rappel textuel de la condition de revenus, non vérifiée. Détection par nom : `ldds|livret developpement durable`, `\blep\b|livret epargne populaire`.

**« Où placer ton prochain euro » (mon choix de règle, ordre fixe, explicable).**
1. Épargne de précaution sous 3 mois de dépenses (`compute_resilience` existant) → livret réglementé avec de la place : LEP > Livret A > LDDS > Livret Jeune.
2. Précaution entre 3 et 6 mois → idem, priorité moindre.
3. PEA ouvert avec de la place → PEA ; aucun PEA → « ouvrir un PEA pour lancer le compteur des 5 ans ».
4. TMI ≥ 30 % et plafond PER restant → PER (économie d'impôt estimée).
5. Assurance-vie (prendre date pour les 8 ans) si aucune ; sinon CTO.
Chaque étape renvoie : enveloppe, compte (s'il existe), raison en une phrase, place restante. Calcul backend (`build_overview` → champ `allocation_advice`), carte en tête de la page Fiscalité. Pas de taux de rendement codés en dur.

## 3. Actions dans ⌘K

L'Omnibox actuelle (navigation, comptes, recherche de transactions) est conservée et enrichie :
- **Saisie rapide** : une requête qui commence par un montant (`12,50 boulangerie`, `+1200 prime`) propose « Ajouter une dépense / un revenu de 12,50 € — boulangerie » sur le compte principal (`is_main`). Sélection → ouverture du formulaire de transaction existant pré-rempli (via paramètres d'URL lus par `AccountDetail`), jamais d'enregistrement silencieux. Mon choix.
- **Actions** (section dédiée, filtrées par la requête) : Nouvelle transaction, Importer un CSV, Démarrer la revue du mois, Basculer le mode confidentialité, Ajouter un crédit, Envoyer une notification de test.
- **Transaction trouvée** : ouvre le compte avec la transaction mise en évidence (paramètre `?tx=<id>`).
- Sections visibles et navigation clavier conservées ; aucune nouvelle dépendance.

## 4. Notifications ntfy et Telegram

**Canaux (décidé : ntfy et Telegram, interface prévue pour en ajouter un).** `core/notifications.py` : protocole `Channel.send(title, body, priority, url)` ; `NtfyChannel` (POST sur `{server}/{topic}`, en-têtes `Title`, `Priority`, `Click`, `Authorization: Bearer` optionnel ; serveur par défaut `https://ntfy.sh`) ; `TelegramChannel` (`sendMessage` du Bot API, `chat_id`). `httpx` asynchrone, délai 10 s, erreurs journalisées sans faire tomber la tâche.

**Réglages** dans `system_settings` (clés `notify.*`) : canaux activés, paramètres de chaque canal, sévérité minimale (défaut `medium`), résumé hebdo activé, masquer les montants (défaut non). Les jetons ne sont jamais renvoyés en clair par l'API (`••••` + 4 derniers caractères). Section « Notifications » dans Paramètres avec bouton « Envoyer un test » par canal.

**Quoi envoyer.**
- *Alertes* : la tâche horaire existante appelle le calcul du Centre d'Actions, garde les actions ≥ sévérité minimale et non ignorées, et envoie celles dont l'empreinte (`id` + titre + description) n'a jamais été envoyée. Table `notification_log` (`fingerprint` unique, `action_id`, `sent_at`, `channel`). Une action qui change (ex. budget 80 % → 100 %) a une nouvelle empreinte et repart. Lien cliquable vers `action_url` si l'URL publique de l'instance est renseignée (réglage `notify.public_url`, facultatif ; aucune variable d'environnement de ce type n'existe aujourd'hui).
- *Première activation* : les actions déjà présentes sont marquées connues et un seul message « Numera connecté : N actions en cours » part. Mon choix (évite la rafale).
- *Résumé hebdo* : dimanche, premier passage après 18 h (heure locale du serveur), une fois par semaine ISO : dépenses de la semaine vs moyenne, budget du mois consommé, actions ouvertes, prochaines échéances 7 jours. Tous les chiffres viennent des fonctions analytics existantes.
- Mode « masquer les montants » : remplace les montants par `•••`.

---

## Contraintes

Python 3.11/3.12 ; une migration Alembic par schéma modifié ; tous les nouveaux routers dans `protected_routers` ; tests pytest qui vérifient l'effet en base ; `npm run build` vert ; `ARCHITECTURE.md` et les skills concernés mis à jour dans le même commit que le code.

## Laissé au constructeur

Disposition fine des écrans, libellés, découpage des composants, noms des fonctions internes.
