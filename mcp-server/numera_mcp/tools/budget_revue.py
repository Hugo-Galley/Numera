"""Outils MCP budget : revue de mois, remboursements, provisions, avantages, temps de travail."""


from numera_mcp.api_client import api, handle_response
from numera_mcp.budget_period import current_budget_month
from numera_mcp.formatting import format_table, serialize


def list_savings_goals() -> str:
    """Liste tous les objectifs d'épargne avec leur progression."""
    try:
        resp = api.get("/goals")
        error = handle_response(resp)
        if error:
            return error
        goals = resp.json()

        simplified = []
        for g in goals:
            simplified.append({
                "id": g["id"],
                "name": g.get("name", ""),
                "cible": g.get("target_amount", 0),
                "actuel": g.get("current_amount", 0),
                "progression_%": g.get("percentage", 0),
                "statut": g.get("status", "—"),
                "deadline": g.get("deadline", "—") or "—",
                "mensuel_requis": g.get("monthly_required", "—") or "—",
            })

        return f"🎯 {len(simplified)} objectif(s) :\n\n" + format_table(simplified)
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_month_review(month: int | None = None, year: int | None = None) -> str:
    """Revue de fin de mois : points à traiter (dépenses sans catégorie, comptes non vérifiés),
    comparaison au budget avec et sans dépenses exceptionnelles, et statut de clôture.

    Args:
        month: Mois (1-12, optionnel, défaut: mois budgétaire précédent)
        year: Année (optionnel, défaut: année du mois précédent)
    """
    try:
        current_year, current_month = current_budget_month()
        default_year, default_month = (current_year - 1, 12) if current_month == 1 else (current_year, current_month - 1)
        params = {
            "month": month if month is not None else default_month,
            "year": year if year is not None else default_year,
        }
        resp = api.get("/month-review", params=params)
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"🗓️ Revue de fin de mois :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def list_month_closures() -> str:
    """Mois clôturés (revue de fin de mois) avec la date, le fait marquant et la photo des chiffres."""
    try:
        resp = api.get("/month-review/closures")
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        return f"✅ Mois clôturés :\n\n{serialize(data)}"
    except Exception as e:
        return f"❌ Erreur : {e}"


def list_provisions() -> str:
    """Provisions pour grosses dépenses périodiques (taxe foncière, assurance…) : prochaine échéance,
    effort mensuel, ce qui devrait déjà être de côté, constitution réelle sur le compte rattaché et statut."""
    try:
        resp = api.get("/provisions")
        error = handle_response(resp)
        if error:
            return error
        simplified = [
            {
                "id": p["id"],
                "name": p["name"],
                "montant": p["amount"],
                "echeance": p["next_due"],
                "mensuel_requis": p["monthly_needed"],
                "cible_aujourdhui": p["target_now"],
                "constitue": p["funded"] if p["funded"] is not None else "—",
                "statut": p["status"],
            }
            for p in resp.json()
        ]
        return f"📅 {len(simplified)} provision(s) :\n\n" + format_table(simplified)
    except Exception as e:
        return f"❌ Erreur : {e}"


def list_benefits() -> str:
    """Aides perçues (prime d'activité, APL…) : organisme, montant attendu, statut du versement du mois
    (reçue, en attente, non reçue), dernier versement, total reçu dans l'année et prochaine déclaration."""
    try:
        resp = api.get("/benefits")
        error = handle_response(resp)
        if error:
            return error
        simplified = [
            {
                "id": b["id"],
                "name": b["name"],
                "organisme": b["organization"],
                "montant_attendu": b["amount"],
                "statut": b["status"],
                "dernier_versement": f"{b['last_payment']['amount']} le {b['last_payment']['date']}" if b["last_payment"] else "—",
                "recu_annee": b["received_this_year"],
                "prochaine_declaration": b["next_declaration_date"] or "—",
            }
            for b in resp.json()
        ]
        return f"🤝 {len(simplified)} aide(s) :\n\n" + format_table(simplified)
    except Exception as e:
        return f"❌ Erreur : {e}"


def get_work_time() -> str:
    """Taux horaire net (salaire net × 12 ÷ heures travaillées par an) pour exprimer un prix en heures de travail.

    Diviser un montant en euros par `taux_horaire_EUR` donne le nombre d'heures de travail qu'il représente.
    """
    try:
        resp = api.get("/salary/work-time")
        error = handle_response(resp)
        if error:
            return error
        data = resp.json()
        if not data["configured"]:
            return "ℹ️ Aucun salaire configuré : le prix en heures de travail n'est pas disponible."
        row = {
            "salaire_net_EUR": data["net_salary"],
            "jours_travailles_an": data["work_days_per_year"],
            "heures_par_jour": data["work_hours_per_day"],
            "heures_par_mois": data["hours_per_month"],
            "taux_horaire_EUR": data["hourly_rate"],
        }
        return "⏱️ Temps de travail :\n\n" + format_table([row])
    except Exception as e:
        return f"❌ Erreur : {e}"


def list_transfer_rules() -> str:
    """Règles de virement interne (compte source → compte destination) qui relient automatiquement
    les sorties aux entrées pour ne pas compter deux fois un revenu réparti entre comptes."""
    try:
        resp = api.get("/transfer-rules")
        error = handle_response(resp)
        if error:
            return error
        accounts = {a["id"]: a["name"] for a in api.get("/accounts").json()}
        rows = [
            {
                "id": r["id"],
                "source": accounts.get(r["source_account_id"], r["source_account_id"]),
                "destination": accounts.get(r["dest_account_id"], r["dest_account_id"]),
                "libelle_contient": r["pattern"] or "—",
                "montant": r["amount"] if r["amount"] is not None else "—",
                "tolerance_%": r["amount_tolerance_pct"],
                "tolerance_jours": r["day_tolerance"],
                "active": "oui" if r["is_active"] else "non",
            }
            for r in resp.json()
        ]
        return f"🔁 {len(rows)} règle(s) de virement :\n\n" + (format_table(rows) if rows else "Aucune règle.")
    except Exception as e:
        return f"❌ Erreur : {e}"


def list_reimbursement_claims(status: str = "open", debtor: str | None = None) -> str:
    """Créances de remboursement (« ce qu'on me doit ») : dépense, débiteur, attendu, reçu, reste dû.
    `status` : open (reste dû > 0, défaut), settled ou all."""
    try:
        params = {"status": status}
        if debtor:
            params["debtor"] = debtor
        resp = api.get("/reimbursements/claims", params=params)
        error = handle_response(resp)
        if error:
            return error
        rows = [
            {
                "id": c["id"],
                "date": c["expense"]["date"][:10],
                "depense": c["expense"]["label"],
                "debiteur": c["debtor"],
                "attendu": c["expected_amount"],
                "recu": c["received"],
                "reste_du": c["remaining"],
            }
            for c in resp.json()
        ]
        total = round(sum(r["reste_du"] for r in rows), 2)
        return f"💸 {len(rows)} créance(s), {total} restant dû :\n\n" + (format_table(rows) if rows else "Aucune créance.")
    except Exception as e:
        return f"❌ Erreur : {e}"


TOOLS = [
    list_savings_goals,
    get_month_review,
    list_month_closures,
    list_provisions,
    list_benefits,
    get_work_time,
    list_transfer_rules,
    list_reimbursement_claims,
]


def register(mcp) -> None:
    for tool in TOOLS:
        mcp.tool()(tool)
