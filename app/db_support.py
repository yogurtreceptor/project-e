import re
from datetime import UTC, datetime

from app.entities import ENTITY_DEFINITIONS


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def parse_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def sql_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Unsafe SQL identifier: {value}")
    return value


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def allowed_entity_type_sql() -> str:
    return ", ".join(sql_literal(definition.type) for definition in ENTITY_DEFINITIONS)
