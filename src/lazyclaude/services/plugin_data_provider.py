"""Single source of truth for plugin data loading and filtering.

This service is used by both CLI and TUI to ensure consistent behavior.
All paths must be explicit - no cwd fallbacks.
"""

from dataclasses import replace
from pathlib import Path

from lazyclaude.models.marketplace import Marketplace, MarketplacePlugin
from lazyclaude.services.marketplace_loader import MarketplaceLoader
from lazyclaude.services.plugin_loader import PluginLoader


class PluginDataProvider:
    """Provides unified access to plugin data for CLI and TUI.

    This is the single source of truth for:
    - Loading marketplace and plugin data
    - Filtering plugins by various criteria
    - Determining plugin enabled/installed status

    Usage:
        provider = PluginDataProvider(
            user_config_path=Path.home() / ".claude",
            project_root=Path("/path/to/project"),
        )
        enabled_plugins = provider.get_filtered_plugins(enabled_only=True)
    """

    def __init__(
        self,
        user_config_path: Path,
        project_root: Path,
    ) -> None:
        """Initialize with explicit paths.

        Args:
            user_config_path: Path to user config (e.g., ~/.claude)
            project_root: Path to project root (contains .claude/)

        Note:
            No cwd fallbacks. Caller must provide explicit paths.
            Entry point (__main__.py) resolves cwd -> --directory default.
        """
        self.user_config_path = user_config_path
        self.project_root = project_root
        self.project_config_path = project_root / ".claude"

        self._plugin_loader = PluginLoader(
            user_config_path=user_config_path,
            project_config_path=self.project_config_path,
            project_root=project_root,
        )
        self._marketplace_loader = MarketplaceLoader(
            user_config_path=user_config_path,
            plugin_loader=self._plugin_loader,
        )

    def get_marketplaces(self) -> list[Marketplace]:
        """Get all marketplaces with their plugins."""
        return self._marketplace_loader.load_marketplaces()

    def get_all_plugins(self) -> list[MarketplacePlugin]:
        """Get all plugins from all marketplaces."""
        plugins: list[MarketplacePlugin] = []
        for marketplace in self.get_marketplaces():
            if marketplace.plugins:
                plugins.extend(marketplace.plugins)
        return plugins

    def get_filtered_plugins(
        self,
        *,
        installed_only: bool = False,
        enabled_only: bool = False,
        marketplace: str | None = None,
        query: str | None = None,
    ) -> list[MarketplacePlugin]:
        """Get plugins with optional filtering.

        This is the single filtering implementation used by CLI and TUI.

        Args:
            installed_only: Only return installed plugins
            enabled_only: Only return enabled plugins (includes override_enabled)
            marketplace: Filter by marketplace name
            query: Search in name and description (case-insensitive)

        Returns:
            List of plugins matching all specified filters
        """
        result = self.get_all_plugins()

        if installed_only:
            result = [p for p in result if p.is_installed]

        if enabled_only:
            result = [p for p in result if p.is_enabled]

        if marketplace:
            result = [p for p in result if p.marketplace_name == marketplace]

        if query:
            query_lower = query.lower()
            result = [
                p
                for p in result
                if query_lower in p.name.lower()
                or query_lower in (p.description or "").lower()
            ]

        return result

    def get_filtered_marketplaces(
        self,
        *,
        installed_only: bool = False,
        enabled_only: bool = False,
        query: str | None = None,
    ) -> list[Marketplace]:
        """Get marketplaces with filtered plugins.

        Used by TUI to maintain tree structure while filtering.

        Args:
            installed_only: Only include installed plugins
            enabled_only: Only include enabled plugins
            query: Search filter

        Returns:
            Marketplaces containing only matching plugins
        """
        if not installed_only and not enabled_only and not query:
            return self.get_marketplaces()

        # Get IDs of plugins that pass the filter
        filtered_ids = {
            p.full_plugin_id
            for p in self.get_filtered_plugins(
                installed_only=installed_only,
                enabled_only=enabled_only,
                query=query,
            )
        }

        # Rebuild marketplaces with only matching plugins
        result: list[Marketplace] = []
        for mp in self.get_marketplaces():
            if mp.error:
                if (
                    not installed_only
                    and not enabled_only
                    and (not query or query.lower() in mp.entry.name.lower())
                ):
                    result.append(mp)
                continue

            matching = [p for p in mp.plugins if p.full_plugin_id in filtered_ids]
            if matching:
                result.append(replace(mp, plugins=matching))

        return result

    def refresh(self) -> None:
        """Clear caches and reload data."""
        self._plugin_loader.refresh()
        self._marketplace_loader.refresh()
