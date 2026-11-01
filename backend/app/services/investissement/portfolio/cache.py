"""Cache bref de la valorisation d'un compte titres.

Plusieurs routes (budget, patrimoine, FIRE, Centre d'Actions, fiscalité) recalculent la même valorisation
(~170 ms par compte). Une entrée vit `TTL_SECONDS` au plus et est vidée dès qu'une session écrit en base
(flush ou commit, quelle que soit la requête ou la tâche de fond) : une lecture ne voit jamais un état antérieur
à une écriture visible. Un calcul démarré avant une écriture n'est pas mémorisé (génération).
"""
import copy
import time

from sqlalchemy import event
from sqlalchemy.orm import Session

TTL_SECONDS = 20.0

_entries: dict[tuple, tuple[float, dict]] = {}
_generation = 0


def invalidate(*_args) -> None:
    global _generation
    _generation += 1
    _entries.clear()


def generation() -> int:
    return _generation


def key(db: Session, account_id: int, fetch: bool, history: bool) -> tuple:
    return (id(db.get_bind()), account_id, fetch, history)


def get(entry_key: tuple) -> dict | None:
    entry = _entries.get(entry_key)
    if entry is None or time.monotonic() - entry[0] > TTL_SECONDS:
        return None
    return copy.deepcopy(entry[1])


def put(entry_key: tuple, value: dict, started_at: int) -> None:
    if started_at == _generation:
        _entries[entry_key] = (time.monotonic(), copy.deepcopy(value))


event.listen(Session, "after_flush", invalidate)
event.listen(Session, "after_commit", invalidate)
