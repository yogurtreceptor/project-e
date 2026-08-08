"""Durable user-owned mobility profile and routing policy identity."""

from __future__ import annotations

import json
import math
import re
import sqlite3
from typing import Any, Mapping

from app.audit import record_audit_event
from app.db_support import utc_now
from app.journey_contract import (
    JourneyMode,
    MobilityProfile,
    PolicyKind,
    RoutingPolicy,
    canonical_json,
)


_KEY_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


def create_mobility_profile(
    connection: sqlite3.Connection,
    profile_key: str,
    display_name: str,
    primary_mode: JourneyMode,
    definition: Mapping[str, Any],
    *,
    commit: bool = True,
    audit_actor: str = "local_user",
    audit_provenance: str = "manual",
    audit_notes: str = "Mobility profile created",
) -> MobilityProfile:
    profile_key = _normalise_key(profile_key, "Profile")
    display_name = _normalise_name(display_name, "Profile")
    primary_mode = JourneyMode(primary_mode)
    definition_json = _profile_definition_json(definition)
    now = utc_now()
    cursor = connection.execute(
        """INSERT INTO mobility_profiles (
               profile_key, display_name, primary_mode, revision,
               definition_json, created_at, updated_at
           ) VALUES (?, ?, ?, 1, ?, ?, ?)""",
        (
            profile_key,
            display_name,
            primary_mode.value,
            definition_json,
            now,
            now,
        ),
    )
    profile = get_mobility_profile_by_id(connection, int(cursor.lastrowid))
    record_audit_event(
        connection,
        "create",
        [("mobility_profile", profile.id)],
        after=_profile_snapshot(profile),
        notes=audit_notes,
        actor=audit_actor,
        provenance=audit_provenance,
    )
    if commit:
        connection.commit()
    return profile


def update_mobility_profile(
    connection: sqlite3.Connection,
    profile_key: str,
    *,
    display_name: str,
    primary_mode: JourneyMode,
    definition: Mapping[str, Any],
    commit: bool = True,
) -> MobilityProfile:
    before = get_mobility_profile(connection, profile_key)
    if before is None:
        raise ValueError("Mobility profile does not exist.")
    display_name = _normalise_name(display_name, "Profile")
    primary_mode = JourneyMode(primary_mode)
    definition_json = _profile_definition_json(definition)
    connection.execute(
        """UPDATE mobility_profiles
           SET display_name=?, primary_mode=?, definition_json=?,
               revision=revision+1, updated_at=?
           WHERE id=?""",
        (
            display_name,
            primary_mode.value,
            definition_json,
            utc_now(),
            before.id,
        ),
    )
    after = get_mobility_profile_by_id(connection, before.id)
    record_audit_event(
        connection,
        "edit",
        [("mobility_profile", before.id)],
        before=_profile_snapshot(before),
        after=_profile_snapshot(after),
        notes="Mobility profile updated",
    )
    if commit:
        connection.commit()
    return after


def get_mobility_profile(
    connection: sqlite3.Connection, profile_key: str
) -> MobilityProfile | None:
    row = connection.execute(
        "SELECT * FROM mobility_profiles WHERE profile_key=?", (profile_key,)
    ).fetchone()
    return _profile_from_row(row) if row else None


def get_mobility_profile_by_id(
    connection: sqlite3.Connection, profile_id: int
) -> MobilityProfile:
    row = connection.execute(
        "SELECT * FROM mobility_profiles WHERE id=?", (profile_id,)
    ).fetchone()
    if row is None:
        raise ValueError("Mobility profile does not exist.")
    return _profile_from_row(row)


def list_mobility_profiles(connection: sqlite3.Connection) -> list[MobilityProfile]:
    return [
        _profile_from_row(row)
        for row in connection.execute(
            "SELECT * FROM mobility_profiles ORDER BY display_name, id"
        )
    ]


def create_routing_policy(
    connection: sqlite3.Connection,
    policy_key: str,
    display_name: str,
    kind: PolicyKind,
    definition: Mapping[str, Any],
    *,
    is_enabled: bool = True,
    commit: bool = True,
) -> RoutingPolicy:
    policy_key = _normalise_key(policy_key, "Policy")
    display_name = _normalise_name(display_name, "Policy")
    kind = PolicyKind(kind)
    is_enabled = _require_bool(is_enabled, "Policy enabled state")
    definition_json = _policy_definition_json(definition)
    now = utc_now()
    cursor = connection.execute(
        """INSERT INTO routing_policies (
               policy_key, display_name, policy_kind, revision,
               definition_json, is_enabled, created_at, updated_at
           ) VALUES (?, ?, ?, 1, ?, ?, ?, ?)""",
        (
            policy_key,
            display_name,
            kind.value,
            definition_json,
            int(is_enabled),
            now,
            now,
        ),
    )
    policy = get_routing_policy_by_id(connection, int(cursor.lastrowid))
    record_audit_event(
        connection,
        "create",
        [("routing_policy", policy.id)],
        after=_policy_snapshot(policy),
        notes="Routing policy created",
    )
    if commit:
        connection.commit()
    return policy


def update_routing_policy(
    connection: sqlite3.Connection,
    policy_key: str,
    *,
    display_name: str,
    kind: PolicyKind,
    definition: Mapping[str, Any],
    is_enabled: bool,
    commit: bool = True,
) -> RoutingPolicy:
    before = get_routing_policy(connection, policy_key)
    if before is None:
        raise ValueError("Routing policy does not exist.")
    display_name = _normalise_name(display_name, "Policy")
    kind = PolicyKind(kind)
    is_enabled = _require_bool(is_enabled, "Policy enabled state")
    definition_json = _policy_definition_json(definition)
    connection.execute(
        """UPDATE routing_policies
           SET display_name=?, policy_kind=?, definition_json=?,
               is_enabled=?, revision=revision+1, updated_at=?
           WHERE id=?""",
        (
            display_name,
            kind.value,
            definition_json,
            int(is_enabled),
            utc_now(),
            before.id,
        ),
    )
    after = get_routing_policy_by_id(connection, before.id)
    record_audit_event(
        connection,
        "edit",
        [("routing_policy", before.id)],
        before=_policy_snapshot(before),
        after=_policy_snapshot(after),
        notes="Routing policy updated",
    )
    if commit:
        connection.commit()
    return after


def get_routing_policy(
    connection: sqlite3.Connection, policy_key: str
) -> RoutingPolicy | None:
    row = connection.execute(
        "SELECT * FROM routing_policies WHERE policy_key=?", (policy_key,)
    ).fetchone()
    return _policy_from_row(row) if row else None


def get_routing_policy_by_id(
    connection: sqlite3.Connection, policy_id: int
) -> RoutingPolicy:
    row = connection.execute(
        "SELECT * FROM routing_policies WHERE id=?", (policy_id,)
    ).fetchone()
    if row is None:
        raise ValueError("Routing policy does not exist.")
    return _policy_from_row(row)


def list_routing_policies(connection: sqlite3.Connection) -> list[RoutingPolicy]:
    return [
        _policy_from_row(row)
        for row in connection.execute(
            "SELECT * FROM routing_policies ORDER BY display_name, id"
        )
    ]


def validate_stored_journey_configuration(
    connection: sqlite3.Connection,
) -> list[str]:
    errors: list[str] = []
    for row in connection.execute("SELECT * FROM mobility_profiles ORDER BY id"):
        try:
            if int(row["revision"]) <= 0:
                raise ValueError("revision must be positive.")
            profile = _profile_from_row(row)
            _normalise_key(profile.profile_key, "Profile")
            _normalise_name(profile.display_name, "Profile")
            _profile_definition_json(profile.definition)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"Mobility profile {row['id']} is invalid: {error}")
    for row in connection.execute("SELECT * FROM routing_policies ORDER BY id"):
        try:
            if int(row["revision"]) <= 0:
                raise ValueError("revision must be positive.")
            if row["is_enabled"] not in (0, 1):
                raise ValueError("enabled state must be zero or one.")
            policy = _policy_from_row(row)
            _normalise_key(policy.policy_key, "Policy")
            _normalise_name(policy.display_name, "Policy")
            _policy_definition_json(policy.definition)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"Routing policy {row['id']} is invalid: {error}")
    return errors


def _normalise_key(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} key must be text.")
    value = value.strip()
    if not _KEY_PATTERN.fullmatch(value):
        raise ValueError(
            f"{label} key must use lowercase letters, numbers, hyphens or underscores."
        )
    return value


def _normalise_name(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} name must be text.")
    value = value.strip()
    if not value:
        raise ValueError(f"{label} name is required.")
    return value


def _profile_definition_json(definition: Mapping[str, Any]) -> str:
    text = canonical_json(definition)
    value = json.loads(text)
    for key in (
        "speed_metres_per_second",
        "maximum_contiguous_distance_metres",
        "maximum_contiguous_duration_seconds",
    ):
        if key not in value:
            continue
        number = value[key]
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise ValueError(f"Profile {key} must be a positive number.")
        if not math.isfinite(float(number)) or float(number) <= 0:
            raise ValueError(f"Profile {key} must be a positive number.")
    return text


def _policy_definition_json(definition: Mapping[str, Any]) -> str:
    text = canonical_json(definition)
    value = json.loads(text)
    modes = value.get("modes")
    if modes is not None:
        if not isinstance(modes, list) or not modes:
            raise ValueError("Policy modes must be a non-empty list when supplied.")
        try:
            tuple(JourneyMode(item) for item in modes)
        except (TypeError, ValueError) as error:
            raise ValueError("Policy modes contain an unsupported journey mode.") from error
    return text


def _require_bool(value: bool, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be true or false.")
    return value


def _profile_from_row(row: sqlite3.Row) -> MobilityProfile:
    return MobilityProfile(
        id=int(row["id"]),
        profile_key=row["profile_key"],
        display_name=row["display_name"],
        primary_mode=JourneyMode(row["primary_mode"]),
        revision=int(row["revision"]),
        definition=json.loads(row["definition_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _policy_from_row(row: sqlite3.Row) -> RoutingPolicy:
    return RoutingPolicy(
        id=int(row["id"]),
        policy_key=row["policy_key"],
        display_name=row["display_name"],
        kind=PolicyKind(row["policy_kind"]),
        revision=int(row["revision"]),
        definition=json.loads(row["definition_json"]),
        is_enabled=bool(row["is_enabled"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _profile_snapshot(profile: MobilityProfile) -> dict[str, object]:
    return {
        "profile_key": profile.profile_key,
        "display_name": profile.display_name,
        "primary_mode": profile.primary_mode.value,
        "revision": profile.revision,
        "definition": profile.definition,
    }


def _policy_snapshot(policy: RoutingPolicy) -> dict[str, object]:
    return {
        "policy_key": policy.policy_key,
        "display_name": policy.display_name,
        "kind": policy.kind.value,
        "revision": policy.revision,
        "definition": policy.definition,
        "is_enabled": policy.is_enabled,
    }
