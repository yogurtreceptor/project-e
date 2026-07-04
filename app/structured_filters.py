import sqlite3
from dataclasses import dataclass
from typing import Callable

from app.entities import EntityRecord

FilterPredicate = Callable[[sqlite3.Connection, EntityRecord, str], bool]


@dataclass(frozen=True)
class FilterDefinition:
    key: str
    label: str
    entity_types: tuple[str, ...]
    value_label: str = ""
    value_type: str = "text"
    predicate: FilterPredicate = lambda _connection, _record, _value: True


def _birthday_month(_connection: sqlite3.Connection, record: EntityRecord, value: str) -> bool:
    birthday = record.metadata.get("birthday", "")
    return bool(value and len(birthday) >= 7 and birthday[5:7] == value.zfill(2))


def _birth_year(_connection: sqlite3.Connection, record: EntityRecord, value: str) -> bool:
    return bool(value and record.metadata.get("birthday", "").startswith(value + "-"))


def _no_birthday(_connection: sqlite3.Connection, record: EntityRecord, _value: str) -> bool:
    return not record.metadata.get("birthday", "")


def _organisation_no_location(connection: sqlite3.Connection, record: EntityRecord, _value: str) -> bool:
    row = connection.execute(
        """SELECT 1 FROM relationships r JOIN entities e
           ON e.id = CASE WHEN r.source_entity_id = ? THEN r.target_entity_id ELSE r.source_entity_id END
           WHERE (r.source_entity_id = ? OR r.target_entity_id = ?) AND e.type = 'location' AND e.deleted_at = '' LIMIT 1""",
        (record.id, record.id, record.id),
    ).fetchone()
    return row is None


FILTERS = (
    FilterDefinition("birthday_month", "Birthday month", ("person",), "Month (1–12)", "number", _birthday_month),
    FilterDefinition("birth_year", "Birth year", ("person",), "Year", "number", _birth_year),
    FilterDefinition("no_birthday", "No birthday", ("person",), predicate=_no_birthday),
    FilterDefinition("no_location", "No location", ("organisation",), predicate=_organisation_no_location),
)
FILTERS_BY_KEY = {item.key: item for item in FILTERS}


def apply_structured_filter(connection: sqlite3.Connection, records: list[EntityRecord], key: str, value: str = "") -> list[EntityRecord]:
    definition = FILTERS_BY_KEY.get(key)
    if definition is None:
        return records
    return [record for record in records if record.type in definition.entity_types and definition.predicate(connection, record, value.strip())]
