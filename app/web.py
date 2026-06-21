from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app import views
from app.config import DATABASE_PATH
from app.db import (
    connect,
    count_entities,
    create_entity,
    create_relationship,
    delete_entity,
    delete_relationship,
    get_entity,
    get_entity_by_id,
    get_relationship,
    initialise_database,
    list_all_entities,
    list_entities,
    list_relationships,
    list_relationships_for_entity,
    normalise_form_values,
    normalise_relationship_values,
    update_entity,
    update_relationship,
    validate_entity_values,
    validate_relationship_values,
)
from app.entities import DEFINITIONS_BY_SLUG, EntityDefinition


STATIC_DIR = Path(__file__).resolve().parent / "static"


class EddyRequestHandler(BaseHTTPRequestHandler):
    database_path = DATABASE_PATH

    def do_GET(self) -> None:
        self.route_request()

    def do_POST(self) -> None:
        self.route_request()

    def log_message(self, format: str, *args: object) -> None:
        print("%s - - %s" % (self.address_string(), format % args))

    def route_request(self) -> None:
        parsed = urlparse(self.path)
        parts = [part for part in parsed.path.split("/") if part]
        query = {key: values[0] for key, values in parse_qs(parsed.query).items()}

        if parsed.path.startswith("/static/"):
            self.serve_static(parsed.path.removeprefix("/static/"))
            return

        if not parts:
            self.handle_dashboard()
            return

        if parts[0] == "relationships":
            self.route_relationship_request(parts, query)
            return

        definition = DEFINITIONS_BY_SLUG.get(parts[0])
        if definition is None:
            self.respond_not_found()
            return

        if len(parts) == 1:
            self.handle_list(definition)
        elif len(parts) == 2 and parts[1] == "new":
            self.handle_new(definition)
        elif len(parts) == 2:
            self.handle_detail(definition, parts[1])
        elif len(parts) == 3 and parts[2] == "edit":
            self.handle_edit(definition, parts[1])
        elif len(parts) == 3 and parts[2] == "delete":
            self.handle_delete(definition, parts[1])
        else:
            self.respond_not_found()

    def route_relationship_request(self, parts: list[str], query: dict[str, str]) -> None:
        if len(parts) == 1:
            self.handle_relationship_list()
        elif len(parts) == 2 and parts[1] == "new":
            self.handle_relationship_new(query)
        elif len(parts) == 2:
            self.handle_relationship_detail(parts[1])
        elif len(parts) == 3 and parts[2] == "edit":
            self.handle_relationship_edit(parts[1], query)
        elif len(parts) == 3 and parts[2] == "delete":
            self.handle_relationship_delete(parts[1], query)
        else:
            self.respond_not_found()

    def handle_dashboard(self) -> None:
        with connect(self.database_path) as connection:
            counts = count_entities(connection)
            relationship_count = len(list_relationships(connection))
        self.respond_page("Dashboard", views.dashboard_page(counts, relationship_count))

    def handle_list(self, definition: EntityDefinition) -> None:
        with connect(self.database_path) as connection:
            records = list_entities(connection, definition)
        self.respond_page(
            definition.plural,
            views.entity_list_page(definition, records),
            active_slug=definition.slug,
        )

    def handle_detail(self, definition: EntityDefinition, raw_id: str) -> None:
        entity_id = self.parse_entity_id(raw_id)
        if entity_id is None:
            self.respond_not_found()
            return

        with connect(self.database_path) as connection:
            record = get_entity(connection, definition, entity_id)
            relationships = list_relationships_for_entity(connection, entity_id) if record else []
        if record is None:
            self.respond_not_found()
            return

        self.respond_page(
            record.title,
            views.entity_detail_page(record, relationships),
            active_slug=definition.slug,
        )

    def handle_new(self, definition: EntityDefinition) -> None:
        if self.command == "POST":
            values = normalise_form_values(definition, self.read_form())
            errors = validate_entity_values(definition, values)
            if not errors:
                with connect(self.database_path) as connection:
                    entity_id = create_entity(connection, definition, values)
                self.redirect(f"/{definition.slug}/{entity_id}")
                return
            self.respond_form(definition, values, errors, "Create")
            return

        self.respond_form(definition, {}, [], "Create")

    def handle_edit(self, definition: EntityDefinition, raw_id: str) -> None:
        entity_id = self.parse_entity_id(raw_id)
        if entity_id is None:
            self.respond_not_found()
            return

        with connect(self.database_path) as connection:
            record = get_entity(connection, definition, entity_id)
        if record is None:
            self.respond_not_found()
            return

        if self.command == "POST":
            values = normalise_form_values(definition, self.read_form())
            errors = validate_entity_values(definition, values)
            if not errors:
                with connect(self.database_path) as connection:
                    update_entity(connection, definition, entity_id, values)
                self.redirect(f"/{definition.slug}/{entity_id}")
                return
            self.respond_form(definition, values, errors, "Edit", entity_id)
            return

        self.respond_form(definition, record.to_form_values(), [], "Edit", entity_id)

    def handle_delete(self, definition: EntityDefinition, raw_id: str) -> None:
        if self.command != "POST":
            self.respond_not_found()
            return
        entity_id = self.parse_entity_id(raw_id)
        if entity_id is None:
            self.respond_not_found()
            return
        with connect(self.database_path) as connection:
            delete_entity(connection, definition, entity_id)
        self.redirect(f"/{definition.slug}")

    def handle_relationship_list(self) -> None:
        with connect(self.database_path) as connection:
            relationships = list_relationships(connection)
        self.respond_page(
            "Relationships",
            views.relationship_list_page(relationships),
            active_slug="relationships",
        )

    def handle_relationship_detail(self, raw_id: str) -> None:
        relationship_id = self.parse_entity_id(raw_id)
        if relationship_id is None:
            self.respond_not_found()
            return
        with connect(self.database_path) as connection:
            relationship = get_relationship(connection, relationship_id)
        if relationship is None:
            self.respond_not_found()
            return
        self.respond_page(
            "Relationship",
            views.relationship_detail_page(relationship),
            active_slug="relationships",
        )

    def handle_relationship_new(self, query: dict[str, str]) -> None:
        if self.command == "POST":
            values = normalise_relationship_values(self.read_form())
            with connect(self.database_path) as connection:
                errors = validate_relationship_values(connection, values)
                entities = list_all_entities(connection)
                if not errors:
                    relationship_id = create_relationship(connection, values)
                    self.redirect(self.relationship_redirect(values, relationship_id, query))
                    return
                context_entity = self.relationship_context_entity(connection, query, values)
            self.respond_relationship_form(values, errors, entities, "Create", context_entity=context_entity, target_type=query.get("target_type"))
            return

        values = {
            "source_entity_id": query.get("source_entity_id", ""),
            "target_entity_id": query.get("target_entity_id", ""),
            "type": "",
            "status": "active",
            "started_at": "",
            "started_at_precision": "exact",
            "ended_at": "",
            "ended_at_precision": "exact",
            "notes": "",
        }
        with connect(self.database_path) as connection:
            entities = list_all_entities(connection)
            context_entity = self.relationship_context_entity(connection, query, values)
        self.respond_relationship_form(values, [], entities, "Create", context_entity=context_entity, target_type=query.get("target_type"))

    def handle_relationship_edit(self, raw_id: str, query: dict[str, str]) -> None:
        relationship_id = self.parse_entity_id(raw_id)
        if relationship_id is None:
            self.respond_not_found()
            return
        with connect(self.database_path) as connection:
            relationship = get_relationship(connection, relationship_id)
            entities = list_all_entities(connection)
        if relationship is None:
            self.respond_not_found()
            return

        if self.command == "POST":
            values = normalise_relationship_values(self.read_form())
            with connect(self.database_path) as connection:
                errors = validate_relationship_values(connection, values)
                entities = list_all_entities(connection)
                if not errors:
                    update_relationship(connection, relationship_id, values)
                    self.redirect(self.relationship_redirect(values, relationship_id, query))
                    return
                context_entity = self.relationship_context_entity(connection, query, values)
            self.respond_relationship_form(values, errors, entities, "Edit", relationship_id, context_entity=context_entity, target_type=query.get("target_type"))
            return

        values = relationship.to_form_values()
        context_entity = self.relationship_context_entity(connection, query, values)
        self.respond_relationship_form(
            values, [], entities, "Edit", relationship_id, context_entity=context_entity, target_type=query.get("target_type")
        )

    def handle_relationship_delete(self, raw_id: str, query: dict[str, str]) -> None:
        if self.command != "POST":
            self.respond_not_found()
            return
        relationship_id = self.parse_entity_id(raw_id)
        if relationship_id is None:
            self.respond_not_found()
            return
        redirect_to = "/relationships"
        with connect(self.database_path) as connection:
            context_entity = self.relationship_context_entity(connection, query, {})
            if context_entity is not None:
                redirect_to = f"/{context_entity.slug}/{context_entity.id}"
            delete_relationship(connection, relationship_id)
        self.redirect(redirect_to)

    def respond_form(
        self,
        definition: EntityDefinition,
        values: dict[str, str],
        errors: list[str],
        action: str,
        entity_id: int | None = None,
    ) -> None:
        self.respond_page(
            f"{action} {definition.singular}",
            views.entity_form_page(definition, values, errors, action, entity_id),
            active_slug=definition.slug,
        )

    def respond_relationship_form(
        self,
        values: dict[str, str],
        errors: list[str],
        entities: list,
        action: str,
        relationship_id: int | None = None,
        context_entity=None,
        target_type: str | None = None,
    ) -> None:
        self.respond_page(
            f"{action} Relationship",
            views.relationship_form_page(
                values,
                errors,
                entities,
                action,
                relationship_id,
                context_entity=context_entity,
                target_type=target_type,
            ),
            active_slug=context_entity.slug if context_entity else "relationships",
        )

    def relationship_context_entity(self, connection, query: dict[str, str], values: dict[str, str]):
        raw_id = query.get("context_entity_id")
        entity_id = self.parse_entity_id(raw_id) if raw_id else None
        if entity_id is None:
            return None
        return get_entity_by_id(connection, entity_id)

    def relationship_redirect(
        self,
        values: dict[str, str],
        relationship_id: int,
        query: dict[str, str] | None = None,
    ) -> str:
        query = query or {}
        context_id = query.get("context_entity_id")
        if context_id:
            return self.entity_url_from_id(context_id) or f"/relationships/{relationship_id}"
        return f"/relationships/{relationship_id}"

    def entity_url_from_id(self, raw_id: str) -> str | None:
        entity_id = self.parse_entity_id(raw_id)
        if entity_id is None:
            return None
        with connect(self.database_path) as connection:
            entity = get_entity_by_id(connection, entity_id)
        if entity is None:
            return None
        return f"/{entity.slug}/{entity.id}"

    def serve_static(self, relative_path: str) -> None:
        if relative_path != "styles.css":
            self.respond_not_found()
            return
        content = (STATIC_DIR / "styles.css").read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/css; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def read_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        parsed = parse_qs(body, keep_blank_values=True)
        return {key: values[0] for key, values in parsed.items()}

    def respond_page(
        self,
        title: str,
        content: str,
        status: HTTPStatus = HTTPStatus.OK,
        active_slug: str | None = None,
    ) -> None:
        body = views.layout(title, content, active_slug)
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def respond_not_found(self) -> None:
        self.respond_page("Not found", views.not_found_page(), HTTPStatus.NOT_FOUND)

    @staticmethod
    def parse_entity_id(raw_id: str) -> int | None:
        try:
            return int(raw_id)
        except ValueError:
            return None


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    initialise_database(EddyRequestHandler.database_path)
    server = ThreadingHTTPServer((host, port), EddyRequestHandler)
    print(f"Operation Eddy running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Operation Eddy stopped.")
    finally:
        server.server_close()
