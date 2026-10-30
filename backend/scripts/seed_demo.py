"""(Re)génère le jeu de démonstration dans la base de démo (`make backend-seed-demo`).

Exige DEMO_MODE=true : la configuration refuse alors toute base dont le nom ne contient pas « demo »,
la vraie base ne peut donc pas être effacée par erreur.
"""
import asyncio
import sys

from app.core.config import settings
from app.core.migrations import run_migrations
from app.db.session import SessionLocal
from app.services.systeme.demo import generate_demo_data, wipe_database


async def main() -> None:
    if not settings.DEMO_MODE:
        sys.exit("DEMO_MODE=true requis (et une DATABASE_URL dédiée, ex. sqlite:///./data/demo.db)")
    run_migrations()
    db = SessionLocal()
    try:
        wipe_database(db)
        await generate_demo_data(db)
    finally:
        db.close()
    print(f"Données de démonstration générées dans {settings.database_url}")


if __name__ == "__main__":
    asyncio.run(main())
