"""Fast isolated database fixtures for tests that do not exercise migrations.

Migration tests must call ``initialise_database`` directly. Ordinary repository,
service and route tests can copy this process-local current-schema template and
retain a separate SQLite file for every test without replaying migration history.
"""

from pathlib import Path
import shutil
import tempfile
import threading

from app.db import initialise_database


_template_directory = tempfile.TemporaryDirectory(prefix="project-e-test-schema-")
_template_path = Path(_template_directory.name) / "current.sqlite3"
_template_lock = threading.Lock()


def initialise_test_database(database_path: Path) -> None:
    """Copy a freshly generated current-schema database to ``database_path``."""
    with _template_lock:
        if not _template_path.exists():
            initialise_database(_template_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_template_path, database_path)
