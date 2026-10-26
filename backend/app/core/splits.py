"""Découpage d'une dépense entre plusieurs catégories.

Une `Sortie` hors virement peut être répartie en parts (`transaction_splits`) dont la somme égale
son montant. Les parts ne servent qu'aux répartitions par catégorie (`category_lines`) : les totaux
de revenus/dépenses, les soldes et les dépenses réelles ne changent pas. Pour que ce soit vrai, une
part ne peut pas viser une catégorie d'épargne/investissement ni de revenu (qui changent de nature
la dépense) ; la transaction prend la catégorie de sa plus grosse part.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction
from app.models.transaction_split import TransactionSplit
from app.schemas.transaction import TransactionSplitItem

NON_SPLITTABLE_CATEGORY_NAMES = {"Investissement", "Epargne"}


def set_splits(db: Session, tx: Transaction, items: list[TransactionSplitItem]) -> None:
    """Remplace le découpage de `tx` (liste vide = annuler). Ne commite pas."""
    if not items:
        tx.splits = []
        return
    if tx.type != "Sortie" or tx.is_transfer:
        raise HTTPException(status_code=400, detail="Seule une dépense (hors virement interne) peut être découpée")
    if len(items) < 2:
        raise HTTPException(status_code=400, detail="Un découpage compte au moins deux parts")

    total_cents = sum(round(item.amount * 100) for item in items)
    if total_cents != round(tx.amount * 100):
        raise HTTPException(
            status_code=400,
            detail=f"La somme des parts ({total_cents / 100:.2f}) doit égaler le montant de la dépense ({tx.amount:.2f})",
        )

    category_ids = {item.category_id for item in items}
    categories = {c.id: c for c in db.query(Category).filter(Category.id.in_(category_ids)).all()}
    for category_id in category_ids:
        category = categories.get(category_id)
        if category is None:
            raise HTTPException(status_code=404, detail=f"Catégorie {category_id} introuvable")
        if category.name in NON_SPLITTABLE_CATEGORY_NAMES or category.type == "revenu":
            raise HTTPException(
                status_code=400,
                detail=f"La catégorie « {category.name} » ne peut pas recevoir une part de dépense",
            )

    tx.splits = [
        TransactionSplit(category_id=item.category_id, amount=round(item.amount, 2), note=item.note)
        for item in items
    ]
    tx.category_id = max(items, key=lambda item: item.amount).category_id


def check_split_compatible(tx: Transaction, new_type: str, new_amount: float, is_transfer: bool) -> None:
    """Refuse une modification qui rendrait le découpage faux (même logique que les remboursements)."""
    if not tx.splits:
        return
    if new_type != "Sortie" or is_transfer:
        raise HTTPException(status_code=400, detail="Annulez le découpage avant de changer le type de cette dépense")
    if round(new_amount * 100) != round(tx.amount * 100):
        raise HTTPException(status_code=400, detail="Annulez ou ajustez le découpage avant de changer le montant")
