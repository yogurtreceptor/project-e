from datetime import date
from decimal import Decimal, InvalidOperation


def normalise_structured_value(value: str, value_kind: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value_kind == "whole_number":
        return str(int(value)) if value.isascii() and value.isdecimal() else value
    if value_kind in {"latitude", "longitude"}:
        number = parse_decimal(value)
        if number is None:
            return value
        if number == 0:
            return "0"
        return format(number.normalize(), "f")
    return value


def validate_structured_value(value: str, value_kind: str, label: str) -> str | None:
    if not value:
        return None
    if value_kind == "date":
        try:
            date.fromisoformat(value)
        except ValueError:
            return f"{label} must be a valid date in YYYY-MM-DD format."
    elif value_kind == "whole_number":
        if not value.isascii() or not value.isdecimal():
            return "Value must be a whole number without a dollar sign."
    elif value_kind in {"latitude", "longitude"}:
        number = parse_decimal(value)
        if number is None:
            return f"{label} must be a valid number."
        limit = Decimal("90") if value_kind == "latitude" else Decimal("180")
        if not -limit <= number <= limit:
            return f"{label} must be between {-limit} and {limit}."
    return None


def parse_decimal(value: str) -> Decimal | None:
    if len(value) > 64:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        return None
    return number if number.is_finite() else None
