"""Unified data loader for marketplace and plugin state.

This loader creates a read-only unified model from disk files for display purposes.
After CLI commands modify settings.json, reload this model to see updated state.
"""

import json
import logging
from pathlib import Path
from typing import Any

from lazyclaude.models.marketplace import (
    MarketplaceState,
    PluginState,
    ScopeState,
)
from lazyclaude.services.plugin_loader import PluginInstallation

logger = logging.getLogger(__name__)


class UnifiedDataLoader:
    """Loads marketplace and plugin data into unified read-only model."""

    def __init__(
        self,
        user_config_path: Path,
        project_config_path: Path,
        project_root: Path,
    ) -> None:
        """Initialize with explicit paths.

        Args:
            user_config_path: Path to user config (e.g., ~/.claude)
            project_config_path: Path to project config (e.g., ./.claude)
            project_root: Path to project root (for matching project-scoped installs)
        """
        self.user_config_path = user_config_path
        self.project_config_path = project_config_path
        self.project_root = project_root

    def load_marketplace_states(self) -> list[MarketplaceState]:
        """Load marketplaces with their plugins - hierarchical structure for TUI tree.

        Returns:
            List of MarketplaceState with nested PluginState objects
        """
        # Load all data sources
        installed_data = self._load_installed_plugins()
        user_enabled = self._load_enabled_plugins(
            self.user_config_path / "settings.json"
        )
        project_enabled = self._load_enabled_plugins(
            self.project_config_path / "settings.json"
        )
        local_enabled = self._load_enabled_plugins(
            self.project_config_path / "settings.local.json"
        )
        marketplace_entries = self._load_known_marketplaces()

        marketplaces: list[MarketplaceState] = []

        for entry_data in marketplace_entries:
            name = entry_data["name"]
            install_location = Path(entry_data["install_location"])
            source_url = entry_data.get("source_url", "")

            # Load marketplace.json
            marketplace_json_path = (
                install_location / ".claude-plugin" / "marketplace.json"
            )
            plugins_metadata, mp_root_metadata = self._load_marketplace_plugins(
                marketplace_json_path
            )

            # Get description: prefer marketplace.json, fallback to known_marketplaces.json
            mp_description = (
                mp_root_metadata.get("description")
                or mp_root_metadata.get("metadata", {}).get("description")
                or entry_data.get("description")
                or ""
            )

            # Get author: prefer marketplace.json owner, fallback to entry_data author
            mp_author = mp_root_metadata.get("owner") or entry_data.get("author")

            # Build marketplace state
            marketplace_state = MarketplaceState(
                name=name,
                source_url=source_url,
                description=mp_description,
                author=mp_author,
                install_location=install_location,
                user=self._build_marketplace_scope_state(name, "user", installed_data),
                project=self._build_marketplace_scope_state(
                    name, "project", installed_data
                ),
                local=self._build_marketplace_scope_state(
                    name, "local", installed_data
                ),
                plugins=[],
            )

            # Build plugin states
            for plugin_meta in plugins_metadata:
                plugin_name = plugin_meta.get("name", "")
                if not plugin_name:
                    continue

                plugin_id = f"{plugin_name}@{name}"

                plugin_state = PluginState(
                    plugin_id=plugin_id,
                    name=plugin_name,
                    marketplace_name=name,
                    user=self._build_plugin_scope_state(
                        plugin_id, "user", installed_data, user_enabled
                    ),
                    project=self._build_plugin_scope_state(
                        plugin_id, "project", installed_data, project_enabled
                    ),
                    local=self._build_plugin_scope_state(
                        plugin_id, "local", installed_data, local_enabled
                    ),
                    description=plugin_meta.get("description", ""),
                    author=plugin_meta.get("author"),
                    source=plugin_meta.get("source", ""),
                    homepage=plugin_meta.get("homepage"),
                    repository=plugin_meta.get("repository"),
                    license=plugin_meta.get("license"),
                    category=plugin_meta.get("category"),
                    keywords=plugin_meta.get("keywords"),
                )
                marketplace_state.plugins.append(plugin_state)

            marketplaces.append(marketplace_state)

        return marketplaces

    def _load_installed_plugins(self) -> dict[str, list[PluginInstallation]]:
        """Load installed_plugins.json.

        Returns:
            Dict mapping plugin_id to list of installations
        """
        plugins_file = self.user_config_path / "plugins" / "installed_plugins.json"
        if not plugins_file.is_file():
            return {}

        try:
            data = json.loads(plugins_file.read_text(encoding="utf-8"))
            plugins_data = data.get("plugins", {})
            result: dict[str, list[PluginInstallation]] = {}

            for plugin_id, installations in plugins_data.items():
                result[plugin_id] = [
                    PluginInstallation(
                        scope=inst.get("scope", "user"),
                        install_path=inst.get("installPath", ""),
                        version=inst.get("version", "unknown"),
                        is_local=inst.get("isLocal", False),
                        project_path=inst.get("projectPath"),
                    )
                    for inst in installations
                ]
            return result
        except (json.JSONDecodeError, OSError):
            return {}

    def _load_enabled_plugins(self, settings_path: Path) -> dict[str, bool]:
        """Load enabledPlugins from settings.json.

        Args:
            settings_path: Path to settings.json file

        Returns:
            Dict mapping plugin_id to enabled boolean (True/False, not None)
        """
        if not settings_path.is_file():
            return {}

        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            result: dict[str, bool] = data.get("enabledPlugins", {})
            return result
        except (json.JSONDecodeError, OSError):
            return {}

    def _load_known_marketplaces(self) -> list[dict[str, Any]]:
        """Load known_marketplaces.json.

        Returns:
            List of marketplace entries (dicts with name, source_url, etc.)
        """
        known_file = self.user_config_path / "plugins" / "known_marketplaces.json"
        if not known_file.is_file():
            return []

        try:
            data = json.loads(known_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        entries: list[dict[str, Any]] = []
        for name, entry_data in data.items():
            source_data = entry_data.get("source", {})
            source_url = source_data.get("repo") or source_data.get("path", "")

            entries.append(
                {
                    "name": name,
                    "source_url": source_url,
                    "install_location": entry_data.get("installLocation", ""),
                    "description": entry_data.get("description"),
                    "author": entry_data.get("owner"),
                }
            )

        return entries

    def _load_marketplace_plugins(
        self, marketplace_json_path: Path
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Load plugins and metadata from marketplace.json.

        Args:
            marketplace_json_path: Path to marketplace.json file

        Returns:
            Tuple of (plugins list, root metadata dict)
        """
        if not marketplace_json_path.is_file():
            return [], {}

        try:
            data = json.loads(marketplace_json_path.read_text(encoding="utf-8"))
            plugins: list[dict[str, Any]] = data.get("plugins", [])
            # Extract root-level metadata (description, owner, metadata)
            root_metadata = {
                "description": data.get("description"),
                "owner": data.get("owner"),
                "metadata": data.get("metadata", {}),
            }
            return plugins, root_metadata
        except (json.JSONDecodeError, OSError):
            return [], {}

    def _build_marketplace_scope_state(
        self,
        marketplace_name: str,
        scope: str,
        installed_data: dict[str, list[PluginInstallation]],
    ) -> ScopeState:
        """Build ScopeState for marketplace in one scope.

        Marketplace is installed if ANY plugin from it is installed in that scope.

        Args:
            marketplace_name: Name of the marketplace
            scope: Scope name ("user", "project", or "local")
            installed_data: Dict from _load_installed_plugins()

        Returns:
            ScopeState with installed flag
        """
        # Check if any plugin from this marketplace is installed in this scope
        for plugin_id, installations in installed_data.items():
            if f"@{marketplace_name}" not in plugin_id:
                continue

            for inst in installations:
                if inst.scope == scope:
                    # For project/local, must match current project
                    if scope in ("project", "local"):
                        if inst.project_path == str(self.project_root.resolve()):
                            return ScopeState(installed=True)
                    else:  # user scope
                        return ScopeState(installed=True)

        return ScopeState(installed=False)

    def get_plugin_states(self) -> list[PluginState]:
        """Get all plugin states for discovery (like CLI does).

        Returns:
            List of PluginState objects from all marketplaces
        """
        marketplaces = self.load_marketplace_states()
        all_plugins: list[PluginState] = []
        for mp in marketplaces:
            all_plugins.extend(mp.plugins)
        return all_plugins

    def _build_plugin_scope_state(
        self,
        plugin_id: str,
        scope: str,
        installed_data: dict[str, list[PluginInstallation]],
        enabled_map: dict[str, bool],
    ) -> ScopeState:
        """Build ScopeState for one scope from disk data.

        Args:
            plugin_id: Full plugin ID (name@marketplace)
            scope: Scope name ("user", "project", or "local")
            installed_data: Dict from _load_installed_plugins()
            enabled_map: Dict from _load_enabled_plugins()

        Returns:
            ScopeState with installed/enabled/path/version
        """
        installations = installed_data.get(plugin_id, [])

        # Find installation in this scope
        matching_install = None
        for inst in installations:
            if inst.scope == scope:
                # For project/local must match project_path
                if scope in ("project", "local"):
                    if inst.project_path == str(self.project_root.resolve()):
                        matching_install = inst
                        break
                else:  # user scope
                    matching_install = inst
                    break

        # installed = found installation in this scope
        installed = matching_install is not None

        # enabled = value from settings.json enabledPlugins
        # None = not in settings.json (no override)
        enabled = enabled_map.get(plugin_id)  # bool | None

        return ScopeState(
            installed=installed,
            enabled=enabled,
            install_path=Path(matching_install.install_path)
            if matching_install
            else None,
            version=matching_install.version if matching_install else None,
        )
