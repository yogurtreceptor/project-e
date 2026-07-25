"""Local catalogue and presentation helpers for IANA timezones."""

from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import TZPATH, ZoneInfo, available_timezones


@lru_cache(maxsize=1)
def timezone_catalogue() -> tuple[tuple[str, str, str], ...]:
    """Return local IANA zones with country names and their current offsets.

    The operating system's tzdb supplies both the zone database and its public
    ``zone.tab``/``iso3166.tab`` metadata, keeping the picker local-first and
    aligned with the set of zones the runtime can actually validate.
    """
    metadata_directory = _metadata_directory()
    country_names = _country_names(metadata_directory / "iso3166.tab")
    countries_by_zone = _countries_by_zone(metadata_directory / "zone.tab")
    available = available_timezones()
    zones = set(countries_by_zone).intersection(available) or available
    zones.add("UTC")
    now = datetime.now(UTC)
    entries = []
    for name in zones:
        try:
            offset = now.astimezone(ZoneInfo(name)).utcoffset()
        except Exception:
            continue
        offset_seconds = int(offset.total_seconds()) if offset else 0
        country_codes = countries_by_zone.get(name, ())
        countries = ", ".join(country_names.get(code, code) for code in country_codes)
        entries.append((name, countries, _offset_label(offset_seconds)))
    return tuple(sorted(entries, key=lambda item: (item[2], item[1], item[0])))


def _metadata_directory() -> Path:
    for location in TZPATH:
        candidate = Path(location)
        if (candidate / "zone.tab").is_file():
            return candidate
    return Path("/usr/share/zoneinfo")


def _country_names(path: Path) -> dict[str, str]:
    return {
        fields[0]: fields[1]
        for fields in _tab_rows(path)
        if len(fields) >= 2
    }


def _countries_by_zone(path: Path) -> dict[str, tuple[str, ...]]:
    return {
        fields[2]: tuple(fields[0].split(","))
        for fields in _tab_rows(path)
        if len(fields) >= 3
    }


def _tab_rows(path: Path) -> list[list[str]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [line.split("\t") for line in lines if line and not line.startswith("#")]


def _offset_label(offset_seconds: int) -> str:
    sign = "+" if offset_seconds >= 0 else "-"
    hours, remainder = divmod(abs(offset_seconds), 3600)
    return f"UTC{sign}{hours:02d}:{remainder // 60:02d}"
