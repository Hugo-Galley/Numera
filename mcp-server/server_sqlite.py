"""
Serveur MCP pour Suivi Budget
==============================
Permet à un agent IA d'interroger et manipuler la base de données
du suivi budgétaire via le protocole MCP (Model Context Protocol).

Transports supportés :
  - stdio  : pour usage local (Claude Desktop, Cursor, etc.)
  - streamable-http : pour usage distant (VPS)

Sécurité :
  - En mode stdio : isolation par processus OS
  - En mode HTTP  : clé API via header Authorization
  - Requêtes SQL brutes limitées au SELECT uniquement
  - LIMIT 200 forcé sur les requêtes SQL brutes
  - Toutes les écritures passent par des outils structurés
"""

__version__ = "1.0.0"

import json
import os
import sqlite3
import logging
from datetime import datetime, date
from contextlib import contextmanager
from typing import Any
import urllib.request
import urllib.error

from mcp.server.fastmcp import FastMCP


# ─── Configuration ───────────────────────────────────────────────────────────

DB_PATH = os.environ.get(
    "MCP_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "backend", "data", "suivi_budget.db")
)
SERVER_NAME = os.environ.get("MCP_SERVER_NAME", "Suivi Budget MCP")
TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio")
HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "8100"))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("mcp-suivi-budget")

# ─── Initialisation du serveur MCP ───────────────────────────────────────────

mcp = FastMCP(SERVER_NAME)

# ─── Helpers DB ──────────────────────────────────────────────────────────────

@contextmanager
def get_db(readonly: bool = True):
    """Ouvre une connexion SQLite. En mode readonly par défaut pour la sécurité."""
    db_path = os.path.abspath(DB_PATH)
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Base de données introuvable : {db_path}")

    uri = f"file:{db_path}"
    if readonly:
        uri += "?mode=ro"

    conn = sqlite3.connect(uri, uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    
    # Vérifier si le serveur MCP est activé dans les paramètres système
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = 'mcp_enabled'")
        row = cursor.fetchone()
        # Par défaut c'est activé si le paramètre n'existe pas encore
        mcp_enabled = row["value"].lower() == "true" if row else True
        if not mcp_enabled:
            conn.close()
            raise PermissionError("Le serveur MCP est actuellement désactivé dans les paramètres de Suivi Budget.")
    except sqlite3.OperationalError:
        # Si la table n'existe pas encore (ex: première install), on laisse passer
        pass

    if not readonly:
        conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    """Convertit des sqlite3.Row en liste de dictionnaires."""
    return [dict(row) for row in rows]


# Simple cache for latest exchange rates
_latest_rates: dict = {}

def get_latest_rates(base="EUR") -> dict:
    global _latest_rates
    if base in _latest_rates:
        return _latest_rates[base]
    
    try:
        url = f"https://api.frankfurter.dev/v1/latest?base={base}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            rates = data.get("rates", {})
            rates[base] = 1.0
            _latest_rates[base] = rates
            return rates
    except Exception as e:
        logger.warning(f"Error fetching latest exchange rates: {e}")
        if base == "EUR":
            return {"EUR": 1.0, "USD": 1.08, "GBP": 0.84, "CHF": 0.95}
    return {base: 1.0}

def get_historical_rate_db(conn, date_val, currency, base="EUR") -> float:
    if currency == base:
        return 1.0
    
    if isinstance(date_val, (datetime, date)):
        date_str = date_val.strftime("%Y-%m-%d")
    elif isinstance(date_val, str):
        date_str = date_val[:10]
    else:
        date_str = str(date_val)[:10]
        
    try:
        row = conn.execute(
            "SELECT rate FROM historical_exchange_rates WHERE date = ? AND currency = ?",
            (date_str, currency)
        ).fetchone()
        if row:
            return row["rate"]
    except Exception as e:
        logger.warning(f"Error reading historical_exchange_rates from DB: {e}")
        
    try:
        url = f"https://api.frankfurter.dev/v1/{date_str}?base={base}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            rate = data.get("rates", {}).get(currency)
            if rate:
                return rate
    except Exception as e:
        logger.warning(f"Error fetching historical rate for {date_str} {currency}: {e}")
        
    rates = get_latest_rates(base)
    return rates.get(currency, 1.0)

def convert_amount(conn, amount, from_currency, to_currency="EUR", date_val=None) -> float:
    if from_currency == to_currency:
        return amount
    
    if to_currency == "EUR" and date_val:
        rate = get_historical_rate_db(conn, date_val, from_currency, base=to_currency)
        return amount / rate
        
    rates = get_latest_rates(to_currency)
    rate = rates.get(from_currency, 1.0)
    return amount / rate



def format_table(rows: list[dict], max_col_width: int = 40) -> str:
    """Formate des résultats en table lisible pour le LLM."""
    if not rows:
        return "Aucun résultat."

    columns = list(rows[0].keys())

    # Calculer la largeur de chaque colonne
    widths = {}
    for col in columns:
        values = [str(row.get(col, "")) for row in rows]
        widths[col] = min(max(len(col), max(len(v) for v in values)), max_col_width)

    # Header
    header = " | ".join(col.ljust(widths[col])[:widths[col]] for col in columns)
    separator = "-+-".join("-" * widths[col] for col in columns)

    # Rows
    lines = [header, separator]
    for row in rows:
        line = " | ".join(
            str(row.get(col, "")).ljust(widths[col])[:widths[col]]
            for col in columns
        )
        lines.append(line)

    return "\n".join(lines)


def serialize(obj: Any) -> str:
    """Sérialise un objet en JSON lisible."""
    return json.dumps(obj, indent=2, default=str, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCES — Données en lecture seule accessibles par le LLM
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.resource("schema://tables")
def resource_list_tables() -> str:
    """Liste toutes les tables de la base de données avec leur nombre de lignes."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'alembic_%' ORDER BY name"
        )
        tables = [row["name"] for row in cursor.fetchall()]

        result = []
        for table in tables:
            count = conn.execute(f"SELECT COUNT(*) as cnt FROM [{table}]").fetchone()["cnt"]
            result.append(f"- {table} ({count} lignes)")

        return "Tables dans la base de données :\n" + "\n".join(result)


@mcp.resource("schema://table/{table_name}")
def resource_table_schema(table_name: str) -> str:
    """Retourne le schéma détaillé d'une table (colonnes, types, contraintes)."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Vérifier que la table existe
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        result = cursor.fetchone()
        if not result:
            return f"❌ Table '{table_name}' introuvable."

        # Infos colonnes via PRAGMA
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        columns = cursor.fetchall()

        lines = [f"## Table : {table_name}\n"]
        lines.append(f"```sql\n{result['sql']}\n```\n")
        lines.append("### Colonnes :\n")
        for col in columns:
            pk = " 🔑 PRIMARY KEY" if col["pk"] else ""
            nullable = " (nullable)" if not col["notnull"] else " (NOT NULL)"
            default = f" [défaut: {col['dflt_value']}]" if col["dflt_value"] else ""
            lines.append(f"- **{col['name']}** : {col['type']}{pk}{nullable}{default}")

        # Foreign keys
        cursor.execute(f"PRAGMA foreign_key_list([{table_name}])")
        fks = cursor.fetchall()
        if fks:
            lines.append("\n### Clés étrangères :\n")
            for fk in fks:
                lines.append(f"- {fk['from']} → {fk['table']}.{fk['to']}")

        return "\n".join(lines)


@mcp.resource("data://accounts")
def resource_accounts() -> str:
    """Liste tous les comptes avec leur dernier solde connu."""
    with get_db() as conn:
        accounts = rows_to_dicts(conn.execute(
            """SELECT a.id, a.name, a.type, a.currency, a.active, a.color,
                      COALESCE(
                          (SELECT t.running_balance FROM transactions t
                           WHERE t.account_id = a.id ORDER BY t.date DESC, t.id DESC LIMIT 1),
                          0
                      ) as balance
               FROM accounts a ORDER BY a.active DESC, a.name"""
        ).fetchall())
        return serialize(accounts)


@mcp.resource("data://categories")
def resource_categories() -> str:
    """Liste toutes les catégories de dépenses/revenus."""
    with get_db() as conn:
        categories = rows_to_dicts(conn.execute(
            "SELECT * FROM categories ORDER BY type, name"
        ).fetchall())
        return serialize(categories)


@mcp.resource("data://tags")
def resource_tags() -> str:
    """Liste tous les tags disponibles."""
    with get_db() as conn:
        tags = rows_to_dicts(conn.execute("SELECT * FROM tags ORDER BY name").fetchall())
        return serialize(tags)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS — Lecture / Consultation
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def list_accounts(type: str | None = None) -> str:
    """Liste tous les comptes bancaires avec leur solde actuel, type et devise.
    Inclut les comptes actifs et inactifs.
    
    Args:
        type: Filtrer par type (ex: courant, epargne, investissement) (optionnel)
    """
    try:
        with get_db() as conn:
            query = """SELECT a.id, a.name, a.type, a.currency, a.active, a.color,
                              a.asset_class, a.sector, a.geographic_zone,
                              COALESCE(
                                  (SELECT t.running_balance FROM transactions t
                                   WHERE t.account_id = a.id ORDER BY t.date DESC, t.id DESC LIMIT 1),
                                  0
                              ) as solde_actuel,
                              (SELECT COUNT(*) FROM transactions t WHERE t.account_id = a.id) as nb_transactions
                       FROM accounts a"""
            params = []
            if type:
                query += " WHERE a.type = ?"
                params.append(type)
            query += " ORDER BY a.active DESC, a.name"
            accounts = rows_to_dicts(conn.execute(query, params).fetchall())
            return format_table(accounts)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def list_categories(type: str | None = None) -> str:
    """Liste les catégories de dépenses/revenus.

    Args:
        type: Filtrer par type (optionnel). Valeurs possibles : toutes les valeurs de la colonne type.
    """
    try:
        with get_db() as conn:
            query = "SELECT * FROM categories"
            params: list = []
            if type:
                query += " WHERE type = ?"
                params.append(type)
            query += " ORDER BY type, name"
            categories = rows_to_dicts(conn.execute(query, params).fetchall())
            return format_table(categories)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def list_transactions(
    account_id: int | None = None,
    category_id: int | None = None,
    type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    merchant: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Liste les transactions avec filtres optionnels.

    Args:
        account_id: Filtrer par compte (ID)
        category_id: Filtrer par catégorie (ID)
        type: Filtrer par type (Entree, Sortie, Interets, Solde Initial)
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
        merchant: Recherche partielle dans le nom du marchand
        limit: Nombre max de résultats (défaut 50, max 200)
        offset: Décalage pour la pagination
    """
    try:
        limit = min(limit, 200)
        with get_db() as conn:
            conditions = []
            params: list = []

            if account_id is not None:
                conditions.append("t.account_id = ?")
                params.append(account_id)
            if category_id is not None:
                conditions.append("t.category_id = ?")
                params.append(category_id)
            if type:
                conditions.append("t.type = ?")
                params.append(type)
            if start_date:
                conditions.append("t.date >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("t.date <= ?")
                params.append(end_date + "T23:59:59")
            if merchant:
                conditions.append("t.merchant LIKE ?")
                params.append(f"%{merchant}%")

            where = " AND ".join(conditions) if conditions else "1=1"
            query = f"""
                SELECT t.id, t.date, t.type, t.merchant, t.amount, t.currency,
                       t.running_balance, t.note, t.month_label,
                       c.name as categorie,
                       a.name as compte
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN accounts a ON t.account_id = a.id
                WHERE {where}
                ORDER BY t.date DESC, t.id DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            rows = rows_to_dicts(conn.execute(query, params).fetchall())

            # Compter le total
            count_query = f"SELECT COUNT(*) as total FROM transactions t WHERE {where}"
            total = conn.execute(count_query, params[:-2]).fetchone()["total"]

            header = f"📊 {len(rows)} transaction(s) affichée(s) sur {total} au total\n\n"
            return header + format_table(rows)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_transaction(transaction_id: int) -> str:
    """Récupère le détail complet d'une transaction par son ID.

    Args:
        transaction_id: L'ID de la transaction
    """
    try:
        with get_db() as conn:
            row = conn.execute(
                """SELECT t.*, c.name as categorie, c.icon as categorie_icon,
                          a.name as compte, a.type as compte_type
                   FROM transactions t
                   LEFT JOIN categories c ON t.category_id = c.id
                   LEFT JOIN accounts a ON t.account_id = a.id
                   WHERE t.id = ?""",
                (transaction_id,)
            ).fetchone()
            if not row:
                return f"❌ Transaction #{transaction_id} introuvable."

            d = dict(row)
            # Récupérer les tags
            tags = rows_to_dicts(conn.execute(
                """SELECT tg.name, tg.color FROM tags tg
                   JOIN transaction_tags tt ON tg.id = tt.tag_id
                   WHERE tt.transaction_id = ?""",
                (transaction_id,)
            ).fetchall())
            d["tags"] = [t["name"] for t in tags]

            return serialize(d)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def search_transactions(query: str, limit: int = 20) -> str:
    """Recherche textuelle dans les transactions (merchant et note).

    Args:
        query: Texte à rechercher
        limit: Nombre max de résultats (défaut 20)
    """
    try:
        limit = min(limit, 100)
        with get_db() as conn:
            rows = rows_to_dicts(conn.execute(
                """SELECT t.id, t.date, t.type, t.merchant, t.amount, t.currency,
                          t.note, c.name as categorie, a.name as compte
                   FROM transactions t
                   LEFT JOIN categories c ON t.category_id = c.id
                   LEFT JOIN accounts a ON t.account_id = a.id
                   WHERE t.merchant LIKE ? OR t.note LIKE ?
                   ORDER BY t.date DESC
                   LIMIT ?""",
                (f"%{query}%", f"%{query}%", limit)
            ).fetchall())
            return f"🔍 {len(rows)} résultat(s) pour '{query}' :\n\n" + format_table(rows)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def list_recurring_transactions(is_active: bool | None = None) -> str:
    """Liste les transactions récurrentes (abonnements, salaires, etc.).

    Args:
        is_active: Filtrer par statut actif/inactif (optionnel)
    """
    try:
        with get_db() as conn:
            query = """
                SELECT rt.id, rt.name, rt.type, rt.amount, rt.currency,
                       rt.frequency, rt.day_of_month, rt.is_active,
                       rt.start_date, rt.end_date, rt.note,
                       c.name as categorie, a.name as compte
                FROM recurring_transactions rt
                LEFT JOIN categories c ON rt.category_id = c.id
                LEFT JOIN accounts a ON rt.account_id = a.id
            """
            params: list = []
            if is_active is not None:
                query += " WHERE rt.is_active = ?"
                params.append(1 if is_active else 0)
            query += " ORDER BY rt.is_active DESC, rt.amount DESC"

            rows = rows_to_dicts(conn.execute(query, params).fetchall())
            return format_table(rows)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def list_savings_goals() -> str:
    """Liste tous les objectifs d'épargne avec leur progression."""
    try:
        with get_db() as conn:
            goals = rows_to_dicts(conn.execute(
                """SELECT sg.id, sg.name, sg.target_amount, sg.keyword,
                          sg.deadline, sg.icon, sg.color,
                          a.name as compte, c.name as categorie
                   FROM savings_goals sg
                   LEFT JOIN accounts a ON sg.account_id = a.id
                   LEFT JOIN categories c ON sg.category_id = c.id
                   ORDER BY sg.name"""
            ).fetchall())
            return format_table(goals)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def list_tags() -> str:
    """Liste tous les tags avec le nombre de transactions associées."""
    try:
        with get_db() as conn:
            tags = rows_to_dicts(conn.execute(
                """SELECT t.id, t.name, t.color,
                          COUNT(tt.transaction_id) as nb_transactions
                   FROM tags t
                   LEFT JOIN transaction_tags tt ON t.id = tt.tag_id
                   GROUP BY t.id
                   ORDER BY t.name"""
            ).fetchall())
            return format_table(tags)
    except Exception as e:
        return f"❌ Erreur : {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS — Analytics
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_budget_summary(
    month: int | None = None,
    year: int | None = None,
    account_id: int | None = None,
) -> str:
    """Résumé budget par catégorie pour un mois donné.
    Compare les dépenses aux limites définies dans les catégories.

    Args:
        month: Mois (1-12, optionnel, défaut: mois en cours)
        year: Année (optionnel, défaut: année en cours)
        account_id: Filtrer par compte spécifique (optionnel)
    """
    try:
        if month is None:
            month = datetime.now().month
        if year is None:
            year = datetime.now().year
            
        month_label = f"{year:04d}-{month:02d}"

        with get_db() as conn:
            # Dépenses par catégorie
            query_expenses = """
                SELECT c.id, c.name, c.icon, c.color, c.type,
                       c.monthly_limit, c.annual_limit,
                       COALESCE(SUM(t.amount), 0) as depense_mois
                FROM categories c
                LEFT JOIN transactions t ON t.category_id = c.id
                    AND t.month_label = ?
                    AND t.type = 'Sortie'
            """
            params_expenses = [month_label]
            if account_id is not None:
                query_expenses += " AND t.account_id = ?"
                params_expenses.append(account_id)
            
            query_expenses += """
                GROUP BY c.id
                HAVING depense_mois > 0 OR c.monthly_limit IS NOT NULL
                ORDER BY depense_mois DESC
            """
            
            rows = rows_to_dicts(conn.execute(query_expenses, params_expenses).fetchall())

            # Ajouter le pourcentage d'utilisation et le statut
            for row in rows:
                if row.get("monthly_limit") and row["monthly_limit"] > 0:
                    ratio = (row["depense_mois"] / row["monthly_limit"]) * 100
                    row["utilisation_%"] = f"{ratio:.0f}%"
                    if ratio >= 100:
                        row["statut"] = "🔴 DÉPASSÉ"
                    elif ratio >= 80:
                        row["statut"] = "🟠 ATTENTION"
                    else:
                        row["statut"] = "🟢 OK"
                else:
                    row["utilisation_%"] = "—"
                    row["statut"] = "—"

            # Calcul des Totaux (revenus / dépenses)
            total_depenses = sum(r["depense_mois"] for r in rows)
            
            query_revenus = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE month_label = ? AND type = 'Entree'"
            params_revenus = [month_label]
            if account_id is not None:
                query_revenus += " AND account_id = ?"
                params_revenus.append(account_id)
            
            total_revenus = conn.execute(query_revenus, params_revenus).fetchone()["total"]

            header = f"📊 Budget {month_label}\n"
            if account_id is not None:
                header += f"🏦 Filtre compte : #{account_id}\n"
            header += f"💰 Revenus : {total_revenus:,.2f} €\n"
            header += f"💸 Dépenses : {total_depenses:,.2f} €\n"
            header += f"📈 Solde : {total_revenus - total_depenses:,.2f} €\n\n"

            return header + format_table(rows)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_expenses_by_category(
    month: int | None = None,
    year: int | None = None,
    account_id: int | None = None,
) -> str:
    """Répartition des dépenses par catégorie pour un mois donné.

    Args:
        month: Mois (1-12, optionnel, défaut: mois en cours)
        year: Année (optionnel, défaut: année en cours)
        account_id: Filtrer par compte (optionnel)
    """
    try:
        if month is None:
            month = datetime.now().month
        if year is None:
            year = datetime.now().year
            
        month_label = f"{year:04d}-{month:02d}"

        with get_db() as conn:
            # Calcul du total global des dépenses pour le calcul du pourcentage
            total_query = "SELECT SUM(amount) FROM transactions WHERE month_label = ? AND type = 'Sortie' AND is_transfer = 0"
            total_params = [month_label]
            if account_id is not None:
                total_query += " AND account_id = ?"
                total_params.append(account_id)
            
            total_val = conn.execute(total_query, total_params).fetchone()[0] or 0.0

            # Requête de répartition
            query = """
                SELECT c.name as categorie, c.icon, c.color,
                       COUNT(t.id) as nb_transactions,
                       SUM(t.amount) as total,
                       ROUND(AVG(t.amount), 2) as moyenne
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.month_label = ? AND t.type = 'Sortie' AND t.is_transfer = 0
            """
            params = [month_label]
            if account_id is not None:
                query += " AND t.account_id = ?"
                params.append(account_id)
                
            query += """
                GROUP BY c.id
                ORDER BY total DESC
            """
            
            rows = rows_to_dicts(conn.execute(query, params).fetchall())
            
            for row in rows:
                row["part_%"] = f"{(((row['total'] or 0) / total_val * 100.0) if total_val > 0 else 0.0):.1f}%"

            header = f"💸 Dépenses par catégorie pour {month_label} : {total_val:,.2f} €\n"
            if account_id is not None:
                header += f"🏦 Filtre compte : #{account_id}\n"
            header += "\n"
            return header + format_table(rows)
    except Exception as e:
        return f"❌ Erreur : {e}"


def _calculate_investment_flows_db(conn, account, end_date, start_date=None, target_currency="EUR") -> dict:
    baseline_date = None
    baseline_val_raw = 0.0
    
    if start_date:
        last_snap = conn.execute(
            """SELECT date, current_value FROM balance_snapshots 
               WHERE account_id = ? AND date < ? 
               ORDER BY date DESC, id DESC LIMIT 1""",
            (account["id"], start_date)
        ).fetchone()
        if last_snap:
            baseline_val_raw = float(last_snap["current_value"])
            baseline_date = last_snap["date"]
        else:
            last_tx = conn.execute(
                """SELECT date, running_balance FROM transactions 
                   WHERE account_id = ? AND date < ? 
                   ORDER BY date DESC, id DESC LIMIT 1""",
                (account["id"], start_date)
            ).fetchone()
            if last_tx:
                baseline_val_raw = float(last_tx["running_balance"])
                baseline_date = last_tx["date"]
    else:
        zero_point = conn.execute(
            """SELECT date, current_value FROM balance_snapshots 
               WHERE account_id = ? AND is_zero_point = 1 AND date <= ? 
               ORDER BY date DESC, id DESC LIMIT 1""",
            (account["id"], end_date)
        ).fetchone()
        if zero_point:
            baseline_val_raw = float(zero_point["current_value"])
            baseline_date = zero_point["date"]
            
    baseline_val_target = 0.0
    if baseline_val_raw != 0:
        baseline_val_target = convert_amount(conn, baseline_val_raw, account["currency"], target_currency, baseline_date)
        
    total_verse_target = 0.0
    total_retire_target = 0.0
    
    # 2. Fetch flows from investment_transactions
    itx_query = "SELECT type, original_amount, currency, date FROM investment_transactions WHERE account_id = ? AND date <= ?"
    itx_params = [account["id"], end_date]
    if start_date:
        itx_query += " AND date >= ?"
        itx_params.append(start_date)
    elif baseline_date:
        itx_query += " AND date > ?"
        itx_params.append(baseline_date)
        
    itxs = conn.execute(itx_query, itx_params).fetchall()
    for tx in itxs:
        amount_target = convert_amount(conn, tx["original_amount"], tx["currency"], target_currency, tx["date"])
        if tx["type"] == "versement":
            total_verse_target += amount_target
        elif tx["type"] == "retrait":
            total_retire_target += amount_target
            
    # 3. Regular Transactions
    rtx_query = """
        SELECT t.type, t.original_amount, t.currency, t.date, t.merchant, c.name as cat_name
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.account_id = ? AND t.date <= ?
    """
    rtx_params = [account["id"], end_date]
    if start_date:
        rtx_query += " AND t.date >= ?"
        rtx_params.append(start_date)
    elif baseline_date:
        rtx_query += " AND t.date > ?"
        rtx_params.append(baseline_date)
        
    rtxs = conn.execute(rtx_query, rtx_params).fetchall()
    for tx in rtxs:
        merchant_lower = (tx["merchant"] or "").lower()
        cat_name = tx["cat_name"] or ""
        
        if tx["type"] in ("Solde Initial", "Entree"):
            if cat_name in ("Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"):
                continue
            if "dividende" in merchant_lower:
                continue
            if "vente" in merchant_lower:
                amount_target = convert_amount(conn, tx["original_amount"], tx["currency"], target_currency, tx["date"])
                total_retire_target += amount_target
                continue
                
            amount_target = convert_amount(conn, tx["original_amount"], tx["currency"], target_currency, tx["date"])
            total_verse_target += amount_target
        elif tx["type"] == "Sortie":
            if any(k in merchant_lower for k in ("achat", "frais", "commission", "tax")):
                continue
            amount_target = convert_amount(conn, tx["original_amount"], tx["currency"], target_currency, tx["date"])
            total_retire_target += amount_target
            
    net_invested_target = baseline_val_target + total_verse_target - total_retire_target
    return {
        "baseline_val_target": baseline_val_target,
        "baseline_date": baseline_date,
        "total_verse_target": total_verse_target,
        "total_retire_target": total_retire_target,
        "net_invested_target": net_invested_target
    }


@mcp.tool()
def get_investments_summary(
    account_id: int | None = None,
    month: int | None = None,
    year: int | None = None,
) -> str:
    """Résumé des investissements (comptes d'investissement actifs).

    Args:
        account_id: Filtrer par compte spécifique (optionnel)
        month: Mois (1-12, optionnel)
        year: Année (optionnel)
    """
    try:
        with get_db() as conn:
            query_acc = "SELECT id, name, currency, active FROM accounts WHERE type = 'investissement' AND active = 1"
            params_acc = []
            if account_id:
                query_acc += " AND id = ?"
                params_acc.append(account_id)
                
            accounts = rows_to_dicts(conn.execute(query_acc, params_acc).fetchall())
            if not accounts:
                return "Aucun compte d'investissement actif trouvé."
                
            end_date = datetime.now()
            start_date = None
            if month and year:
                start_date = datetime(year, month, 1)
                end_date = datetime(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
                
            latest_snapshots = {}
            for acc in accounts:
                row = conn.execute(
                    """SELECT current_value, date FROM balance_snapshots 
                       WHERE account_id = ? AND date <= ? 
                       ORDER BY date DESC, id DESC LIMIT 1""",
                    (acc["id"], end_date)
                ).fetchone()
                if row:
                    latest_snapshots[acc["id"]] = (float(row["current_value"]), row["date"])
                else:
                    last_tx = conn.execute(
                        """SELECT running_balance, date FROM transactions 
                           WHERE account_id = ? AND date <= ? 
                           ORDER BY date DESC, id DESC LIMIT 1""",
                        (acc["id"], end_date)
                    ).fetchone()
                    if last_tx:
                        latest_snapshots[acc["id"]] = (float(last_tx["running_balance"]), last_tx["date"])
                        
            items = []
            total_net_invested_eur = 0.0
            total_current_value_eur = 0.0
            
            for acc in accounts:
                flows = _calculate_investment_flows_db(conn, acc, end_date, start_date=start_date, target_currency="EUR")
                net_invested_eur = flows["net_invested_target"]
                
                snap_info = latest_snapshots.get(acc["id"])
                if snap_info:
                    raw_val, snap_date = snap_info
                    current_value_eur = convert_amount(conn, raw_val, acc["currency"], "EUR", snap_date)
                else:
                    current_value_eur = net_invested_eur
                    
                gain_eur = current_value_eur - net_invested_eur
                performance_pct = (gain_eur / net_invested_eur * 100.0) if net_invested_eur > 0 else 0.0
                
                total_net_invested_eur += net_invested_eur
                total_current_value_eur += current_value_eur
                
                items.append({
                    "id": acc["id"],
                    "compte": acc["name"],
                    "versements": round(flows["total_verse_target"], 2),
                    "retraits": round(flows["total_retire_target"], 2),
                    "investi_net": round(net_invested_eur, 2),
                    "valeur_actuelle": round(current_value_eur, 2),
                    "gain_eur": round(gain_eur, 2),
                    "performance": f"{performance_pct:.2f}%",
                    "devise": acc["currency"]
                })
                
            total_gain_eur = total_current_value_eur - total_net_invested_eur
            total_perf_pct = (total_gain_eur / total_net_invested_eur * 100.0) if total_net_invested_eur > 0 else 0.0
            
            header = (
                f"📈 Résumé des Investissements ({'Tous comptes' if not account_id else accounts[0]['name']})\n"
                f"{'='*50}\n"
                f"💰 Total Investi Net : {total_net_invested_eur:,.2f} €\n"
                f"📊 Valeur Actuelle  : {total_current_value_eur:,.2f} €\n"
                f"📈 Gain Latent Global: {total_gain_eur:,.2f} €\n"
                f"📈 Performance Glob.: {total_perf_pct:.2f} %\n\n"
            )
            return header + format_table(items)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_investment_performance(account_id: int) -> str:
    """Analyse de performance détaillée d'un compte d'investissement spécifique.

    Args:
        account_id: ID du compte d'investissement
    """
    try:
        with get_db() as conn:
            account = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
            if not account:
                return f"❌ Compte #{account_id} introuvable."
            account = dict(account)
            if account["type"] != "investissement":
                return f"❌ Le compte #{account_id} n'est pas un compte d'investissement."
                
            zero_point = conn.execute(
                """SELECT * FROM balance_snapshots 
                   WHERE account_id = ? AND is_zero_point = 1
                   ORDER BY date DESC, id DESC LIMIT 1""",
                (account_id,)
            ).fetchone()
            
            baseline_date = zero_point["date"] if zero_point else None
            baseline_val = float(zero_point["current_value"]) if zero_point else 0.0
            
            flows = _calculate_investment_flows_db(conn, account, datetime.now(), target_currency=account["currency"])
            net_invested = flows["net_invested_target"]
            baseline_date = flows["baseline_date"]
            
            latest_snap = conn.execute(
                """SELECT * FROM balance_snapshots 
                   WHERE account_id = ? 
                   ORDER BY date DESC, id DESC LIMIT 1""",
                (account_id,)
            ).fetchone()
            if latest_snap:
                current_value = float(latest_snap["current_value"])
            else:
                current_value = net_invested
                last_tx = conn.execute(
                    "SELECT running_balance FROM transactions WHERE account_id = ? ORDER BY date DESC, id DESC LIMIT 1",
                    (account_id,)
                ).fetchone()
                if last_tx:
                    current_value = float(last_tx["running_balance"])
                    
            gain = current_value - net_invested
            performance_pct = (gain / net_invested * 100.0) if net_invested > 0 else 0.0
            
            snapshots = rows_to_dicts(conn.execute(
                "SELECT date, current_value, is_zero_point, note FROM balance_snapshots WHERE account_id = ? ORDER BY date ASC",
                (account_id,)
            ).fetchall())
            
            itxs = rows_to_dicts(conn.execute(
                """SELECT 'investissement' as src, date, type, original_amount, currency, note,
                           asset_class, sector, geographic_zone
                   FROM investment_transactions
                   WHERE account_id = ?
                   ORDER BY date ASC""",
                (account_id,)
            ).fetchall())
            
            rtxs = rows_to_dicts(conn.execute(
                """SELECT 'courant' as src, date, type, original_amount, currency, merchant as note
                   FROM transactions
                   WHERE account_id = ?
                   ORDER BY date ASC""",
                (account_id,)
            ).fetchall())
            
            all_txs = []
            for tx in itxs:
                amount = convert_amount(conn, tx["original_amount"], tx["currency"], account["currency"], tx["date"])
                all_txs.append({
                    "date": tx["date"],
                    "source": "Investissement",
                    "type": tx["type"],
                    "montant_devise": f"{tx['original_amount']:,.2f} {tx['currency']}",
                    "montant_compte": f"{amount:,.2f} {account['currency']}",
                    "note": tx["note"] or "",
                    "allocation": f"{tx['asset_class'] or ''} / {tx['sector'] or ''} / {tx['geographic_zone'] or ''}"
                })
            for tx in rtxs:
                merchant_lower = (tx["note"] or "").lower()
                if tx["type"] in ("Solde Initial", "Entree"):
                    if "dividende" in merchant_lower:
                        continue
                elif tx["type"] == "Sortie":
                    if any(k in merchant_lower for k in ("achat", "frais", "commission", "tax")):
                        continue
                
                amount = convert_amount(conn, tx["original_amount"], tx["currency"], account["currency"], tx["date"])
                tx_type = "versement" if tx["type"] in ("Entree", "Solde Initial") else "retrait"
                all_txs.append({
                    "date": tx["date"],
                    "source": "Courant (Liée)",
                    "type": tx_type,
                    "montant_devise": f"{tx['original_amount']:,.2f} {tx['currency']}",
                    "montant_compte": f"{amount:,.2f} {account['currency']}",
                    "note": tx["note"] or "",
                    "allocation": "—"
                })
                
            all_txs.sort(key=lambda x: x["date"], reverse=True)
            
            header = (
                f"🏦 Performance du compte '{account['name']}' ({account['currency']})\n"
                f"{'='*60}\n"
                f"📉 Point zéro (baseline)  : {baseline_val:,.2f} {account['currency']} (le {baseline_date or 'N/A'})\n"
                f"💵 Versements cumulés     : {flows['total_verse_target']:,.2f} {account['currency']}\n"
                f"💸 Retraits cumulés       : {flows['total_retire_target']:,.2f} {account['currency']}\n"
                f"💰 Capital net investi    : {net_invested:,.2f} {account['currency']}\n"
                f"📈 Valeur actuelle        : {current_value:,.2f} {account['currency']}\n"
                f"📊 Gain net               : {gain:,.2f} {account['currency']}\n"
                f"📈 Performance            : {performance_pct:.2f} %\n\n"
            )
            
            res = header
            if snapshots:
                res += "📋 Historique des Valeurs Liquidatives (Snapshots) :\n" + format_table(snapshots) + "\n\n"
            if all_txs:
                res += "📝 Transactions récentes :\n" + format_table(all_txs[:30])
            return res
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_investment_performance_history(account_id: int, months: int = 12) -> str:
    """Historique des performances mensuelles d'un compte d'investissement spécifique.

    Args:
        account_id: ID du compte d'investissement
        months: Nombre de mois (défaut 12)
    """
    try:
        with get_db() as conn:
            account = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
            if not account:
                return f"❌ Compte #{account_id} introuvable."
            account = dict(account)
            if account["type"] != "investissement":
                return f"❌ Le compte #{account_id} n'est pas un compte d'investissement."
                
            zero_point = conn.execute(
                """SELECT * FROM balance_snapshots 
                   WHERE account_id = ? AND is_zero_point = 1
                   ORDER BY date DESC, id DESC LIMIT 1""",
                (account_id,)
            ).fetchone()
            
            baseline_date = zero_point["date"] if zero_point else None
            baseline_value = float(zero_point["current_value"]) if zero_point else 0.0
            
            tx_q = "SELECT type, original_amount, currency, date FROM investment_transactions WHERE account_id = ?"
            rtx_q = """
                SELECT t.type, t.original_amount, t.currency, t.date, t.merchant, c.name as cat_name
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.account_id = ?
            """
            snap_q = "SELECT date, current_value, is_zero_point FROM balance_snapshots WHERE account_id = ?"
            params = [account_id]
            if baseline_date:
                tx_q += " AND date >= ?"
                rtx_q += " AND t.date >= ?"
                snap_q += " AND date >= ?"
                params.append(baseline_date)
                
            txs = conn.execute(tx_q, params).fetchall()
            rtxs = conn.execute(rtx_q, params).fetchall()
            snaps = conn.execute(snap_q, params).fetchall()
            
            tx_events_by_day = {}
            for tx in txs:
                if tx["type"] == "dividende":
                    continue
                day_str = tx["date"][:10]
                if day_str not in tx_events_by_day:
                    tx_events_by_day[day_str] = {"versement": 0.0, "retrait": 0.0}
                amount = convert_amount(conn, tx["original_amount"], tx["currency"], account["currency"], tx["date"])
                if tx["type"] == "versement":
                    tx_events_by_day[day_str]["versement"] += amount
                elif tx["type"] == "retrait":
                    tx_events_by_day[day_str]["retrait"] += amount
                    
            for tx in rtxs:
                merchant_lower = (tx["merchant"] or "").lower()
                cat_name = tx["cat_name"] or ""
                day_str = tx["date"][:10]
                if day_str not in tx_events_by_day:
                    tx_events_by_day[day_str] = {"versement": 0.0, "retrait": 0.0}
                
                if tx["type"] in ("Solde Initial", "Entree"):
                    if cat_name in ("Interets", "Intérêts", "Intérêt", "Interet", "Dividendes", "Dividende"):
                        continue
                    if "dividende" in merchant_lower:
                        continue
                    if "vente" in merchant_lower:
                        amount = convert_amount(conn, tx["original_amount"], tx["currency"], account["currency"], tx["date"])
                        tx_events_by_day[day_str]["retrait"] += amount
                        continue
                    amount = convert_amount(conn, tx["original_amount"], tx["currency"], account["currency"], tx["date"])
                    tx_events_by_day[day_str]["versement"] += amount
                elif tx["type"] == "Sortie":
                    if any(k in merchant_lower for k in ("achat", "frais", "commission", "tax")):
                        continue
                    amount = convert_amount(conn, tx["original_amount"], tx["currency"], account["currency"], tx["date"])
                    tx_events_by_day[day_str]["retrait"] += amount
                    
            all_dates = sorted(set(tx_events_by_day.keys()) | {s["date"][:10] for s in snaps})
            
            running_verse = 0.0
            running_retire = 0.0
            series = []
            
            snaps_by_day = {s["date"][:10]: s for s in snaps}
            
            for day_str in all_dates:
                event = tx_events_by_day.get(day_str, {"versement": 0.0, "retrait": 0.0})
                running_verse += event["versement"]
                running_retire += event["retrait"]
                
                snap = snaps_by_day.get(day_str)
                if snap:
                    net_invested = baseline_value + running_verse - running_retire
                    current_value = float(snap["current_value"])
                    gain = current_value - net_invested
                    performance_pct = (gain / net_invested * 100.0) if net_invested > 0 else 0.0
                    series.append({
                        "date": day_str,
                        "net_invested": round(net_invested, 2),
                        "current_value": round(current_value, 2),
                        "gain": round(gain, 2),
                        "performance": f"{performance_pct:.2f}%",
                        "baseline": "Oui" if snap["is_zero_point"] else "Non"
                    })
                    
            series.sort(key=lambda x: x["date"], reverse=True)
            limited_series = series[:months]
            limited_series.reverse()
            
            header = f"📈 Historique des performances de '{account['name']}' ({account['currency']}) :\n\n"
            return header + format_table(limited_series)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_investments_allocation(account_id: int | None = None) -> str:
    """Répartition de l'allocation d'actifs globale ou pour un compte spécifique.

    Args:
        account_id: Filtrer par compte spécifique (optionnel)
    """
    try:
        with get_db() as conn:
            query = "SELECT id, name, currency FROM accounts WHERE type = 'investissement' AND active = 1"
            params = []
            if account_id:
                query += " AND id = ?"
                params.append(account_id)
                
            accounts = rows_to_dicts(conn.execute(query, params).fetchall())
            if not accounts:
                return "Aucun compte d'investissement actif trouvé."
                
            total_current_value_eur = 0.0
            items = []
            
            for acc in accounts:
                flows = _calculate_investment_flows_db(conn, acc, datetime.now(), target_currency="EUR")
                net_invested_eur = flows["net_invested_target"]
                
                snap = conn.execute(
                    "SELECT current_value, date FROM balance_snapshots WHERE account_id = ? ORDER BY date DESC, id DESC LIMIT 1",
                    (acc["id"],)
                ).fetchone()
                if snap:
                    val_eur = convert_amount(conn, float(snap["current_value"]), acc["currency"], "EUR", snap["date"])
                else:
                    val_eur = net_invested_eur
                    
                total_current_value_eur += val_eur
                items.append({
                    "id": acc["id"],
                    "compte": acc["name"],
                    "valeur_eur": val_eur,
                    "investi_net_eur": net_invested_eur,
                    "gain_eur": val_eur - net_invested_eur,
                    "devise": acc["currency"]
                })
                
            for item in items:
                pct = (item["valeur_eur"] / total_current_value_eur * 100.0) if total_current_value_eur > 0 else 0.0
                item["pourcentage"] = f"{pct:.2f}%"
                item["valeur_eur"] = f"{item['valeur_eur']:,.2f} €"
                item["investi_net_eur"] = f"{item['investi_net_eur']:,.2f} €"
                item["gain_eur"] = f"{item['gain_eur']:,.2f} €"
                
            items.sort(key=lambda x: float(x["pourcentage"].replace("%", "")), reverse=True)
            
            header = f"🧩 Allocation des investissements (Total : {total_current_value_eur:,.2f} €) :\n\n"
            return header + format_table(items)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_investments_allocation_advanced() -> str:
    """Allocation d'actifs détaillée avancée par classe, secteur et zone géographique."""
    try:
        with get_db() as conn:
            accounts = rows_to_dicts(conn.execute(
                "SELECT id, name, currency, asset_class, sector, geographic_zone FROM accounts WHERE type = 'investissement' AND active = 1"
            ).fetchall())
            if not accounts:
                return "Aucun compte d'investissement actif trouvé."
                
            total_value_eur = 0.0
            current_by_account = {}
            for acc in accounts:
                flows = _calculate_investment_flows_db(conn, acc, datetime.now(), target_currency="EUR")
                net_invested_eur = flows["net_invested_target"]
                
                snap = conn.execute(
                    "SELECT current_value, date FROM balance_snapshots WHERE account_id = ? ORDER BY date DESC, id DESC LIMIT 1",
                    (acc["id"],)
                ).fetchone()
                if snap:
                    val_eur = convert_amount(conn, float(snap["current_value"]), acc["currency"], "EUR", snap["date"])
                else:
                    val_eur = net_invested_eur
                current_by_account[acc["id"]] = val_eur
                total_value_eur += val_eur
                
            by_asset_class = {}
            by_sector = {}
            by_zone = {}
            
            def _add_to_agg(agg_dict, cat_name, val, acc):
                if not cat_name:
                    cat_name = "Non classé"
                if cat_name not in agg_dict:
                    agg_dict[cat_name] = {"value": 0.0, "items": {}}
                agg_dict[cat_name]["value"] += val
                acc_id = acc["id"]
                if acc_id not in agg_dict[cat_name]["items"]:
                    agg_dict[cat_name]["items"][acc_id] = {"name": acc["name"], "value": 0.0}
                agg_dict[cat_name]["items"][acc_id]["value"] += val
                
            for acc in accounts:
                val_eur = current_by_account[acc["id"]]
                if val_eur <= 0:
                    continue
                    
                txs_with_allocation = rows_to_dicts(conn.execute(
                    "SELECT amount, asset_class, sector, geographic_zone FROM investment_transactions WHERE account_id = ? AND asset_class IS NOT NULL",
                    (acc["id"],)
                ).fetchall())
                
                if txs_with_allocation:
                    total_tx_amount = sum(abs(tx["amount"]) for tx in txs_with_allocation)
                    if total_tx_amount > 0:
                        for tx in txs_with_allocation:
                            weight = abs(tx["amount"]) / total_tx_amount
                            tx_val_eur = val_eur * weight
                            _add_to_agg(by_asset_class, tx["asset_class"], tx_val_eur, acc)
                            _add_to_agg(by_sector, tx["sector"], tx_val_eur, acc)
                            _add_to_agg(by_zone, tx["geographic_zone"], tx_val_eur, acc)
                    else:
                        _add_to_agg(by_asset_class, acc["asset_class"], val_eur, acc)
                        _add_to_agg(by_sector, acc["sector"], val_eur, acc)
                        _add_to_agg(by_zone, acc["geographic_zone"], val_eur, acc)
                else:
                    _add_to_agg(by_asset_class, acc["asset_class"], val_eur, acc)
                    _add_to_agg(by_sector, acc["sector"], val_eur, acc)
                    _add_to_agg(by_zone, acc["geographic_zone"], val_eur, acc)
                    
            def _format_agg(agg_dict):
                result = []
                for name, data in agg_dict.items():
                    val = data["value"]
                    pct = (val / total_value_eur * 100.0) if total_value_eur > 0 else 0.0
                    result.append({
                        "Allocation": name,
                        "Valeur (EUR)": f"{val:,.2f} €",
                        "Part (%)": f"{pct:.2f}%"
                    })
                result.sort(key=lambda x: float(x["Part (%)"].replace("%", "")), reverse=True)
                return format_table(result)
                
            res = (
                f"🔬 Allocation d'Actifs Avancée (Total : {total_value_eur:,.2f} €)\n"
                f"{'='*60}\n\n"
                f"📁 Répartition par Classe d'Actifs :\n"
                f"{_format_agg(by_asset_class)}\n\n"
                f"🏭 Répartition par Secteur :\n"
                f"{_format_agg(by_sector)}\n\n"
                f"🌍 Répartition par Zone Géographique :\n"
                f"{_format_agg(by_zone)}\n"
            )
            return res
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_income_vs_expenses(start_date: str, end_date: str) -> str:
    """Compare les revenus et dépenses sur une période.

    Args:
        start_date: Date de début (YYYY-MM-DD)
        end_date: Date de fin (YYYY-MM-DD)
    """
    try:
        with get_db() as conn:
            result = conn.execute(
                """SELECT
                       SUM(CASE WHEN type = 'Entree' THEN amount ELSE 0 END) as revenus,
                       SUM(CASE WHEN type = 'Sortie' AND is_transfer = 0 THEN amount ELSE 0 END) as depenses,
                       SUM(CASE WHEN type = 'Interets' THEN amount ELSE 0 END) as interets,
                       COUNT(*) as nb_transactions
                   FROM transactions
                   WHERE date >= ? AND date <= ?""",
                (start_date, end_date + "T23:59:59")
            ).fetchone()

            revenus = result["revenus"] or 0
            depenses = result["depenses"] or 0
            interets = result["interets"] or 0
            solde = revenus + interets - depenses
            taux_epargne = ((revenus - depenses) / revenus * 100) if revenus > 0 else 0

            return (
                f"📊 Bilan du {start_date} au {end_date}\n"
                f"{'='*40}\n"
                f"💰 Revenus      : {revenus:>12,.2f} €\n"
                f"📈 Intérêts     : {interets:>12,.2f} €\n"
                f"💸 Dépenses     : {depenses:>12,.2f} €\n"
                f"{'─'*40}\n"
                f"📈 Solde net    : {solde:>12,.2f} €\n"
                f"🏦 Taux épargne : {taux_epargne:>11,.1f} %\n"
                f"📝 Transactions : {result['nb_transactions']:>12}\n"
            )
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_top_merchants(
    month: int | None = None,
    year: int | None = None,
    account_id: int | None = None,
    limit: int = 10,
) -> str:
    """Top marchands par montant total dépensé.

    Args:
        month: Mois (1-12, optionnel, défaut: mois en cours)
        year: Année (optionnel, défaut: année en cours)
        account_id: Filtrer par compte (optionnel)
        limit: Nombre de marchands à afficher (défaut 10)
    """
    try:
        if month is None:
            month = datetime.now().month
        if year is None:
            year = datetime.now().year
            
        month_label = f"{year:04d}-{month:02d}"
        limit = min(limit, 50)
        
        with get_db() as conn:
            conditions = ["t.month_label = ?", "t.type = 'Sortie'", "t.is_transfer = 0"]
            params = [month_label]
            if account_id is not None:
                conditions.append("t.account_id = ?")
                params.append(account_id)

            where = " AND ".join(conditions)
            rows = rows_to_dicts(conn.execute(
                f"""SELECT t.merchant,
                           COUNT(*) as nb_transactions,
                           SUM(t.amount) as total,
                           ROUND(AVG(t.amount), 2) as moyenne,
                           MIN(t.date) as premiere_transaction,
                           MAX(t.date) as derniere_transaction
                    FROM transactions t
                    WHERE {where}
                    GROUP BY t.merchant
                    ORDER BY total DESC
                    LIMIT ?""",
                params + [limit]
            ).fetchall())

            header = f"🏪 Top {limit} marchands pour {month_label} :\n"
            if account_id is not None:
                header += f"🏦 Filtre compte : #{account_id}\n"
            header += "\n"
            return header + format_table(rows)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_monthly_trends(months: int = 6) -> str:
    """Tendances mensuelles des revenus et dépenses sur les N derniers mois.

    Args:
        months: Nombre de mois à analyser (défaut 6)
    """
    try:
        months = min(months, 24)
        with get_db() as conn:
            rows = rows_to_dicts(conn.execute(
                """SELECT month_label as mois,
                          SUM(CASE WHEN type = 'Entree' THEN amount ELSE 0 END) as revenus,
                          SUM(CASE WHEN type = 'Sortie' AND is_transfer = 0 THEN amount ELSE 0 END) as depenses,
                          SUM(CASE WHEN type = 'Interets' THEN amount ELSE 0 END) as interets,
                          COUNT(*) as nb_transactions
                   FROM transactions
                   GROUP BY month_label
                   ORDER BY month_label DESC
                   LIMIT ?""",
                (months,)
            ).fetchall())

            for row in rows:
                row["solde"] = round(row["revenus"] - row["depenses"], 2)
                if row["revenus"] > 0:
                    row["taux_epargne_%"] = f"{((row['revenus'] - row['depenses']) / row['revenus'] * 100):.1f}%"
                else:
                    row["taux_epargne_%"] = "—"

            return f"📈 Tendances sur {months} mois :\n\n" + format_table(rows)
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def get_account_balance_history(account_id: int, months: int = 12) -> str:
    """Historique du solde d'un compte par mois.

    Args:
        account_id: ID du compte
        months: Nombre de mois d'historique (défaut 12)
    """
    try:
        months = min(months, 36)
        with get_db() as conn:
            # Vérifier que le compte existe
            account = conn.execute(
                "SELECT name FROM accounts WHERE id = ?", (account_id,)
            ).fetchone()
            if not account:
                return f"❌ Compte #{account_id} introuvable."

            # Dernier solde connu par mois
            rows = rows_to_dicts(conn.execute(
                """SELECT month_label as mois,
                          running_balance as solde_fin_mois,
                          COUNT(*) as nb_transactions,
                          SUM(CASE WHEN type = 'Entree' THEN amount ELSE 0 END) as entrees,
                          SUM(CASE WHEN type = 'Sortie' THEN amount ELSE 0 END) as sorties
                   FROM transactions
                   WHERE account_id = ?
                   GROUP BY month_label
                   ORDER BY month_label DESC
                   LIMIT ?""",
                (account_id, months)
            ).fetchall())

            # Corriger le solde de fin de mois : prendre le running_balance de la dernière transaction du mois
            for row in rows:
                last_balance = conn.execute(
                    """SELECT running_balance FROM transactions
                       WHERE account_id = ? AND month_label = ?
                       ORDER BY date DESC, id DESC LIMIT 1""",
                    (account_id, row["mois"])
                ).fetchone()
                if last_balance:
                    row["solde_fin_mois"] = last_balance["running_balance"]

            return f"🏦 Historique du compte '{account['name']}' :\n\n" + format_table(rows)
    except Exception as e:
        return f"❌ Erreur : {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS — Écriture
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def add_transaction(
    account_id: int,
    date: str,
    type: str,
    merchant: str,
    amount: float,
    category_id: int | None = None,
    note: str | None = None,
    currency: str = "EUR",
    tag_ids: list[int] | None = None,
) -> str:
    """Ajoute une nouvelle transaction dans la base.

    Args:
        account_id: ID du compte bancaire
        date: Date de la transaction (YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)
        type: Type de transaction (Entree, Sortie, Interets)
        merchant: Nom du marchand / description
        amount: Montant (toujours positif, le type détermine le sens)
        category_id: ID de la catégorie (optionnel)
        note: Note additionnelle (optionnel)
        currency: Devise (défaut EUR)
        tag_ids: Liste d'IDs de tags à associer (optionnel)
    """
    try:
        # Validation
        if type not in ("Entree", "Sortie", "Interets"):
            return "❌ Type invalide. Valeurs autorisées : Entree, Sortie, Interets"
        if amount <= 0:
            return "❌ Le montant doit être positif."
        if len(merchant) > 120:
            return "❌ Le nom du marchand ne doit pas dépasser 120 caractères."

        # Parser la date et calculer le month_label
        try:
            if "T" in date:
                dt = datetime.fromisoformat(date)
            else:
                dt = datetime.fromisoformat(date + "T00:00:00")
        except ValueError:
            return "❌ Format de date invalide. Utilisez YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS"

        month_label = dt.strftime("%Y-%m")

        with get_db(readonly=False) as conn:
            # Vérifier que le compte existe
            account = conn.execute(
                "SELECT id, name FROM accounts WHERE id = ?", (account_id,)
            ).fetchone()
            if not account:
                return f"❌ Compte #{account_id} introuvable."

            # Vérifier la catégorie si fournie
            if category_id is not None:
                cat = conn.execute(
                    "SELECT id, name FROM categories WHERE id = ?", (category_id,)
                ).fetchone()
                if not cat:
                    return f"❌ Catégorie #{category_id} introuvable."

            # Calculer le running_balance
            last_tx = conn.execute(
                """SELECT running_balance FROM transactions
                   WHERE account_id = ?
                   ORDER BY date DESC, id DESC LIMIT 1""",
                (account_id,)
            ).fetchone()
            last_balance = last_tx["running_balance"] if last_tx else 0.0

            if type == "Entree" or type == "Interets":
                running_balance = last_balance + amount
            else:
                running_balance = last_balance - amount

            # Insérer la transaction
            cursor = conn.execute(
                """INSERT INTO transactions
                   (account_id, date, month_label, type, merchant, category_id,
                    amount, currency, original_amount, running_balance, note,
                    is_recurring, is_subscription_ignored, is_transfer, is_transfer_ignored)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0)""",
                (account_id, dt.isoformat(), month_label, type, merchant,
                 category_id, amount, currency, amount, running_balance, note)
            )
            tx_id = cursor.lastrowid

            # Associer les tags si fournis
            if tag_ids:
                for tag_id in tag_ids:
                    conn.execute(
                        "INSERT OR IGNORE INTO transaction_tags (transaction_id, tag_id) VALUES (?, ?)",
                        (tx_id, tag_id)
                    )

            conn.commit()

            return (
                f"✅ Transaction #{tx_id} créée avec succès !\n"
                f"  📅 Date : {date}\n"
                f"  🏷️ Type : {type}\n"
                f"  🏪 Marchand : {merchant}\n"
                f"  💰 Montant : {amount:,.2f} {currency}\n"
                f"  🏦 Compte : {account['name']}\n"
                f"  📊 Solde après : {running_balance:,.2f} {currency}\n"
            )
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def update_transaction(
    transaction_id: int,
    date: str | None = None,
    type: str | None = None,
    merchant: str | None = None,
    category_id: int | None = None,
    amount: float | None = None,
    note: str | None = None,
) -> str:
    """Met à jour une transaction existante (mise à jour partielle).

    Args:
        transaction_id: ID de la transaction à modifier
        date: Nouvelle date (YYYY-MM-DD, optionnel)
        type: Nouveau type (Entree, Sortie, Interets, optionnel)
        merchant: Nouveau marchand (optionnel)
        category_id: Nouvelle catégorie ID (optionnel)
        amount: Nouveau montant (optionnel)
        note: Nouvelle note (optionnel)
    """
    try:
        updates = {}
        if date is not None:
            try:
                if "T" in date:
                    dt = datetime.fromisoformat(date)
                else:
                    dt = datetime.fromisoformat(date + "T00:00:00")
                updates["date"] = dt.isoformat()
                updates["month_label"] = dt.strftime("%Y-%m")
            except ValueError:
                return "❌ Format de date invalide."
        if type is not None:
            if type not in ("Entree", "Sortie", "Interets"):
                return "❌ Type invalide."
            updates["type"] = type
        if merchant is not None:
            updates["merchant"] = merchant
        if category_id is not None:
            updates["category_id"] = category_id
        if amount is not None:
            if amount <= 0:
                return "❌ Le montant doit être positif."
            updates["amount"] = amount
            updates["original_amount"] = amount
        if note is not None:
            updates["note"] = note

        if not updates:
            return "❌ Aucun champ à mettre à jour."

        with get_db(readonly=False) as conn:
            # Vérifier l'existence
            existing = conn.execute(
                "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
            ).fetchone()
            if not existing:
                return f"❌ Transaction #{transaction_id} introuvable."

            # Construire la requête UPDATE
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            params = list(updates.values()) + [transaction_id]
            conn.execute(
                f"UPDATE transactions SET {set_clause} WHERE id = ?",
                params
            )
            conn.commit()

            return f"✅ Transaction #{transaction_id} mise à jour avec succès.\nChamps modifiés : {', '.join(updates.keys())}"
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def delete_transaction(transaction_id: int) -> str:
    """Supprime une transaction par son ID.

    ⚠️ Action irréversible ! Demande confirmation avant d'exécuter.

    Args:
        transaction_id: ID de la transaction à supprimer
    """
    try:
        with get_db(readonly=False) as conn:
            # Récupérer les infos avant suppression
            tx = conn.execute(
                """SELECT t.id, t.date, t.merchant, t.amount, t.type, a.name as compte
                   FROM transactions t
                   LEFT JOIN accounts a ON t.account_id = a.id
                   WHERE t.id = ?""",
                (transaction_id,)
            ).fetchone()
            if not tx:
                return f"❌ Transaction #{transaction_id} introuvable."

            # Supprimer les tags associés
            conn.execute(
                "DELETE FROM transaction_tags WHERE transaction_id = ?",
                (transaction_id,)
            )
            # Supprimer la transaction
            conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            conn.commit()

            return (
                f"🗑️ Transaction #{transaction_id} supprimée :\n"
                f"  📅 {tx['date']} | {tx['type']} | {tx['merchant']} | {tx['amount']:,.2f} €\n"
                f"  🏦 Compte : {tx['compte']}"
            )
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def add_category(
    name: str,
    type: str,
    icon: str | None = None,
    color: str | None = None,
    group: str | None = None,
    monthly_limit: float | None = None,
    annual_limit: float | None = None,
) -> str:
    """Ajoute une nouvelle catégorie de dépense ou revenu.

    Args:
        name: Nom de la catégorie
        type: Type (ex: Sortie, Entree, etc.)
        icon: Icône emoji (optionnel)
        color: Couleur hex (optionnel, ex: #FF5733)
        group: Groupe de catégorie (optionnel)
        monthly_limit: Limite budgétaire mensuelle (optionnel)
        annual_limit: Limite budgétaire annuelle (optionnel)
    """
    try:
        if not name or len(name) > 120:
            return "❌ Le nom doit faire entre 1 et 120 caractères."

        with get_db(readonly=False) as conn:
            # Vérifier l'unicité
            existing = conn.execute(
                "SELECT id FROM categories WHERE name = ?", (name,)
            ).fetchone()
            if existing:
                return f"❌ La catégorie '{name}' existe déjà (ID: {existing['id']})."

            cursor = conn.execute(
                """INSERT INTO categories (name, type, icon, color, "group", monthly_limit, annual_limit)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, type, icon, color, group, monthly_limit, annual_limit)
            )
            conn.commit()

            return f"✅ Catégorie '{name}' créée avec l'ID #{cursor.lastrowid}"
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def categorize_transaction(transaction_id: int, category_id: int) -> str:
    """Change la catégorie d'une transaction.

    Args:
        transaction_id: ID de la transaction
        category_id: ID de la nouvelle catégorie
    """
    try:
        with get_db(readonly=False) as conn:
            # Vérifier la transaction
            tx = conn.execute(
                "SELECT id, merchant FROM transactions WHERE id = ?",
                (transaction_id,)
            ).fetchone()
            if not tx:
                return f"❌ Transaction #{transaction_id} introuvable."

            # Vérifier la catégorie
            cat = conn.execute(
                "SELECT id, name FROM categories WHERE id = ?", (category_id,)
            ).fetchone()
            if not cat:
                return f"❌ Catégorie #{category_id} introuvable."

            conn.execute(
                "UPDATE transactions SET category_id = ? WHERE id = ?",
                (category_id, transaction_id)
            )
            conn.commit()

            return f"✅ Transaction #{transaction_id} ({tx['merchant']}) → catégorie '{cat['name']}'"
    except Exception as e:
        return f"❌ Erreur : {e}"


@mcp.tool()
def bulk_categorize(merchant: str, category_id: int) -> str:
    """Catégorise en masse toutes les transactions d'un marchand donné.

    Args:
        merchant: Nom exact du marchand
        category_id: ID de la catégorie à appliquer
    """
    try:
        with get_db(readonly=False) as conn:
            # Vérifier la catégorie
            cat = conn.execute(
                "SELECT id, name FROM categories WHERE id = ?", (category_id,)
            ).fetchone()
            if not cat:
                return f"❌ Catégorie #{category_id} introuvable."

            # Compter les transactions à modifier
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM transactions WHERE merchant = ?",
                (merchant,)
            ).fetchone()["cnt"]

            if count == 0:
                return f"❌ Aucune transaction trouvée pour le marchand '{merchant}'."

            conn.execute(
                "UPDATE transactions SET category_id = ? WHERE merchant = ?",
                (category_id, merchant)
            )
            conn.commit()

            return (
                f"✅ {count} transaction(s) du marchand '{merchant}' "
                f"catégorisée(s) en '{cat['name']}'"
            )
    except Exception as e:
        return f"❌ Erreur : {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS — SQL brut sécurisé
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def execute_read_query(sql: str) -> str:
    """Exécute une requête SQL en lecture seule (SELECT uniquement).

    ⚠️ Sécurité : Seules les requêtes SELECT sont autorisées.
    Un LIMIT 200 est automatiquement ajouté si absent.

    Args:
        sql: Requête SQL SELECT à exécuter
    """
    try:
        # Validation stricte : uniquement SELECT
        cleaned = sql.strip().upper()
        if not cleaned.startswith("SELECT"):
            return "❌ Seules les requêtes SELECT sont autorisées."

        # Vérifier l'absence de mots-clés dangereux
        dangerous_keywords = [
            "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
            "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA",
        ]
        for keyword in dangerous_keywords:
            # Chercher le mot-clé comme mot entier (pas dans un nom de colonne)
            if f" {keyword} " in f" {cleaned} " or cleaned.startswith(f"{keyword} "):
                return f"❌ Mot-clé interdit détecté : {keyword}"

        # Forcer un LIMIT si absent
        if "LIMIT" not in cleaned:
            sql = sql.rstrip(";").strip() + " LIMIT 200"

        with get_db() as conn:
            rows = rows_to_dicts(conn.execute(sql).fetchall())
            return f"📋 {len(rows)} résultat(s) :\n\n" + format_table(rows)
    except sqlite3.Error as e:
        return f"❌ Erreur SQL : {e}"
    except Exception as e:
        return f"❌ Erreur : {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS — Templates pour l'agent IA
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.prompt()
def analyze_month(month: int, year: int) -> str:
    """Prompt pour analyser en détail un mois de budget.

    Args:
        month: Mois à analyser (1-12)
        year: Année (ex: 2026)
    """
    month_label = f"{year:04d}-{month:02d}"
    return f"""Analyse complète du budget pour le mois {month_label}.

Étapes à suivre :
1. Utilise `get_budget_summary` avec month={month} et year={year} pour obtenir le résumé
2. Utilise `get_expenses_by_category` avec month={month} et year={year} pour la répartition des dépenses
3. Utilise `get_top_merchants` avec month={month} et year={year} pour voir les plus gros postes de dépenses
4. Utilise `list_transactions` avec start_date="{month_label}-01" et end_date="{month_label}-31" pour voir le détail

Fournis une analyse complète incluant :
- Résumé revenus / dépenses / solde
- Top 5 catégories de dépenses
- Top 5 marchands
- Alertes budget (catégories qui dépassent les limites)
- Comparaison avec le mois précédent si possible
- Recommandations pour optimiser le budget
"""


@mcp.prompt()
def audit_subscriptions() -> str:
    """Prompt pour auditer tous les abonnements et paiements récurrents."""
    return """Audit complet des abonnements et paiements récurrents.

Étapes à suivre :
1. Utilise `list_recurring_transactions` pour voir tous les abonnements définis
2. Utilise `search_transactions` pour chercher des patterns récurrents non déclarés
3. Utilise `get_monthly_trends` pour voir l'évolution

Pour chaque abonnement identifié, indique :
- Nom et montant mensuel
- Catégorie
- Depuis quand il est actif
- S'il est toujours utilisé / pertinent

Fournis :
- Coût total mensuel des abonnements
- Coût total annuel
- Recommandations d'optimisation (abonnements à annuler, alternatives moins chères)
- Abonnements potentiellement oubliés (transactions récurrentes non déclarées)
"""


@mcp.prompt()
def budget_review() -> str:
    """Prompt pour une review complète et approfondie du budget."""
    return """Review complète du budget et des finances.

Étapes à suivre :
1. Utilise `list_accounts` pour voir tous les comptes et soldes
2. Utilise `get_monthly_trends` avec months=12 pour les tendances annuelles
3. Utilise `get_budget_summary` pour le mois en cours
4. Utilise `get_expenses_by_category` sur les 3 derniers mois
5. Utilise `list_recurring_transactions` pour les charges fixes
6. Utilise `list_savings_goals` pour les objectifs d'épargne

Fournis une review structurée :

## 1. Situation financière globale
- Solde total tous comptes
- Évolution sur les 6 derniers mois

## 2. Revenus et dépenses
- Moyenne mensuelle des revenus
- Moyenne mensuelle des dépenses
- Taux d'épargne moyen

## 3. Catégories de dépenses
- Top 5 postes de dépenses
- Catégories en croissance
- Catégories où on peut économiser

## 4. Abonnements et charges fixes
- Total mensuel
- Recommandations

## 5. Objectifs d'épargne
- Progression
- Recommandations

## 6. Recommandations globales
- Actions prioritaires
- Objectifs à fixer
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Point d'entrée
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info(f"Démarrage du serveur MCP '{SERVER_NAME}' v{__version__}")
    logger.info(f"Base de données : {os.path.abspath(DB_PATH)}")
    logger.info(f"Transport : {TRANSPORT}")

    if TRANSPORT == "sse" or TRANSPORT == "streamable-http":
        import uvicorn
        import time
        # Small delay to let the backend finish migrations first
        time.sleep(5)
        logger.info(f"Écoute sur {HOST}:{PORT}")
        uvicorn.run(mcp.sse_app(), host=HOST, port=PORT)
    else:
        mcp.run(transport="stdio")
