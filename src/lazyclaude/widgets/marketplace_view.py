"""Marketplace browser view widget."""

import os
import shlex
import subprocess
from dataclasses import replace

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Tree

from lazyclaude.models.marketplace import (
    MarketplaceState,
    PluginState,
)
from lazyclaude.services.unified_data_loader import UnifiedDataLoader
from lazyclaude.widgets.filter_input import FilterInput
from lazyclaude.widgets.helpers.rendering import format_keybinding
from lazyclaude.widgets.marketplace_info_panel import MarketplaceInfoPanel
from lazyclaude.widgets.scope_selector import ScopeSelector


class MarketplaceView(Widget):
    """View for browsing marketplaces and their plugins."""

    BINDINGS = [
        Binding("escape", "cancel_filter", "Cancel", show=False),
        Binding("/", "search", "Search", show=False),
        # Shift+key bindings for plugin actions
        Binding("I", "install_plugin", "Install", show=False),
        Binding("E", "enable_plugin", "Enable", show=False),
        Binding("D", "disable_plugin", "Disable", show=False),
        Binding("U", "uninstall", "Uninstall", show=False),
        Binding("A", "add_marketplace", "Add MarketplaceState", show=False),
        # Lowercase bindings
        Binding("i", "toggle_installed_filter", "Installed Only", show=False),
        Binding("n", "toggle_enabled_filter", "Enabled Only", show=False),
        Binding("p", "preview_plugin", "Preview", show=False),
        Binding("e", "open_plugin_folder", "Edit", show=False),
        Binding("o", "open_source", "Open", show=False),
        Binding("u", "update_marketplace", "Update", show=False),
        # Navigation bindings
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("space", "toggle_node", "Toggle", show=False),
        Binding("right", "expand_node", "Expand", show=False),
        Binding("l", "expand_node", "Expand", show=False),
        Binding("left", "collapse_node", "Collapse", show=False),
        Binding("h", "collapse_node", "Collapse", show=False),
        Binding("L", "expand_all", "Expand All", show=False),
        Binding("H", "collapse_all", "Collapse All", show=False),
    ]

    DEFAULT_CSS = """
    MarketplaceView {
        display: none;
        width: 100%;
        height: 100%;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
        layout: grid;
        grid-size: 1 2;
        grid-rows: 2fr 1fr;
    }

    MarketplaceView.visible {
        display: block;
    }

    MarketplaceView:focus-within {
        border: solid $accent;
    }

    MarketplaceView #marketplace-tree {
        height: 100%;
        padding: 0 1;
        scrollbar-gutter: stable;
        row-span: 1;
    }

    MarketplaceView MarketplaceInfoPanel {
        height: 100%;
        row-span: 2;
    }

    MarketplaceView FilterInput {
        dock: bottom;
        height: 3;
        background: $surface;
        border-top: solid $primary;
    }
    """

    can_focus = True

    class PluginUninstall(Message):
        """Emitted when a plugin uninstall is requested."""

        def __init__(self, plugin: PluginState) -> None:
            self.plugin = plugin
            super().__init__()

    class OpenPluginFolder(Message):
        """Emitted when user requests to open plugin folder."""

        def __init__(self, plugin: PluginState) -> None:
            self.plugin = plugin
            super().__init__()

    class OpenPluginSource(Message):
        """Emitted when user requests to open plugin source location."""

        def __init__(self, plugin: PluginState, marketplace: MarketplaceState) -> None:
            self.plugin = plugin
            self.marketplace = marketplace
            super().__init__()

    class OpenMarketplaceFolder(Message):
        """Emitted when user requests to open marketplace folder."""

        def __init__(self, marketplace: MarketplaceState) -> None:
            self.marketplace = marketplace
            super().__init__()

    class OpenMarketplaceSource(Message):
        """Emitted when user requests to open marketplace source location."""

        def __init__(self, marketplace: MarketplaceState) -> None:
            self.marketplace = marketplace
            super().__init__()

    class MarketplaceUpdate(Message):
        """Emitted when user requests to update a marketplace."""

        def __init__(self, marketplace: MarketplaceState) -> None:
            self.marketplace = marketplace
            super().__init__()

    class MarketplaceAdd(Message):
        """Emitted when user requests to add a marketplace."""

        def __init__(self, source: str) -> None:
            self.source = source
            super().__init__()

    class PluginPreview(Message):
        """Emitted when user requests to preview a plugin."""

        def __init__(self, plugin: PluginState) -> None:
            self.plugin = plugin
            super().__init__()

    class PluginUpdate(Message):
        """Emitted when user requests to update a plugin."""

        def __init__(self, plugin: PluginState) -> None:
            self.plugin = plugin
            super().__init__()

    class ScopeSelected(Message):
        """Emitted when user selects a scope for plugin action."""

        def __init__(self, plugin: PluginState, scope: str, action: str) -> None:
            self.plugin = plugin
            self.scope = scope
            self.action = action
            super().__init__()

    class MarketplaceRemove(Message):
        """Emitted when user requests to remove a marketplace."""

        def __init__(self, marketplace: MarketplaceState) -> None:
            self.marketplace = marketplace
            super().__init__()

    class MarketplaceAddRequest(Message):
        """Emitted when user wants to add a marketplace."""

        pass

    class FooterChanged(Message):
        """Emitted when footer content should be updated."""

        pass

    def __init__(
        self,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._loader: UnifiedDataLoader | None = None
        self._marketplaces: list[MarketplaceState] = []
        self._marketplace_order: list[str] = []
        self._tree: Tree[PluginState | MarketplaceState | None] | None = None
        self._filter_query: str = ""
        self._filter_input: FilterInput | None = None
        self._scope_selector: ScopeSelector | None = None
        self._info_panel: MarketplaceInfoPanel | None = None
        self._installed_only_filter: bool = False
        self._enabled_only_filter: bool = False
        self._auto_collapse: bool = True
        self._collapsed_marketplaces: set[str] = (
            set()
        )  # Track collapsed, default=expanded
        self._selected_data: PluginState | MarketplaceState | None = None

    def compose(self) -> ComposeResult:
        tree: Tree[PluginState | MarketplaceState | None] = Tree(
            "MarketplaceState Browser", id="marketplace-tree"
        )
        tree.show_root = False
        self._tree = tree
        yield tree
        self._info_panel = MarketplaceInfoPanel()
        yield self._info_panel
        self._filter_input = FilterInput(id="marketplace-filter")
        yield self._filter_input
        self._scope_selector = ScopeSelector()
        yield self._scope_selector

    def on_tree_node_highlighted(
        self, event: Tree.NodeHighlighted[PluginState | MarketplaceState | None]
    ) -> None:
        """Update selection and info panel."""
        self._selected_data = event.node.data
        if self._info_panel:
            self._info_panel.set_data(event.node.data)
        self.post_message(self.FooterChanged())

    def get_footer_text(self) -> str:
        """Return footer text based on current selection and filter state."""
        installed_filter = format_keybinding(
            "i", "Installed", active=self._installed_only_filter
        )
        enabled_filter = format_keybinding(
            "n", "Enabled", active=self._enabled_only_filter
        )
        search_filter = format_keybinding(
            "/", "Search", active=bool(self._filter_query)
        )

        sep = "[dim]|[/]"
        nav = f"{installed_filter}  {enabled_filter}  {search_filter}  [bold]L[/] Expand  [bold]H[/] Collapse"

        if isinstance(self._selected_data, PluginState):
            view = "[bold]o[/] Open  [bold]e[/] Edit  [bold]p[/] Preview"
            actions = "[bold]A[/] Add  [bold]I[/] Install  [bold]E[/] Enable  [bold]D[/] Disable  [bold]u[/] Update  [bold]U[/] Remove"
            return f"{view}  {sep}  {actions}  {sep}  {nav}"
        elif isinstance(self._selected_data, MarketplaceState):
            view = "[bold]o[/] Open  [bold]e[/] Edit"
            actions = "[bold]A[/] Add  [bold]u[/] Update  [bold]U[/] Remove"
            return f"{view}  {sep}  {actions}  {sep}  {nav}"
        else:
            return f"[bold]A[/] Add  {sep}  {nav}"

    @staticmethod
    def _plugin_to_scope_status(plugin: PluginState) -> dict[str, str]:
        """Convert PluginState to scope_status dict for ScopeSelector."""
        scope_status: dict[str, str] = {}
        for scope_name in ["user", "project", "local"]:
            scope = getattr(plugin, scope_name)
            if scope.installed:
                if scope.enabled is False:
                    scope_status[scope_name] = "disabled"
                else:
                    scope_status[scope_name] = "enabled"
            elif scope.enabled is not None:
                if scope.enabled:
                    scope_status[scope_name] = "override_enabled"
                else:
                    scope_status[scope_name] = "override_disabled"
            else:
                scope_status[scope_name] = "not_installed"
        return scope_status

    def set_loader(self, loader: UnifiedDataLoader) -> None:
        """Set the unified data loader."""
        self._loader = loader

    def show(self, preserve_state: bool = False, auto_collapse: bool = True) -> None:
        """Show the modal and load marketplace data."""
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            f"[MARKETPLACE VIEW] show() called, preserve_state={preserve_state}"
        )

        if not preserve_state:
            logger.debug("[MARKETPLACE VIEW] Loading data and building tree")
            self._installed_only_filter = False
            self._enabled_only_filter = False
            self._auto_collapse = auto_collapse
            self._marketplace_order = []
            self._collapsed_marketplaces.clear()  # Reset expand state on fresh open
            self._load_data()
            self._build_tree()
            self._select_first_node()
        self.add_class("visible")
        logger.debug("[MARKETPLACE VIEW] Added 'visible' class")
        if self._tree:
            self._tree.focus()
            logger.debug("[MARKETPLACE VIEW] Focused tree")

    def _select_first_node(self) -> None:
        """Select the first marketplace node in the tree."""
        if self._tree and self._tree.root.children:
            first_node = self._tree.root.children[0]
            self._tree.move_cursor(first_node)
            self._selected_data = first_node.data
            self.post_message(self.FooterChanged())

    def hide(self, preserve_state: bool = False) -> None:
        """Hide the modal."""
        self.remove_class("visible")
        if not preserve_state:
            self._filter_query = ""
            if self._filter_input:
                self._filter_input.clear()
                self._filter_input.hide()

    def _load_data(self) -> None:
        """Load marketplace data from the loader."""
        if self._loader:
            marketplace_states = self._loader.load_marketplace_states()
            if not self._marketplace_order:
                marketplace_states.sort(
                    key=lambda m: sum(
                        1 for p in m.plugins if p.is_accessible_in_current_project
                    ),
                    reverse=True,
                )
                self._marketplace_order = [m.name for m in marketplace_states]
            else:
                order_map = {name: i for i, name in enumerate(self._marketplace_order)}
                marketplace_states.sort(
                    key=lambda m: order_map.get(m.name, len(order_map))
                )
            self._marketplaces = marketplace_states
        else:
            self._marketplaces = []

    def _build_tree(self) -> None:
        """Build the tree widget with marketplace data."""
        if not self._tree:
            return

        # Update persistent collapsed state from current tree
        for node in self._tree.root.children:
            if isinstance(node.data, MarketplaceState):
                name = node.data.name
                if node.is_expanded:
                    self._collapsed_marketplaces.discard(name)
                else:
                    self._collapsed_marketplaces.add(name)

        self._tree.clear()

        filtered = self._get_filtered_marketplaces()

        if not filtered:
            if (
                self._filter_query
                or self._installed_only_filter
                or self._enabled_only_filter
            ):
                self._tree.root.add_leaf("[dim italic]No matches found[/]")
            else:
                self._tree.root.add_leaf("[dim italic]No marketplaces found[/]")
            return

        for marketplace in filtered:
            mp_label = self._render_marketplace_label(marketplace)
            mp_node = self._tree.root.add(mp_label, data=marketplace)

            for plugin in marketplace.plugins:
                plugin_label = self._render_plugin_label(plugin)
                mp_node.add_leaf(plugin_label, data=plugin)

            # Restore state: collapsed if in set, otherwise expanded (default)
            if marketplace.name in self._collapsed_marketplaces:
                mp_node.collapse()
            else:
                mp_node.expand()

    def _get_filtered_marketplaces(self) -> list[MarketplaceState]:
        """Get filtered marketplaces based on current filters."""
        if not self._loader:
            return []

        if (
            not self._filter_query
            and not self._installed_only_filter
            and not self._enabled_only_filter
        ):
            return self._marketplaces

        # Manual filtering
        result = self._marketplaces
        filtered_marketplaces: list[MarketplaceState] = []
        for mp in result:
            filtered_plugins = mp.plugins

            if self._installed_only_filter:
                filtered_plugins = [
                    p for p in filtered_plugins if p.is_installed_anywhere
                ]

            if self._enabled_only_filter:
                filtered_plugins = [p for p in filtered_plugins if p.effective_enabled]

            if self._filter_query:
                query_lower = self._filter_query.lower()
                filtered_plugins = [
                    p
                    for p in filtered_plugins
                    if query_lower in p.name.lower()
                    or query_lower in (p.description or "").lower()
                ]

            if filtered_plugins:
                filtered_marketplaces.append(replace(mp, plugins=filtered_plugins))

        return filtered_marketplaces

    @staticmethod
    def _is_semver(version: str | None) -> bool:
        """Check if version string is semver (x.y.z format)."""
        if not version:
            return False
        try:
            parts = version.split(".")
            return len(parts) >= 2 and all(part.isdigit() for part in parts)
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _parse_version(version_str: str) -> tuple[int, ...]:
        """Parse version string into comparable tuple of integers."""
        return tuple(int(part) for part in version_str.split("."))

    def _has_update(self, installed: str, available: str) -> bool:
        """Check if available version is newer than installed."""
        if not self._is_semver(installed) or not self._is_semver(available):
            return False
        try:
            return self._parse_version(available) > self._parse_version(installed)
        except ValueError:
            return False

    def _render_marketplace_label(self, marketplace: MarketplaceState) -> str:
        """Render a marketplace node label."""
        total = len(marketplace.plugins)
        installed = sum(1 for p in marketplace.plugins if p.is_installed_anywhere)

        # Add description if available
        desc_part = f" - {marketplace.description}" if marketplace.description else ""

        source_info = (
            f" [dim]({marketplace.source_url})[/]" if marketplace.source_url else ""
        )

        return (
            f"[bold]{marketplace.name}[/] [{installed}/{total}]{desc_part}{source_info}"
        )

    def _render_plugin_label(self, plugin: PluginState) -> str:
        """Render a plugin node label."""
        # Use unified format_scope_display: Ie/Id/e/d/-
        status_display = plugin.format_scope_display()
        status_icon = f"[{status_display}]" if plugin.is_installed_anywhere else "[ ]"

        # Get version from first available scope
        version = plugin.user.version or plugin.project.version or plugin.local.version
        version_display = ""
        if version:
            version_display = f" [dim]({version})[/]"

        desc = f" - {plugin.description}" if plugin.description else ""
        max_desc_len = 80
        if len(desc) > max_desc_len:
            desc = desc[: max_desc_len - 3] + "..."

        return f"{status_icon} {plugin.name}{version_display}{desc}"

    def action_cancel_filter(self) -> None:
        """Cancel filter input if visible."""
        if self._filter_input and self._filter_input.is_visible:
            self._filter_input.action_cancel()

    def action_search(self) -> None:
        """Show the filter input."""
        if self._filter_input:
            self._filter_input.show()

    def action_toggle_installed_filter(self) -> None:
        """Toggle installed-only filter."""
        self._installed_only_filter = not self._installed_only_filter
        self._rebuild_tree_preserving_cursor()

    def action_toggle_enabled_filter(self) -> None:
        """Toggle enabled-only filter."""
        self._enabled_only_filter = not self._enabled_only_filter
        self._rebuild_tree_preserving_cursor()

    def _rebuild_tree_preserving_cursor(self) -> None:
        """Rebuild tree while preserving cursor position by ID."""
        selected_id: str | None = None
        if self._tree and self._tree.cursor_node:
            data = self._tree.cursor_node.data
            if isinstance(data, PluginState):
                selected_id = data.plugin_id
            elif isinstance(data, MarketplaceState):
                selected_id = f"marketplace:{data.name}"

        self._build_tree()

        if selected_id and self._tree:
            self._tree.call_after_refresh(self._restore_cursor, selected_id)
        else:
            self._update_footer_for_current_selection()

    def _update_footer_for_current_selection(self) -> None:
        """Update footer based on current tree selection."""
        if self._tree and self._tree.cursor_node:
            self._selected_data = self._tree.cursor_node.data
        else:
            self._selected_data = None
        self.post_message(self.FooterChanged())

    def on_filter_input_filter_changed(self, event: FilterInput.FilterChanged) -> None:
        """Handle real-time filter changes."""
        self._filter_query = event.query
        self._rebuild_tree_preserving_cursor()

    def on_filter_input_filter_cancelled(
        self,
        event: FilterInput.FilterCancelled,  # noqa: ARG002
    ) -> None:
        """Handle filter cancellation."""
        self._filter_query = ""
        self._rebuild_tree_preserving_cursor()
        if self._tree:
            self._tree.focus()

    def on_filter_input_filter_applied(
        self,
        event: FilterInput.FilterApplied,  # noqa: ARG002
    ) -> None:
        """Handle filter applied (Enter)."""
        if self._filter_input:
            self._filter_input.hide()
        if self._tree:
            self._tree.focus()

    def action_uninstall(self) -> None:
        """Uninstall plugin (with scope selector) or remove marketplace."""
        if not self._tree:
            return

        node = self._tree.cursor_node
        if node is None:
            return

        data = node.data
        if isinstance(data, PluginState) and self._scope_selector:
            # Show scope selector for uninstall
            self._scope_selector.show(
                data, self._plugin_to_scope_status(data), action="uninstall"
            )
        elif isinstance(data, MarketplaceState):
            # Remove marketplace
            self.post_message(self.MarketplaceRemove(data))

    def action_install_plugin(self) -> None:
        """Install the selected plugin with scope selector."""
        if not self._tree:
            return

        node = self._tree.cursor_node
        if node is None:
            return

        data = node.data
        if isinstance(data, PluginState) and self._scope_selector:
            self._scope_selector.show(
                data, self._plugin_to_scope_status(data), action="install"
            )

    def action_enable_plugin(self) -> None:
        """Enable the selected plugin with scope selector."""
        if not self._tree:
            return

        node = self._tree.cursor_node
        if node is None:
            return

        data = node.data
        if isinstance(data, PluginState) and self._scope_selector:
            self._scope_selector.show(
                data, self._plugin_to_scope_status(data), action="enable"
            )

    def action_disable_plugin(self) -> None:
        """Disable the selected plugin with scope selector."""
        if not self._tree:
            return

        node = self._tree.cursor_node
        if node is None:
            return

        data = node.data
        if isinstance(data, PluginState) and self._scope_selector:
            self._scope_selector.show(
                data, self._plugin_to_scope_status(data), action="disable"
            )

    def action_open_plugin_folder(self) -> None:
        """Open the selected marketplace or plugin folder."""
        if not self._tree:
            return

        node = self._tree.cursor_node
        if node is None:
            return

        data = node.data
        if isinstance(data, MarketplaceState):
            # Open marketplace install directory
            self.post_message(self.OpenMarketplaceFolder(data))
        elif isinstance(data, PluginState):
            # Open plugin folder
            if data.is_installed_anywhere:
                # Installed plugin - open install location
                self.post_message(self.OpenPluginFolder(data))
            elif data.source:
                from ..models.marketplace import extract_source_url

                source_url = extract_source_url(data.source)
                if "://" not in source_url:
                    # Uninstalled plugin with path source - open in marketplace
                    # Source is already downloaded in marketplace repo

                    # Find marketplace for this plugin
                    for marketplace in self._marketplaces:
                        if (
                            marketplace.name == data.marketplace_name
                            and marketplace.install_location
                        ):
                            source_url_path = extract_source_url(data.source)
                            source_path = marketplace.install_location / source_url_path
                            if source_path.exists():
                                editor = os.environ.get("EDITOR", "vi")
                                cmd_str = shlex.join([editor, str(source_path)])
                                subprocess.Popen(cmd_str, shell=True)
                                return
                    self.app.notify(
                        "Plugin source not found in marketplace", severity="error"
                    )
                else:
                    # Uninstalled plugin with remote source (github/url)
                    self.app.notify(
                        "Plugin must be installed to edit", severity="warning"
                    )

    def action_noop(self) -> None:
        """No-op action to prevent default behavior."""
        pass

    def action_open_source(self) -> None:
        """Open the selected item's source location."""
        if not self._tree:
            return

        node = self._tree.cursor_node
        if node is None:
            return

        data = node.data
        if isinstance(data, MarketplaceState):
            self.post_message(self.OpenMarketplaceSource(data))
        elif isinstance(data, PluginState):
            parent = node.parent
            if parent and isinstance(parent.data, MarketplaceState):
                self.post_message(self.OpenPluginSource(data, parent.data))

    def action_update_marketplace(self) -> None:
        """Update the selected marketplace or plugin."""
        if not self._tree:
            return

        node = self._tree.cursor_node
        if node is None:
            return

        data = node.data
        if isinstance(data, MarketplaceState):
            self.post_message(self.MarketplaceUpdate(data))
        elif isinstance(data, PluginState) and data.is_installed_anywhere:
            self.post_message(self.PluginUpdate(data))

    def action_preview_plugin(self) -> None:
        """Preview the selected plugin's customizations."""
        if not self._tree:
            return

        node = self._tree.cursor_node
        if node is None:
            return

        data = node.data
        if isinstance(data, PluginState):
            if data.is_installed_anywhere:
                self.post_message(self.PluginPreview(data))
            elif data.source:
                from ..models.marketplace import extract_source_url

                source_url = extract_source_url(data.source)
                if "://" not in source_url:
                    # Uninstalled plugin with path source - preview from marketplace
                    # Find marketplace for this plugin
                    for marketplace in self._marketplaces:
                        if (
                            marketplace.name == data.marketplace_name
                            and marketplace.install_location
                        ):
                            source_url_path = extract_source_url(data.source)
                            source_path = marketplace.install_location / source_url_path
                            if source_path.exists():
                                # Plugin source exists in marketplace - preview it
                                self.post_message(self.PluginPreview(data))
                                return
                    self.app.notify(
                        "Plugin source not found in marketplace", severity="error"
                    )
                else:
                    self.app.notify(
                        "Plugin must be installed to preview", severity="warning"
                    )
        elif isinstance(data, MarketplaceState):
            self.app.notify(
                "Preview is only available for plugins, not marketplaces",
                severity="warning",
            )

    def action_cursor_down(self) -> None:
        """Move cursor down in tree."""
        if self._tree:
            self._tree.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up in tree."""
        if self._tree:
            self._tree.action_cursor_up()

    def action_toggle_node(self) -> None:
        """Toggle node expansion."""
        if self._tree:
            self._tree.action_select_cursor()

    def action_expand_node(self) -> None:
        """Expand current node."""
        if self._tree and self._tree.cursor_node:
            self._tree.cursor_node.expand()

    def action_collapse_node(self) -> None:
        """Collapse current node."""
        if self._tree and self._tree.cursor_node:
            self._tree.cursor_node.collapse()

    def action_expand_all(self) -> None:
        """Expand all marketplace nodes."""
        if self._tree:
            for node in self._tree.root.children:
                node.expand()

    def action_collapse_all(self) -> None:
        """Collapse all marketplace nodes."""
        if self._tree:
            for node in self._tree.root.children:
                node.collapse()

    def refresh_tree(self) -> None:
        """Refresh the tree after changes, preserving cursor position."""
        selected_id: str | None = None
        if self._tree and self._tree.cursor_node:
            data = self._tree.cursor_node.data
            if isinstance(data, PluginState):
                selected_id = data.plugin_id
            elif isinstance(data, MarketplaceState):
                selected_id = f"marketplace:{data.name}"

        # Loader is stateless, just reload data
        self._load_data()
        self._build_tree()

        if selected_id and self._tree:
            self._tree.call_after_refresh(self._restore_cursor, selected_id)

    def _restore_cursor(self, selected_id: str) -> None:
        """Restore cursor to the node with the given ID."""
        if not self._tree:
            return

        for node in self._tree.root.children:
            data = node.data
            if isinstance(data, MarketplaceState):
                if selected_id == f"marketplace:{data.name}":
                    self._tree.move_cursor(node)
                    self._selected_data = data
                    self.post_message(self.FooterChanged())
                    return
                for child in node.children:
                    child_data = child.data
                    if (
                        isinstance(child_data, PluginState)
                        and child_data.plugin_id == selected_id
                    ):
                        self._tree.move_cursor(child)
                        self._selected_data = child_data
                        self.post_message(self.FooterChanged())
                        return

    def on_scope_selector_scope_selected(
        self, message: ScopeSelector.ScopeSelected
    ) -> None:
        """Handle scope selection from scope selector."""
        # Emit to parent for handling
        self.post_message(
            self.ScopeSelected(message.plugin, message.scope, message.action)
        )

    def on_scope_selector_selection_cancelled(
        self,
        message: ScopeSelector.SelectionCancelled,  # noqa: ARG002
    ) -> None:
        """Handle scope selector cancellation."""
        # Just return focus to tree
        if self._tree:
            self._tree.focus()

    def action_add_marketplace(self) -> None:
        """Request to add a new marketplace."""
        self.post_message(self.MarketplaceAddRequest())

    @property
    def is_visible(self) -> bool:
        """Check if the modal is visible."""
        return self.has_class("visible")

    def focus_tree(self) -> None:
        """Focus the tree widget for keyboard navigation."""
        if self._tree:
            self._tree.focus()
