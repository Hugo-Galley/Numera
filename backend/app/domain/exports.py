"""Export CSV compatible Numbers : rendu pur des lignes déjà assemblées."""
import csv
import io
from datetime import datetime

EXPORT_HEADERS = ["Compte", "Date", "Mois", "Type", "Commercant", "Categorie", "Montant", "Solde Compte"]


def csv_safe(value: str) -> str:
    """Neutralise l'injection de formules (Excel/Numbers) dans les champs texte exportés."""
    if value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def to_csv(rows: list[dict]) -> str:
    """Lignes triées par compte puis date ; montants à deux décimales."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(EXPORT_HEADERS)
    for item in sorted(rows, key=lambda x: (x["account_name"], x["date"])):
        date_str = item["date"].strftime("%d/%m/%Y %H:%M") if isinstance(item["date"], datetime) else ""
        writer.writerow([
            csv_safe(item["account_name"]),
            date_str,
            item["month_label"],
            item["type"],
            csv_safe(item["merchant"]),
            csv_safe(item["category"]),
            f"{item['amount']:.2f}",
            f"{item['balance']:.2f}",
        ])
    return output.getvalue()
