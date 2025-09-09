from typing import Optional

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Label, TextArea, Button, Static
from textual.containers import VerticalGroup, Horizontal, Container
from textual import events

from functools import cached_property

# Support both package (python -m app.generate) and script (python app/generate.py) execution.
try:  # pragma: no cover - import flexibility convenience
    from .tree import build_standard_names_tree  # type: ignore
except ImportError:  # direct script run, fall back to absolute import
    from app.tree import build_standard_names_tree  # type: ignore


class LabeledTextArea(VerticalGroup):
    """A label stacked above a plain TextArea.

    Child ids:
      <id>_label  - the label widget
      <id>_text   - the TextArea
    """

    def __init__(self, id: str, label: Optional[str] = None, **kwargs) -> None:
        super().__init__(id=id)
        self.label = label
        self._text_area_kwargs = kwargs

    def compose(self) -> ComposeResult:
        if self.label:
            yield Label(self.label, id=f"{self.id}_label")
        yield TextArea(id=f"{self.id}_text", **self._text_area_kwargs)

    @cached_property
    def text_area(self) -> TextArea:  # cached lookup after compose
        return self.query_one(f"#{self.id}_text", TextArea)

    @property
    def text(self) -> str:
        return self.text_area.text

    @text.setter
    def text(self, value: str) -> None:
        self.text_area.load_text(value)

    def append_text(self, more: str) -> None:
        current = self.text
        if current and not current.endswith("\n"):
            current += "\n"
        self.text = (current + more) if current else more

    def focus(self, scroll_visible: bool = True):  # pragma: no cover
        self.text_area.focus(scroll_visible=scroll_visible)
        return self


class SendTextArea(TextArea):  # internal helper with auto-resize
    MIN_LINES = 1
    MAX_LINES = 10

    def on_key(self, event: events.Key) -> None:  # type: ignore[override]
        # Enter sends (unless Alt for newline). Other keys handled by base class.
        modifiers = getattr(event, "modifiers", set())
        if event.key == "enter" and "alt" not in modifiers:
            event.stop()
            action = getattr(self.app, "action_send_query", None)
            if callable(action):
                action()


class SendLabeledTextArea(LabeledTextArea):
    """Labeled text input with send-on-enter and a send button."""

    def compose(self) -> ComposeResult:  # type: ignore[override]
        if self.label:
            yield Label(self.label, id=f"{self.id}_label")
        yield SendTextArea(id=f"{self.id}_text", **self._text_area_kwargs)
        yield Horizontal(
            Static(),
            Button(
                "▶",
                id=f"{self.id}_send",
                classes="send-btn",
                variant="primary",
                tooltip="Send",
            ),
            classes="send-row",
        )

    @cached_property
    def text_area(self) -> TextArea:
        return self.query_one(f"#{self.id}_text", TextArea)

    @property
    def text(self) -> str:
        return self.text_area.text

    @text.setter
    def text(self, value: str) -> None:
        self.text_area.load_text(value)

    def append_text(self, more: str) -> None:
        current = self.text
        if current and not current.endswith("\n"):
            current += "\n"
        self.text = (current + more) if current else more

    def focus(self, scroll_visible: bool = True):  # pragma: no cover
        self.text_area.focus(scroll_visible=scroll_visible)
        return self


class Query(VerticalGroup):
    def compose(self) -> ComposeResult:  # type: ignore[override]
        """Compose the query panel widgets with an auto-resizing input."""
        yield LabeledTextArea(id="response", read_only=True)
        yield SendLabeledTextArea(id="query", placeholder="Type your query...")


class StandardNameApp(App):
    """A Textual Standard Name generator application."""

    CSS_PATH = "standard_name.tcss"
    BINDINGS = [("enter", "send_query", "Send")]
    TITLE = "IMAS Standard Name Generator"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=False)
        with Container(id="body"):
            # Left side: tree of existing standard names
            yield build_standard_names_tree()
            # Right side: query / generation panel
            yield Query()
        yield Footer()
        # yield Tree("equilibrium")

    def on_mount(self) -> None:
        # Focus query on start; splitter will apply persisted layout automatically on mount
        try:
            self.query_one("#query_text", TextArea).focus()
        except Exception:  # pragma: no cover
            pass

    def action_send_query(self) -> None:
        """Collect query text and echo to output (temporary demo implementation)."""
        query_field = self.query_one("#query", LabeledTextArea)
        response_field = self.query_one("#response", LabeledTextArea)
        text = query_field.text.strip()
        if text:
            response_field.append_text(f"> {text}")
            query_field.text = ""  # clear after sending

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.endswith("_send"):
            # Derive field id (strip suffix)
            field_id = btn_id[:-5]
            if field_id == "query":
                self.action_send_query()


if __name__ == "__main__":
    app = StandardNameApp()
    app.run()
