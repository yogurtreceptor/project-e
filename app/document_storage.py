import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.config import DOCUMENT_STORAGE_DIR


@dataclass(frozen=True)
class UploadedFile:
    file_name: str
    content_type: str
    data: bytes


def safe_file_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(value).name).strip(".-")
    return cleaned or "document"


def format_file_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def store_document_upload(
    upload: UploadedFile,
    storage_dir: Path = DOCUMENT_STORAGE_DIR,
) -> dict[str, str]:
    storage_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}-{safe_file_name(upload.file_name)}"
    stored_path = storage_dir / stored_name
    stored_path.write_bytes(upload.data)
    return {
        "file_name": upload.file_name,
        "file_path": f"documents/{stored_name}",
        "mime_type": upload.content_type,
        "file_size": format_file_size(len(upload.data)),
    }


def stored_document_path(
    value: str,
    storage_dir: Path = DOCUMENT_STORAGE_DIR,
) -> Path | None:
    if not value:
        return None
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    path = (storage_dir.parent / relative).resolve()
    storage_root = storage_dir.resolve()
    if storage_root not in (path, *path.parents):
        return None
    return path


def delete_stored_document(
    value: str,
    storage_dir: Path = DOCUMENT_STORAGE_DIR,
) -> bool:
    path = stored_document_path(value, storage_dir)
    if path is None or not path.is_file():
        return False
    path.unlink()
    return True
