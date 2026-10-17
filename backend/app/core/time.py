from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def to_naive_utc(value: datetime) -> datetime:
    """Datetime reçu avec fuseau (ex. ISO « Z » du navigateur) → UTC naïf, convention de la base."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


# Champ de schéma : accepte les dates avec ou sans fuseau, les ramène en UTC naïf.
NaiveUTCDatetime = Annotated[datetime, AfterValidator(to_naive_utc)]
