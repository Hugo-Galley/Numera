"""Réponses de `/import/{logs,preview,commit}`."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImportLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_file: str
    imported_count: int
    skipped_count: int
    error_count: int
    summary_json: str | None
    created_at: datetime


class ImportPreviewRow(BaseModel):
    """Ligne du CSV telle qu'elle a été lue : les colonnes gardent le nom (capitalisé) de leur en-tête."""

    line: int
    Date: str | None
    Type: str | None
    Commercant: str | None
    Categorie: str | None
    Montant: str | None
    error: str | None


class ImportPreview(BaseModel):
    filename: str | None
    total_rows: int
    invalid_rows: int
    warnings: list[str]
    delimiter: str
    raw_headers: list[str]
    preview: list[ImportPreviewRow]
    unknown_categories: list[str]


class ImportErrorDetail(BaseModel):
    line: int
    reason: str


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: int
    created_categories: int
    error_samples: list[str]
    error_details: list[ImportErrorDetail]
