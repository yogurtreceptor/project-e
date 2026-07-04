import re
import sqlite3
from dataclasses import dataclass

from app.db_support import utc_now


@dataclass(frozen=True)
class TaxonomyEntry:
    id: int
    taxonomy_key: str
    key: str
    label: str
    parent_id: int | None
    depth: int
    archived_at: str
    path: str

    @property
    def active(self) -> bool:
        return not self.archived_at


def create_taxonomy_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS taxonomies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL,
            max_depth INTEGER NOT NULL DEFAULT 3 CHECK(max_depth BETWEEN 1 AND 3),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS taxonomy_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            taxonomy_id INTEGER NOT NULL REFERENCES taxonomies(id),
            parent_id INTEGER REFERENCES taxonomy_entries(id),
            key TEXT NOT NULL,
            label TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            archived_at TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(taxonomy_id, key)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_taxonomy_sibling_label
            ON taxonomy_entries(taxonomy_id, COALESCE(parent_id, 0), label COLLATE NOCASE);
        CREATE INDEX IF NOT EXISTS idx_taxonomy_parent ON taxonomy_entries(taxonomy_id, parent_id, sort_order, label);
        CREATE TABLE IF NOT EXISTS relationship_type_definitions (
            taxonomy_entry_id INTEGER PRIMARY KEY REFERENCES taxonomy_entries(id),
            source_entity_type TEXT NOT NULL,
            target_entity_type TEXT NOT NULL,
            directional INTEGER NOT NULL DEFAULT 1,
            source_role TEXT NOT NULL,
            target_role TEXT NOT NULL,
            source_label TEXT NOT NULL,
            target_label TEXT NOT NULL,
            source_role_male TEXT NOT NULL DEFAULT '', source_role_female TEXT NOT NULL DEFAULT '',
            target_role_male TEXT NOT NULL DEFAULT '', target_role_female TEXT NOT NULL DEFAULT '',
            source_label_male TEXT NOT NULL DEFAULT '', source_label_female TEXT NOT NULL DEFAULT '',
            target_label_male TEXT NOT NULL DEFAULT '', target_label_female TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '', selectable INTEGER NOT NULL DEFAULT 1
        );
        """
    )
    _ensure_column(connection, "organisations", "organisation_type", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(connection, "organisations", "taxonomy_entry_id", "INTEGER REFERENCES taxonomy_entries(id)")
    _ensure_column(connection, "relationships", "taxonomy_entry_id", "INTEGER REFERENCES taxonomy_entries(id)")
    seed_taxonomies(connection)
    migrate_taxonomy_assignments(connection)


def _ensure_column(connection: sqlite3.Connection, table: str, name: str, declaration: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if name not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")


def _taxonomy_id(connection: sqlite3.Connection, key: str) -> int:
    row = connection.execute("SELECT id FROM taxonomies WHERE key=?", (key,)).fetchone()
    if row is None:
        now = utc_now()
        cursor = connection.execute(
            "INSERT INTO taxonomies(key,label,max_depth,created_at,updated_at) VALUES(?,?,?,?,?)",
            (key, key.replace("_", " ").title(), 3, now, now),
        )
        return int(cursor.lastrowid)
    return int(row["id"])


def _seed_entry(connection, taxonomy_key, key, label, parent_key=None, archived=False, order=0):
    taxonomy_id = _taxonomy_id(connection, taxonomy_key)
    parent_id = None
    if parent_key:
        parent = connection.execute(
            "SELECT id FROM taxonomy_entries WHERE taxonomy_id=? AND key=?", (taxonomy_id, parent_key)
        ).fetchone()
        parent_id = int(parent["id"])
    now = utc_now()
    connection.execute(
        """INSERT INTO taxonomy_entries(taxonomy_id,parent_id,key,label,sort_order,archived_at,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(taxonomy_id,key) DO NOTHING""",
        (taxonomy_id, parent_id, key, label, order, now if archived else "", now, now),
    )
    return int(connection.execute(
        "SELECT id FROM taxonomy_entries WHERE taxonomy_id=? AND key=?", (taxonomy_id, key)
    ).fetchone()["id"])


def seed_taxonomies(connection: sqlite3.Connection) -> None:
    organisation = (
        ("business", "Business", None), ("finance", "Finance", "business"), ("bank", "Bank", "finance"),
        ("health_business", "Health", "business"), ("doctors_practice", "Doctor's Practice", "health_business"),
        ("government_agency", "Government Agency", None),
        ("educational_institution", "Educational Institution", None), ("school", "School", "educational_institution"),
        ("university", "University", "educational_institution"), ("nonprofit", "Nonprofit", None),
        ("charity", "Charity", "nonprofit"), ("community_organisation", "Community Organisation", None),
        ("club", "Club", "community_organisation"), ("political_organisation", "Political Organisation", None),
        ("political_party", "Political Party", "political_organisation"), ("other", "Other", None),
    )
    for order, (key, label, parent) in enumerate(organisation):
        _seed_entry(connection, "organisation_classification", key, label, parent, order=order)

    from app.relationship_catalog import RELATIONSHIP_TYPES
    paths = _relationship_paths()
    created = set()
    for item in RELATIONSHIP_TYPES:
        root, middle, leaf = paths.get(item.key, (item.category.replace("Legacy / ", "Legacy"), "", item.subtype or item.label))
        root_key = "group_" + _slug(root)
        if root_key not in created:
            _seed_entry(connection, "relationship_type", root_key, root, archived=root.startswith("Legacy"))
            created.add(root_key)
        parent_key = root_key
        if middle:
            middle_key = root_key + "__" + _slug(middle)
            if middle_key not in created:
                _seed_entry(connection, "relationship_type", middle_key, middle, root_key, archived=root.startswith("Legacy"))
                created.add(middle_key)
            parent_key = middle_key
        leaf = leaf or item.subtype or item.label
        parent_row = connection.execute("SELECT id FROM taxonomy_entries WHERE taxonomy_id=? AND key=?", (_taxonomy_id(connection, "relationship_type"), parent_key)).fetchone()
        duplicate = connection.execute("SELECT 1 FROM taxonomy_entries WHERE taxonomy_id=? AND parent_id=? AND label=? COLLATE NOCASE", (_taxonomy_id(connection, "relationship_type"), parent_row["id"], leaf)).fetchone()
        if duplicate:
            leaf = f"{leaf} ({item.source_type.title()}–{item.target_type.title()})"
        entry_id = _seed_entry(connection, "relationship_type", item.key, leaf, parent_key, archived=not item.selectable)
        role_source = item.role_labels[0] if item.role_labels else None
        role_target = item.role_labels[1] if item.role_labels else None
        display_source = item.display_labels[0] if item.display_labels else None
        display_target = item.display_labels[1] if item.display_labels else None
        connection.execute(
            """INSERT INTO relationship_type_definitions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(taxonomy_entry_id) DO NOTHING""",
            (entry_id, item.source_type, item.target_type, int(item.directional),
             role_source.neutral if role_source else item.subtype or item.label,
             role_target.neutral if role_target else item.subtype or item.label,
             display_source.neutral if display_source else item.label,
             display_target.neutral if display_target else item.inverse_label,
             role_source.male if role_source else "", role_source.female if role_source else "",
             role_target.male if role_target else "", role_target.female if role_target else "",
             display_source.male if display_source else "", display_source.female if display_source else "",
             display_target.male if display_target else "", display_target.female if display_target else "",
             item.notes, int(item.selectable),),
        )


def _relationship_paths() -> dict[str, tuple[str, str, str]]:
    groups = {
        "Family": {"Immediate": ["parent_child", "sibling_of", "spouse_of", "partner_of"], "Extended": ["grandparent_child", "aunt_uncle_niece_nephew", "cousin_of"], "Other": ["family_other"]},
        "Work": {"Peer": ["coworker_of", "team_member_of"], "Reporting": ["manager_person"]},
        "Education": {"Teaching": ["student_teacher", "classmate_of"], "Enrollment": ["student_at"]},
        "Health": {"Care": ["clinician_patient"]},
        "Social": {"": ["friend_of", "knows"]},
        "Role": {"Employment": ["works_for", "manager_at", "director_of"], "Volunteering": ["volunteer_for"]},
        "Membership": {"": ["member_of"]}, "Service": {"": ["patient_client_of", "customer_of"]},
        "Ownership": {"": ["owner_of"]},
    }
    labels = {"parent_child":"Parent", "grandparent_child":"Grandparent", "aunt_uncle_niece_nephew":"Aunt/Uncle", "team_member_of":"Teammate", "knows":"Acquaintance", "works_for":"Employee", "patient_client_of":"Patient"}
    result = {}
    for root, middles in groups.items():
        for middle, keys in middles.items():
            for key in keys:
                result[key] = (root, middle, labels.get(key, ""))
    return result


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_") or "other"


ORG_LEGACY_MAP = {
    "Business": "business", "Government agency": "government_agency", "School": "school",
    "University": "university", "Medical practice": "doctors_practice", "Bank": "bank",
    "Club": "club", "Charity": "charity", "Political party": "political_party", "Other": "other",
}


def migrate_taxonomy_assignments(connection: sqlite3.Connection) -> None:
    taxonomy_id = _taxonomy_id(connection, "organisation_classification")
    for row in connection.execute("SELECT entity_id, organisation_type FROM organisations WHERE taxonomy_entry_id IS NULL AND organisation_type<>''").fetchall():
        value = row["organisation_type"]
        key = ORG_LEGACY_MAP.get(value)
        if key is None:
            key = "legacy_" + _slug(value)
            _seed_entry(connection, "organisation_classification", key, value, archived=True)
        entry = connection.execute("SELECT id FROM taxonomy_entries WHERE taxonomy_id=? AND key=?", (taxonomy_id, key)).fetchone()
        connection.execute("UPDATE organisations SET taxonomy_entry_id=? WHERE entity_id=?", (entry["id"], row["entity_id"]))
    relationship_taxonomy_id = _taxonomy_id(connection, "relationship_type")
    connection.execute(
        """UPDATE relationships SET taxonomy_entry_id=(SELECT id FROM taxonomy_entries
           WHERE taxonomy_id=? AND key=relationships.type) WHERE taxonomy_entry_id IS NULL""", (relationship_taxonomy_id,)
    )


def list_entries(connection, taxonomy_key: str, include_archived: bool = False) -> list[TaxonomyEntry]:
    rows = connection.execute(
        """WITH RECURSIVE paths(id,path,ancestor_archived) AS (
             SELECT e.id,e.label,(e.archived_at<>'') FROM taxonomy_entries e JOIN taxonomies t ON t.id=e.taxonomy_id WHERE t.key=? AND e.parent_id IS NULL
             UNION ALL SELECT e.id,paths.path||' › '||e.label,(paths.ancestor_archived OR e.archived_at<>'') FROM taxonomy_entries e JOIN paths ON e.parent_id=paths.id)
           SELECT e.*,t.key taxonomy_key,paths.path,paths.ancestor_archived FROM taxonomy_entries e JOIN taxonomies t ON t.id=e.taxonomy_id JOIN paths ON paths.id=e.id
           WHERE t.key=? AND (? OR NOT paths.ancestor_archived) ORDER BY e.sort_order,lower(paths.path)""",
        (taxonomy_key, taxonomy_key, int(include_archived)),
    ).fetchall()
    return [TaxonomyEntry(int(r["id"]), r["taxonomy_key"], r["key"], r["label"], r["parent_id"], len(r["path"].split(" › "))-1, r["archived_at"] or ("ancestor" if r["ancestor_archived"] else ""), r["path"]) for r in rows]


def get_entry(connection, entry_id: int) -> TaxonomyEntry | None:
    for taxonomy in ("organisation_classification", "relationship_type"):
        for entry in list_entries(connection, taxonomy, include_archived=True):
            if entry.id == entry_id:
                return entry
    return None


def create_entry(connection, taxonomy_key: str, label: str, parent_id: int | None = None, relationship=None) -> int:
    label = label.strip()
    if not label:
        raise ValueError("Label is required.")
    taxonomy = connection.execute("SELECT id FROM taxonomies WHERE key=?", (taxonomy_key,)).fetchone()
    if taxonomy is None:
        raise ValueError("Taxonomy is invalid.")
    taxonomy_id = int(taxonomy["id"])
    parent = get_entry(connection, parent_id) if parent_id else None
    if parent_id and parent is None:
        raise ValueError("Parent is invalid.")
    if parent and (parent.taxonomy_key != taxonomy_key or parent.depth >= 2 or not parent.active):
        raise ValueError("Parent is invalid or already at the third level.")
    key = "custom_" + _slug(label)
    suffix = 2
    while connection.execute("SELECT 1 FROM taxonomy_entries WHERE taxonomy_id=? AND key=?", (taxonomy_id, key)).fetchone():
        key = "custom_" + _slug(label) + f"_{suffix}"; suffix += 1
    entry_id = _seed_entry(connection, taxonomy_key, key, label, parent.key if parent else None)
    if taxonomy_key == "relationship_type":
        if not relationship:
            raise ValueError("Relationship metadata is required.")
        from app.entities import DEFINITIONS_BY_TYPE
        source_type = relationship.get("source_entity_type", "")
        target_type = relationship.get("target_entity_type", "")
        labels = [relationship.get(name, "").strip() for name in ("source_role", "target_role", "source_label", "target_label")]
        if source_type not in DEFINITIONS_BY_TYPE or target_type not in DEFINITIONS_BY_TYPE:
            raise ValueError("Relationship endpoint types are invalid.")
        if not all(labels):
            raise ValueError("Relationship roles and display phrases are required.")
        directional = int(relationship.get("directional", "1") == "1")
        connection.execute(
            """INSERT INTO relationship_type_definitions(taxonomy_entry_id,source_entity_type,target_entity_type,directional,source_role,target_role,source_label,target_label)
               VALUES(?,?,?,?,?,?,?,?)""",
            (entry_id, source_type, target_type, directional, *labels),
        )
    from app.audit import record_audit_event
    record_audit_event(connection, "create", [("taxonomy_entry", entry_id)], after={"taxonomy": taxonomy_key, "label": label})
    return entry_id


def archive_entry(connection, entry_id: int) -> None:
    entry = get_entry(connection, entry_id)
    if entry is None: raise ValueError("Taxonomy entry not found.")
    connection.execute("UPDATE taxonomy_entries SET archived_at=?,updated_at=? WHERE id=?", (utc_now(), utc_now(), entry_id))
    from app.audit import record_audit_event
    record_audit_event(connection, "edit", [("taxonomy_entry", entry_id)], before={"archived": False}, after={"archived": True})


def reparent_entry(connection, entry_id: int, parent_id: int | None) -> None:
    entry = get_entry(connection, entry_id)
    parent = get_entry(connection, parent_id) if parent_id else None
    if entry is None or (parent_id and parent is None) or (parent and parent.taxonomy_key != entry.taxonomy_key):
        raise ValueError("Taxonomy entry or parent is invalid.")
    if parent and not parent.active:
        raise ValueError("Archived entries cannot be parents.")
    cursor = parent
    while cursor is not None:
        if cursor.id == entry_id:
            raise ValueError("Taxonomy hierarchy cannot contain a cycle.")
        cursor = get_entry(connection, cursor.parent_id) if cursor.parent_id else None
    new_depth = (parent.depth + 1) if parent else 0
    descendants = [item for item in list_entries(connection, entry.taxonomy_key, include_archived=True) if item.path.startswith(entry.path + " › ")]
    relative_depth = max((item.depth - entry.depth for item in descendants), default=0)
    if new_depth + relative_depth > 2:
        raise ValueError("Taxonomy paths cannot exceed three levels.")
    connection.execute("UPDATE taxonomy_entries SET parent_id=?,updated_at=? WHERE id=?", (parent_id, utc_now(), entry_id))


def organisation_options(connection, include_entry_id: int | None = None):
    entries = list_entries(connection, "organisation_classification")
    if include_entry_id and all(e.id != include_entry_id for e in entries):
        entry = get_entry(connection, include_entry_id)
        if entry:
            existing = {item.id for item in entries}
            for candidate in list_entries(connection, "organisation_classification", include_archived=True):
                if candidate.id not in existing and (entry.path == candidate.path or entry.path.startswith(candidate.path + " › ")):
                    entries.append(candidate)
    return [(str(e.id), e.path) for e in entries]


def assign_organisation_value(connection, entity_id: int, value: str) -> None:
    if value.isdecimal():
        connection.execute("UPDATE organisations SET taxonomy_entry_id=? WHERE entity_id=?", (int(value), entity_id))
        return
    if not value:
        connection.execute("UPDATE organisations SET taxonomy_entry_id=NULL WHERE entity_id=?", (entity_id,))
        return
    key = ORG_LEGACY_MAP.get(value, "legacy_" + _slug(value))
    if key not in ORG_LEGACY_MAP.values():
        _seed_entry(connection, "organisation_classification", key, value, archived=True)
    taxonomy_id = _taxonomy_id(connection, "organisation_classification")
    entry_id = connection.execute("SELECT id FROM taxonomy_entries WHERE taxonomy_id=? AND key=?", (taxonomy_id, key)).fetchone()["id"]
    connection.execute("UPDATE organisations SET organisation_type=?,taxonomy_entry_id=? WHERE entity_id=?", (value, entry_id, entity_id))


def hydrate_organisation_taxonomy(connection, record) -> None:
    if record.type != "organisation": return
    row = connection.execute("SELECT taxonomy_entry_id,organisation_type FROM organisations WHERE entity_id=?", (record.id,)).fetchone()
    if not row: return
    entry = get_entry(connection, row["taxonomy_entry_id"]) if row["taxonomy_entry_id"] else None
    record.metadata["organisation_type"] = entry.path if entry else row["organisation_type"]
    record.metadata["organisation_type__taxonomy_entry_id"] = str(entry.id) if entry else ""


def load_relationship_catalog(connection) -> None:
    from app.relationship_catalog import LabelSet, RelationshipType, RELATIONSHIP_TYPES_BY_KEY
    rows = connection.execute(
        """SELECT e.key,e.label,e.archived_at,d.* FROM taxonomy_entries e JOIN taxonomies t ON t.id=e.taxonomy_id
           JOIN relationship_type_definitions d ON d.taxonomy_entry_id=e.id WHERE t.key='relationship_type'"""
    ).fetchall()
    active_ids = {entry.id for entry in list_entries(connection, "relationship_type")}
    for r in rows:
        previous = RELATIONSHIP_TYPES_BY_KEY.get(r["key"])
        roles = (LabelSet(r["source_role"],r["source_role_male"],r["source_role_female"]), LabelSet(r["target_role"],r["target_role_male"],r["target_role_female"]))
        labels = (LabelSet(r["source_label"],r["source_label_male"],r["source_label_female"]), LabelSet(r["target_label"],r["target_label_male"],r["target_label_female"]))
        category = previous.category if previous else "Other"
        RELATIONSHIP_TYPES_BY_KEY[r["key"]] = RelationshipType(r["key"],r["source_entity_type"],r["target_entity_type"],category,r["label"],r["source_label"],r["target_label"],bool(r["directional"]),r["notes"],bool(r["selectable"] and int(r["taxonomy_entry_id"]) in active_ids),roles,labels)
