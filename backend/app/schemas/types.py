"""Types de champs partagés : bornes sur les montants et les dates (audit R1)."""
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, Field

from app.core.time import to_naive_utc

MAX_AMOUNT = 1e12
MIN_DATE = datetime(1900, 1, 1)
MAX_DATE = datetime(2200, 1, 1)

# Montant strictement positif, fini et borné (Infinity/NaN/1e308 refusés).
Amount = Annotated[float, Field(gt=0, lt=MAX_AMOUNT, allow_inf_nan=False)]
# Montant pouvant valoir 0 (ex. Solde Initial à 0).
AmountOrZero = Annotated[float, Field(ge=0, lt=MAX_AMOUNT, allow_inf_nan=False)]
# Quantité de titres / prix unitaire.
Quantity = Annotated[float, Field(ge=0, lt=MAX_AMOUNT, allow_inf_nan=False)]


def _check_date_range(value: datetime) -> datetime:
    naive = to_naive_utc(value) if value.tzinfo else value
    if not (MIN_DATE <= naive < MAX_DATE):
        raise ValueError("date hors de la plage 1900-2200")
    return value


# Date saisie : bornée, et un fuseau éventuel est converti en UTC naïf (jamais tronqué : 23:30−05:00 change de mois)
BoundedDatetime = Annotated[datetime, AfterValidator(_check_date_range), AfterValidator(to_naive_utc)]

BoundedNaiveUTCDatetime = BoundedDatetime
