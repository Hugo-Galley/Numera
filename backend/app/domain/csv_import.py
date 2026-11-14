"""Analyse d'un relevé CSV (export Numbers ou bancaire) : calcul pur, sans base ni HTTP.

Détection du délimiteur (`,` `;` `\t`), en-têtes normalisés via `HEADER_ALIASES`, lignes validées en
`ParsedRow` (montant toujours positif, sens porté par le type).
"""

import csv
import io
import math
import unicodedata
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.errors import BusinessRuleError
from app.core.i18n import tr
from app.domain.finance import normalize_transaction_type
from app.schemas.types import MAX_AMOUNT

REQUIRED_COLUMNS = ["Date", "Mois", "Type", "Commercant", "Categorie", "Montant", "Solde Compte", "Note"]
# Seules ces colonnes sont indispensables : « Mois » est recalculé depuis la date, « Type » se déduit du
# signe du montant, « Categorie » est facultative.
MANDATORY_COLUMNS = ["Date", "Commercant", "Montant"]

HEADER_ALIASES = {
    "date": "Date",
    "mois": "Mois",
    "type": "Type",
    "commercant": "Commercant",
    "commercant_": "Commercant",
    "commercant_nom": "Commercant",
    "commercant/payeur": "Commercant",
    "commercantpersonne": "Commercant",
    "commercantpersonne_": "Commercant",
    "commercantoupersonne": "Commercant",
    "commercantoupersonne_": "Commercant",
    "commercantoubeneficiaire": "Commercant",
    "commercantoubeneficiaire_": "Commercant",
    "commercant_ou_personne": "Commercant",
    "commercant_ou_beneficiaire": "Commercant",
    "commercant_ou_payeur": "Commercant",
    "commercant_ou_destinataire": "Commercant",
    "categorie": "Categorie",
    "cat": "Categorie",
    "montant": "Montant",
    "note": "Note",
    "description": "Note",
    "commentaire": "Note",
    "details": "Note",
    "soldecompte": "Solde Compte",
    "solde_compte": "Solde Compte",
    "solde": "Solde Compte",
}


def normalize_header(value: str) -> str:
    cleaned = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    cleaned = cleaned.strip().lower()
    cleaned = cleaned.replace("'", "").replace('"', "")
    for ch in [" ", "-", "(", ")", ".", ":", ";"]:
        cleaned = cleaned.replace(ch, "")
    return cleaned


def read_csv(content: str) -> tuple[list[dict[str, str]], str, list[str]]:
    sample = content[:4000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:  # délimiteur indétectable : virgule par défaut
        delimiter = ","

    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    rows: list[dict[str, str]] = []
    for row in reader:
        row["_line"] = str(reader.line_num)  # numéro de ligne du fichier (1 = en-têtes)
        rows.append(row)
    return rows, delimiter, list(reader.fieldnames or [])


def canonicalize_row(raw_row: dict[str, str]) -> dict[str, str]:
    canonical: dict[str, str] = dict.fromkeys(REQUIRED_COLUMNS, "")
    canonical["_line"] = str(raw_row.get("_line", ""))
    for raw_key, raw_value in raw_row.items():
        if raw_key == "_line":
            continue
        normalized_key = normalize_header(raw_key or "")
        canonical_key = HEADER_ALIASES.get(normalized_key)
        if canonical_key:
            canonical[canonical_key] = (raw_value or "").strip()
    return canonical


def parse_csv(file_bytes: bytes) -> tuple[list[dict[str, str]], str, list[str]]:
    try:
        content = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Exports bancaires fréquemment en Windows-1252 / Latin-1 (accents, « € »)
        content = file_bytes.decode("cp1252", errors="replace")
    rows, delimiter, raw_headers = read_csv(content)
    if not raw_headers:
        raise BusinessRuleError(tr("errors.csv_empty"))

    canonical_rows = [canonicalize_row(row) for row in rows]
    available = {k for row in canonical_rows for k, v in row.items() if (v or "").strip() != ""}
    missing = [col for col in MANDATORY_COLUMNS if col not in available]
    if missing:
        raise BusinessRuleError(
            tr("errors.csv_missing_columns", missing=", ".join(missing)),
        )
    return canonical_rows, delimiter, raw_headers


def parse_date(value: str) -> datetime:
    raw = (value or "").strip()
    formats = [
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {raw}")


def parse_amount(value: str) -> float:
    """Montant avec signe éventuel. Le séparateur décimal est le dernier des deux quand « , » et « . »
    sont présents (1,234.50 et 1.234,50 valent tous deux 1234,5) ; seul, « , » est décimal ; « . » aussi,
    sauf répété (1.234.567 = milliers)."""
    raw = (value or "").strip()
    raw = raw.replace("€", "").replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    if "," in raw and "." in raw:
        decimal = "," if raw.rfind(",") > raw.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        raw = raw.replace(thousands, "").replace(decimal, ".")
    elif "," in raw:
        raw = raw.replace(",", ".") if raw.count(",") == 1 else raw.replace(",", "")
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    return float(raw)


class ImportRowError(ValueError):
    """Ligne inexploitable ; le message (en français) est montré à l'utilisateur."""


@dataclass
class ParsedRow:
    line: int
    date: datetime
    type: str
    merchant: str
    category_name: str
    amount: float  # toujours positif
    note: str


def is_blank(row: dict[str, str]) -> bool:
    return not any((v or "").strip() for k, v in row.items() if k != "_line")


def parse_row(row: dict[str, str]) -> ParsedRow:
    """Valide une ligne (date, montant, type) ; lève ImportRowError avec un motif lisible."""
    line = int(row.get("_line") or 0)
    raw_date = (row.get("Date") or "").strip()
    try:
        dt = parse_date(raw_date)
    except ValueError:
        raise ImportRowError(tr("import.row_bad_date", value=raw_date)) from None

    raw_amount = (row.get("Montant") or "").strip()
    try:
        signed = parse_amount(raw_amount)
    except ValueError:
        raise ImportRowError(tr("import.row_bad_amount", value=raw_amount)) from None
    if not math.isfinite(signed) or abs(signed) >= MAX_AMOUNT:
        raise ImportRowError(tr("import.row_amount_limits", value=raw_amount))

    raw_type = (row.get("Type") or "").strip()
    if raw_type:
        try:
            tx_type = normalize_transaction_type(raw_type)
        except ValueError:
            raise ImportRowError(tr("import.row_unknown_type", value=raw_type)) from None
    elif signed < 0:
        tx_type = "Sortie"
    elif signed > 0:
        tx_type = "Entree"
    else:
        raise ImportRowError(tr("import.row_no_direction"))

    amount = abs(signed)
    if amount == 0 and tx_type != "Solde Initial":
        raise ImportRowError(tr("import.row_zero_amount"))

    if not 1900 <= dt.year < 2200:
        raise ImportRowError(tr("import.row_date_range", value=raw_date))

    return ParsedRow(
        line=line,
        date=dt,
        type=tx_type,
        merchant=(row.get("Commercant") or "").strip() or "Inconnu",
        category_name=(row.get("Categorie") or "").strip(),
        amount=amount,
        note=row.get("Note") or "",
    )


def duplicate_key(date: datetime, amount: float, merchant: str, tx_type: str) -> tuple[Any, ...]:
    """Clé de doublon d'une ligne dans un compte (règle métier 4 : date, montant, marchand, type)."""
    return (date, round(float(amount), 4), merchant, tx_type)


def apply_import_rules(rules: list[Any], merchant: str, note: str, tx_type: str) -> tuple[int | None, str, str | None]:
    """Première règle (par priorité) dont le motif figure dans le marchand ou la note :
    (catégorie, type, nom de marchand canonique) après application. Le libellé bancaire `merchant`
    n'est jamais modifié (règle 7) : le nom de la règle sert à rattacher un marchand, `None` sans règle de nom.
    Un type de règle invalide est ignoré."""
    for rule in rules:
        pattern = rule.pattern.lower()
        if pattern in merchant.lower() or pattern in note.lower():
            category_id = rule.category_id or None
            if rule.transaction_type:
                with suppress(ValueError):  # règle ancienne au type invalide : ignorée plutôt que de corrompre la ligne
                    tx_type = normalize_transaction_type(rule.transaction_type)
            return category_id, tx_type, rule.merchant_name or None
    return None, tx_type, None
