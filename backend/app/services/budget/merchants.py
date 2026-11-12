from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.core.i18n import tr
from app.models.merchant import Merchant, MerchantAlias
from app.repositories.budget import merchants as repo
from app.schemas.merchant import MerchantAliasCreate, MerchantCreate, MerchantUpdate


def _require(db: Session, merchant_id: int) -> Merchant:
    merchant = repo.get(db, merchant_id)
    if not merchant:
        raise NotFoundError(tr("errors.merchant_not_found"))
    return merchant


def get_merchants(db: Session, skip: int, limit: int, search: str | None) -> list[Merchant]:
    return repo.list_page(db, skip, limit, search)


def create_merchant(db: Session, merchant_in: MerchantCreate) -> Merchant:
    if repo.name_taken(db, merchant_in.name):
        raise ConflictError(tr("errors.merchant_name_exists"))
    taken = repo.taken_aliases(db, merchant_in.aliases or [])
    if taken:
        raise ConflictError(tr("errors.alias_taken", aliases=", ".join(taken)))

    merchant = Merchant(
        name=merchant_in.name,
        category_id=merchant_in.category_id,
        icon=merchant_in.icon,
        color=merchant_in.color
    )
    repo.add(db, merchant)
    for label in merchant_in.aliases or []:
        db.add(MerchantAlias(merchant_id=merchant.id, label=label))

    # Un marchand créé s'applique tout de suite aux libellés déjà importés
    repo.link_unnormalized_transactions(db, merchant.id, merchant_in.aliases or [])
    db.commit()
    db.refresh(merchant)
    return merchant


def get_or_create_by_name(db: Session, name: str) -> Merchant:
    """Marchand canonique de ce nom, créé au besoin (sans commit : l'appelant valide)."""
    merchant = repo.get_by_name(db, name)
    if not merchant:
        merchant = Merchant(name=name)
        repo.add(db, merchant)
    return merchant


def get_merchant(db: Session, merchant_id: int) -> Merchant:
    return _require(db, merchant_id)


def update_merchant(db: Session, merchant_id: int, merchant_in: MerchantUpdate) -> Merchant:
    merchant = _require(db, merchant_id)
    update_data = merchant_in.model_dump(exclude_unset=True)
    if update_data.get("name", "") is None:  # colonne NOT NULL : un `null` explicite est ignoré
        del update_data["name"]
    new_name = update_data.get("name")
    if new_name and new_name != merchant.name and repo.name_taken(db, new_name):
        raise ConflictError(tr("errors.merchant_name_exists"))
    for field, value in update_data.items():
        setattr(merchant, field, value)
    db.commit()
    db.refresh(merchant)
    return merchant


def delete_merchant(db: Session, merchant_id: int) -> None:
    repo.delete(db, _require(db, merchant_id))
    db.commit()


def add_alias(db: Session, merchant_id: int, alias_in: MerchantAliasCreate) -> MerchantAlias:
    _require(db, merchant_id)
    if repo.taken_aliases(db, [alias_in.label]):
        raise ConflictError(tr("errors.alias_exists"))
    alias = MerchantAlias(merchant_id=merchant_id, label=alias_in.label)
    db.add(alias)
    repo.link_unnormalized_transactions(db, merchant_id, [alias_in.label])
    db.commit()
    db.refresh(alias)
    return alias


def remove_alias(db: Session, alias_id: int) -> None:
    alias = repo.get_alias(db, alias_id)
    if not alias:
        raise NotFoundError(tr("errors.alias_not_found"))
    repo.delete(db, alias)
    db.commit()


def auto_normalize_transactions(db: Session) -> dict[str, Any]:
    """Rattache aux marchands les transactions dont le libellé correspond à un alias."""
    count = sum(
        repo.link_unnormalized_transactions(db, alias.merchant_id, [alias.label])
        for alias in repo.all_aliases(db)
    )
    db.commit()
    return {"normalized_count": count}


def get_unnormalized_merchant_labels(db: Session, min_count: int) -> list[dict[str, Any]]:
    """Libellés bancaires fréquents encore rattachés à aucun marchand."""
    return [{"label": r.merchant, "count": r.count} for r in repo.unnormalized_labels(db, min_count)]
