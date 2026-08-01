"""Safe public iCalendar URL subscriptions and last-known-good projections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import ipaddress
import json
import re
import socket
import sqlite3
from pathlib import Path
import time
from typing import Callable
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.audit import record_audit_event
from app.calendar_service import CalendarRecord
from app.db_support import utc_now
from app.defaults import DEFAULT_EXTERNAL_CALENDAR_COLOUR, PLATFORM_TIMEZONE
from app.event_recurrence import RecurrenceDefinition, RecurrenceRule
from app.event_service import EventRecord
from app.icalendar_service import ICalendarDocument, ICalendarEvent, MAX_ICALENDAR_BYTES, parse_icalendar
from app.temporal import TemporalValueError, get_timezone


REFRESH_AFTER = timedelta(hours=24)
FETCH_TIMEOUT_SECONDS = 10
MAX_REDIRECTS = 3
_COLOUR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
_STAGING_TOKEN = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True)
class SubscriptionRecord:
    id: int
    source_url: str
    final_url: str
    name: str
    colour: str
    timezone: str
    enabled: bool
    sort_order: int
    etag: str
    last_modified: str
    content_type: str
    last_checked_at: str
    last_success_at: str
    current_error: str
    created_at: str
    updated_at: str

    @property
    def host(self) -> str:
        return urlparse(self.final_url or self.source_url).hostname or ""


@dataclass(frozen=True)
class SubscriptionSettingsInput:
    name: str
    colour: str
    timezone: str


@dataclass(frozen=True)
class SubscriptionFetch:
    source_url: str
    final_url: str
    content: bytes
    content_type: str
    etag: str
    last_modified: str
    document: ICalendarDocument | None
    not_modified: bool = False


@dataclass(frozen=True)
class SubscriptionProjection:
    calendars: tuple[CalendarRecord, ...]
    events: tuple[EventRecord, ...]
    recurrences: dict[int, RecurrenceDefinition]


def stage_subscription_fetch(fetched: SubscriptionFetch, staging_dir: Path) -> str:
    if fetched.document is None or fetched.not_modified:
        raise ValueError("A validated Calendar response is required.")
    import uuid
    token = uuid.uuid4().hex
    staging_dir.mkdir(parents=True, exist_ok=True)
    (staging_dir / f"subscription-{token}.ics").write_bytes(fetched.content)
    (staging_dir / f"subscription-{token}.json").write_text(
        json.dumps({
            "source_url": fetched.source_url,
            "final_url": fetched.final_url,
            "content_type": fetched.content_type,
            "etag": fetched.etag,
            "last_modified": fetched.last_modified,
        }, sort_keys=True),
        encoding="utf-8",
    )
    return token


def read_staged_subscription(
    token: str,
    staging_dir: Path,
    *,
    consume: bool = False,
) -> SubscriptionFetch:
    if not _STAGING_TOKEN.fullmatch(token):
        raise ValueError("Calendar subscription preview token is invalid.")
    content_path = staging_dir / f"subscription-{token}.ics"
    metadata_path = staging_dir / f"subscription-{token}.json"
    if (
        not content_path.is_file()
        or not metadata_path.is_file()
        or time.time() - min(content_path.stat().st_mtime, metadata_path.stat().st_mtime) > 30 * 60
    ):
        for path in (content_path, metadata_path):
            if path.is_file():
                path.unlink()
        raise ValueError("Calendar subscription preview has expired or does not exist.")
    content = content_path.read_bytes()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    document = parse_icalendar(content)
    fetched = SubscriptionFetch(
        metadata["source_url"],
        metadata["final_url"],
        content,
        metadata.get("content_type", ""),
        metadata.get("etag", ""),
        metadata.get("last_modified", ""),
        document,
    )
    if consume:
        content_path.unlink()
        metadata_path.unlink()
    return fetched


def validate_public_https_url(
    value: str,
    *,
    resolver: Callable[..., object] = socket.getaddrinfo,
) -> str:
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise ValueError("Calendar URL must be an absolute public HTTPS URL.")
    if parsed.username or parsed.password:
        raise ValueError("Calendar URL cannot contain embedded credentials.")
    if parsed.fragment:
        raise ValueError("Calendar URL cannot contain a fragment.")
    host = parsed.hostname
    if not host:
        raise ValueError("Calendar URL has no valid host.")
    try:
        addresses = resolver(host, parsed.port or 443, type=socket.SOCK_STREAM)
    except OSError as error:
        raise ValueError("Calendar URL host could not be resolved.") from error
    resolved = {
        item[4][0] for item in addresses  # type: ignore[index]
    }
    if not resolved:
        raise ValueError("Calendar URL host could not be resolved.")
    for raw_address in resolved:
        try:
            address = ipaddress.ip_address(raw_address.split("%", 1)[0])
        except ValueError as error:
            raise ValueError("Calendar URL resolved to an invalid address.") from error
        if not address.is_global:
            raise ValueError("Calendar URL must not resolve to a private or local address.")
    return url


def fetch_subscription(
    url: str,
    *,
    etag: str = "",
    last_modified: str = "",
    resolver: Callable[..., object] = socket.getaddrinfo,
    opener=None,
) -> SubscriptionFetch:
    source_url = validate_public_https_url(url, resolver=resolver)
    headers = {
        "Accept": "text/calendar, application/octet-stream;q=0.5",
        "User-Agent": "Project-E-Calendar/1",
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    active_opener = opener or build_opener(_PublicRedirectHandler(resolver))
    try:
        response = active_opener.open(
            Request(source_url, headers=headers),
            timeout=FETCH_TIMEOUT_SECONDS,
        )
    except HTTPError as error:
        if error.code == 304:
            return SubscriptionFetch(
                source_url, source_url, b"", error.headers.get("Content-Type", ""),
                etag, last_modified, None, True,
            )
        raise ValueError(f"Calendar URL returned HTTP {error.code}.") from error
    except OSError as error:
        raise ValueError("Calendar URL could not be fetched safely.") from error
    with response:
        final_url = validate_public_https_url(response.geturl(), resolver=resolver)
        content = response.read(MAX_ICALENDAR_BYTES + 1)
        if len(content) > MAX_ICALENDAR_BYTES:
            raise ValueError("Calendar URL response exceeds the 2 MB limit.")
        document = parse_icalendar(content)
        blockers = [
            *document.blockers,
            *(blocker for event in document.events for blocker in event.blockers),
        ]
        if blockers:
            raise ValueError("Calendar URL contains unsupported data: " + "; ".join(blockers))
        return SubscriptionFetch(
            source_url,
            final_url,
            content,
            response.headers.get("Content-Type", ""),
            response.headers.get("ETag", ""),
            response.headers.get("Last-Modified", ""),
            document,
        )


def list_subscriptions(
    connection: sqlite3.Connection,
    *,
    include_disabled: bool = True,
) -> list[SubscriptionRecord]:
    clause = "" if include_disabled else "WHERE enabled = 1"
    rows = connection.execute(
        f"""SELECT * FROM calendar_subscriptions {clause}
            ORDER BY enabled DESC, sort_order, lower(name), id"""
    ).fetchall()
    return [_subscription(row) for row in rows]


def get_subscription(
    connection: sqlite3.Connection,
    subscription_id: int,
) -> SubscriptionRecord | None:
    row = connection.execute(
        "SELECT * FROM calendar_subscriptions WHERE id = ?",
        (subscription_id,),
    ).fetchone()
    return _subscription(row) if row else None


def create_subscription(
    connection: sqlite3.Connection,
    fetched: SubscriptionFetch,
    *,
    colour: str = DEFAULT_EXTERNAL_CALENDAR_COLOUR,
    display_name: str = "",
) -> int:
    if fetched.document is None or fetched.not_modified:
        raise ValueError("A validated Calendar response is required.")
    name, timezone = _normalise_metadata(fetched.document, display_name, colour)
    now = utc_now()
    sort_order = int(connection.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM calendar_subscriptions"
    ).fetchone()[0])
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """INSERT INTO calendar_subscriptions (
                source_url, final_url, name, colour, timezone, enabled, sort_order,
                etag, last_modified, content_type, last_checked_at, last_success_at,
                current_error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, '', ?, ?)""",
            (
                fetched.source_url,
                fetched.final_url,
                name,
                colour,
                timezone,
                sort_order,
                fetched.etag,
                fetched.last_modified,
                fetched.content_type,
                now,
                now,
                now,
                now,
            ),
        )
        subscription_id = int(cursor.lastrowid)
        _replace_cache(connection, subscription_id, fetched.document.events)
        record_audit_event(
            connection,
            "import",
            [("calendar_subscription", subscription_id)],
            after={
                "name": name,
                "host": urlparse(fetched.final_url).hostname or "",
                "events": len(fetched.document.events),
            },
            notes="Read-only public iCalendar subscription added",
            provenance="imported",
        )
        connection.commit()
        return subscription_id
    except sqlite3.IntegrityError as error:
        connection.rollback()
        if "source_url" in str(error):
            raise ValueError("This Calendar URL is already subscribed.") from error
        raise
    except Exception:
        connection.rollback()
        raise


def refresh_subscription(
    connection: sqlite3.Connection,
    subscription_id: int,
    *,
    fetcher: Callable[..., SubscriptionFetch] = fetch_subscription,
) -> bool:
    subscription = get_subscription(connection, subscription_id)
    if subscription is None:
        raise ValueError("Calendar subscription does not exist.")
    checked_at = utc_now()
    try:
        fetched = fetcher(
            subscription.source_url,
            etag=subscription.etag,
            last_modified=subscription.last_modified,
        )
        if fetched.not_modified:
            connection.execute(
                """UPDATE calendar_subscriptions
                   SET last_checked_at = ?, current_error = '', updated_at = ?
                   WHERE id = ?""",
                (checked_at, checked_at, subscription_id),
            )
            connection.commit()
            return False
        if fetched.document is None:
            raise ValueError("Calendar refresh returned no parsed document.")
        connection.execute("BEGIN IMMEDIATE")
        _replace_cache(connection, subscription_id, fetched.document.events)
        connection.execute(
            """UPDATE calendar_subscriptions SET final_url = ?,
               etag = ?, last_modified = ?, content_type = ?, last_checked_at = ?,
               last_success_at = ?, current_error = '', updated_at = ? WHERE id = ?""",
            (
                fetched.final_url,
                fetched.etag,
                fetched.last_modified,
                fetched.content_type,
                checked_at,
                checked_at,
                checked_at,
                subscription_id,
            ),
        )
        connection.commit()
        return True
    except Exception as error:
        connection.rollback()
        connection.execute(
            """UPDATE calendar_subscriptions SET last_checked_at = ?,
               current_error = ?, updated_at = ? WHERE id = ?""",
            (checked_at, str(error)[:500], checked_at, subscription_id),
        )
        connection.commit()
        return False


def refresh_due_subscriptions(
    connection: sqlite3.Connection,
    *,
    now: datetime | None = None,
    fetcher: Callable[..., SubscriptionFetch] = fetch_subscription,
) -> int:
    instant = (now or datetime.now(UTC)).astimezone(UTC)
    refreshed = 0
    for subscription in list_subscriptions(connection, include_disabled=False):
        last_check = _parse_timestamp(subscription.last_checked_at)
        if last_check is not None and instant - last_check < REFRESH_AFTER:
            continue
        refresh_subscription(connection, subscription.id, fetcher=fetcher)
        refreshed += 1
    return refreshed


def update_subscription_settings(
    connection: sqlite3.Connection,
    subscription_id: int,
    values: SubscriptionSettingsInput,
) -> bool:
    """Update local presentation settings for a read-only URL Calendar."""
    current = get_subscription(connection, subscription_id)
    if current is None:
        raise ValueError("Calendar subscription does not exist.")
    name, colour, timezone = _normalise_subscription_settings(
        values.name, values.colour, values.timezone
    )
    before = {
        "name": current.name,
        "colour": current.colour,
        "timezone": current.timezone,
    }
    after = {"name": name, "colour": colour, "timezone": timezone}
    if before == after:
        return False
    now = utc_now()
    try:
        connection.execute(
            """UPDATE calendar_subscriptions
               SET name = ?, colour = ?, timezone = ?, updated_at = ?
               WHERE id = ?""",
            (name, colour, timezone, now, subscription_id),
        )
        record_audit_event(
            connection,
            "edit",
            [("calendar_subscription", subscription_id)],
            before=before,
            after=after,
            notes="Other calendar settings updated",
        )
        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise


def set_subscription_enabled(
    connection: sqlite3.Connection,
    subscription_id: int,
    enabled: bool,
) -> bool:
    current = get_subscription(connection, subscription_id)
    if current is None:
        raise ValueError("Calendar subscription does not exist.")
    if current.enabled == enabled:
        return False
    now = utc_now()
    if not enabled:
        from app.inbox_repository import resolve_source_items
        rows = connection.execute(
            "SELECT id FROM external_calendar_events WHERE subscription_id = ?",
            (subscription_id,),
        ).fetchall()
        for row in rows:
            resolve_source_items(connection, "event", -int(row["id"]))
    connection.execute(
        "UPDATE calendar_subscriptions SET enabled = ?, updated_at = ? WHERE id = ?",
        (int(enabled), now, subscription_id),
    )
    connection.commit()
    return True


def remove_subscription(connection: sqlite3.Connection, subscription_id: int) -> None:
    current = get_subscription(connection, subscription_id)
    if current is None:
        raise ValueError("Calendar subscription does not exist.")
    from app.inbox_repository import resolve_source_items
    event_ids = [
        -int(row["id"])
        for row in connection.execute(
            "SELECT id FROM external_calendar_events WHERE subscription_id = ?",
            (subscription_id,),
        )
    ]
    for event_id in event_ids:
        resolve_source_items(connection, "event", event_id)
    if event_ids:
        placeholders = ", ".join("?" for _ in event_ids)
        connection.execute(
            f"""DELETE FROM reminder_overrides
                WHERE source_kind = 'event' AND source_id IN ({placeholders})""",
            event_ids,
        )
    connection.execute(
        """DELETE FROM reminder_policies
           WHERE context_kind = 'calendar_subscription'
             AND context_id = ? AND source_kind = 'event'""",
        (subscription_id,),
    )
    connection.execute(
        "DELETE FROM calendar_subscriptions WHERE id = ?",
        (subscription_id,),
    )
    record_audit_event(
        connection,
        "delete",
        [("calendar_subscription", subscription_id)],
        before={"name": current.name, "host": current.host},
        notes="Read-only Calendar subscription and cache removed",
    )
    connection.commit()


def reorder_subscriptions(
    connection: sqlite3.Connection,
    subscription_ids: list[int],
) -> bool:
    expected = [item.id for item in list_subscriptions(connection, include_disabled=False)]
    if len(subscription_ids) != len(set(subscription_ids)):
        raise ValueError("Other calendars order contains duplicate identifiers.")
    if len(subscription_ids) != len(expected) or set(subscription_ids) != set(expected):
        raise ValueError("Other calendars order must contain every enabled source exactly once.")
    if subscription_ids == expected and all(
        item.sort_order == position
        for position, item in enumerate(list_subscriptions(connection, include_disabled=False))
    ):
        return False
    now = utc_now()
    connection.executemany(
        "UPDATE calendar_subscriptions SET sort_order = ?, updated_at = ? WHERE id = ?",
        [(position, now, item_id) for position, item_id in enumerate(subscription_ids)],
    )
    connection.commit()
    return True


def subscription_projection(connection: sqlite3.Connection) -> SubscriptionProjection:
    calendars: list[CalendarRecord] = []
    events: list[EventRecord] = []
    recurrences: dict[int, RecurrenceDefinition] = {}
    for subscription in list_subscriptions(connection, include_disabled=False):
        projection_calendar_id = -subscription.id
        calendars.append(CalendarRecord(
            projection_calendar_id,
            subscription.name,
            "external",
            subscription.colour,
            subscription.timezone,
            60,
            subscription.sort_order,
            False,
            subscription.created_at,
            subscription.updated_at,
            "",
        ))
        rows = connection.execute(
            """SELECT * FROM external_calendar_events
               WHERE subscription_id = ? ORDER BY start_date, id""",
            (subscription.id,),
        ).fetchall()
        for row in rows:
            projection_event_id = -int(row["id"])
            events.append(EventRecord(
                projection_event_id,
                row["title"],
                row["description"],
                projection_calendar_id,
                True,
                "",
                "",
                row["start_date"],
                row["end_date_exclusive"],
                "",
                "exact",
                row["status"],
                "",
                "",
                subscription.created_at,
                subscription.updated_at,
            ))
            if row["recurrence_json"]:
                rule = RecurrenceRule(**json.loads(row["recurrence_json"]))
                recurrences[projection_event_id] = RecurrenceDefinition(
                    projection_event_id, rule, 1
                )
    return SubscriptionProjection(tuple(calendars), tuple(events), recurrences)


def get_external_projection_event(
    connection: sqlite3.Connection,
    projection_event_id: int,
) -> tuple[EventRecord, CalendarRecord] | None:
    if projection_event_id >= 0:
        return None
    row = connection.execute(
        """SELECT event.*, source.name AS source_name, source.colour, source.timezone,
                  source.sort_order, source.created_at, source.updated_at, source.id AS source_id
           FROM external_calendar_events AS event
           JOIN calendar_subscriptions AS source ON source.id = event.subscription_id
           WHERE event.id = ? AND source.enabled = 1""",
        (-projection_event_id,),
    ).fetchone()
    if row is None:
        return None
    calendar = CalendarRecord(
        -int(row["source_id"]),
        row["source_name"],
        "external",
        row["colour"],
        row["timezone"],
        60,
        int(row["sort_order"]),
        False,
        row["created_at"],
        row["updated_at"],
        "",
    )
    event = EventRecord(
        projection_event_id,
        row["title"],
        row["description"],
        calendar.id,
        True,
        "",
        "",
        row["start_date"],
        row["end_date_exclusive"],
        "",
        "exact",
        row["status"],
        "",
        "",
        row["created_at"],
        row["updated_at"],
    )
    return event, calendar


def _replace_cache(
    connection: sqlite3.Connection,
    subscription_id: int,
    events: tuple[ICalendarEvent, ...],
) -> None:
    from app.inbox_repository import resolve_source_items

    existing = {
        row["source_uid"]: row
        for row in connection.execute(
            "SELECT * FROM external_calendar_events WHERE subscription_id = ?",
            (subscription_id,),
        )
    }
    retained_ids: set[int] = set()
    for event in events:
        recurrence_json = (
            json.dumps(event.recurrence.__dict__, sort_keys=True)
            if event.recurrence else ""
        )
        stored = (
            event.sequence,
            event.fingerprint,
            event.title,
            event.description,
            event.start_date,
            event.end_date_exclusive,
            event.status,
            recurrence_json,
        )
        row = existing.get(event.uid)
        if row is None:
            cursor = connection.execute(
                """INSERT INTO external_calendar_events (
                    subscription_id, source_uid, source_sequence,
                    source_fingerprint, title, description, start_date,
                    end_date_exclusive, status, recurrence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (subscription_id, event.uid, *stored),
            )
            retained_ids.add(int(cursor.lastrowid))
            continue

        event_id = int(row["id"])
        retained_ids.add(event_id)
        material_before = (
            row["start_date"],
            row["end_date_exclusive"],
            row["status"],
            row["recurrence_json"],
        )
        material_after = (
            event.start_date,
            event.end_date_exclusive,
            event.status,
            recurrence_json,
        )
        connection.execute(
            """UPDATE external_calendar_events
               SET source_sequence = ?, source_fingerprint = ?, title = ?,
                   description = ?, start_date = ?, end_date_exclusive = ?,
                   status = ?, recurrence_json = ?
               WHERE id = ?""",
            (*stored, event_id),
        )
        if material_before != material_after:
            resolve_source_items(connection, "event", -event_id)

    removed = [
        int(row["id"]) for row in existing.values()
        if int(row["id"]) not in retained_ids
    ]
    for event_id in removed:
        resolve_source_items(connection, "event", -event_id)
    if removed:
        placeholders = ", ".join("?" for _ in removed)
        connection.execute(
            f"DELETE FROM external_calendar_events WHERE id IN ({placeholders})",
            removed,
        )


def _normalise_metadata(
    document: ICalendarDocument,
    display_name: str,
    colour: str,
) -> tuple[str, str]:
    name = (display_name or document.name or "Subscribed Calendar").strip()
    name, _, timezone = _normalise_subscription_settings(
        name, colour, document.timezone or PLATFORM_TIMEZONE
    )
    return name, timezone


def _normalise_subscription_settings(
    name: str,
    colour: str,
    timezone: str,
) -> tuple[str, str, str]:
    name = name.strip()
    if not name:
        raise ValueError("Calendar subscription name is required.")
    if not _COLOUR_PATTERN.fullmatch(colour):
        raise ValueError("Calendar subscription colour must be a #RRGGBB value.")
    try:
        get_timezone(timezone)
    except TemporalValueError as error:
        raise ValueError("Calendar subscription timezone is not a known IANA timezone.") from error
    return name, colour.upper(), timezone


def _subscription(row: sqlite3.Row) -> SubscriptionRecord:
    values = dict(row)
    values["id"] = int(values["id"])
    values["enabled"] = bool(values["enabled"])
    values["sort_order"] = int(values["sort_order"])
    return SubscriptionRecord(**values)


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).astimezone(UTC)
    except ValueError:
        return None


class _PublicRedirectHandler(HTTPRedirectHandler):
    def __init__(self, resolver: Callable[..., object]):
        super().__init__()
        self.resolver = resolver
        self.redirects = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirects += 1
        if self.redirects > MAX_REDIRECTS:
            raise ValueError("Calendar URL exceeded the redirect limit.")
        validate_public_https_url(newurl, resolver=self.resolver)
        return super().redirect_request(req, fp, code, msg, headers, newurl)
