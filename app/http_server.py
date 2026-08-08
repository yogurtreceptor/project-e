"""Per-server path configuration for Project E's local HTTP runtime."""

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TypeVar

from app.config import (
    BACKUP_DIR,
    DATABASE_PATH,
    DOCUMENT_STORAGE_DIR,
    IMPORT_STAGING_DIR,
    JOURNEY_CACHE_PATH,
    ROUTING_DIR,
    SPATIAL_PACK_DIR,
)


@dataclass(frozen=True)
class HttpServerConfig:
    database_path: Path
    document_storage_dir: Path
    backup_dir: Path
    import_staging_dir: Path
    spatial_pack_dir: Path
    routing_dir: Path | None = None
    journey_cache_path: Path | None = None


DEFAULT_HTTP_CONFIG = HttpServerConfig(
    database_path=DATABASE_PATH,
    document_storage_dir=DOCUMENT_STORAGE_DIR,
    backup_dir=BACKUP_DIR,
    import_staging_dir=IMPORT_STAGING_DIR,
    spatial_pack_dir=SPATIAL_PACK_DIR,
    routing_dir=ROUTING_DIR,
    journey_cache_path=JOURNEY_CACHE_PATH,
)


HandlerType = TypeVar("HandlerType", bound=BaseHTTPRequestHandler)


def configured_handler(
    handler_type: type[HandlerType], config: HttpServerConfig
) -> type[HandlerType]:
    """Bind immutable paths to one server without mutating a shared handler class."""

    class ConfiguredHandler(handler_type):
        database_path = config.database_path
        document_storage_dir = config.document_storage_dir
        backup_dir = config.backup_dir
        import_staging_dir = config.import_staging_dir
        spatial_pack_dir = config.spatial_pack_dir
        routing_dir = config.routing_dir or config.database_path.parent / "routing"
        journey_cache_path = (
            config.journey_cache_path
            or config.database_path.parent / "journey-cache.sqlite3"
        )

    ConfiguredHandler.__name__ = f"Configured{handler_type.__name__}"
    ConfiguredHandler.__qualname__ = ConfiguredHandler.__name__
    return ConfiguredHandler


def create_http_server(
    address: tuple[str, int],
    handler_type: type[HandlerType],
    config: HttpServerConfig = DEFAULT_HTTP_CONFIG,
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(address, configured_handler(handler_type, config))
