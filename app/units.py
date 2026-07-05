"""Canonical measurement storage with unit-aware presentation conversion."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class MeasurementUnit:
    id: int
    key: str
    name: str
    symbol: str
    category: str
    canonical: bool
    conversion_factor: Decimal
    conversion_offset: Decimal


@dataclass(frozen=True)
class Measurement:
    entity_id: int
    field_name: str
    category: str
    canonical_value: Decimal
    display_unit: MeasurementUnit

    @property
    def display_value(self) -> Decimal:
        return from_canonical(self.canonical_value, self.display_unit)

    @property
    def display_text(self) -> str:
        return f"{format_decimal(self.display_value)} {self.display_unit.symbol}"


UNIT_SEED = (
    ("metre", "Metre", "m", "length", True, "1", "0"),
    ("centimetre", "Centimetre", "cm", "length", False, "0.01", "0"),
    ("inch", "Inch", "in", "length", False, "0.0254", "0"),
    ("kilogram", "Kilogram", "kg", "mass", True, "1", "0"),
    ("pound", "Pound", "lb", "mass", False, "0.45359237", "0"),
    ("celsius", "Degree Celsius", "°C", "temperature", True, "1", "0"),
    ("fahrenheit", "Degree Fahrenheit", "°F", "temperature", False, "0.5555555555555555555555555556", "-17.77777777777777777777777778"),
)


def create_unit_tables(connection: object) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS measurement_units (
            reference_item_id INTEGER PRIMARY KEY
                REFERENCES reference_data_items(id),
            symbol TEXT NOT NULL,
            category TEXT NOT NULL,
            canonical INTEGER NOT NULL DEFAULT 0 CHECK (canonical IN (0, 1)),
            conversion_factor TEXT NOT NULL,
            conversion_offset TEXT NOT NULL DEFAULT '0'
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_measurement_units_canonical
            ON measurement_units(category) WHERE canonical = 1;
        CREATE TABLE IF NOT EXISTS entity_measurements (
            entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            field_name TEXT NOT NULL,
            category TEXT NOT NULL,
            canonical_value TEXT NOT NULL,
            display_unit_id INTEGER NOT NULL REFERENCES measurement_units(reference_item_id),
            PRIMARY KEY (entity_id, field_name)
        );
        """
    )
    connection.execute(
        "INSERT INTO reference_data_types(key, name) VALUES ('measurement_unit', 'Measurement units') ON CONFLICT DO NOTHING"
    )
    for key, name, symbol, category, canonical, factor, offset in UNIT_SEED:
        connection.execute(
            """INSERT INTO reference_data_items(type_key, key, name, code)
               VALUES ('measurement_unit', ?, ?, ?) ON CONFLICT DO NOTHING""",
            (key, name, symbol),
        )
        item_id = connection.execute(
            "SELECT id FROM reference_data_items WHERE type_key='measurement_unit' AND key=?",
            (key,),
        ).fetchone()["id"]
        connection.execute(
            """INSERT INTO measurement_units
               (reference_item_id, symbol, category, canonical, conversion_factor, conversion_offset)
               VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING""",
            (item_id, symbol, category, int(canonical), factor, offset),
        )


def list_units(connection: object, category: str = "") -> list[MeasurementUnit]:
    clause = "WHERE unit.category = ?" if category else ""
    parameters = (category,) if category else ()
    rows = connection.execute(
        f"""SELECT item.id, item.key, item.name, unit.symbol, unit.category,
                   unit.canonical, unit.conversion_factor, unit.conversion_offset
            FROM measurement_units unit
            JOIN reference_data_items item ON item.id = unit.reference_item_id
            {clause}
            ORDER BY unit.canonical DESC, lower(item.name)""",
        parameters,
    ).fetchall()
    return [_to_unit(row) for row in rows]


def get_unit(connection: object, unit_id: int) -> MeasurementUnit | None:
    row = connection.execute(
        """SELECT item.id, item.key, item.name, unit.symbol, unit.category,
                  unit.canonical, unit.conversion_factor, unit.conversion_offset
           FROM measurement_units unit
           JOIN reference_data_items item ON item.id = unit.reference_item_id
           WHERE item.id = ?""",
        (unit_id,),
    ).fetchone()
    return _to_unit(row) if row else None


def to_canonical(value: Decimal | str, unit: MeasurementUnit) -> Decimal:
    number = _decimal(value)
    return number * unit.conversion_factor + unit.conversion_offset


def from_canonical(value: Decimal | str, unit: MeasurementUnit) -> Decimal:
    number = _decimal(value)
    return (number - unit.conversion_offset) / unit.conversion_factor


def set_measurement(
    connection: object,
    entity_id: int,
    field_name: str,
    category: str,
    value: Decimal | str,
    display_unit_id: int,
) -> None:
    unit = get_unit(connection, display_unit_id)
    if unit is None or unit.category != category:
        raise ValueError(f"Invalid {category} measurement unit.")
    canonical_value = format(to_canonical(value, unit).normalize(), "f")
    connection.execute(
        """INSERT INTO entity_measurements
           (entity_id, field_name, category, canonical_value, display_unit_id)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(entity_id, field_name) DO UPDATE SET
               category=excluded.category,
               canonical_value=excluded.canonical_value,
               display_unit_id=excluded.display_unit_id""",
        (entity_id, field_name, category, canonical_value, display_unit_id),
    )


def clear_measurement(connection: object, entity_id: int, field_name: str) -> None:
    connection.execute(
        "DELETE FROM entity_measurements WHERE entity_id=? AND field_name=?",
        (entity_id, field_name),
    )


def get_measurement(
    connection: object, entity_id: int, field_name: str
) -> Measurement | None:
    row = connection.execute(
        """SELECT measurement.entity_id, measurement.field_name,
                  measurement.category, measurement.canonical_value,
                  item.id, item.key, item.name, unit.symbol, unit.canonical,
                  unit.conversion_factor, unit.conversion_offset
           FROM entity_measurements measurement
           JOIN measurement_units unit
             ON unit.reference_item_id = measurement.display_unit_id
           JOIN reference_data_items item ON item.id = unit.reference_item_id
           WHERE measurement.entity_id=? AND measurement.field_name=?""",
        (entity_id, field_name),
    ).fetchone()
    if not row:
        return None
    return Measurement(
        entity_id=int(row["entity_id"]),
        field_name=row["field_name"],
        category=row["category"],
        canonical_value=Decimal(row["canonical_value"]),
        display_unit=_to_unit(row),
    )


def format_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _decimal(value: Decimal | str) -> Decimal:
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except InvalidOperation as error:
        raise ValueError("Measurement value must be a number.") from error
    if not number.is_finite():
        raise ValueError("Measurement value must be finite.")
    return number


def _to_unit(row: dict) -> MeasurementUnit:
    return MeasurementUnit(
        id=int(row["id"]),
        key=row["key"],
        name=row["name"],
        symbol=row["symbol"],
        category=row["category"],
        canonical=bool(row["canonical"]),
        conversion_factor=Decimal(row["conversion_factor"]),
        conversion_offset=Decimal(row["conversion_offset"]),
    )
