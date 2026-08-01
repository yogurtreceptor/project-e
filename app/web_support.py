"""HTTP transport, form parsing and response helpers for the web handler."""

import json
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs

from app import views
from app.calendar_subscription_service import list_subscriptions
from app.db import connect, inbox_count, normalise_form_values
from app.defaults import MAX_EVENT_REMINDERS
from app.document_storage import (
    UploadedFile,
    delete_stored_document,
    format_file_size,
    store_document_upload,
    stored_document_path,
)
from app.entities import EntityDefinition


STATIC_DIR = Path(__file__).resolve().parent / "static"


class RequestSupportMixin:
    """Low-level request and response operations shared by domain routes."""

    def serve_static(self, relative_path: str) -> None:
        content_types = {
            "action-menus.js": "text/javascript; charset=utf-8",
            "calendar-groups.js": "text/javascript; charset=utf-8",
            "calendar-grid.js": "text/javascript; charset=utf-8",
            "calendar-ordering.js": "text/javascript; charset=utf-8",
            "calendar-export-selection.js": "text/javascript; charset=utf-8",
            "calendar-visibility.js": "text/javascript; charset=utf-8",
            "confirmation.js": "text/javascript; charset=utf-8",
            "description-field.js": "text/javascript; charset=utf-8",
            "dirty-form.js": "text/javascript; charset=utf-8",
            "event-form.js": "text/javascript; charset=utf-8",
            "inbox-count.js": "text/javascript; charset=utf-8",
            "mini-month-picker.js": "text/javascript; charset=utf-8",
            "reminder-timings.js": "text/javascript; charset=utf-8",
            "quick-create.js": "text/javascript; charset=utf-8",
            "shell.js": "text/javascript; charset=utf-8",
            "super-key.js": "text/javascript; charset=utf-8",
            "taxonomy.js": "text/javascript; charset=utf-8",
            "timezone-picker.js": "text/javascript; charset=utf-8",
        }
        if relative_path.startswith("icons/") and relative_path.endswith(".svg"):
            icon_name = relative_path.removeprefix("icons/").removesuffix(".svg")
            if not icon_name or not icon_name.replace("-", "").isalnum():
                self.respond_not_found()
                return
            path = STATIC_DIR / "icons" / f"{icon_name}.svg"
            if not path.is_file():
                self.respond_not_found()
                return
            content_type = "image/svg+xml"
        elif (
            "/" not in relative_path
            and relative_path.endswith(".css")
            and relative_path.removesuffix(".css").replace("-", "").isalnum()
        ):
            path = STATIC_DIR / relative_path
            if not path.is_file():
                self.respond_not_found()
                return
            content_type = "text/css; charset=utf-8"
        elif relative_path in content_types:
            path = STATIC_DIR / relative_path
            content_type = content_types[relative_path]
        else:
            self.respond_not_found()
            return
        content = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def read_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        parsed = parse_qs(body, keep_blank_values=True)
        return {key: ",".join(values) for key, values in parsed.items()}

    def read_entity_form(
        self, definition: EntityDefinition
    ) -> tuple[dict[str, str], UploadedFile | None]:
        if (
            definition.type != "document"
            or not self.headers.get("Content-Type", "").startswith("multipart/form-data")
        ):
            raw_values = self.read_form()
            values = normalise_form_values(definition, raw_values)
            values["confirm_duplicate"] = raw_values.get("confirm_duplicate", "")
            return values, None
        raw_values, upload = self.read_multipart_form()
        values = normalise_form_values(definition, raw_values)
        values["confirm_duplicate"] = raw_values.get("confirm_duplicate", "")
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
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
            + body
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
                    content_type=item.get_content_type()
                    or "application/octet-stream",
                    data=data,
                )
            elif not file_name:
                charset = item.get_content_charset() or "utf-8"
                values[key] = data.decode(charset, errors="replace")
        return values, upload

    @staticmethod
    def clear_document_file_values(values: dict[str, str]) -> None:
        for field_name in ("file_name", "file_path", "mime_type", "file_size"):
            values[field_name] = ""

    @staticmethod
    def restore_document_file_values(
        values: dict[str, str], metadata: dict[str, str]
    ) -> None:
        for field_name in ("file_name", "file_path", "mime_type", "file_size"):
            values[field_name] = metadata.get(field_name, "")

    def store_document_upload(self, upload: UploadedFile) -> dict[str, str]:
        return store_document_upload(upload, self.document_storage_dir)

    def stored_document_path(self, value: str) -> Path | None:
        return stored_document_path(value, self.document_storage_dir)

    def delete_document_file(self, value: str) -> bool:
        return delete_stored_document(value, self.document_storage_dir)

    def respond_page(
        self,
        title: str,
        content: str,
        status: HTTPStatus = HTTPStatus.OK,
        active_slug: str | None = None,
        show_save_toast: bool = False,
        sidebar_variant: str = "browse",
        sidebar_content: str = "",
        header_content: str = "",
    ) -> None:
        with connect(self.database_path) as connection:
            active_inbox_count = inbox_count(connection)
        body = views.layout(
            title,
            content,
            active_slug=active_slug,
            show_save_toast=show_save_toast,
            sidebar_variant=sidebar_variant,
            sidebar_content=sidebar_content,
            header_content=header_content,
            inbox_count=active_inbox_count,
        )
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def respond_calendar_settings(
        self,
        title: str,
        content: str,
        calendars,
        *,
        active_section: str,
        return_to: str,
        status: HTTPStatus = HTTPStatus.OK,
        show_save_toast: bool = False,
    ) -> None:
        with connect(self.database_path) as connection:
            subscriptions = list_subscriptions(connection)
        self.respond_page(
            title,
            content,
            status,
            show_save_toast=show_save_toast,
            sidebar_variant="calendar-settings",
            sidebar_content=views.calendar_settings_sidebar(
                calendars,
                subscriptions,
                active_section=active_section,
                return_to=return_to,
            ),
            header_content=views.calendar_settings_header(return_to),
        )

    def respond_json(
        self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK
    ) -> None:
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

    @staticmethod
    def reminder_timings(values: dict[str, str], prefix: str) -> list[str]:
        timings = []
        units = {"m", "h", "d", "w", "mo"}
        amount_prefix = f"{prefix}_amount_"
        unit_prefix = f"{prefix}_unit_"
        for key in values:
            if key.startswith(amount_prefix) or key.startswith(unit_prefix):
                suffix = key.rsplit("_", 1)[-1]
                if not suffix.isdigit() or int(suffix) >= MAX_EVENT_REMINDERS:
                    raise ValueError(
                        f"No more than {MAX_EVENT_REMINDERS} reminder "
                        "notifications are allowed."
                    )
        for index in range(MAX_EVENT_REMINDERS):
            amount = values.get(f"{prefix}_amount_{index}", "")
            unit = values.get(f"{prefix}_unit_{index}", "")
            if not amount and not unit:
                continue
            if not amount.isdigit() or int(amount) <= 0 or unit not in units:
                raise ValueError(
                    "Each reminder needs a positive whole number and a valid unit."
                )
            timings.append(f"{int(amount)}{unit}")
        if len(set(timings)) != len(timings):
            raise ValueError(
                "Each reminder notification must use a different time."
            )
        return timings
