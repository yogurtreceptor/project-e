import http.client
import tempfile
import threading
import unittest
from pathlib import Path

from app.db import connect, create_entity, create_relationship, initialise_database, list_relationships_for_entity, search_entities
from app.entities import DEFINITIONS_BY_TYPE
from app.task_service import (TaskInput, TaskListInput, TaskSessionInput, add_task_session, archive_task_list, complete_task,
    create_task, create_task_list, get_task, list_task_lists, list_tasks,
    reopen_task, set_default_task_list, list_task_sessions)
from app.web import EddyRequestHandler, ThreadingHTTPServer


class TaskServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.directory.name) / "tasks.sqlite3"
        initialise_database(self.database_path)
        self.connection = connect(self.database_path)

    def tearDown(self):
        self.connection.close()
        self.directory.cleanup()

    def test_default_list_and_task_lifecycle_preserve_canonical_identity(self):
        default = list_task_lists(self.connection)[0]
        self.assertEqual("Tasks", default.name)
        task_id = create_task(self.connection, TaskInput("Prepare agenda", notes="Bring draft"))
        task = get_task(self.connection, task_id)
        self.assertEqual(default.id, task.task_list_id)
        self.assertEqual("open", task.status)
        self.assertTrue(complete_task(self.connection, task_id))
        self.assertEqual([], list_tasks(self.connection))
        completed = list_tasks(self.connection, include_completed=True)
        self.assertEqual([task_id], [item.id for item in completed])
        self.assertTrue(get_task(self.connection, task_id).completed_at)
        self.assertTrue(reopen_task(self.connection, task_id))
        self.assertEqual("", get_task(self.connection, task_id).completed_at)

    def test_archived_list_retains_tasks_but_rejects_new_assignment(self):
        work_id = create_task_list(self.connection, TaskListInput("Work"))
        task_id = create_task(self.connection, TaskInput("Existing", work_id))
        self.assertTrue(archive_task_list(self.connection, work_id))
        self.assertEqual(work_id, get_task(self.connection, task_id).task_list_id)
        with self.assertRaisesRegex(ValueError, "Archived Task list"):
            create_task(self.connection, TaskInput("Unsafe", work_id))

    def test_tasks_use_normal_relationships_and_global_search(self):
        task_id = create_task(self.connection, TaskInput("Prepare launch"))
        project_id = create_entity(self.connection, DEFINITIONS_BY_TYPE["project"], {"display_name": "Launch", "summary": "", "notes": "", "project_type": "", "status": "Active", "started_at": "", "target_date": "", "ended_at": ""})
        create_relationship(self.connection, {"source_entity_id": str(task_id), "target_entity_id": str(project_id), "type": "task_related_to_project"})
        self.connection.commit()
        self.assertEqual([task_id], [result["entity"].id for result in search_entities(self.connection, "prepare", entity_type="task")])
        self.assertEqual("task_related_to_project", list_relationships_for_entity(self.connection, task_id)[0].type_key)

    def test_deadlines_and_sessions_use_shared_temporal_contract(self):
        task_id = create_task(self.connection, TaskInput("Book venue", deadline_date="2026-08-10"))
        self.assertEqual("2026-08-10", get_task(self.connection, task_id).deadline_date)
        add_task_session(self.connection, task_id, TaskSessionInput(False, start_local="2026-08-01T09:00", end_local="2026-08-01T10:00"))
        self.assertEqual(1, len(list_task_sessions(self.connection, task_id)))
        complete_task(self.connection, task_id)
        self.assertEqual([], list_task_sessions(self.connection, task_id))

    def test_calendar_originates_undated_task_creation(self):
        EddyRequestHandler.database_path = self.database_path
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            client = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            client.request("GET", "/calendar/tasks/new")
            response = client.getresponse()
            self.assertEqual(200, response.status)
            self.assertIn("Add Task", response.read().decode())
            client.request("POST", "/calendar/tasks/new", "title=Undated+Task&task_list_id=1&notes=", {"Content-Type": "application/x-www-form-urlencoded"})
            response = client.getresponse()
            self.assertEqual(303, response.status)
            self.assertTrue(response.getheader("Location").startswith("/tasks/"))
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == "__main__":
    unittest.main()
