"""Import CSV : aperçu et import idempotent d'un relevé dans un compte.

Doublon = (compte, date, montant, marchand, type) déjà présent en base, en nombre d'exemplaires :
deux lignes identiques d'un même fichier sont légitimes. Le solde courant part de la dernière
transaction du compte, puis tout le compte est recalculé si au moins une ligne est importée.
"""
import json
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, NotFoundError
from app.domain.finance import apply_transaction_to_balance, month_label_from_date
from app.core.logging import get_logger
from app.domain.csv_import import (
    ImportRowError, ParsedRow, apply_import_rules, duplicate_key, is_blank, parse_csv, parse_row,
)
from app.models.account import Account
from app.models.category import Category
from app.models.import_log import ImportLog
from app.models.transaction import Transaction
from app.repositories import accounts as account_repo
from app.repositories import categorization_rules as rule_repo
from app.repositories import imports as repo
from app.services.balances import recalculate_running_balances
from app.services.transfers import auto_link_transfers

logger = get_logger(__name__)

MAX_ERROR_DETAILS = 50
MAX_ERROR_SAMPLES = 10


def get_import_logs(db: Session, limit: int) -> list[ImportLog]:
    return repo.recent_logs(db, limit)


def preview_import(db: Session, content: bytes, filename: str | None, sample_size: int) -> dict:
    rows, delimiter, raw_headers = parse_csv(content)
    category_names = set(repo.categories_by_name(db))
    unknown = sorted({
        (row.get("Categorie") or "").strip() for row in rows
        if (row.get("Categorie") or "").strip() and (row.get("Categorie") or "").strip() not in category_names
    })

    rows = [r for r in rows if not is_blank(r)]
    preview_rows = []
    invalid_rows = 0
    repeated: Counter = Counter()
    for index, row in enumerate(rows):
        try:
            parsed = parse_row(row)
            error = None
            repeated[(parsed.date, round(parsed.amount, 4), parsed.merchant, parsed.type)] += 1
        except ImportRowError as exc:
            parsed, error = None, str(exc)
            invalid_rows += 1
        if index < sample_size:
            preview_rows.append({
                "line": int(row.get("_line") or 0),
                "Date": row.get("Date"),
                "Type": parsed.type if parsed else row.get("Type"),
                "Commercant": row.get("Commercant"),
                "Categorie": row.get("Categorie"),
                "Montant": row.get("Montant"),
                "error": error,
            })

    return {
        "filename": filename,
        "total_rows": len(rows),
        "invalid_rows": invalid_rows,
        "warnings": _preview_warnings(rows, repeated),
        "delimiter": delimiter,
        "raw_headers": raw_headers,
        "preview": preview_rows,
        "unknown_categories": unknown,
    }


def _preview_warnings(rows: list[dict], repeated: Counter) -> list[str]:
    warnings: list[str] = []
    if not any((r.get("Type") or "").strip() for r in rows):
        warnings.append("Colonne Type absente : le sens est déduit du signe du montant (négatif = Sortie).")
    repeated_in_file = sum(count - 1 for count in repeated.values() if count > 1)
    if repeated_in_file:
        warnings.append(
            f"{repeated_in_file} ligne(s) identique(s) à une autre du fichier : elles seront toutes importées "
            "(deux achats identiques le même jour sont légitimes)."
        )
    return warnings


@dataclass
class _ImportRun:
    """État d'un import en cours : compteurs, catégories connues, détection de doublons."""
    account: Account
    categories: dict[str, Category]
    mapping: dict
    create_missing_categories: bool
    existing_counts: Counter
    has_initial_balance: bool
    running_balance: float
    rules: list = field(default_factory=list)
    imported: int = 0
    skipped: int = 0
    errors: int = 0
    created_categories: int = 0
    seen_in_file: Counter = field(default_factory=Counter)
    error_samples: list[str] = field(default_factory=list)
    error_details: list[dict] = field(default_factory=list)

    def record_error(self, line: int, reason: str) -> None:
        self.errors += 1
        if len(self.error_details) < MAX_ERROR_DETAILS:
            self.error_details.append({"line": line, "reason": reason})
        if len(self.error_samples) < MAX_ERROR_SAMPLES:
            self.error_samples.append(f"Ligne {line} : {reason}")


def _parse_mapping(category_mapping: str | None) -> dict:
    if not category_mapping:
        return {}
    try:
        return json.loads(category_mapping)
    except Exception:
        raise BusinessRuleError("Invalid category_mapping JSON")


def _create_category(db: Session, run: _ImportRun, name: str) -> Category:
    category = Category(name=name, type="depense")
    repo.add(db, category)
    run.categories[name] = category
    run.created_categories += 1
    return category


def _resolve_category(db: Session, run: _ImportRun, csv_name: str) -> int | None:
    """Catégorie d'une ligne : correspondance manuelle (id, « CREATE » ou nom), sinon même nom,
    créé si `create_missing_categories`."""
    target = run.mapping.get(csv_name)
    if target:
        if isinstance(target, int):
            return target
        if target == "CREATE":
            return (run.categories.get(csv_name) or _create_category(db, run, csv_name)).id
        category = run.categories.get(target)
        if category:
            return category.id
    category = run.categories.get(csv_name)
    if not category and run.create_missing_categories:
        category = _create_category(db, run, csv_name)
    return category.id if category else None


def _import_row(db: Session, run: _ImportRun, parsed: ParsedRow, raw_date: str | None) -> None:
    category_id, tx_type, merchant = apply_import_rules(rules=run.rules, merchant=parsed.merchant,
                                                        note=parsed.note, tx_type=parsed.type)
    # Doublon : détecté avant toute création de catégorie (un fichier 100 % doublons ne crée rien)
    key = duplicate_key(parsed.date, parsed.amount, merchant, tx_type)
    run.seen_in_file[key] += 1
    if run.seen_in_file[key] <= run.existing_counts[key]:
        run.skipped += 1
        return
    if not category_id and parsed.category_name:
        category_id = _resolve_category(db, run, parsed.category_name)
    if tx_type == "Solde Initial":
        # Un seul Solde Initial par compte (il remet le solde à zéro à sa date)
        if run.has_initial_balance:
            raise ValueError(f"Un Solde Initial existe déjà pour ce compte ({raw_date})")
        run.has_initial_balance = True

    run.running_balance = apply_transaction_to_balance(run.running_balance, tx_type, parsed.amount)
    db.add(Transaction(
        account_id=run.account.id,
        date=parsed.date,
        month_label=month_label_from_date(parsed.date),
        type=tx_type,
        merchant=merchant,
        category_id=category_id,
        amount=parsed.amount,
        currency=run.account.currency,
        original_amount=parsed.amount,
        running_balance=run.running_balance,
        note=parsed.note or "Imported CSV",
    ))
    run.imported += 1


def _log_import(db: Session, run: _ImportRun, filename: str | None, delimiter: str, raw_headers: list[str]) -> None:
    summary = {
        "filename": filename,
        "account_id": run.account.id,
        "created_categories": run.created_categories,
        "delimiter": delimiter,
        "raw_headers": raw_headers,
        "error_samples": run.error_samples,
        "error_details": run.error_details,
    }
    db.add(ImportLog(
        source_file=filename or "unknown.csv",
        imported_count=run.imported,
        skipped_count=run.skipped,
        error_count=run.errors,
        summary_json=json.dumps(summary),
    ))


def _start_run(db: Session, account: Account, mapping: dict, create_missing_categories: bool) -> _ImportRun:
    last = account_repo.latest_transaction(db, account.id)
    run = _ImportRun(
        account=account,
        categories=repo.categories_by_name(db),
        mapping=mapping,
        create_missing_categories=create_missing_categories,
        existing_counts=repo.existing_keys(db, account.id),
        has_initial_balance=repo.has_initial_balance(db, account.id),
        running_balance=last.running_balance if last else 0.0,
        rules=rule_repo.list_for_application(db),
    )
    return run


async def commit_import(db: Session, account_id: int, read_content: Callable[[], Awaitable[bytes]],
                        filename: str | None, create_missing_categories: bool, category_mapping: str | None) -> dict:
    """Importe le fichier dans le compte ; `read_content` n'est lu qu'après validation du compte et du mapping."""
    logger.info(f"Starting CSV import: file={filename}, account_id={account_id}")
    account = account_repo.get(db, account_id)
    if not account:
        raise NotFoundError("Account not found")
    mapping = _parse_mapping(category_mapping)
    rows, delimiter, raw_headers = parse_csv(await read_content())

    run = _start_run(db, account, mapping, create_missing_categories)
    for row in rows:
        if is_blank(row):
            continue  # ligne vide ou « ;;;; » : ni importée ni comptée en erreur
        line = int(row.get("_line") or 0)
        try:
            _import_row(db, run, parse_row(row), row.get("Date"))
        except Exception as exc:  # ImportRowError (ligne invalide) ou refus métier
            run.record_error(line, str(exc))

    _log_import(db, run, filename, delimiter, raw_headers)
    db.commit()
    if run.imported > 0:
        logger.info(f"Recalculating running balances for account_id={account_id}")
        recalculate_running_balances(db, account_id)
        await auto_link_transfers(db)

    logger.info(
        f"Import finished: file={filename}, imported={run.imported}, "
        f"skipped={run.skipped}, errors={run.errors}, created_categories={run.created_categories}"
    )
    return {
        "imported": run.imported,
        "skipped": run.skipped,
        "errors": run.errors,
        "created_categories": run.created_categories,
        "error_samples": run.error_samples,
        "error_details": run.error_details,
    }
