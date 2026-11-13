"""Types partagés des repositories."""
from typing import Any, TypeVar

from sqlalchemy import Row
from sqlalchemy.orm import Query

# Lignes d'un `SELECT` de colonnes : la forme du tuple dépend de la requête, le repository
# la documente par son nom et le service qui consomme les lignes les déstructure.
Rows = list[Row[*tuple[Any, ...]]]

# Un helper qui ajoute des filtres à une requête rend la même requête, avec le même type de lignes.
QueryT = TypeVar("QueryT", bound="Query[Any]")
