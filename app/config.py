from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
DATABASE_PATH = INSTANCE_DIR / "eddy.sqlite3"
DOCUMENT_STORAGE_DIR = INSTANCE_DIR / "documents"


def initialise_local_storage() -> None:
    """Create private runtime directories required by a fresh checkout."""
    DOCUMENT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
