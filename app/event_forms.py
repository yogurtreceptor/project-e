"""Pure parsing of Calendar Event form values into domain inputs."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.event_recurrence import RecurrenceRule, until_date_after_occurrences
from app.event_service import EventInput, EventRecord


def calendar_anchor_date(value: str) -> date:
    try:
        return date.fromisoformat(value) if value else date.today()
    except ValueError:
        return date.today()


def event_input_from_form(values: dict[str, str]) -> EventInput:
    calendar_id = (
        int(values["calendar_id"])
        if values.get("calendar_id", "").isdigit()
        else None
    )
    return EventInput(
        values.get("title", ""),
        values.get("all_day") == "1",
        calendar_id,
        values.get("notes", ""),
        values.get("timezone", ""),
        values.get("start_local", ""),
        values.get("end_local", ""),
        start_date=values.get("start_date", ""),
        end_date=values.get("end_date", ""),
    )


def recurrence_rule_from_form(
    values: dict[str, str],
    event: EventRecord,
    fallback: RecurrenceRule | None = None,
) -> RecurrenceRule | None:
    """Map the simple Event-form picker to canonical recurrence rules."""
    preset = values.get("recurrence_preset")
    if not preset:
        if "recurrence_frequency" not in values:
            return fallback
        frequency = values.get("recurrence_frequency", "")
        if not frequency:
            return None
        interval = int(values.get("recurrence_interval", "1"))
        weekdays = tuple(
            int(day)
            for day in values.get("recurrence_weekdays", "").split(",")
            if day.isdigit()
        )
        return RecurrenceRule(
            frequency,
            interval,
            weekdays,
            int(values.get("recurrence_ordinal", "0")),
            int(values.get("recurrence_monthly_weekday", "-1")),
            values.get("recurrence_until", ""),
        )
    if preset == "none":
        return None
    if preset == "custom":
        return custom_recurrence_rule_from_form(values, event)
    anchor = _event_anchor(event)
    if preset == "daily":
        return RecurrenceRule("daily")
    if preset == "yearly":
        return RecurrenceRule("yearly")
    if preset == "weekdays":
        return RecurrenceRule("weekly", weekdays=(0, 1, 2, 3, 4))
    if preset == f"weekly_{anchor.weekday()}":
        return RecurrenceRule("weekly", weekdays=(anchor.weekday(),))
    parts = preset.split("_")
    if (
        len(parts) == 3
        and parts[0] == "monthly"
        and parts[2].isdigit()
        and int(parts[2]) == anchor.weekday()
    ):
        ordinal = (
            -1
            if parts[1] == "last"
            else int(parts[1])
            if parts[1].isdigit()
            else 0
        )
        if ordinal in (-1, 1, 2, 3, 4, 5):
            return RecurrenceRule(
                "monthly",
                monthly_ordinal=ordinal,
                monthly_weekday=anchor.weekday(),
            )
    raise ValueError("Recurrence choice is invalid.")


def custom_recurrence_rule_from_form(
    values: dict[str, str], event: EventRecord
) -> RecurrenceRule:
    interval = int(values.get("recurrence_custom_interval", "1"))
    if not 1 <= interval <= 999:
        raise ValueError("Repeat interval must be between 1 and 999.")
    frequency = {
        "day": "daily",
        "week": "weekly",
        "month": "monthly",
        "year": "yearly",
    }.get(values.get("recurrence_custom_frequency", ""))
    if frequency is None:
        raise ValueError("Custom recurrence frequency is invalid.")
    weekdays = tuple(
        sorted(
            {
                int(day)
                for day in values.get("recurrence_custom_weekdays", "").split(",")
                if day.isdigit() and int(day) in range(7)
            }
        )
    )
    ordinal = 0
    monthly_weekday = -1
    if frequency == "weekly" and not weekdays:
        raise ValueError("Choose at least one weekday for a weekly recurrence.")
    if frequency == "monthly" and values.get(
        "recurrence_custom_monthly_pattern"
    ) in {"ordinal", "last"}:
        anchor = _event_anchor(event)
        monthly_weekday = anchor.weekday()
        if values.get("recurrence_custom_monthly_pattern") == "last":
            if (anchor + timedelta(days=7)).month == anchor.month:
                raise ValueError(
                    "This Event date is not the last matching weekday of its month."
                )
            ordinal = -1
        else:
            ordinal = (anchor.day - 1) // 7 + 1
        if ordinal not in (-1, 1, 2, 3, 4):
            raise ValueError(
                "This Event date has no first-through-fourth weekday monthly pattern."
            )
    rule = RecurrenceRule(frequency, interval, weekdays, ordinal, monthly_weekday)
    ending = values.get("recurrence_custom_ends", "never")
    if ending == "never":
        return rule
    if ending == "on":
        return RecurrenceRule(
            **{
                **rule.__dict__,
                "until_date": values.get("recurrence_custom_until", ""),
            }
        )
    if ending == "after":
        count = int(values.get("recurrence_custom_count", "0"))
        return RecurrenceRule(
            **{
                **rule.__dict__,
                "until_date": until_date_after_occurrences(event, rule, count),
            }
        )
    raise ValueError("Custom recurrence end condition is invalid.")


def _event_anchor(event: EventRecord) -> date:
    if event.is_all_day:
        return date.fromisoformat(event.start_date)
    return (
        datetime.fromisoformat(event.start_utc.removesuffix("Z") + "+00:00")
        .astimezone(ZoneInfo(event.timezone))
        .date()
    )
