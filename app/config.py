import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
DATABASE_URL = os.environ.get(
    "PROJECT_E_DATABASE_URL",
    f"postgresql://project_e@/project_e?host={INSTANCE_DIR / 'postgres' / 'socket'}",
)
POSTGRES_DATA_DIR = Path(os.environ.get("PROJECT_E_POSTGRES_DATA", INSTANCE_DIR / "postgres" / "data"))
POSTGRES_SOCKET_DIR = Path(os.environ.get("PROJECT_E_POSTGRES_SOCKET", INSTANCE_DIR / "postgres" / "socket"))
DOCUMENT_STORAGE_DIR = INSTANCE_DIR / "documents"
BACKUP_DIR = INSTANCE_DIR / "backups"
IMPORT_STAGING_DIR = INSTANCE_DIR / "imports"


def initialise_local_storage() -> None:
    """Create private runtime directories required by a fresh checkout."""
    DOCUMENT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    IMPORT_STAGING_DIR.mkdir(parents=True, exist_ok=True)
    POSTGRES_DATA_DIR.parent.mkdir(parents=True, exist_ok=True)
    POSTGRES_SOCKET_DIR.mkdir(parents=True, exist_ok=True)
