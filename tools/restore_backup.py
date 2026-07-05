"""Restore a Project E recovery bundle after explicit confirmation."""
import argparse
from pathlib import Path

from app.config import BACKUP_DIR, DATABASE_URL, DOCUMENT_STORAGE_DIR
from app.portability import inspect_bundle, restore_recovery_bundle


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and restore a Project E portable recovery bundle."
    )
    parser.add_argument("bundle", type=Path)
    parser.add_argument(
        "--confirm-replace",
        action="store_true",
        help="replace the current database and document store after making a safety backup",
    )
    parser.add_argument("--database", default=DATABASE_URL)
    parser.add_argument("--documents", type=Path, default=DOCUMENT_STORAGE_DIR)
    parser.add_argument("--backups", type=Path, default=BACKUP_DIR)
    args = parser.parse_args()

    preview = inspect_bundle(args.bundle.read_bytes())
    print(
        f"Valid bundle: {preview.entities} entities, "
        f"{preview.relationships} relationships, {preview.documents} documents."
    )
    if not args.confirm_replace:
        print("Preview only. Re-run with --confirm-replace to restore it.")
        return 0
    restore_recovery_bundle(
        args.bundle, args.database, args.documents, args.backups
    )
    print("Recovery bundle restored. A safety backup of the replaced state was created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
