import sqlite3
from pathlib import Path

from app.config import DOCUMENT_STORAGE_DIR
from app.document_storage import delete_stored_document


def delete_unreferenced_document_file(
    connection: sqlite3.Connection,
    file_path: str,
    storage_dir: Path = DOCUMENT_STORAGE_DIR,
) -> bool:
    if not file_path:
        return False
    reference = connection.execute(
        "SELECT 1 FROM documents WHERE file_path = ? LIMIT 1",
        (file_path,),
    ).fetchone()
    if reference is not None:
        return False
    return delete_stored_document(file_path, storage_dir)
