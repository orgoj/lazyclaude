"""Tests for PluginDataProvider - single source of truth for plugin data."""

from pathlib import Path

import pytest

from lazyclaude.models.marketplace import (
    Marketplace,
    MarketplaceEntry,
    MarketplacePlugin,
    MarketplaceSource,
)
from lazyclaude.services.plugin_data_provider import PluginDataProvider


@pytest.fixture
def temp_config(tmp_path: Path) -> dict[str, Path]:
    """Create temporary config directories."""
    user_config = tmp_path / "user" / ".claude"
    user_config.mkdir(parents=True)

    project_root = tmp_path / "project"
    project_config = project_root / ".claude"
    project_config.mkdir(parents=True)

    # Create minimal known_marketplaces.json
    plugins_dir = user_config / "plugins"
    plugins_dir.mkdir()
    (plugins_dir / "known_marketplaces.json").write_text("{}")
    (plugins_dir / "installed_plugins.json").write_text('{"plugins": {}}')

    return {
        "user_config": user_config,
        "project_root": project_root,
    }


class TestPluginDataProviderInit:
    """Test PluginDataProvider initialization."""

    def test_requires_explicit_paths(self) -> None:
        """Must provide explicit paths, no cwd fallback."""
        with pytest.raises(TypeError):
            PluginDataProvider()  # type: ignore

    def test_creates_with_explicit_paths(self, temp_config: dict[str, Path]) -> None:
        """Creates successfully with explicit paths."""
        provider = PluginDataProvider(
            user_config_path=temp_config["user_config"],
            project_root=temp_config["project_root"],
        )
        assert provider is not None
        assert provider.user_config_path == temp_config["user_config"]
        assert provider.project_root == temp_config["project_root"]


class TestPluginDataProviderFiltering:
    """Test filtering methods."""

    @pytest.fixture
    def provider_with_plugins(self, temp_config: dict[str, Path]) -> PluginDataProvider:
        """Provider with mocked marketplace data."""
        provider = PluginDataProvider(
            user_config_path=temp_config["user_config"],
            project_root=temp_config["project_root"],
        )

        # Mock the marketplace loader's data
        plugins = [
            MarketplacePlugin(
                name="plugin-a",
                description="Plugin A - enabled in user",
                source="a",
                marketplace_name="market1",
                full_plugin_id="plugin-a@market1",
                is_installed=True,
                is_enabled=True,
                scope_status={
                    "user": "enabled",
                    "project": "not_installed",
                    "local": "not_installed",
                },
            ),
            MarketplacePlugin(
                name="plugin-b",
                description="Plugin B - disabled",
                source="b",
                marketplace_name="market1",
                full_plugin_id="plugin-b@market1",
                is_installed=True,
                is_enabled=False,
                scope_status={
                    "user": "disabled",
                    "project": "not_installed",
                    "local": "not_installed",
                },
            ),
            MarketplacePlugin(
                name="plugin-c",
                description="Plugin C - enabled via local override",
                source="c",
                marketplace_name="market2",
                full_plugin_id="plugin-c@market2",
                is_installed=True,
                is_enabled=True,
                scope_status={
                    "user": "disabled",
                    "project": "not_installed",
                    "local": "override_enabled",
                },
            ),
        ]

        marketplaces = [
            Marketplace(
                entry=MarketplaceEntry(
                    name="market1",
                    source=MarketplaceSource(source_type="github", repo="org/m1"),
                    install_location=Path("/tmp/m1"),
                ),
                plugins=plugins[:2],
            ),
            Marketplace(
                entry=MarketplaceEntry(
                    name="market2",
                    source=MarketplaceSource(source_type="directory", path="/local"),
                    install_location=Path("/tmp/m2"),
                ),
                plugins=plugins[2:],
            ),
        ]

        provider._marketplace_loader._marketplaces_cache = marketplaces
        return provider

    def test_get_all_plugins(self, provider_with_plugins: PluginDataProvider) -> None:
        """Returns all plugins."""
        result = provider_with_plugins.get_all_plugins()
        assert len(result) == 3

    def test_get_filtered_plugins_enabled_only(
        self, provider_with_plugins: PluginDataProvider
    ) -> None:
        """Enabled filter includes override_enabled."""
        result = provider_with_plugins.get_filtered_plugins(enabled_only=True)

        assert len(result) == 2
        ids = {p.full_plugin_id for p in result}
        assert "plugin-a@market1" in ids  # enabled in user
        assert "plugin-c@market2" in ids  # override_enabled in local

    def test_get_filtered_plugins_installed_only(
        self, provider_with_plugins: PluginDataProvider
    ) -> None:
        """Installed filter."""
        result = provider_with_plugins.get_filtered_plugins(installed_only=True)
        assert len(result) == 3
        assert all(p.is_installed for p in result)

    def test_get_filtered_plugins_by_marketplace(
        self, provider_with_plugins: PluginDataProvider
    ) -> None:
        """Marketplace filter."""
        result = provider_with_plugins.get_filtered_plugins(marketplace="market1")
        assert len(result) == 2
        assert all(p.marketplace_name == "market1" for p in result)

    def test_get_filtered_plugins_by_query(
        self, provider_with_plugins: PluginDataProvider
    ) -> None:
        """Query filter searches name and description."""
        result = provider_with_plugins.get_filtered_plugins(query="local override")
        assert len(result) == 1
        assert result[0].full_plugin_id == "plugin-c@market2"

    def test_get_filtered_plugins_combined(
        self, provider_with_plugins: PluginDataProvider
    ) -> None:
        """Multiple filters combined."""
        result = provider_with_plugins.get_filtered_plugins(
            enabled_only=True,
            marketplace="market2",
        )
        assert len(result) == 1
        assert result[0].full_plugin_id == "plugin-c@market2"


class TestPluginDataProviderMarketplaceFiltering:
    """Test marketplace filtering methods."""

    @pytest.fixture
    def provider_with_marketplaces(
        self, temp_config: dict[str, Path]
    ) -> PluginDataProvider:
        """Provider with mocked marketplace data including error marketplace."""
        provider = PluginDataProvider(
            user_config_path=temp_config["user_config"],
            project_root=temp_config["project_root"],
        )

        plugins = [
            MarketplacePlugin(
                name="plugin-a",
                description="Plugin A",
                source="a",
                marketplace_name="market1",
                full_plugin_id="plugin-a@market1",
                is_installed=True,
                is_enabled=True,
                scope_status={
                    "user": "enabled",
                    "project": "not_installed",
                    "local": "not_installed",
                },
            ),
            MarketplacePlugin(
                name="plugin-b",
                description="Plugin B",
                source="b",
                marketplace_name="market2",
                full_plugin_id="plugin-b@market2",
                is_installed=False,
                is_enabled=False,
                scope_status={
                    "user": "not_installed",
                    "project": "not_installed",
                    "local": "not_installed",
                },
            ),
        ]

        marketplaces = [
            Marketplace(
                entry=MarketplaceEntry(
                    name="market1",
                    source=MarketplaceSource(source_type="github", repo="org/m1"),
                    install_location=Path("/tmp/m1"),
                ),
                plugins=[plugins[0]],
            ),
            Marketplace(
                entry=MarketplaceEntry(
                    name="market2",
                    source=MarketplaceSource(source_type="github", repo="org/m2"),
                    install_location=Path("/tmp/m2"),
                ),
                plugins=[plugins[1]],
            ),
            Marketplace(
                entry=MarketplaceEntry(
                    name="error-market",
                    source=MarketplaceSource(source_type="github", repo="org/err"),
                    install_location=Path("/tmp/err"),
                ),
                plugins=[],
                error="Failed to load",
            ),
        ]

        provider._marketplace_loader._marketplaces_cache = marketplaces
        return provider

    def test_get_filtered_marketplaces_no_filters(
        self, provider_with_marketplaces: PluginDataProvider
    ) -> None:
        """No filters returns all marketplaces."""
        result = provider_with_marketplaces.get_filtered_marketplaces()
        assert len(result) == 3

    def test_get_filtered_marketplaces_installed_only(
        self, provider_with_marketplaces: PluginDataProvider
    ) -> None:
        """Installed filter excludes marketplaces without matching plugins."""
        result = provider_with_marketplaces.get_filtered_marketplaces(
            installed_only=True
        )
        assert len(result) == 1
        assert result[0].entry.name == "market1"

    def test_get_filtered_marketplaces_preserves_error_without_installed_filter(
        self, provider_with_marketplaces: PluginDataProvider
    ) -> None:
        """Error marketplaces are preserved when no installed filter."""
        result = provider_with_marketplaces.get_filtered_marketplaces(query="error")
        assert len(result) == 1
        assert result[0].entry.name == "error-market"

    def test_get_filtered_marketplaces_excludes_error_with_installed_filter(
        self, provider_with_marketplaces: PluginDataProvider
    ) -> None:
        """Error marketplaces are excluded when installed filter is on."""
        result = provider_with_marketplaces.get_filtered_marketplaces(
            installed_only=True, query="error"
        )
        assert len(result) == 0


class TestPluginDataProviderRefresh:
    """Test refresh functionality."""

    def test_refresh_clears_caches(self, temp_config: dict[str, Path]) -> None:
        """Refresh clears both loader caches."""
        provider = PluginDataProvider(
            user_config_path=temp_config["user_config"],
            project_root=temp_config["project_root"],
        )

        # Load to populate cache
        provider.get_marketplaces()
        assert provider._marketplace_loader._marketplaces_cache is not None

        # Refresh should clear
        provider.refresh()
        assert provider._marketplace_loader._marketplaces_cache is None
