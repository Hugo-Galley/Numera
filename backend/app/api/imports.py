import csv
import io
import json
import unicodedata
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
from app.api.transactions import recalculate_running_balances

from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/import", tags=["import"])

REQUIRED_COLUMNS = ["Date", "Mois", "Type", "Commercant", "Categorie", "Montant", "Solde Compte", "Note"]

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
    rows = list(reader)
    return rows, delimiter, reader.fieldnames or []


def _canonicalize_row(raw_row: dict[str, str]) -> dict[str, str]:
    canonical: dict[str, str] = {key: "" for key in REQUIRED_COLUMNS}
    for raw_key, raw_value in raw_row.items():
        normalized_key = _normalize_header(raw_key or "")
        canonical_key = HEADER_ALIASES.get(normalized_key)
        if canonical_key:
            canonical[canonical_key] = (raw_value or "").strip()
    return canonical


def _parse_csv(file_bytes: bytes) -> tuple[list[dict[str, str]], str, list[str]]:
    content = file_bytes.decode("utf-8-sig")
    rows, delimiter, raw_headers = _read_csv_with_detected_delimiter(content)
    if not raw_headers:
        raise HTTPException(status_code=422, detail="Empty CSV file")

    canonical_rows = [_canonicalize_row(row) for row in rows]
    available = {k for row in canonical_rows for k, v in row.items() if (v or "").strip() != ""}
    missing = [col for col in REQUIRED_COLUMNS if col not in available and col not in ["Solde Compte", "Note"]]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing columns after normalization: {', '.join(missing)}")
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
    raw = (value or "").strip()
    raw = raw.replace("€", "").replace(" ", "")
    raw = raw.replace("\u202f", "").replace("\xa0", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "")
        raw = raw.replace(",", ".")
    else:
        raw = raw.replace(",", ".")
    return float(raw)


@router.get("/logs")
async def get_import_logs(limit: int = 10, db: Session = Depends(get_db)):
    logs = db.query(ImportLog).order_by(ImportLog.created_at.desc()).limit(limit).all()
    return logs


@router.post("/preview")
async def preview_import(
    file: UploadFile = File(...),
    sample_size: int = Form(default=20),
    db: Session = Depends(get_db),
):
    rows, delimiter, raw_headers = _parse_csv(await file.read())
    category_names = {c.name for c in db.query(Category).all()}
    unknown = sorted({(row.get("Categorie") or "").strip() for row in rows if (row.get("Categorie") or "").strip() and (row.get("Categorie") or "").strip() not in category_names})

    preview_rows = []
    for row in rows[:sample_size]:
        preview_rows.append(
            {
                "Date": row.get("Date"),
                "Type": row.get("Type"),
                "Commercant": row.get("Commercant"),
                "Categorie": row.get("Categorie"),
                "Montant": row.get("Montant"),
            }
        )

    return {
        "filename": file.filename,
        "total_rows": len(rows),
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

    rows, delimiter, raw_headers = _parse_csv(await file.read())
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

    for row in rows:
        try:
            dt = _parse_date(row["Date"])
            tx_type = normalize_transaction_type(row["Type"])
            merchant = (row.get("Commercant") or "").strip() or "Inconnu"
            csv_category_name = (row.get("Categorie") or "").strip()
            amount = _parse_amount(row.get("Montant") or "0")
            if amount <= 0:
                errors += 1
                if len(error_samples) < 10:
                    error_samples.append(f"Invalid amount <= 0 at {row.get('Date')} / {row.get('Montant')}")
                continue

            category_id = None

            # 0. Apply categorization rules (Highest priority)
            for rule in rules:
                pattern = rule.pattern.lower()
                note = (row.get("Note") or "").lower()
                if pattern in merchant.lower() or pattern in note:
                    if rule.category_id:
                        category_id = rule.category_id
                    if rule.transaction_type:
                        tx_type = rule.transaction_type
                    if rule.merchant_name:
                        merchant = rule.merchant_name
                    break

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

            duplicate = (
                db.query(Transaction)
                .filter(
                    and_(
                        Transaction.account_id == account_id,
                        Transaction.date == dt,
                        Transaction.amount == amount,
                        Transaction.merchant == merchant,
                        Transaction.type == tx_type,
                    )
                )
                .first()
            )
            if duplicate:
                skipped += 1
                continue

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
                note=row.get("Note") or "Imported CSV",
            )
            db.add(tx)
            imported += 1
        except Exception as exc:
            errors += 1
            if len(error_samples) < 10:
                error_samples.append(str(exc))

    summary = {
        "filename": file.filename,
        "account_id": account_id,
        "created_categories": created_categories,
        "delimiter": delimiter,
        "raw_headers": raw_headers,
        "error_samples": error_samples,
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
    }
