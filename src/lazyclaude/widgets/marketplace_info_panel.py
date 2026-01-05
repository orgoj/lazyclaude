"""Info panel for displaying marketplace and plugin metadata."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from lazyclaude.models.marketplace import MarketplaceState, PluginState


class MarketplaceInfoPanel(Widget):
    """Panel showing marketplace/plugin metadata with scrollable content."""

    can_focus = False

    DEFAULT_CSS = """
    MarketplaceInfoPanel {
        height: 1fr;
        border-top: solid $primary;
        background: $surface;
        padding: 1;
        overflow-y: auto;
    }

    MarketplaceInfoPanel VerticalScroll {
        height: 100%;
        scrollbar-gutter: stable;
    }

    .info-label {
        text-style: bold;
        color: $accent;
        margin-top: 1;
    }

    .info-value {
        margin-left: 2;
        text-style: dim;
    }

    .info-section {
        margin-top: 1;
    }
    """

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self._data: PluginState | MarketplaceState | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield VerticalScroll()

    def set_data(self, data: PluginState | MarketplaceState | None) -> None:
        """Update panel with selected item data."""
        self._data = data
        self._update_content()

    def _update_content(self) -> None:
        """Rebuild content based on current data."""
        # Guard against calling before widget is mounted
        if not self.is_mounted:
            return

        try:
            scroll = self.query_one(VerticalScroll)
        except Exception:
            # Widget not ready yet, will be called again
            return

        scroll.remove_children()

        if not self._data:
            return

        if isinstance(self._data, MarketplaceState):
            self._render_marketplace_info(scroll, self._data)
        elif isinstance(self._data, PluginState):
            self._render_plugin_info(scroll, self._data)

    def _render_marketplace_info(
        self, scroll: VerticalScroll, marketplace: MarketplaceState
    ) -> None:
        """Render marketplace metadata."""
        # Name
        self._add_field(scroll, "Name", marketplace.name)

        # Description (full, scrollable)
        if marketplace.description:
            self._add_field(scroll, "Description", marketplace.description)

        # Author (flatten dict)
        if marketplace.author and isinstance(marketplace.author, dict):
            for key, value in marketplace.author.items():
                if value:
                    self._add_field(scroll, key.title(), str(value))

        # Stats
        total = len(marketplace.plugins)
        installed = sum(1 for p in marketplace.plugins if p.is_installed_anywhere)
        self._add_field(scroll, "Plugins", f"{installed}/{total} installed")

    def _render_plugin_info(self, scroll: VerticalScroll, plugin: PluginState) -> None:
        """Render plugin metadata."""
        # Name
        self._add_field(scroll, "Name", plugin.name)

        # Description (full, no truncation)
        if plugin.description:
            self._add_field(scroll, "Description", plugin.description)

        # Source - construct full URL for github marketplaces
        if plugin.source:
            from pathlib import Path

            # Try to construct GitHub URL for github marketplaces
            # Convert source to string (can be str or dict)
            if isinstance(plugin.source, dict):
                source_display = str(plugin.source)
            else:
                source_display = plugin.source

            if hasattr(plugin, "marketplace_name"):
                marketplaces_file = (
                    Path.home() / ".claude" / "plugins" / "known_marketplaces.json"
                )
                if marketplaces_file.is_file():
                    try:
                        import json

                        data = json.loads(marketplaces_file.read_text(encoding="utf-8"))
                        mp_data = data.get(plugin.marketplace_name, {})
                        source = mp_data.get("source", {})

                        if source.get("source") == "github":
                            repo = source.get("repo", "")
                            plugin_path = (
                                plugin.source if isinstance(plugin.source, str) else ""
                            )

                            # Construct GitHub URL
                            if repo:
                                github_url = f"https://github.com/{repo}"
                                if plugin_path:
                                    clean_path = plugin_path.lstrip("./").rstrip("/")
                                    github_url = f"{github_url}/tree/main/{clean_path}"
                                source_display = github_url
                    except (OSError, json.JSONDecodeError):
                        pass

            self._add_field(scroll, "Source", source_display)

        # Version
        installed_version = (
            plugin.user.version or plugin.project.version or plugin.local.version
        )
        if installed_version:
            self._add_field(scroll, "Version", f"{installed_version} (installed)")

        # Author (flatten dict)
        if plugin.author and isinstance(plugin.author, dict):
            for key, value in plugin.author.items():
                if value and key != "name":  # Skip name, already shown
                    self._add_field(scroll, f"Author {key.title()}", str(value))

        # Homepage
        if plugin.homepage:
            self._add_field(scroll, "Homepage", plugin.homepage)

        # Repository
        if plugin.repository:
            self._add_field(scroll, "Repository", plugin.repository)

        # License
        if plugin.license:
            self._add_field(scroll, "License", plugin.license)

        # Category
        if plugin.category:
            self._add_field(scroll, "Category", plugin.category)

        # Keywords
        if plugin.keywords:
            keywords_str = ", ".join(plugin.keywords[:5])  # Show first 5
            if len(plugin.keywords) > 5:
                keywords_str += f" ... ({len(plugin.keywords)} total)"
            self._add_field(scroll, "Keywords", keywords_str)

        # Scope status
        scopes_display = plugin.format_scope_display()
        self._add_field(scroll, "Status", scopes_display)

    def _add_field(self, scroll: VerticalScroll, label: str, value: str) -> None:
        """Add a label:value field to the content."""
        label_widget = Static(f"{label}:", classes="info-label")
        value_widget = Static(value, classes="info-value")
        scroll.mount(label_widget)
        scroll.mount(value_widget)
