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
    delete_entity,
    get_entity,
    initialise_database,
    list_entities,
    normalise_form_values,
    update_entity,
    validate_entity_values,
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

        if parsed.path.startswith("/static/"):
            self.serve_static(parsed.path.removeprefix("/static/"))
            return

        if not parts:
            self.handle_dashboard()
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

    def handle_dashboard(self) -> None:
        with connect(self.database_path) as connection:
            counts = count_entities(connection)
        self.respond_page("Dashboard", views.dashboard_page(counts))

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
        if record is None:
            self.respond_not_found()
            return

        self.respond_page(
            record.title,
            views.entity_detail_page(record),
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
