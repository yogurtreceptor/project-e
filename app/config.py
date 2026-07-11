from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
DATABASE_PATH = INSTANCE_DIR / "eddy.sqlite3"
DOCUMENT_STORAGE_DIR = INSTANCE_DIR / "documents"
BACKUP_DIR = INSTANCE_DIR / "backups"
IMPORT_STAGING_DIR = INSTANCE_DIR / "imports"


def initialise_local_storage() -> None:
    """Create private runtime directories required by a fresh checkout."""
    DOCUMENT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    IMPORT_STAGING_DIR.mkdir(parents=True, exist_ok=True)
