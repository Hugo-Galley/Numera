import math
import csv
import io
import json
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.finance import apply_transaction_to_balance, month_label_from_date, normalize_transaction_type
from app.db.session import get_db
from app.models.account import Account
from app.models.category import Category
from app.models.categorization_rule import CategorizationRule
from app.models.import_log import ImportLog
from app.models.transaction import Transaction
from app.services.balances import recalculate_running_balances
from app.services.transfers import auto_link_transfers

from app.core.logging import get_logger

logger = get_logger(__name__)

from app.schemas.types import MAX_AMOUNT

router = APIRouter(prefix="/import", tags=["import"])

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


def _normalize_header(value: str) -> str:
    cleaned = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    cleaned = cleaned.strip().lower()
    cleaned = cleaned.replace("'", "").replace('"', "")
    for ch in [" ", "-", "(", ")", ".", ":", ";"]:
        cleaned = cleaned.replace(ch, "")
    return cleaned


def _read_csv_with_detected_delimiter(content: str) -> tuple[list[dict[str, str]], str, list[str]]:
    sample = content[:4000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ","

    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    rows = []
    for row in reader:
        row["_line"] = str(reader.line_num)  # numéro de ligne du fichier (1 = en-têtes)
        rows.append(row)
    return rows, delimiter, reader.fieldnames or []


def _canonicalize_row(raw_row: dict[str, str]) -> dict[str, str]:
    canonical: dict[str, str] = {key: "" for key in REQUIRED_COLUMNS}
    canonical["_line"] = str(raw_row.get("_line", ""))
    for raw_key, raw_value in raw_row.items():
        if raw_key == "_line":
            continue
        normalized_key = _normalize_header(raw_key or "")
        canonical_key = HEADER_ALIASES.get(normalized_key)
        if canonical_key:
            canonical[canonical_key] = (raw_value or "").strip()
    return canonical


def _parse_csv(file_bytes: bytes) -> tuple[list[dict[str, str]], str, list[str]]:
    try:
        content = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Exports bancaires fréquemment en Windows-1252 / Latin-1 (accents, « € »)
        content = file_bytes.decode("cp1252", errors="replace")
    rows, delimiter, raw_headers = _read_csv_with_detected_delimiter(content)
    if not raw_headers:
        raise HTTPException(status_code=422, detail="Fichier CSV vide")

    canonical_rows = [_canonicalize_row(row) for row in rows]
    available = {k for row in canonical_rows for k, v in row.items() if (v or "").strip() != ""}
    missing = [col for col in MANDATORY_COLUMNS if col not in available]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Colonnes manquantes dans le fichier : {', '.join(missing)}. "
            "Colonnes attendues : Date, Commercant, Montant (Type, Categorie, Mois et Note sont facultatives).",
        )
    return canonical_rows, delimiter, raw_headers


def _parse_date(value: str) -> datetime:
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


def _parse_amount(value: str) -> float:
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


def _is_blank(row: dict[str, str]) -> bool:
    return not any((v or "").strip() for k, v in row.items() if k != "_line")


def _parse_row(row: dict[str, str]) -> ParsedRow:
    """Valide une ligne (date, montant, type) ; lève ImportRowError avec un motif lisible."""
    line = int(row.get("_line") or 0)
    raw_date = (row.get("Date") or "").strip()
    try:
        dt = _parse_date(raw_date)
    except ValueError:
        raise ImportRowError(f"Date invalide « {raw_date} » (formats acceptés : JJ/MM/AAAA, AAAA-MM-JJ)") from None

    raw_amount = (row.get("Montant") or "").strip()
    try:
        signed = _parse_amount(raw_amount)
    except ValueError:
        raise ImportRowError(f"Montant invalide « {raw_amount} »") from None
    if not math.isfinite(signed) or abs(signed) >= MAX_AMOUNT:
        raise ImportRowError(f"Montant hors limites « {raw_amount} »")

    raw_type = (row.get("Type") or "").strip()
    if raw_type:
        try:
            tx_type = normalize_transaction_type(raw_type)
        except ValueError:
            raise ImportRowError(f"Type inconnu « {raw_type} » (Entree, Sortie, Interets ou Solde Initial)") from None
    elif signed < 0:
        tx_type = "Sortie"
    elif signed > 0:
        tx_type = "Entree"
    else:
        raise ImportRowError("Type absent et montant nul : impossible de déduire le sens")

    amount = abs(signed)
    if amount == 0 and tx_type != "Solde Initial":
        raise ImportRowError("Montant nul")

    if not 1900 <= dt.year < 2200:
        raise ImportRowError(f"Date hors de la plage 1900-2200 « {raw_date} »")

    return ParsedRow(
        line=line,
        date=dt,
        type=tx_type,
        merchant=(row.get("Commercant") or "").strip() or "Inconnu",
        category_name=(row.get("Categorie") or "").strip(),
        amount=amount,
        note=row.get("Note") or "",
    )


MAX_UPLOAD_BYTES = 10 * 1024 * 1024


async def _read_upload(file: UploadFile) -> bytes:
    """Lit le fichier par blocs et refuse (413) au-delà de MAX_UPLOAD_BYTES, sans tout charger en mémoire."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Fichier trop volumineux (10 Mo maximum)")
        chunks.append(chunk)
    return b"".join(chunks)


@router.get("/logs")
async def get_import_logs(limit: int = 10, db: Session = Depends(get_db)):
    logs = db.query(ImportLog).order_by(ImportLog.created_at.desc()).limit(limit).all()
    return logs


@router.post("/preview")
async def preview_import(
    file: UploadFile = File(...),
    sample_size: int = Form(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows, delimiter, raw_headers = _parse_csv(await _read_upload(file))
    category_names = {c.name for c in db.query(Category).all()}
    unknown = sorted({(row.get("Categorie") or "").strip() for row in rows if (row.get("Categorie") or "").strip() and (row.get("Categorie") or "").strip() not in category_names})

    rows = [r for r in rows if not _is_blank(r)]
    preview_rows = []
    invalid_rows = 0
    repeated: Counter = Counter()
    for index, row in enumerate(rows):
        try:
            parsed = _parse_row(row)
            error = None
            repeated[(parsed.date, round(parsed.amount, 4), parsed.merchant, parsed.type)] += 1
        except ImportRowError as exc:
            parsed, error = None, str(exc)
            invalid_rows += 1
        if index < sample_size:
            preview_rows.append(
                {
                    "line": int(row.get("_line") or 0),
                    "Date": row.get("Date"),
                    "Type": parsed.type if parsed else row.get("Type"),
                    "Commercant": row.get("Commercant"),
                    "Categorie": row.get("Categorie"),
                    "Montant": row.get("Montant"),
                    "error": error,
                }
            )

    warnings: list[str] = []
    if not any((r.get("Type") or "").strip() for r in rows):
        warnings.append("Colonne Type absente : le sens est déduit du signe du montant (négatif = Sortie).")
    repeated_in_file = sum(count - 1 for count in repeated.values() if count > 1)
    if repeated_in_file:
        warnings.append(
            f"{repeated_in_file} ligne(s) identique(s) à une autre du fichier : elles seront toutes importées "
            "(deux achats identiques le même jour sont légitimes)."
        )

    return {
        "filename": file.filename,
        "total_rows": len(rows),
        "invalid_rows": invalid_rows,
        "warnings": warnings,
        "delimiter": delimiter,
        "raw_headers": raw_headers,
        "preview": preview_rows,
        "unknown_categories": unknown,
    }


@router.post("/commit")
async def commit_import(
    account_id: int = Form(...),
    file: UploadFile = File(...),
    create_missing_categories: bool = Form(default=True),
    category_mapping: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    logger.info(f"Starting CSV import: file={file.filename}, account_id={account_id}")
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    mapping = {}
    if category_mapping:
        try:
            mapping = json.loads(category_mapping)
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid category_mapping JSON")

    rows, delimiter, raw_headers = _parse_csv(await _read_upload(file))
    imported = 0
    skipped = 0
    errors = 0
    created_categories = 0
    error_samples: list[str] = []

    categories = {c.name: c for c in db.query(Category).all()}
    categories_by_id = {c.id: c for c in categories.values()}
    
    rules = db.query(CategorizationRule).order_by(CategorizationRule.priority.desc()).all()
    
    last = (
        db.query(Transaction)
        .filter(Transaction.account_id == account_id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .first()
    )
    running_balance = last.running_balance if last else 0.0

    # Pre-fetch existing transactions for duplicate detection in O(1) to avoid N+1 queries.
    # On compte les occurrences : deux lignes identiques d'un même fichier (ex. deux cafés
    # au même prix le même jour) sont légitimes ; seule une ligne déjà présente en base
    # (en nombre d'exemplaires) est un doublon, ce qui garde l'import idempotent.
    existing_counts: Counter = Counter(
        (tx.date, round(float(tx.amount), 4), tx.merchant, tx.type)
        for tx in db.query(Transaction.date, Transaction.amount, Transaction.merchant, Transaction.type)
        .filter(Transaction.account_id == account_id)
        .all()
    )
    seen_in_file: Counter = Counter()
    has_initial_balance = (
        db.query(Transaction.id)
        .filter(Transaction.account_id == account_id, Transaction.type == "Solde Initial")
        .first()
        is not None
    )

    error_details: list[dict] = []

    def _record_error(line: int, reason: str) -> None:
        nonlocal errors
        errors += 1
        if len(error_details) < 50:
            error_details.append({"line": line, "reason": reason})
        if len(error_samples) < 10:
            error_samples.append(f"Ligne {line} : {reason}")

    for row in rows:
        if _is_blank(row):
            continue  # ligne vide ou « ;;;; » : ni importée ni comptée en erreur
        line = int(row.get("_line") or 0)
        try:
            parsed = _parse_row(row)
        except ImportRowError as exc:
            _record_error(line, str(exc))
            continue
        try:
            dt, tx_type, merchant, amount = parsed.date, parsed.type, parsed.merchant, parsed.amount
            csv_category_name = parsed.category_name

            category_id = None

            # 0. Apply categorization rules (Highest priority)
            for rule in rules:
                pattern = rule.pattern.lower()
                note = (row.get("Note") or "").lower()
                if pattern in merchant.lower() or pattern in note:
                    if rule.category_id:
                        category_id = rule.category_id
                    if rule.transaction_type:
                        try:
                            tx_type = normalize_transaction_type(rule.transaction_type)
                        except ValueError:
                            pass  # règle ancienne au type invalide : ignorée plutôt que de corrompre la ligne
                    if rule.merchant_name:
                        merchant = rule.merchant_name
                    break

            # Doublon : détecté avant toute création de catégorie (un fichier 100 % doublons ne crée rien)
            tx_key = (dt, round(float(amount), 4), merchant, tx_type)
            seen_in_file[tx_key] += 1
            if seen_in_file[tx_key] <= existing_counts[tx_key]:
                skipped += 1
                continue

            if not category_id and csv_category_name:
                # 1. Check if we have a manual mapping for this CSV category
                target = mapping.get(csv_category_name)
                if target:
                    # target can be an int (category_id) or "NEW" or a name
                    if isinstance(target, int):
                        category_id = target
                    elif target == "CREATE":
                        category = categories.get(csv_category_name)
                        if not category:
                            category = Category(name=csv_category_name, type="depense")
                            db.add(category)
                            db.flush()
                            categories[csv_category_name] = category
                            created_categories += 1
                        category_id = category.id
                    else:
                        # Assume it's a category name
                        category = categories.get(target)
                        if category:
                            category_id = category.id

                # 2. If no mapping, fallback to name-based lookup or auto-creation
                if not category_id:
                    category = categories.get(csv_category_name)
                    if not category and create_missing_categories:
                        category = Category(name=csv_category_name, type="depense")
                        db.add(category)
                        db.flush()
                        categories[csv_category_name] = category
                        created_categories += 1
                    category_id = category.id if category else None

            if tx_type == "Solde Initial":
                # Un seul Solde Initial par compte (il remet le solde à zéro à sa date)
                if has_initial_balance:
                    raise ValueError(f"Un Solde Initial existe déjà pour ce compte ({row.get('Date')})")
                has_initial_balance = True

            running_balance = apply_transaction_to_balance(running_balance, tx_type, amount)
            tx = Transaction(
                account_id=account_id,
                date=dt,
                month_label=month_label_from_date(dt),
                type=tx_type,
                merchant=merchant,
                category_id=category_id,
                amount=amount,
                currency=account.currency,
                original_amount=amount,
                running_balance=running_balance,
                note=parsed.note or "Imported CSV",
            )
            db.add(tx)
            imported += 1
        except Exception as exc:
            _record_error(line, str(exc))

    summary = {
        "filename": file.filename,
        "account_id": account_id,
        "created_categories": created_categories,
        "delimiter": delimiter,
        "raw_headers": raw_headers,
        "error_samples": error_samples,
        "error_details": error_details,
    }
    db.add(
        ImportLog(
            source_file=file.filename or "unknown.csv",
            imported_count=imported,
            skipped_count=skipped,
            error_count=errors,
            summary_json=json.dumps(summary),
        )
    )
    db.commit()

    if imported > 0:
        logger.info(f"Recalculating running balances for account_id={account_id}")
        recalculate_running_balances(db, account_id)
        await auto_link_transfers(db)

    logger.info(
        f"Import finished: file={file.filename}, imported={imported}, "
        f"skipped={skipped}, errors={errors}, created_categories={created_categories}"
    )

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "created_categories": created_categories,
        "error_samples": error_samples,
        "error_details": error_details,
    }
