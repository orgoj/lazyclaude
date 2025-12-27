"""Debug overlay for displaying live debug messages."""

from textual.widgets import Static


class DebugOverlay(Static):
    """Overlay for displaying debug messages."""

    DEFAULT_CSS = """
    DebugOverlay {
        dock: top;
        height: 30%;
        border: solid yellow;
        background: $panel;
        display: none;
        overflow-y: auto;
    }

    DebugOverlay.visible {
        display: block;
    }
    """

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self._max_lines = 1000
        self._lines: list[str] = []

    def log_message(self, message: str) -> None:
        """Add a log message to the overlay."""
        # Keep only last N lines
        self._lines.append(message)
        if len(self._lines) > self._max_lines:
            self._lines = self._lines[-self._max_lines // 2 :]

        self.update("\n".join(self._lines))

    def clear(self) -> None:
        """Clear all log messages."""
        self._lines = []
        self.update("")

    def on_mount(self) -> None:
        """Initialize widget on mount."""
        self.border_title = "Debug Output"
