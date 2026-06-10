from sqlalchemy.orm import Session

from app.models.category import Category

DEFAULT_CATEGORIES = [
    # (name, type, group)
    ("Abonnement", "depense", "Fixe"),
    ("Achat divers", "depense", "Vie courante"),
    ("Nourriture", "depense", "Vie courante"),
    ("Sortie", "depense", "Loisirs"),
    ("Cadeaux (emis)", "depense", "Autres"),
    ("Don", "depense", "Autres"),
    ("Sport", "depense", "Loisirs"),
    ("Categorie", "depense", None),
    ("Remboursement (recu)", "revenu", None),
    ("Salaire", "revenu", None),
    ("Revenus supplementaires", "revenu", None),
    ("Dividendes", "revenu", None),
]


def seed_default_categories(db: Session) -> int:
    # 1. Fill groups for existing categories if they are missing
    updated = 0
    for name, _, group in DEFAULT_CATEGORIES:
        if group:
            existing = db.query(Category).filter(Category.name == name, (Category.group == None) | (Category.group == "")).first()
            if existing:
                existing.group = group
                updated += 1
    
    if updated:
        db.commit()

    # 2. Only seed new ones on a fresh install (empty table). 
    if db.query(Category).first() is not None and updated == 0:
        return 0
    
    if db.query(Category).first() is not None:
        return updated

    created = 0
    for name, category_type, group in DEFAULT_CATEGORIES:
        db.add(Category(name=name, type=category_type, group=group))
        created += 1
    if created:
        db.commit()
    return created + updated
