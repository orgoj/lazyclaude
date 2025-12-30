"""Custom application footer with dynamic mode-based content."""

from textual.app import ComposeResult
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from lazyclaude.models.view_mode import ViewMode


class AppFooter(Widget):
    """Footer widget that displays mode and view-specific content."""

    DEFAULT_CSS = """
    AppFooter {
        dock: bottom;
        height: 1;
        background: $panel;
    }

    AppFooter .footer-content {
        width: 100%;
        text-align: center;
    }
    """

    mode: reactive[ViewMode] = reactive(ViewMode.NORMAL)
    content_text: reactive[str] = reactive("")

    def compose(self) -> ComposeResult:
        yield Static(self._render_footer(), classes="footer-content")

    def _render_footer(self) -> str:
        """Render footer with mode label and content."""
        mode_label = f"[bold][{self.mode.value.title()}][/]"
        mode_key = "[bold]M[/] Mode"
        palette = "[bold][$accent]^p[/][/] Palette"

        if self.content_text:
            return f"{mode_label}  {mode_key}  [dim]|[/]  {self.content_text}  [dim]|[/]  {palette}"
        else:
            return f"{mode_label}  {mode_key}  [dim]|[/]  {palette}"

    def set_content(self, mode: ViewMode, content: str) -> None:
        """Update footer with new mode and content."""
        self.mode = mode
        self.content_text = content

    def _update_content(self) -> None:
        """Update the footer content display."""
        if self.is_mounted:
            try:
                content = self.query_one(".footer-content", Static)
                content.update(self._render_footer())
            except NoMatches:
                pass  # Widget not yet composed

    def watch_mode(self, mode: ViewMode) -> None:  # noqa: ARG002
        """React to mode changes."""
        self._update_content()

    def watch_content_text(self, content: str) -> None:  # noqa: ARG002
        """React to content changes."""
        self._update_content()
