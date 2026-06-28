import json
import sqlite3
import unittest

from app.db_schema import create_schema
from app.db_support import utc_now
from app.relationship_inference import list_review_batches, recompute_inferences, review_suggestion, undo_suggestion_review
from app.relationship_repository import create_relationship, delete_relationship, get_relationship, list_relationships, update_relationship
from app.view_pages.relationships import inference_review_page


class RelationshipInferenceTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        create_schema(self.connection)

    def tearDown(self):
        self.connection.close()

    def person(self, name, birthday="", sex="Unknown"):
        now = utc_now()
        cursor = self.connection.execute("INSERT INTO entities(type,display_name,created_at,updated_at) VALUES('person',?,?,?)", (name, now, now))
        entity_id = cursor.lastrowid
        self.connection.execute("INSERT INTO people(entity_id,given_name,sex,birthday) VALUES(?,?,?,?)", (entity_id, name, sex, birthday))
        return entity_id

    def parent(self, parent, child):
        return create_relationship(self.connection, {"source_entity_id": str(parent), "target_entity_id": str(child), "type": "parent_child"})

    def pending(self):
        return [item for _, items in list_review_batches(self.connection) for item in items if item.status == "pending"]

    def test_generates_safe_bloodline_rules_with_dates_and_no_active_inferences(self):
        gp1, gp2 = self.person("GP1"), self.person("GP2")
        p1, p2 = self.person("P1"), self.person("P2")
        c1, c2 = self.person("C1", "2020-01-02"), self.person("C2", "2022-03-04")
        for parent, child in ((gp1,p1),(gp2,p1),(gp1,p2),(gp2,p2),(p1,c1),(p2,c2)):
            self.parent(parent, child)
        suggestions = self.pending()
        keys = {(x.type_key, x.source.id, x.target.id) for x in suggestions}
        self.assertIn(("sibling_of", min(p1,p2), max(p1,p2)), keys)
        self.assertIn(("aunt_uncle_niece_nephew", p2, c1), keys)
        self.assertIn(("cousin_of", min(c1,c2), max(c1,c2)), keys)
        grandchild = next(x for x in suggestions if x.type_key == "grandparent_child" and x.target.id == c1)
        self.assertEqual(grandchild.started_at, "2020-01-02")
        self.assertGreaterEqual(len(grandchild.supporting_relationship_ids), 2)
        self.assertEqual(self.connection.execute("SELECT count(*) FROM relationships WHERE record_origin='inferred'").fetchone()[0], 0)

    def test_confirmation_creates_editable_relationship_with_audit_provenance(self):
        gp, parent, child = self.person("GP"), self.person("Parent"), self.person("Child", "2020-01-02")
        upper, lower = self.parent(gp, parent), self.parent(parent, child)
        item = next(x for x in self.pending() if x.type_key == "grandparent_child")
        review_suggestion(self.connection, item.id, "confirm")
        row = self.connection.execute("SELECT id, provenance_json FROM relationships WHERE inference_suggestion_id=?", (item.id,)).fetchone()
        record = get_relationship(self.connection, row["id"])
        self.assertEqual(record.record_origin, "manual")
        self.assertTrue(record.created_from_inference)
        self.assertEqual(record.inference_evidence_status, "current")
        provenance = json.loads(row["provenance_json"])
        self.assertEqual(provenance["supporting_relationship_ids"], [upper, lower])
        self.assertEqual(provenance["source_batch_id"], item.batch_id)
        self.assertTrue(provenance["confirmed_at"])
        values = record.to_form_values(); values["notes"] = "User corrected details"
        update_relationship(self.connection, record.id, values)
        self.assertEqual(get_relationship(self.connection, record.id).notes, "User corrected details")
        delete_relationship(self.connection, record.id)
        self.assertIsNone(get_relationship(self.connection, record.id))

    def test_rejection_is_suppressed_until_evidence_changes(self):
        gp, parent, child = self.person("GP"), self.person("Parent"), self.person("Child", "2020-01-02")
        self.parent(gp, parent); self.parent(parent, child)
        item = next(x for x in self.pending() if x.type_key == "grandparent_child")
        review_suggestion(self.connection, item.id, "reject")
        recompute_inferences(self.connection)
        self.assertFalse(self.pending())
        self.connection.execute("UPDATE people SET birthday='2021-02-03' WHERE entity_id=?", (child,))
        recompute_inferences(self.connection, "person_date_updated", child)
        replacement = next(x for x in self.pending() if x.type_key == "grandparent_child")
        self.assertNotEqual(replacement.evidence_fingerprint, item.evidence_fingerprint)

    def test_support_removal_flags_but_preserves_confirmed_relationship(self):
        gp, parent, child = self.person("GP"), self.person("Parent"), self.person("Child")
        upper = self.parent(gp, parent); self.parent(parent, child)
        item = next(x for x in self.pending() if x.type_key == "grandparent_child")
        review_suggestion(self.connection, item.id, "confirm")
        confirmed_id = self.connection.execute("SELECT id FROM relationships WHERE inference_suggestion_id=?", (item.id,)).fetchone()[0]
        delete_relationship(self.connection, upper)
        self.assertEqual(self.connection.execute("SELECT status FROM inference_suggestions WHERE id=?", (item.id,)).fetchone()[0], "confirmed")
        record = get_relationship(self.connection, confirmed_id)
        self.assertIsNotNone(record)
        self.assertEqual(record.inference_evidence_status, "changed")

    def test_conflicts_cycles_self_and_half_siblings_are_not_suggested(self):
        a,b,c,d = [self.person(name) for name in "ABCD"]
        self.parent(a,c); self.parent(b,c); self.parent(a,d)
        self.assertFalse(any(x.type_key == "sibling_of" and {x.source.id,x.target.id} == {c,d} for x in self.pending()))
        self.parent(c,a)
        self.assertFalse(any(x.source.id == x.target.id for x in self.pending()))

    def test_batch_auto_archives_after_final_review_and_rejection_can_be_undone(self):
        gp, parent, child = self.person("GP"), self.person("Parent"), self.person("Child")
        self.parent(gp,parent); self.parent(parent,child)
        batch, items = list_review_batches(self.connection)[0]
        for item in items:
            review_suggestion(self.connection, item.id, "reject")
        stored = self.connection.execute("SELECT status,dismissed_at FROM inference_batches WHERE id=?", (batch["id"],)).fetchone()
        self.assertEqual(stored["status"], "dismissed")
        self.assertTrue(stored["dismissed_at"])
        self.assertFalse(list_review_batches(self.connection))
        undo_suggestion_review(self.connection, items[0].id)
        self.assertEqual(self.connection.execute("SELECT status FROM inference_batches WHERE id=?", (batch["id"],)).fetchone()[0], "open")
        self.assertEqual(self.connection.execute("SELECT status FROM inference_suggestions WHERE id=?", (items[0].id,)).fetchone()[0], "pending")

    def test_undo_confirmation_removes_created_relationship_and_reopens_batch(self):
        gp, parent, child = self.person("GP"), self.person("Parent"), self.person("Child")
        self.parent(gp,parent); self.parent(parent,child)
        item = next(x for x in self.pending() if x.type_key == "grandparent_child")
        review_suggestion(self.connection, item.id, "confirm")
        self.assertTrue(self.connection.execute("SELECT 1 FROM relationships WHERE inference_suggestion_id=?", (item.id,)).fetchone())
        undo_suggestion_review(self.connection, item.id)
        self.assertFalse(self.connection.execute("SELECT 1 FROM relationships WHERE inference_suggestion_id=?", (item.id,)).fetchone())
        self.assertEqual(self.connection.execute("SELECT status FROM inference_suggestions WHERE id=?", (item.id,)).fetchone()[0], "pending")
        self.assertTrue(list_review_batches(self.connection))

    def test_review_queue_shows_one_pending_card_then_advances(self):
        gp1, gp2, parent, child = (self.person("GP1"), self.person("GP2"), self.person("Parent"), self.person("Child"))
        self.parent(gp1, parent); self.parent(gp2, parent); self.parent(parent, child)
        batches = list_review_batches(self.connection)
        pending = [item for _, items in batches for item in items if item.status == "pending" and item.type_key == "grandparent_child"]
        relationships = {item.id: item for item in list_relationships(self.connection)}
        html = inference_review_page(batches, relationships)
        self.assertIn("Suggestion 1 of 2", html)
        self.assertIn(pending[0].source.title, html)
        self.assertNotIn(f'<h3>{pending[1].source.title}', html)
        review_suggestion(self.connection, pending[0].id, "reject")
        html = inference_review_page(list_review_batches(self.connection), relationships)
        self.assertIn("Suggestion 2 of 2", html)
        self.assertIn(pending[1].source.title, html)

    def test_history_section_exposes_undo_for_completed_decisions(self):
        gp, parent, child = self.person("GP"), self.person("Parent"), self.person("Child")
        self.parent(gp,parent); self.parent(parent,child)
        item = next(x for x in self.pending() if x.type_key == "grandparent_child")
        review_suggestion(self.connection, item.id, "reject")
        all_batches = list_review_batches(self.connection, include_closed=True)
        history = [(batch, items) for batch, items in all_batches if batch["status"] == "dismissed"]
        html = inference_review_page([], {r.id: r for r in list_relationships(self.connection)}, history)
        self.assertIn("Show archived batches (1)", html)
        self.assertIn('id="inference-history" hidden', html)
        self.assertNotIn("<details", html)
        self.assertIn("<section class=\"history-batch\">", html)
        self.assertIn(f'/relationships/inferences/{item.id}/undo', html)
        self.assertIn("rejected", html)

    def test_reconciliation_recovers_parent_chain_created_outside_repository_hooks(self):
        gp, parent, child = self.person("GP"), self.person("Parent"), self.person("Child")
        now = utc_now()
        for source, target in ((gp, parent), (parent, child)):
            self.connection.execute("""INSERT INTO relationships
                (source_entity_id,target_entity_id,type,status,created_at,updated_at)
                VALUES(?,?,'parent_child','active',?,?)""", (source, target, now, now))
        self.connection.commit()
        self.assertFalse(self.pending())
        recompute_inferences(self.connection, "queue_reconciliation")
        self.assertTrue(any(item.type_key == "grandparent_child" and item.source.id == gp and item.target.id == child for item in self.pending()))


if __name__ == "__main__":
    unittest.main()
