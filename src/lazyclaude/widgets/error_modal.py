"""Persistent error display screen."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Static


class ErrorScreen(ModalScreen[None]):
    """Modal screen for displaying persistent error messages."""

    BINDINGS = [
        Binding("escape", "close_error", "Close", show=False),
    ]

    DEFAULT_CSS = """
    ErrorScreen {
        background: $background 60%;
    }

    ErrorScreen > #error-dialog {
        dock: top;
        width: 100%;
        height: auto;
        max-height: 80%;
        margin: 5 2 0 2;
        border: solid $error;
        padding: 1 2;
        background: $surface;
        overflow-y: auto;
    }
    """

    def __init__(self, message: str) -> None:
        """Initialize ErrorScreen with error message."""
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        """Compose the error dialog."""
        yield Static(
            f"[bold red]Error:[/]\n\n{self._message}\n\n[dim]Press [/][bold]Esc[/][dim] to close[/]",
            id="error-dialog",
        )

    def action_close_error(self) -> None:
        """Close the error screen."""
        self.dismiss()
