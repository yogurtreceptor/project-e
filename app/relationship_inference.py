"""Deterministic family inference and human review lifecycle."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass

from app.db_support import utc_now
from app.entity_repository import get_entity_by_id


@dataclass(frozen=True)
class Candidate:
    type_key: str
    source_id: int
    target_id: int
    rule_key: str
    support_ids: tuple[int, ...]
    started_at: str = ""

    @property
    def key(self) -> tuple[str, int, int]:
        return self.type_key, self.source_id, self.target_id


@dataclass(frozen=True)
class InferenceSuggestion:
    id: int
    batch_id: int
    type_key: str
    source: object
    target: object
    started_at: str
    started_at_precision: str
    status: str
    source_type: str
    rule_key: str
    supporting_relationship_ids: tuple[int, ...]
    evidence_fingerprint: str
    created_at: str
    reviewed_at: str


class InferenceRule:
    key = ""
    def infer(self, facts: "FamilyFacts") -> list[Candidate]:
        raise NotImplementedError


class FamilyFacts:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        rows = connection.execute("""
            SELECT r.* FROM relationships r JOIN entities s ON s.id=r.source_entity_id
            JOIN entities t ON t.id=r.target_entity_id
            WHERE r.status='active' AND s.type='person' AND t.type='person'
              AND (r.record_origin='manual' OR r.record_origin='inferred')
        """).fetchall()
        self.rows = {int(r["id"]): r for r in rows}
        self.parents: dict[int, dict[int, int]] = {}
        for r in rows:
            if r["type"] == "parent_child":
                self.parents.setdefault(int(r["target_entity_id"]), {})[int(r["source_entity_id"])] = int(r["id"])
        self.people = {int(r["id"]): r for r in connection.execute("SELECT e.id, p.birthday FROM entities e JOIN people p ON p.entity_id=e.id WHERE e.type='person'")}

    def birth(self, person_id: int) -> str:
        row = self.people.get(person_id)
        return row["birthday"] if row else ""

    def relationship_start(self, first_id: int, second_id: int) -> str:
        """Return the lower DOB only when both related people have one."""
        first = self.birth(first_id)
        second = self.birth(second_id)
        return min(first, second) if first and second else ""

    def is_ancestor(self, ancestor: int, descendant: int) -> bool:
        seen = set()
        stack = [descendant]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            for parent in self.parents.get(node, {}):
                if parent == ancestor:
                    return True
                stack.append(parent)
        return False

    def full_siblings(self) -> dict[tuple[int, int], tuple[int, ...]]:
        result = {}
        children = sorted(self.parents)
        for i, first in enumerate(children):
            first_parents = set(self.parents[first])
            if len(first_parents) < 2:
                continue
            for second in children[i + 1:]:
                second_parents = set(self.parents[second])
                if first_parents == second_parents:
                    ids = tuple(sorted(self.parents[first].values()) + sorted(self.parents[second].values()))
                    result[(first, second)] = ids
        return result


class GrandparentRule(InferenceRule):
    key = "grandparent_via_parent"
    def infer(self, facts):
        out = []
        for child, parent_map in facts.parents.items():
            for parent, lower_id in parent_map.items():
                for grandparent, upper_id in facts.parents.get(parent, {}).items():
                    if grandparent != child:
                        out.append(Candidate("grandparent_child", grandparent, child, self.key, tuple(sorted((upper_id, lower_id))), facts.relationship_start(grandparent, child)))
        return out


class SiblingRule(InferenceRule):
    key = "full_sibling_shared_parents"
    def infer(self, facts):
        return [Candidate("sibling_of", a, b, self.key, ids, facts.relationship_start(a, b)) for (a, b), ids in facts.full_siblings().items()]


class AuntUncleRule(InferenceRule):
    key = "full_sibling_of_parent"
    def infer(self, facts):
        out = []
        for (a, b), sibling_ids in facts.full_siblings().items():
            for parent, relative in ((a, b), (b, a)):
                for child, parent_map in facts.parents.items():
                    if parent in parent_map and child != relative:
                        out.append(Candidate("aunt_uncle_niece_nephew", relative, child, self.key, tuple(sorted((*sibling_ids, parent_map[parent]))), facts.relationship_start(relative, child)))
        return out


class CousinRule(InferenceRule):
    key = "children_of_full_siblings"
    def infer(self, facts):
        out = []
        children_by_parent: dict[int, list[tuple[int, int]]] = {}
        for child, parents in facts.parents.items():
            for parent, rid in parents.items():
                children_by_parent.setdefault(parent, []).append((child, rid))
        for (a, b), sibling_ids in facts.full_siblings().items():
            for first, first_rid in children_by_parent.get(a, []):
                for second, second_rid in children_by_parent.get(b, []):
                    if first != second:
                        x, y = sorted((first, second))
                        out.append(Candidate("cousin_of", x, y, self.key, tuple(sorted((*sibling_ids, first_rid, second_rid))), facts.relationship_start(x, y)))
        return out


RULES: tuple[InferenceRule, ...] = (GrandparentRule(), SiblingRule(), AuntUncleRule(), CousinRule())
SYMMETRIC = {"sibling_of", "cousin_of"}


def _fingerprint(connection: sqlite3.Connection, candidate: Candidate) -> str:
    evidence = []
    for rid in candidate.support_ids:
        row = connection.execute("SELECT id, source_entity_id, target_entity_id, type, status, updated_at FROM relationships WHERE id=?", (rid,)).fetchone()
        if row:
            evidence.append(tuple(row))
    return hashlib.sha256(json.dumps([candidate.key, candidate.rule_key, candidate.started_at, evidence], separators=(",", ":")).encode()).hexdigest()


def _valid_candidate(facts: FamilyFacts, candidate: Candidate) -> bool:
    if candidate.source_id == candidate.target_id or not candidate.support_ids:
        return False
    if candidate.type_key in SYMMETRIC and candidate.source_id > candidate.target_id:
        return False
    if candidate.type_key in {"sibling_of", "cousin_of"} and (facts.is_ancestor(candidate.source_id, candidate.target_id) or facts.is_ancestor(candidate.target_id, candidate.source_id)):
        return False
    # Any manual bloodline statement for the same pair wins over a different inference.
    for row in facts.rows.values():
        pair = {int(row["source_entity_id"]), int(row["target_entity_id"])}
        if row["record_origin"] == "manual" and not row["created_from_inference"] and pair == {candidate.source_id, candidate.target_id}:
            if row["type"] != candidate.type_key:
                return False
            return False
    return True


def recompute_inferences(connection: sqlite3.Connection, trigger_type: str = "manual_change", trigger_id: int | None = None) -> int | None:
    facts = FamilyFacts(connection)
    candidates: dict[tuple[str, int, int], Candidate] = {}
    for rule in RULES:
        for candidate in rule.infer(facts):
            if _valid_candidate(facts, candidate):
                existing = candidates.get(candidate.key)
                if existing is None or candidate.support_ids < existing.support_ids:
                    candidates[candidate.key] = candidate
    fingerprints = {key: _fingerprint(connection, item) for key, item in candidates.items()}
    pending = connection.execute("SELECT * FROM inference_suggestions WHERE status='pending'").fetchall()
    for row in pending:
        key = (row["type"], int(row["source_entity_id"]), int(row["target_entity_id"]))
        if key not in candidates or fingerprints[key] != row["evidence_fingerprint"]:
            connection.execute("UPDATE inference_suggestions SET status='invalidated', reviewed_at=? WHERE id=?", (utc_now(), row["id"]))

    # Confirmation transfers ownership to the normal relationship workflow. Later
    # evidence changes are audit information only: never delete, lock, or rewrite
    # the user's confirmed relationship.
    confirmed = connection.execute("SELECT * FROM inference_suggestions WHERE status='confirmed'").fetchall()
    for row in confirmed:
        key = (row["type"], int(row["source_entity_id"]), int(row["target_entity_id"]))
        evidence_status = "current" if key in candidates and fingerprints[key] == row["evidence_fingerprint"] else "changed"
        connection.execute("UPDATE relationships SET inference_evidence_status=? WHERE inference_suggestion_id=?", (evidence_status, row["id"]))
    new_items = []
    for key, candidate in candidates.items():
        fingerprint = fingerprints[key]
        prior = connection.execute("SELECT 1 FROM inference_suggestions WHERE type=? AND source_entity_id=? AND target_entity_id=? AND evidence_fingerprint=? AND status IN ('pending','confirmed','rejected')", (*key, fingerprint)).fetchone()
        relationship = connection.execute("SELECT 1 FROM relationships WHERE type=? AND source_entity_id=? AND target_entity_id=? AND status='active'", key).fetchone()
        if not prior and not relationship:
            new_items.append((candidate, fingerprint))
    batch_id = None
    if new_items:
        now = utc_now()
        cursor = connection.execute("INSERT INTO inference_batches(trigger_type, trigger_id, created_at) VALUES(?,?,?)", (trigger_type, trigger_id, now))
        batch_id = int(cursor.lastrowid)
        for candidate, fingerprint in new_items:
            connection.execute("""INSERT INTO inference_suggestions
                (batch_id,type,source_entity_id,target_entity_id,started_at,rule_key,supporting_relationship_ids,evidence_fingerprint,created_at)
                VALUES(?,?,?,?,?,?,?,?,?)""", (batch_id, candidate.type_key, candidate.source_id, candidate.target_id, candidate.started_at, candidate.rule_key, json.dumps(candidate.support_ids), fingerprint, now))
    _close_reviewed_batches(connection)
    connection.commit()
    return batch_id


def list_review_batches(connection: sqlite3.Connection, include_closed: bool = False):
    where = "" if include_closed else "WHERE b.status='open'"
    batches = []
    for batch in connection.execute(f"SELECT b.* FROM inference_batches b {where} ORDER BY b.id DESC"):
        items = [to_suggestion(connection, row) for row in connection.execute("SELECT * FROM inference_suggestions WHERE batch_id=? ORDER BY id", (batch["id"],))]
        batches.append((dict(batch), items))
    return batches


def get_suggestion(connection: sqlite3.Connection, suggestion_id: int):
    row = connection.execute("SELECT * FROM inference_suggestions WHERE id=?", (suggestion_id,)).fetchone()
    return to_suggestion(connection, row) if row else None


def to_suggestion(connection, row):
    return InferenceSuggestion(int(row["id"]), int(row["batch_id"]), row["type"], get_entity_by_id(connection, int(row["source_entity_id"])), get_entity_by_id(connection, int(row["target_entity_id"])), row["started_at"], row["started_at_precision"], row["status"], row["source_type"], row["rule_key"], tuple(json.loads(row["supporting_relationship_ids"])), row["evidence_fingerprint"], row["created_at"], row["reviewed_at"])


def review_suggestion(connection: sqlite3.Connection, suggestion_id: int, decision: str) -> int | None:
    if decision not in {"confirm", "reject"}:
        raise ValueError("Invalid inference review decision.")
    row = connection.execute("SELECT * FROM inference_suggestions WHERE id=? AND status='pending'", (suggestion_id,)).fetchone()
    if not row:
        raise ValueError("Suggestion is no longer pending.")
    now = utc_now()
    status = "confirmed" if decision == "confirm" else "rejected"
    connection.execute("UPDATE inference_suggestions SET status=?, reviewed_at=? WHERE id=?", (status, now, suggestion_id))
    if decision == "confirm":
        provenance = json.dumps({"source_type": row["source_type"], "rule_key": row["rule_key"], "supporting_relationship_ids": json.loads(row["supporting_relationship_ids"]), "source_batch_id": row["batch_id"], "evidence_fingerprint": row["evidence_fingerprint"], "inferred_at": row["created_at"], "confirmed_at": now}, sort_keys=True)
        connection.execute("""INSERT INTO relationships
            (source_entity_id,target_entity_id,type,status,started_at,started_at_precision,ended_at,ended_at_precision,notes,created_at,updated_at,record_origin,inference_suggestion_id,provenance_json,created_from_inference,inference_evidence_status)
            VALUES(?,?,?,'active',?,?,'','exact','',?,?, 'manual',?,?,1,'current')""", (row["source_entity_id"], row["target_entity_id"], row["type"], row["started_at"], row["started_at_precision"], now, now, suggestion_id, provenance))
    _close_reviewed_batches(connection)
    connection.commit()
    return recompute_inferences(connection, "inference_confirmation", suggestion_id) if decision == "confirm" else None


def dismiss_batch(connection: sqlite3.Connection, batch_id: int) -> None:
    pending = connection.execute("SELECT 1 FROM inference_suggestions WHERE batch_id=? AND status='pending'", (batch_id,)).fetchone()
    if pending:
        raise ValueError("Review every suggestion before dismissing the batch.")
    connection.execute("UPDATE inference_batches SET status='dismissed', dismissed_at=? WHERE id=?", (utc_now(), batch_id))
    connection.commit()


def undo_suggestion_review(connection: sqlite3.Connection, suggestion_id: int) -> None:
    row = connection.execute("SELECT * FROM inference_suggestions WHERE id=? AND status IN ('confirmed','rejected')", (suggestion_id,)).fetchone()
    if not row:
        raise ValueError("Only confirmed or rejected suggestions can be undone.")
    if row["status"] == "confirmed":
        connection.execute("DELETE FROM relationships WHERE inference_suggestion_id=?", (suggestion_id,))
    connection.execute("UPDATE inference_suggestions SET status='pending', reviewed_at='' WHERE id=?", (suggestion_id,))
    connection.execute("UPDATE inference_batches SET status='open', dismissed_at='' WHERE id=?", (row["batch_id"],))
    connection.commit()
    recompute_inferences(connection, "inference_review_undo", suggestion_id)


def _close_reviewed_batches(connection):
    now = utc_now()
    connection.execute("""UPDATE inference_batches
        SET status='dismissed', dismissed_at=?
        WHERE status='open'
          AND NOT EXISTS (
              SELECT 1 FROM inference_suggestions
              WHERE batch_id=inference_batches.id AND status='pending'
          )""", (now,))
