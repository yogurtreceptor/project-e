"""Shared Phase 2 temporal normalization and validation.

Timed values enter this boundary as local wall times plus an IANA timezone and
leave it as precise UTC instants. All-day values remain dates. Intervals are
always start-inclusive and end-exclusive.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class TemporalValueError(ValueError):
    """Raised when a temporal value cannot represent the approved semantics."""


@dataclass(frozen=True)
class TimedInterval:
    start_utc: str
    end_utc: str
    timezone: str


@dataclass(frozen=True)
class AllDayInterval:
    start_date: str
    end_date_exclusive: str

    @property
    def inclusive_end_date(self) -> str:
        return (
            date.fromisoformat(self.end_date_exclusive) - timedelta(days=1)
        ).isoformat()


def get_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise TemporalValueError(f"Unknown IANA timezone: {name}.") from None


def parse_local_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise TemporalValueError("Date and time must be a valid ISO local value.") from None
    if parsed.tzinfo is not None:
        raise TemporalValueError("Local date and time must not include a UTC offset.")
    return parsed


def local_datetime_to_utc(value: str, timezone_name: str, fold: int | None = None) -> str:
    """Convert a local wall time, rejecting DST gaps and unresolved ambiguity."""
    local_value = parse_local_datetime(value)
    zone = get_timezone(timezone_name)
    candidates: list[tuple[int, datetime]] = []
    for candidate_fold in (0, 1):
        aware = local_value.replace(tzinfo=zone, fold=candidate_fold)
        round_trip = aware.astimezone(timezone.utc).astimezone(zone)
        if round_trip.replace(tzinfo=None) == local_value and round_trip.fold == candidate_fold:
            candidates.append((candidate_fold, aware.astimezone(timezone.utc)))

    distinct = {candidate for _, candidate in candidates}
    if not candidates:
        raise TemporalValueError(
            f"{value} does not exist in {timezone_name} because of a timezone transition."
        )
    if len(distinct) > 1 and fold is None:
        raise TemporalValueError(
            f"{value} occurs twice in {timezone_name}; choose the earlier or later occurrence."
        )
    selected_fold = fold if fold is not None else candidates[0][0]
    if selected_fold not in (0, 1):
        raise TemporalValueError("Timezone fold must be 0 (earlier) or 1 (later).")
    selected = next(
        (instant for item_fold, instant in candidates if item_fold == selected_fold),
        None,
    )
    if selected is None:
        raise TemporalValueError("The selected timezone occurrence is not valid.")
    return selected.strftime(UTC_FORMAT)


def normalise_timed_interval(
    start_local: str,
    end_local: str,
    timezone_name: str,
    *,
    start_fold: int | None = None,
    end_fold: int | None = None,
) -> TimedInterval:
    start_utc = local_datetime_to_utc(start_local, timezone_name, start_fold)
    end_utc = local_datetime_to_utc(end_local, timezone_name, end_fold)
    if datetime.strptime(end_utc, UTC_FORMAT) <= datetime.strptime(start_utc, UTC_FORMAT):
        raise TemporalValueError("Event end must be after its start.")
    return TimedInterval(start_utc, end_utc, timezone_name)


def normalise_all_day_interval(
    start_date: str, inclusive_end_date: str
) -> AllDayInterval:
    try:
        start = date.fromisoformat(start_date)
        inclusive_end = date.fromisoformat(inclusive_end_date)
    except ValueError:
        raise TemporalValueError("All-day boundaries must be valid ISO dates.") from None
    if inclusive_end < start:
        raise TemporalValueError("All-day Event end date cannot precede its start date.")
    return AllDayInterval(start.isoformat(), (inclusive_end + timedelta(days=1)).isoformat())
