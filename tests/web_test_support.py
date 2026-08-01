"""Shared isolated HTTP-server configuration for route tests."""

from pathlib import Path

from app.http_server import DEFAULT_HTTP_CONFIG, HttpServerConfig, create_http_server
from app.web import EddyRequestHandler


def make_test_server(
    database_path: Path | None = None,
    *,
    document_storage_dir: Path | None = None,
    backup_dir: Path | None = None,
    import_staging_dir: Path | None = None,
):
    if database_path is None:
        config = DEFAULT_HTTP_CONFIG
    else:
        root = Path(database_path).parent
        config = HttpServerConfig(
            database_path=Path(database_path),
            document_storage_dir=document_storage_dir or root / "documents",
            backup_dir=backup_dir or root / "backups",
            import_staging_dir=import_staging_dir or root / "import-staging",
        )
    return create_http_server(("127.0.0.1", 0), EddyRequestHandler, config)
