"""Calculs purs des répartitions d'investissement et du patrimoine."""
from typing import Any

UNCLASSIFIED = "Non classé"


class AllocationGroups:
    """Valeur EUR cumulée par classe d'actifs, secteur et zone, avec le détail par compte."""

    def __init__(self) -> None:
        self.total = 0.0
        self.by_asset_class: dict = {}
        self.by_sector: dict = {}
        self.by_zone: dict = {}

    @staticmethod
    def _add_to(groups: dict, name: str, value: float, account: Any) -> None:
        group = groups.setdefault(name, {"value": 0.0, "items": {}})
        group["value"] += value
        item = group["items"].setdefault(account.id, {"account_id": account.id, "account_name": account.name, "value": 0.0})
        item["value"] += value

    def add(self, asset_class: str | None, sector: str | None, zone: str | None, value: float, account: Any) -> None:
        self._add_to(self.by_asset_class, asset_class or UNCLASSIFIED, value, account)
        self._add_to(self.by_sector, sector or UNCLASSIFIED, value, account)
        self._add_to(self.by_zone, zone or UNCLASSIFIED, value, account)

    def _format(self, groups: dict) -> list[dict]:
        result = []
        for name, data in groups.items():
            val = data["value"]
            items = sorted(
                (
                    {
                        "account_id": item["account_id"],
                        "account_name": item["account_name"],
                        "value": round(item["value"], 2),
                        "percentage_of_group": round((item["value"] / val * 100.0) if val > 0 else 0.0, 2),
                    }
                    for item in data["items"].values()
                ),
                key=lambda x: x["value"], reverse=True,
            )
            result.append({
                "name": name,
                "value": round(val, 2),
                "percentage": round((val / self.total * 100.0) if self.total > 0 else 0.0, 2),
                "items": items,
            })
        return sorted(result, key=lambda x: x["value"], reverse=True)

    def result(self) -> dict:
        return {
            "total_value_eur": round(self.total, 2),
            "by_asset_class": self._format(self.by_asset_class),
            "by_sector": self._format(self.by_sector),
            "by_geographic_zone": self._format(self.by_zone),
        }


def _patrimoine_item(account: Any, name: str, type_: str, balance: float, balance_eur: float) -> dict:
    return {
        "account_id": account.id,
        "account_name": name,
        "type": type_,
        "currency": account.currency,
        "balance": round(balance, 2),
        "balance_eur": round(balance_eur, 2),
        "institution": account.institution,
        "logo": account.logo,
    }


def patrimoine_items(accounts: list[Any], values: dict[int, Any]) -> dict:
    """Répartition du patrimoine : une assurance-vie se partage entre fonds euros et unités de compte."""
    total_patrimoine_eur = 0.0
    total_debts_eur = 0.0
    items = []
    for acc in accounts:
        val, val_eur = values[acc.id].value, values[acc.id].value_eur
        if acc.type == "credit":
            # Dette : hors camembert (valeur négative), déduite dans le patrimoine net
            total_debts_eur -= val_eur
            continue
        total_patrimoine_eur += val_eur
        if acc.type == "assurance_vie":
            euros_pct = acc.fonds_euros_pct if acc.fonds_euros_pct is not None else 100.0
            investis_pct = acc.fonds_investis_pct if acc.fonds_investis_pct is not None else 0.0
            items.append(_patrimoine_item(acc, f"{acc.name} - Fonds Euro", "epargne",
                                          val * (euros_pct / 100.0), val_eur * (euros_pct / 100.0)))
            items.append(_patrimoine_item(acc, f"{acc.name} - Investi", "investissement",
                                          val * (investis_pct / 100.0), val_eur * (investis_pct / 100.0)))
        else:
            items.append(_patrimoine_item(acc, acc.name, acc.type, val, val_eur))
    for item in items:
        item["percentage"] = round((item["balance_eur"] / total_patrimoine_eur * 100.0), 2) if total_patrimoine_eur > 0 else 0.0
    items.sort(key=lambda i: i["balance_eur"], reverse=True)
    return {
        "total_patrimoine": round(total_patrimoine_eur, 2),
        "total_debts_eur": round(total_debts_eur, 2),
        "net_patrimoine_eur": round(total_patrimoine_eur - total_debts_eur, 2),
        "items": items
    }
