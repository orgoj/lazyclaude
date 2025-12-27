"""Scope selector bar for plugin install/enable/disable operations."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from lazyclaude.models.marketplace import MarketplacePlugin


class ScopeSelector(Widget):
    """Bottom bar for selecting plugin scope."""

    BINDINGS = [
        Binding("1", "select_user", "User", show=False),
        Binding("2", "select_project", "Project", show=False),
        Binding("3", "select_local", "Local", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    ScopeSelector {
        dock: bottom;
        height: 3;
        border: solid $accent;
        padding: 0 1;
        margin-bottom: 1;
        display: none;
        background: $surface;
    }

    ScopeSelector.visible {
        display: block;
    }

    ScopeSelector:focus {
        border: double $accent;
    }

    ScopeSelector #prompt {
        width: 100%;
        height: 1fr;
        text-align: center;
        content-align: center;
    }

    ScopeSelector .key {
        color: $accent;
        text-style: bold;
    }
    """

    can_focus = True

    class ScopeSelected(Message):
        """Emitted when a scope is selected."""

        def __init__(self, plugin: MarketplacePlugin, scope: str, action: str) -> None:
            self.plugin = plugin
            self.scope = scope
            self.action = action
            super().__init__()

    class SelectionCancelled(Message):
        """Emitted when selection is cancelled."""

        pass

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize ScopeSelector."""
        super().__init__(name=name, id=id, classes=classes)
        self._plugin: MarketplacePlugin | None = None
        self._scope_status: dict[str, str] = {}
        self._action: str = "enable"

    def compose(self) -> ComposeResult:
        """Compose the scope selector bar."""
        yield Static("", id="prompt")

    def show(
        self,
        plugin: MarketplacePlugin,
        scope_status: dict[str, str],
        action: str = "enable",
    ) -> None:
        """Show the scope selector and focus it."""
        self._plugin = plugin
        self._scope_status = scope_status
        self._action = action
        self._update_prompt()
        self.add_class("visible")
        self.focus()

    def hide(self) -> None:
        """Hide the scope selector."""
        self.remove_class("visible")
        self._plugin = None

    def _update_prompt(self) -> None:
        """Update the prompt text based on scope status."""
        if not self._plugin:
            return

        action_label = self._action.capitalize()

        # Status icons
        def get_icon(status: str) -> str:
            if status == "enabled":
                return "[✓]"
            elif status == "disabled":
                return "[✗]"
            else:
                return "[ ]"

        user_icon = get_icon(self._scope_status.get("user", "not_installed"))
        project_icon = get_icon(self._scope_status.get("project", "not_installed"))
        local_icon = get_icon(self._scope_status.get("local", "not_installed"))

        options_text = (
            f"{user_icon} 1:User  {project_icon} 2:Project  {local_icon} 3:Local"
        )
        prompt_widget = self.query_one("#prompt", Static)
        prompt_widget.update(
            f"{action_label}: {self._plugin.name}\n{options_text}  \\[Esc] Cancel"
        )

    def action_select_user(self) -> None:
        """Select user scope."""
        self._select_scope("user")

    def action_select_project(self) -> None:
        """Select project scope."""
        self._select_scope("project")

    def action_select_local(self) -> None:
        """Select local scope."""
        self._select_scope("local")

    def _select_scope(self, scope: str) -> None:
        """Handle scope selection."""
        if not self._plugin:
            return

        status = self._scope_status.get(scope, "not_installed")

        # Determine action based on current status
        if status == "enabled":
            # Already enabled - show warning, don't emit message
            self._show_warning(f"Plugin already enabled in {scope.capitalize()} scope")
            return

        if status == "not_installed":
            action = "install"
        elif status == "disabled":
            action = "enable"
        else:
            action = self._action

        self.hide()
        self.post_message(self.ScopeSelected(self._plugin, scope, action))

    def _show_warning(self, message: str) -> None:
        """Show warning message to user."""
        # TODO: Implement warning display (could use a toast or status bar message)
        # For now, just log or could emit a warning message
        pass

    def action_cancel(self) -> None:
        """Cancel selection."""
        self.hide()
        self.post_message(self.SelectionCancelled())

    @property
    def is_visible(self) -> bool:
        """Check if the scope selector is visible."""
        return self.has_class("visible")
