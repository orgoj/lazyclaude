"""Info panel for displaying marketplace and plugin metadata."""

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from lazyclaude.models.marketplace import Marketplace, MarketplacePlugin


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
        self._data: MarketplacePlugin | Marketplace | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield VerticalScroll()

    def set_data(self, data: MarketplacePlugin | Marketplace | None) -> None:
        """Update panel with selected item data."""
        self._data = data
        self._update_content()

    def _update_content(self) -> None:
        """Rebuild content based on current data."""
        scroll = self.query_one(VerticalScroll)
        scroll.remove_children()

        if not self._data:
            return

        if isinstance(self._data, Marketplace):
            self._render_marketplace_info(scroll, self._data)
        elif isinstance(self._data, MarketplacePlugin):
            self._render_plugin_info(scroll, self._data)

    def _render_marketplace_info(
        self, scroll: VerticalScroll, marketplace: Marketplace
    ) -> None:
        """Render marketplace metadata."""
        # Name
        self._add_field(scroll, "Name", marketplace.entry.name)

        # Description (full, scrollable)
        if marketplace.entry.description:
            self._add_field(scroll, "Description", marketplace.entry.description)

        # Owner (flatten dict)
        if marketplace.entry.owner and isinstance(marketplace.entry.owner, dict):
            for key, value in marketplace.entry.owner.items():
                if value:
                    self._add_field(scroll, key.title(), str(value))

        # Metadata (version, etc)
        if marketplace.entry.metadata:
            for key, value in marketplace.entry.metadata.items():
                if key.lower() != "description":  # Skip duplicate description
                    self._add_field(scroll, key.title(), str(value))

        # Stats
        total = len(marketplace.plugins)
        installed = sum(1 for p in marketplace.plugins if p.is_installed)
        self._add_field(scroll, "Plugins", f"{installed}/{total} installed")

    def _render_plugin_info(
        self, scroll: VerticalScroll, plugin: MarketplacePlugin
    ) -> None:
        """Render plugin metadata."""
        # Name
        self._add_field(scroll, "Name", plugin.name)

        # Description (full, no truncation)
        if plugin.description:
            self._add_field(scroll, "Description", plugin.description)

        # Source
        if plugin.source_raw:
            if isinstance(plugin.source_raw, str):
                # Relative path
                self._add_field(scroll, "Source (Path)", plugin.source_raw)
            elif isinstance(plugin.source_raw, dict):
                source_type = plugin.source_raw.get("source", "")
                if source_type == "github":
                    repo = plugin.source_raw.get("repo", "")
                    self._add_field(scroll, "Source (GitHub)", repo)
                elif source_type == "url":
                    url = plugin.source_raw.get("url", "")
                    self._add_field(scroll, "Source (URL)", url)
                else:
                    self._add_field(scroll, "Source", str(plugin.source_raw))

        # Version
        available_version = plugin.extra_metadata.get("version")
        if plugin.installed_version:
            version_str = f"{plugin.installed_version} (installed)"
            if available_version:
                version_str += f", {available_version} (available)"
            self._add_field(scroll, "Version", version_str)
        elif available_version:
            self._add_field(scroll, "Version", f"{available_version} (available)")

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
        if plugin.scope_status:
            scopes = []
            for scope, status in plugin.scope_status.items():
                icon = (
                    "✓" if status == "enabled" else "✗" if status == "disabled" else "○"
                )
                scopes.append(f"{scope}: {icon}")
            self._add_field(scroll, "Scopes", ", ".join(scopes))

        # Other metadata (strict, tags, etc.)
        for key, value in plugin.extra_metadata.items():
            if key != "version":  # Already shown above
                if isinstance(value, list):
                    value_str = ", ".join(str(v) for v in value[:3])
                    if len(value) > 3:
                        value_str += f" ... ({len(value)} total)"
                    self._add_field(scroll, key.title(), value_str)
                elif isinstance(value, bool):
                    self._add_field(scroll, key.title(), "Yes" if value else "No")
                else:
                    self._add_field(scroll, key.title(), str(value))

    def _add_field(self, scroll: VerticalScroll, label: str, value: str) -> None:
        """Add a label:value field to the content."""
        label_widget = Static(f"{label}:", classes="info-label")
        value_widget = Static(value, classes="info-value")
        scroll.mount(label_widget)
        scroll.mount(value_widget)
