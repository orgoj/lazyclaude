"""Data models for marketplace plugins."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def extract_source_url(source: str | dict[str, Any]) -> str:
    """Extract URL from source (handle both string and dict formats).

    Args:
        source: Either a URL string or a dict with 'url' key

    Returns:
        The source URL as a string
    """
    if isinstance(source, dict):
        url = source.get("url")
        return str(url) if url is not None else str(source)
    return source


@dataclass
class MarketplaceSource:
    """Source configuration for a marketplace."""

    source_type: str  # "github" or "directory"
    repo: str | None = None
    path: str | None = None


@dataclass
class MarketplaceEntry:
    """A marketplace entry from known_marketplaces.json."""

    name: str
    source: MarketplaceSource
    install_location: Path
    last_updated: str | None = None
    description: str | None = None  # From marketplace.json root or metadata
    owner: dict[str, str] | None = None  # {"name": "...", "email": "...", "url": "..."}
    metadata: dict[str, Any] | None = None  # {"version": "...", "description": "..."}


@dataclass
class MarketplacePlugin:
    """A plugin available in a marketplace."""

    name: str
    description: str
    source: str
    marketplace_name: str
    full_plugin_id: str
    is_installed: bool = False
    is_enabled: bool = True
    install_path: Path | None = None
    installed_version: str | None = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)
    scope_status: dict[str, str] = field(
        default_factory=dict
    )  # {"user": "enabled", ...}
    # Additional metadata from marketplace.json
    author: dict[str, str] | None = (
        None  # {"name": "...", "email": "...", "url": "..."}
    )
    source_raw: str | dict[str, Any] | None = None  # Raw source from JSON
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None
    category: str | None = None
    keywords: list[str] | None = None


@dataclass
class Marketplace:
    """A fully loaded marketplace with its plugins."""

    entry: MarketplaceEntry
    plugins: list[MarketplacePlugin] = field(default_factory=list)
    error: str | None = None


# Unified Data Model (read-only display layer)


@dataclass
class ScopeState:
    """State of plugin/marketplace in one scope (user/project/local)."""

    installed: bool
    enabled: bool | None = None  # None = no override in settings.json
    install_path: Path | None = None
    version: str | None = None


@dataclass
class MarketplaceState:
    """Unified marketplace state across all scopes."""

    name: str
    source_url: str
    description: str = ""
    author: dict[str, Any] | None = None
    install_location: Path | None = None
    user: ScopeState = field(default_factory=lambda: ScopeState(installed=False))
    project: ScopeState = field(default_factory=lambda: ScopeState(installed=False))
    local: ScopeState = field(default_factory=lambda: ScopeState(installed=False))
    plugins: list["PluginState"] = field(default_factory=list)

    def format_scope_display(self) -> str:
        """Format status as 'user/project/local' e.g: 'I/-/-'."""
        return f"{self._format_scope('user')}/{self._format_scope('project')}/{self._format_scope('local')}"

    def _format_scope(self, scope_name: str) -> str:
        """Format one scope as: I or -."""
        scope = getattr(self, scope_name)
        return "I" if scope.installed else "-"


@dataclass
class PluginState:
    """Unified plugin state across all scopes."""

    plugin_id: str
    name: str
    marketplace_name: str
    user: ScopeState = field(default_factory=lambda: ScopeState(installed=False))
    project: ScopeState = field(default_factory=lambda: ScopeState(installed=False))
    local: ScopeState = field(default_factory=lambda: ScopeState(installed=False))
    description: str = ""
    author: dict[str, Any] | None = None
    source: str | dict[str, Any] = ""
    source_path: str | None = (
        None  # Resolved path (local) or URL (remote) to plugin source
    )
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None
    category: str | None = None
    keywords: list[str] | None = None

    @property
    def is_installed_anywhere(self) -> bool:
        """Is plugin installed in any scope?"""
        return self.user.installed or self.project.installed or self.local.installed

    @property
    def is_accessible_in_current_project(self) -> bool:
        """Is plugin accessible in current project?

        - user installed → YES (available everywhere)
        - project installed → YES (in this project)
        - local installed → YES (in this project)
        """
        return self.user.installed or self.project.installed or self.local.installed

    @property
    def effective_enabled(self) -> bool:
        """Effective enabled state based on hierarchy local > project > user.

        Returns last non-null enabled value, or True if no override.
        """
        if self.local.enabled is not None:
            return self.local.enabled
        if self.project.enabled is not None:
            return self.project.enabled
        if self.user.enabled is not None:
            return self.user.enabled
        return self.is_installed_anywhere

    def format_scope_display(self) -> str:
        """Format status as 'user/project/local' e.g: 'Ie/Id/-'."""
        return f"{self._format_scope('user')}/{self._format_scope('project')}/{self._format_scope('local')}"

    def _format_scope(self, scope_name: str) -> str:
        """Format one scope as: Ie/Id/e/d/-."""
        scope = getattr(self, scope_name)

        if scope.installed:
            if scope.enabled is False:
                return "Id"
            else:
                return "Ie"
        else:
            if scope.enabled is True:
                return "e"
            elif scope.enabled is False:
                return "d"
            else:
                return "-"
