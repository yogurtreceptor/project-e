"""Shared isolated HTTP-server configuration for route tests."""

from pathlib import Path
import re

from app.http_server import DEFAULT_HTTP_CONFIG, HttpServerConfig, create_http_server
from app.web import EddyRequestHandler


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "app" / "static"
STYLESHEET_IMPORT_PATTERN = re.compile(
    r'@import url\("/static/([a-z0-9-]+\.css)"\);'
)


def application_stylesheet_paths() -> tuple[Path, ...]:
    """Resolve the ordered top-level modules declared by the CSS manifest."""
    manifest = (STATIC_DIR / "styles.css").read_text()
    return tuple(
        STATIC_DIR / file_name
        for file_name in STYLESHEET_IMPORT_PATTERN.findall(manifest)
    )


def read_application_css(*, include_foundation: bool = True) -> str:
    """Read the ordered application cascade without duplicating its module list."""
    paths = application_stylesheet_paths()
    if not include_foundation:
        paths = tuple(path for path in paths if path.name != "foundation.css")
    return "\n".join(path.read_text() for path in paths)


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
