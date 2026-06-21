import json
import re
import uuid
from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app import views
from app.config import DATABASE_PATH, DOCUMENT_STORAGE_DIR
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
    list_favourite_entities,
    list_recent_entities,
    list_relationships,
    list_relationships_for_entity,
    mark_entity_viewed,
    normalise_form_values,
    normalise_relationship_values,
    search_entities,
    set_entity_favourite,
    update_entity,
    update_relationship,
    validate_entity_values,
    validate_relationship_values,
)
from app.entities import DEFINITIONS_BY_SLUG, EntityDefinition
from app.geo import build_map_payload, geocoder


STATIC_DIR = Path(__file__).resolve().parent / "static"


@dataclass(frozen=True)
class UploadedFile:
    file_name: str
    content_type: str
    data: bytes


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

        if parts[0] == "search":
            self.handle_search(query)
            return

        if parts[0] == "map":
            self.handle_map(query)
            return

        if parts[0] == "geocoding" and len(parts) == 2 and parts[1] == "search":
            self.handle_geocoding_search(query)
            return

        if parts[0] == "relationships":
            self.route_relationship_request(parts, query)
            return

        definition = DEFINITIONS_BY_SLUG.get(parts[0])
        if definition is None:
            self.respond_not_found()
            return

        if len(parts) == 1:
            self.handle_list(definition, query)
        elif len(parts) == 2 and parts[1] == "new":
            self.handle_new(definition)
        elif len(parts) == 2:
            self.handle_detail(definition, parts[1])
        elif len(parts) == 3 and parts[2] == "download" and definition.type == "document":
            self.handle_document_download(parts[1])
        elif len(parts) == 3 and parts[2] == "edit":
            self.handle_edit(definition, parts[1])
        elif len(parts) == 3 and parts[2] == "delete":
            self.handle_delete(definition, parts[1])
        elif len(parts) == 3 and parts[2] == "favourite":
            self.handle_favourite(definition, parts[1])
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
            recent_entities = list_recent_entities(connection)
            favourite_entities = list_favourite_entities(connection)
        self.respond_page(
            "Dashboard",
            views.dashboard_page(counts, relationship_count, recent_entities, favourite_entities),
        )

    def handle_search(self, query: dict[str, str]) -> None:
        search_query = query.get("q", "")
        entity_type = query.get("type", "")
        favourites_only = query.get("favourites") == "1"
        with connect(self.database_path) as connection:
            results = search_entities(connection, search_query, entity_type, favourites_only)
        self.respond_page(
            "Search",
            views.search_page(search_query, entity_type, favourites_only, results),
            active_slug="search",
        )


    def handle_map(self, query: dict[str, str]) -> None:
        with connect(self.database_path) as connection:
            payload = build_map_payload(connection)
        self.respond_page(
            "Map",
            views.map_page(payload, query.get("entity_id", "")),
            active_slug="map",
        )

    def handle_geocoding_search(self, query: dict[str, str]) -> None:
        if self.command != "GET":
            self.respond_not_found()
            return
        try:
            results = geocoder().search(query.get("q", ""))
            self.respond_json({"results": results})
        except Exception as error:
            self.respond_json({"results": [], "error": str(error)}, status=HTTPStatus.OK)

    def handle_list(self, definition: EntityDefinition, query: dict[str, str]) -> None:
        filter_query = query.get("q", "")
        favourites_only = query.get("favourites") == "1"
        with connect(self.database_path) as connection:
            records = list_entities(connection, definition, filter_query, favourites_only)
        self.respond_page(
            definition.plural,
            views.entity_list_page(definition, records, filter_query, favourites_only),
            active_slug=definition.slug,
        )

    def handle_detail(self, definition: EntityDefinition, raw_id: str) -> None:
        entity_id = self.parse_entity_id(raw_id)
        if entity_id is None:
            self.respond_not_found()
            return

        with connect(self.database_path) as connection:
            record = get_entity(connection, definition, entity_id)
            if record is not None:
                mark_entity_viewed(connection, entity_id)
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
            values, upload = self.read_entity_form(definition)
            errors = validate_entity_values(definition, values)
            if not errors:
                if upload is not None:
                    values.update(self.store_document_upload(upload))
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
            values, upload = self.read_entity_form(definition)
            errors = validate_entity_values(definition, values)
            if not errors:
                if upload is not None:
                    values.update(self.store_document_upload(upload))
                with connect(self.database_path) as connection:
                    update_entity(connection, definition, entity_id, values)
                self.redirect(f"/{definition.slug}/{entity_id}")
                return
            self.respond_form(definition, values, errors, "Edit", entity_id)
            return

        self.respond_form(definition, record.to_form_values(), [], "Edit", entity_id)

    def handle_document_download(self, raw_id: str) -> None:
        entity_id = self.parse_entity_id(raw_id)
        if entity_id is None:
            self.respond_not_found()
            return
        definition = DEFINITIONS_BY_SLUG["documents"]
        with connect(self.database_path) as connection:
            record = get_entity(connection, definition, entity_id)
        if record is None:
            self.respond_not_found()
            return
        file_path = self.stored_document_path(record.metadata.get("file_path", ""))
        if file_path is None or not file_path.exists():
            self.respond_not_found()
            return
        content = file_path.read_bytes()
        file_name = record.metadata.get("file_name", file_path.name)
        content_type = record.metadata.get("mime_type", "") or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", f'attachment; filename="{file_name.replace(chr(34), "")}"')
        self.end_headers()
        self.wfile.write(content)

    def handle_favourite(self, definition: EntityDefinition, raw_id: str) -> None:
        if self.command != "POST":
            self.respond_not_found()
            return
        entity_id = self.parse_entity_id(raw_id)
        if entity_id is None:
            self.respond_not_found()
            return
        is_favourite = self.read_form().get("is_favourite") == "1"
        with connect(self.database_path) as connection:
            record = get_entity(connection, definition, entity_id)
            if record is None:
                self.respond_not_found()
                return
            set_entity_favourite(connection, entity_id, is_favourite)
        self.redirect(f"/{definition.slug}/{entity_id}")

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

    def read_entity_form(self, definition: EntityDefinition) -> tuple[dict[str, str], UploadedFile | None]:
        if definition.type != "document" or not self.headers.get("Content-Type", "").startswith("multipart/form-data"):
            return normalise_form_values(definition, self.read_form()), None
        raw_values, upload = self.read_multipart_form()
        values = normalise_form_values(definition, raw_values)
        if upload is not None:
            values["file_name"] = upload.file_name
            values["mime_type"] = upload.content_type
            values["file_size"] = format_file_size(len(upload.data))
            if not values.get("display_name"):
                values["display_name"] = Path(upload.file_name).stem or upload.file_name
        return values, upload

    def read_multipart_form(self) -> tuple[dict[str, str], UploadedFile | None]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "")
        message = BytesParser(policy=default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
        )
        values: dict[str, str] = {}
        upload = None
        for item in message.iter_parts():
            key = item.get_param("name", header="content-disposition")
            if not key:
                continue
            file_name = item.get_filename()
            data = item.get_payload(decode=True) or b""
            if key == "upload" and file_name:
                upload = UploadedFile(
                    file_name=Path(file_name).name,
                    content_type=item.get_content_type() or "application/octet-stream",
                    data=data,
                )
            elif not file_name:
                charset = item.get_content_charset() or "utf-8"
                values[key] = data.decode(charset, errors="replace")
        return values, upload

    def store_document_upload(self, upload: UploadedFile) -> dict[str, str]:
        DOCUMENT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = safe_file_name(upload.file_name)
        stored_name = f"{uuid.uuid4().hex}-{safe_name}"
        stored_path = DOCUMENT_STORAGE_DIR / stored_name
        stored_path.write_bytes(upload.data)
        return {
            "file_name": upload.file_name,
            "file_path": f"documents/{stored_name}",
            "mime_type": upload.content_type,
            "file_size": format_file_size(len(upload.data)),
        }

    @staticmethod
    def stored_document_path(value: str) -> Path | None:
        if not value:
            return None
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            return None
        path = (DOCUMENT_STORAGE_DIR.parent / relative).resolve()
        storage_root = DOCUMENT_STORAGE_DIR.resolve()
        if storage_root not in (path, *path.parents):
            return None
        return path

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

    def respond_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
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


def safe_file_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(value).name).strip(".-")
    return cleaned or "document"


def format_file_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


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
