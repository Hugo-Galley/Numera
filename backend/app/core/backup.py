"""Instantané cohérent de la base SQLite (API de backup, valable aussi en mode WAL)."""
import sqlite3
from datetime import datetime
from pathlib import Path


def snapshot_database(db_path: str, dest_dir: Path | str, prefix: str = "snapshot") -> Path:
    """Copie `db_path` dans `dest_dir/<prefix>_<horodatage>.db` et vérifie son intégrité."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    source = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
    try:
        target = sqlite3.connect(dest)
        try:
            source.backup(target)
            result = target.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            target.close()
    finally:
        source.close()
    if result != "ok":
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"Instantané invalide : {result}")
    return dest
