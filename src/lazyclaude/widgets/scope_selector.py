"""Scope selector bar for plugin install/enable/disable operations."""

import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from lazyclaude.models.marketplace import MarketplacePlugin

logger = logging.getLogger(__name__)


class ScopeSelector(Widget):
    """Bottom bar for selecting plugin scope."""

    BINDINGS = [
        Binding("1", "select_user", "User", show=False),
        Binding("2", "select_project", "Project", show=False),
        Binding("3", "select_local", "Local", show=False),
        Binding("u", "select_user", "User", show=False),
        Binding("p", "select_project", "Project", show=False),
        Binding("l", "select_local", "Local", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    DEFAULT_CSS = """
    ScopeSelector {
        dock: bottom;
        height: 4;
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
        text-align: center;
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
        logger.debug(f"[SCOPE SELECTOR] {action} {plugin.full_plugin_id}")
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
            f"{user_icon} [1/u] User  {project_icon} [2/p] Project  {local_icon} [3/l] Local"
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

        plugin = self._plugin
        action = self._action
        self.hide()
        logger.debug(f"[SCOPE SELECTOR] -> {action} {plugin.full_plugin_id} @ {scope}")
        self.post_message(self.ScopeSelected(plugin, scope, action))

    def _show_warning(self, message: str) -> None:
        """Show warning message to user."""
        self.app.notify(message, severity="warning")  # type: ignore[attr-defined]

    def action_cancel(self) -> None:
        """Cancel selection."""
        self.hide()
        self.post_message(self.SelectionCancelled())

    @property
    def is_visible(self) -> bool:
        """Check if the scope selector is visible."""
        return self.has_class("visible")
