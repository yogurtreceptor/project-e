"""Bounded disposable SQLite cache for provider-independent journey results."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.journey_contract import CacheStatus, JourneyResult


@dataclass(frozen=True)
class JourneyCacheLookup:
    status: CacheStatus
    result: JourneyResult | None = None


class JourneyCache:
    """A clearable performance aid kept outside the canonical database."""

    def __init__(self, path: Path | str, *, maximum_entries: int) -> None:
        if isinstance(maximum_entries, bool) or maximum_entries <= 0:
            raise ValueError("Journey cache maximum entries must be positive.")
        self.path = Path(path)
        self.maximum_entries = maximum_entries

    def lookup(
        self, fingerprint: str, *, now: datetime | None = None
    ) -> JourneyCacheLookup:
        current = _normalise_now(now)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_json, fresh_until FROM journey_results WHERE fingerprint=?",
                (fingerprint,),
            ).fetchone()
            if row is None:
                return JourneyCacheLookup(CacheStatus.MISS)
            try:
                payload = json.loads(row["result_json"])
                if not isinstance(payload, dict):
                    raise ValueError
                result = JourneyResult.from_dict(payload)
                if result.fingerprint != fingerprint:
                    raise ValueError
                fresh_until = _parse_timestamp(row["fresh_until"])
            except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                connection.execute(
                    "DELETE FROM journey_results WHERE fingerprint=?", (fingerprint,)
                )
                return JourneyCacheLookup(CacheStatus.MISS)
            connection.execute(
                "UPDATE journey_results SET last_accessed_at=? WHERE fingerprint=?",
                (current.isoformat(), fingerprint),
            )
            status = (
                CacheStatus.FRESH if current <= fresh_until else CacheStatus.STALE
            )
            return JourneyCacheLookup(status, result)

    def store(
        self, result: JourneyResult, *, now: datetime | None = None
    ) -> None:
        current = _normalise_now(now)
        fresh_until = _parse_timestamp(result.provenance.fresh_until)
        calculated_at = _parse_timestamp(result.provenance.calculated_at)
        if fresh_until < calculated_at:
            raise ValueError("Journey result freshness cannot end before calculation.")
        payload = json.dumps(
            result.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO journey_results (
                       fingerprint, result_json, calculated_at, fresh_until,
                       created_at, last_accessed_at
                   ) VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(fingerprint) DO UPDATE SET
                       result_json=excluded.result_json,
                       calculated_at=excluded.calculated_at,
                       fresh_until=excluded.fresh_until,
                       created_at=excluded.created_at,
                       last_accessed_at=excluded.last_accessed_at""",
                (
                    result.fingerprint,
                    payload,
                    calculated_at.isoformat(),
                    fresh_until.isoformat(),
                    current.isoformat(),
                    current.isoformat(),
                ),
            )
            connection.execute(
                """DELETE FROM journey_results
                   WHERE fingerprint IN (
                       SELECT fingerprint FROM journey_results
                       ORDER BY last_accessed_at DESC, created_at DESC, fingerprint DESC
                       LIMIT -1 OFFSET ?
                   )""",
                (self.maximum_entries,),
            )

    def clear(self) -> int:
        if not self.path.exists():
            return 0
        with self._connect() as connection:
            count = int(
                connection.execute("SELECT COUNT(*) FROM journey_results").fetchone()[0]
            )
            connection.execute("DELETE FROM journey_results")
            return count

    def delete(self, fingerprint: str) -> bool:
        if not self.path.exists():
            return False
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM journey_results WHERE fingerprint=?", (fingerprint,)
            )
            return cursor.rowcount > 0

    def count(self) -> int:
        if not self.path.exists():
            return 0
        with self._connect() as connection:
            return int(
                connection.execute("SELECT COUNT(*) FROM journey_results").fetchone()[0]
            )

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            return self._open_connection()
        except sqlite3.DatabaseError as error:
            if not _is_disposable_corruption(error):
                raise
            self.path.unlink(missing_ok=True)
            return self._open_connection()

    def _open_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute(
                """CREATE TABLE IF NOT EXISTS journey_results (
                       fingerprint TEXT PRIMARY KEY,
                       result_json TEXT NOT NULL,
                       calculated_at TEXT NOT NULL,
                       fresh_until TEXT NOT NULL,
                       created_at TEXT NOT NULL,
                       last_accessed_at TEXT NOT NULL
                   )"""
            )
            return connection
        except Exception:
            connection.close()
            raise


def _normalise_now(value: datetime | None) -> datetime:
    value = value or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Journey cache timestamps must include a timezone.")
    return value.astimezone(UTC)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Journey result timestamps must include a timezone.")
    return parsed.astimezone(UTC)


def _is_disposable_corruption(error: sqlite3.DatabaseError) -> bool:
    message = str(error).lower()
    return "not a database" in message or "malformed" in message
