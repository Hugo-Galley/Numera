"""Pont entre routes synchrones et services asynchrones.

Une route `async def` exécute sur la boucle d'événements de l'unique worker uvicorn : ses requêtes SQLAlchemy
synchrones et son calcul Python bloquent alors toutes les autres requêtes (`/health` compris). Les routes sont donc
des `def` (threadpool de FastAPI) ; celles dont le service attend du réseau (cours, taux de change) exécutent sa
coroutine dans la boucle propre au thread avec `run_async`."""
import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")


def run_async(coroutine: Coroutine[Any, Any, T]) -> T:
    """Exécute `coroutine` jusqu'au bout dans une boucle neuve ; à appeler depuis un thread sans boucle (route `def`)."""
    return asyncio.run(coroutine)
