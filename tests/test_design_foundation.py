import unittest
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
import re
from urllib.request import urlopen

from app.view_pages.layout import layout
from app.view_pages.forms import error_block
from app.web import EddyRequestHandler


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "app" / "static"


def contrast_ratio(first: str, second: str) -> float:
    def luminance(colour: str) -> float:
        channels = [int(colour[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
            for value in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def mix(first: str, second: str, first_weight: float) -> str:
    first_channels = [int(first[index : index + 2], 16) for index in (1, 3, 5)]
    second_channels = [int(second[index : index + 2], 16) for index in (1, 3, 5)]
    channels = [
        round(left * first_weight + right * (1 - first_weight))
        for left, right in zip(first_channels, second_channels)
    ]
    return "#" + "".join(f"{channel:02x}" for channel in channels)


class DesignFoundationTests(unittest.TestCase):
    def test_application_stylesheet_imports_single_foundation_entry_first(self) -> None:
        stylesheet = (STATIC_DIR / "styles.css").read_text()

        self.assertTrue(stylesheet.startswith('@import url("/static/foundation.css");'))
        self.assertEqual(stylesheet.count("foundation.css"), 1)
        self.assertTrue((STATIC_DIR / "foundation.css").is_file())

    def test_shared_layout_keeps_the_existing_application_stylesheet(self) -> None:
        html = layout("Foundation smoke", "<h1>Foundation smoke</h1>")

        self.assertIn('<link rel="stylesheet" href="/static/styles.css">', html)

    def test_foundation_file_is_allowed_by_static_handler(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), EddyRequestHandler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with urlopen(
                f"http://127.0.0.1:{server.server_port}/static/foundation.css",
                timeout=5,
            ) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_content_type(), "text/css")
                self.assertIn(b"Project E design foundation", response.read())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_shared_stylesheet_has_balanced_blocks_and_defined_custom_properties(self) -> None:
        foundation = (STATIC_DIR / "foundation.css").read_text()
        stylesheet = (STATIC_DIR / "styles.css").read_text()
        combined = foundation + stylesheet

        self.assertEqual(combined.count("{"), combined.count("}"))
        self.assertNotIn("var(--ink)", combined)

        defined = set(re.findall(r"(--[a-zA-Z0-9_-]+)\s*:", combined))
        used = set(re.findall(r"var\((--[a-zA-Z0-9_-]+)", combined))
        self.assertEqual(used - defined, set())

    def test_foundation_defines_one_accent_primitive_and_complete_theme_base(self) -> None:
        foundation = (STATIC_DIR / "foundation.css").read_text()

        self.assertEqual(foundation.lower().count("#66ccff"), 1)
        self.assertIn("color-scheme: dark", foundation)
        self.assertIn("@media (prefers-color-scheme: light)", foundation)
        for role in (
            "--color-canvas",
            "--color-surface-panel",
            "--color-text-primary",
            "--color-border-focus",
            "--color-action-primary",
            "--color-status-success",
            "--color-status-warning",
            "--color-status-danger",
            "--color-series-5",
            "--font-family-interface",
            "--space-16",
            "--radius-panel",
            "--elevation-floating",
        ):
            self.assertIn(f"{role}:", foundation)

    def test_representative_theme_pairs_meet_wcag_contrast(self) -> None:
        self.assertGreaterEqual(contrast_ratio("#f6f8f9", "#111517"), 4.5)
        self.assertGreaterEqual(contrast_ratio("#66ccff", "#111517"), 4.5)
        self.assertGreaterEqual(contrast_ratio("#171c1f", "#f6f8f9"), 4.5)
        light_primary = mix("#66ccff", "#111517", 0.55)
        light_focus = mix("#66ccff", "#111517", 0.48)
        self.assertGreaterEqual(contrast_ratio("#ffffff", light_primary), 4.5)
        self.assertGreaterEqual(contrast_ratio(light_focus, "#ffffff"), 3.0)

    def test_keyboard_focus_and_reduced_motion_are_global(self) -> None:
        foundation = (STATIC_DIR / "foundation.css").read_text()

        self.assertIn(":focus-visible", foundation)
        self.assertIn("--focus-ring: 0 0 0 2px", foundation)
        self.assertIn("@media (prefers-reduced-motion: reduce)", foundation)
        self.assertIn("transition-duration: 0.01ms !important", foundation)

    def test_first_shared_component_slice_has_semantic_states(self) -> None:
        stylesheet = (STATIC_DIR / "styles.css").read_text()

        for selector in (
            ".button.quiet",
            '.button[disabled]',
            'input[readonly]',
            'input[aria-invalid="true"]',
            ".button.danger",
        ):
            self.assertIn(selector, stylesheet)
        self.assertIn("background: var(--color-surface-inset)", stylesheet)
        self.assertIn("border-color: var(--color-status-danger)", stylesheet)
        self.assertIn("background: var(--color-status-danger-surface)", stylesheet)
        self.assertIn('input[aria-invalid="true"]:focus-visible', stylesheet)
        self.assertIn("0 0 0 3px var(--color-border-focus)", stylesheet)

    def test_shared_feedback_and_content_states_use_semantic_roles(self) -> None:
        stylesheet = (STATIC_DIR / "styles.css").read_text()

        for selector in (
            ".empty-state",
            ".loading-state",
            ".failure-state",
            ".notice",
            ".warnings",
            ".status-badge.active",
            '.panel[aria-busy="true"]',
        ):
            self.assertIn(selector, stylesheet)
        self.assertIn("var(--color-status-success-surface)", stylesheet)
        self.assertIn("var(--color-status-warning-surface)", stylesheet)
        self.assertIn("var(--color-status-info-surface)", stylesheet)

    def test_error_summary_is_an_accessible_alert(self) -> None:
        html = error_block(["Display name is required."])

        self.assertIn('role="alert"', html)
        self.assertIn('aria-labelledby="form-errors-title"', html)
        self.assertIn('id="form-errors-title"', html)
        self.assertIn('tabindex="-1"', html)

    def test_save_toast_is_passive_and_cleans_redirect_marker(self) -> None:
        normal_html = layout("No save", "<h1>No save</h1>")
        saved_html = layout("Saved", "<h1>Saved</h1>", show_save_toast=True)

        self.assertNotIn("Changes saved", normal_html)
        self.assertIn('class="save-toast" role="status" aria-live="polite"', saved_html)
        self.assertNotIn("autofocus", saved_html)
        self.assertIn('url.searchParams.delete("saved")', saved_html)
        self.assertIn("history.replaceState", saved_html)

        stylesheet = (STATIC_DIR / "styles.css").read_text()
        self.assertIn(".save-toast", stylesheet)
        self.assertIn("@keyframes save-toast-fade", stylesheet)

    def test_confirmation_dialog_has_object_consequence_and_focus_management(self) -> None:
        html = layout("Confirm", "<h1>Confirm</h1>")
        script = (STATIC_DIR / "confirmation.js").read_text()

        self.assertIn('data-confirmation-dialog aria-labelledby="confirmation-title"', html)
        self.assertIn('aria-describedby="confirmation-consequence"', html)
        self.assertIn('data-confirmation-object', html)
        self.assertIn('data-confirmation-consequence', html)
        self.assertIn('data-confirmation-confirm', html)
        self.assertIn('dialog.showModal()', script)
        self.assertIn('confirmButton.focus()', script)
        self.assertIn('invoker.focus()', script)
        self.assertIn('pendingForm.requestSubmit()', script)

    def test_entity_soft_delete_uses_shared_confirmation_not_native_confirm(self) -> None:
        from app.entities import EntityRecord, DEFINITIONS_BY_SLUG
        from app.view_pages.entities import entity_profile_header

        definition = DEFINITIONS_BY_SLUG["people"]
        record = EntityRecord(
            id=1,
            definition=definition,
            display_name="Ada Lovelace",
            summary="",
            notes="",
            created_at="",
            updated_at="",
            last_viewed_at="",
            is_favourite=False,
            metadata={},
        )
        html = entity_profile_header(record)

        self.assertIn('data-confirm-object="Ada Lovelace"', html)
        self.assertIn("It can be restored later.", html)
        self.assertNotIn("confirm(", html)


if __name__ == "__main__":
    unittest.main()
