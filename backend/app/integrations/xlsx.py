"""Lecture d'une feuille xlsx avec la bibliothèque standard (un zip de fichiers XML), pour les fichiers des émetteurs.

Le contenu vient d'un site tiers : taille bornée, aucune déclaration DTD (donc aucune entité) acceptée.
"""
import io
import re
import zipfile
import zlib
from xml.etree import ElementTree  # DTD refusées avant lecture, cf. _parse

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_MAX_PART_BYTES = 50_000_000
_MAX_ROWS = 100_000
_MAX_COLUMNS = 200
_CELL_REF = re.compile(r"^([A-Z]+)[0-9]+$")


def read_rows(data: bytes, sheet: int = 1) -> list[list[str]]:
    """Valeurs texte de la feuille `sheet` : l'index d'une ligne est son numéro dans le tableur moins un.

    Les lignes et cellules vides sont conservées à leur place. `ValueError` si le fichier est inexploitable."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            shared = _shared_strings(archive)
            root = _parse(archive, f"xl/worksheets/sheet{sheet}.xml")
        rows: list[list[str]] = []
        for row in root.iter(f"{_NS}row"):
            number = int(row.get("r") or len(rows) + 1)
            if not len(rows) < number <= _MAX_ROWS:
                raise ValueError(f"xlsx : ligne {number} hors limites")
            rows.extend([] for _ in range(number - len(rows) - 1))
            rows.append(_cells(row, shared))
    except (zipfile.BadZipFile, zlib.error, ElementTree.ParseError, KeyError, IndexError) as exc:
        raise ValueError(f"xlsx illisible : {exc!r}") from exc
    return rows


def _parse(archive: zipfile.ZipFile, name: str) -> ElementTree.Element:
    if archive.getinfo(name).file_size > _MAX_PART_BYTES:
        raise ValueError(f"xlsx : {name} trop volumineux")
    content = archive.read(name)
    if b"<!DOCTYPE" in content or b"\x00" in content:  # octet nul : UTF-16, qui masquerait la déclaration
        raise ValueError(f"xlsx : {name} refusé (DTD ou encodage inattendu)")
    return ElementTree.fromstring(content)  # noqa: S314 : sans DTD, aucune entité à développer


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    return [_text(item) for item in _parse(archive, "xl/sharedStrings.xml")]


def _text(element: ElementTree.Element) -> str:
    return "".join(node.text or "" for node in element.iter(f"{_NS}t"))


def _column(reference: str) -> int:
    match = _CELL_REF.match(reference)
    if not match:
        raise ValueError(f"xlsx : référence de cellule invalide {reference!r}")
    index = 0
    for letter in match.group(1):
        index = index * 26 + ord(letter) - ord("A") + 1
    if index > _MAX_COLUMNS:
        raise ValueError(f"xlsx : colonne {reference!r} hors limites")
    return index - 1


def _cells(row: ElementTree.Element, shared: list[str]) -> list[str]:
    values: list[str] = []
    for cell in row.iter(f"{_NS}c"):
        reference = cell.get("r")
        index = _column(reference) if reference else len(values)
        values.extend("" for _ in range(index + 1 - len(values)))
        raw = cell.findtext(f"{_NS}v") or ""
        kind = cell.get("t")
        values[index] = _text(cell) if kind == "inlineStr" else shared[int(raw)] if kind == "s" else raw
    return values
