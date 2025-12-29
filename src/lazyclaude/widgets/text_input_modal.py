"""Generic text input modal widget for prompting user input."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input


class TextInputModal(Widget):
    """Reusable text input modal for prompting user input.

    Can be embedded in other widgets and shown/hidden as needed.
    Emits InputSubmitted with the entered value and optional context.
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    TextInputModal {
        dock: bottom;
        height: 3;
        border: solid $accent;
        padding: 0 1;
        display: none;
    }

    TextInputModal.visible {
        display: block;
    }

    TextInputModal:focus-within {
        border: double $accent;
    }

    TextInputModal Input {
        width: 100%;
    }
    """

    class InputSubmitted(Message):
        """Emitted when user submits input (Enter key)."""

        def __init__(self, value: str, context: str | None = None) -> None:
            self.value = value
            self.context = context
            super().__init__()

    class InputCancelled(Message):
        """Emitted when input is cancelled (Escape key)."""

        def __init__(self, context: str | None = None) -> None:
            self.context = context
            super().__init__()

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize TextInputModal."""
        super().__init__(name=name, id=id, classes=classes)
        self._input: Input | None = None
        self._input_context: str | None = None
        self._placeholder: str = "Enter value..."

    def compose(self) -> ComposeResult:
        """Compose the text input."""
        self._input = Input(placeholder=self._placeholder)
        yield self._input

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission (Enter key)."""
        value = event.value.strip()
        if value:
            self.post_message(self.InputSubmitted(value, self._input_context))
            self.hide()

    def action_cancel(self) -> None:
        """Cancel input."""
        self.hide()
        self.post_message(self.InputCancelled(self._input_context))

    def show(self, placeholder: str, context: str | None = None) -> None:
        """Show the input with custom placeholder and optional context.

        Args:
            placeholder: Text to show as placeholder in the input field.
            context: Optional context string passed back in messages.
        """
        self._placeholder = placeholder
        self._input_context = context
        if self._input:
            self._input.placeholder = placeholder
            self._input.value = ""
        self.add_class("visible")
        if self._input:
            self._input.focus()

    def hide(self) -> None:
        """Hide and clear the input."""
        self.remove_class("visible")
        if self._input:
            self._input.value = ""

    @property
    def is_visible(self) -> bool:
        """Check if the input is visible."""
        return self.has_class("visible")
