import json
from dataclasses import dataclass

from app.db_support import utc_now


EVENT_TYPES = {
    "create", "edit", "delete", "restore", "permanent_delete",
    "relationship_change", "inference", "validation", "merge", "import",
    "manual_override",
}
PROVENANCE_TYPES = {
    "manual", "inferred", "imported", "document", "contact_import",
    "user_confirmed", "unknown",
}


@dataclass(frozen=True)
class AuditFilters:
    event_type: str = ""
    record_kind: str = ""


@dataclass(frozen=True)
class AuditEvent:
    id: int
    event_type: str
    occurred_at: str
    actor: str
    notes: str
    before: object
    after: object
    provenance: str
    records: tuple

    @property
    def record_kinds(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(kind for kind, _record_id in self.records))

    @property
    def subject_kind(self) -> str:
        return next((kind for kind in self.record_kinds if kind != "entity"), self.record_kinds[0] if self.record_kinds else "system")

    @property
    def action(self) -> str:
        if self.event_type != "relationship_change":
            return self.event_type
        note = self.notes.lower()
        for action in ("create", "edit", "delete", "restore"):
            if action in note or (action == "edit" and "updated" in note):
                return action
        return "edit"


def record_audit_event(connection, event_type, records, before=None, after=None, notes="", actor="local_user", provenance="manual"):
    if event_type not in EVENT_TYPES:
        raise ValueError("Unknown audit event type.")
    if provenance not in PROVENANCE_TYPES:
        raise ValueError("Unknown provenance type.")
    cursor = connection.execute(
        "INSERT INTO audit_events(event_type,occurred_at,actor,notes,before_json,after_json,provenance) VALUES(?,?,?,?,?,?,?)",
        (event_type, utc_now(), actor, notes, json.dumps(before, sort_keys=True) if before is not None else "", json.dumps(after, sort_keys=True) if after is not None else "", provenance),
    )
    event_id = int(cursor.lastrowid)
    connection.executemany("INSERT INTO audit_event_records VALUES(?,?,?)", [(event_id, kind, record_id) for kind, record_id in records])
    return event_id


def list_audit_events(connection, record_kind=None, record_id=None, filters=None):
    selected = filters or AuditFilters()
    sql = "SELECT DISTINCT a.* FROM audit_events a"
    clauses, params = [], []
    if record_kind is not None:
        sql += " JOIN audit_event_records selected_record ON selected_record.event_id=a.id"
        clauses.extend(("selected_record.record_kind=?", "selected_record.record_id=?"))
        params.extend((record_kind, record_id))
    if selected.record_kind:
        sql += " JOIN audit_event_records filtered_record ON filtered_record.event_id=a.id"
        clauses.append("filtered_record.record_kind=?")
        params.append(selected.record_kind)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    result = []
    for row in connection.execute(sql + " ORDER BY a.occurred_at DESC,a.id DESC", params):
        references = tuple((item[0], item[1]) for item in connection.execute("SELECT record_kind,record_id FROM audit_event_records WHERE event_id=? ORDER BY record_kind,record_id", (row["id"],)))
        event = AuditEvent(row["id"], row["event_type"], row["occurred_at"], row["actor"], row["notes"], json.loads(row["before_json"]) if row["before_json"] else None, json.loads(row["after_json"]) if row["after_json"] else None, row["provenance"], references)
        if not selected.event_type or event.action == selected.event_type:
            result.append(event)
    return result


def set_provenance(connection, kind, record_id, field_name, provenance):
    if provenance not in PROVENANCE_TYPES:
        raise ValueError("Unknown provenance type.")
    connection.execute("INSERT INTO provenance_metadata VALUES(?,?,?,?,?) ON CONFLICT(record_kind,record_id,field_name) DO UPDATE SET provenance=excluded.provenance,updated_at=excluded.updated_at", (kind, record_id, field_name, provenance, utc_now()))


def get_provenance(connection, kind, record_id):
    return {row[0]: row[1] for row in connection.execute("SELECT field_name,provenance FROM provenance_metadata WHERE record_kind=? AND record_id=?", (kind, record_id))}
