from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from pydantic import AfterValidator


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def utcnow_aware() -> datetime:
    return datetime.now(UTC)


def end_of_today() -> datetime:
    """Borne haute exclusive des lectures « à ce jour » : demain à minuit.

    Une transaction datée d'aujourd'hui (à n'importe quelle heure) compte ; une transaction
    future (saisie à venir) ne compte qu'à sa date.
    """
    return datetime.combine(date.today() + timedelta(days=1), time.min)


def to_naive_utc(value: datetime) -> datetime:
    """Datetime reçu avec fuseau (ex. ISO « Z » du navigateur) → UTC naïf, convention de la base."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


# Champ de schéma : accepte les dates avec ou sans fuseau, les ramène en UTC naïf.
NaiveUTCDatetime = Annotated[datetime, AfterValidator(to_naive_utc)]
