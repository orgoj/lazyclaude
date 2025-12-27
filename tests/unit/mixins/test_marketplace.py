"""Unit tests for MarketplaceMixin command builder."""

from unittest.mock import Mock

import pytest

from lazyclaude.mixins.marketplace import MarketplaceMixin
from lazyclaude.models.customization import ConfigLevel
from lazyclaude.models.marketplace import MarketplacePlugin


class TestMarketplaceCommandBuilder:
    """Test CLI command builder for marketplace actions."""

    @pytest.fixture
    def mixin(self):
        """Create a mixin instance for testing."""
        # Create a simple class that uses the mixin
        class TestClass(MarketplaceMixin):
            pass

        return TestClass()

    @pytest.fixture
    def mock_plugin(self):
        """Create a mock MarketplacePlugin."""
        plugin = Mock(spec=MarketplacePlugin)
        plugin.full_plugin_id = "test-plugin@test-marketplace"
        plugin.name = "test-plugin"
        plugin.marketplace_name = "test-marketplace"
        plugin.is_installed = False
        plugin.is_enabled = False
        plugin.install_path = None
        return plugin

    def test_build_install_command_user_scope(self, mixin, mock_plugin):
        """Test building install command with user scope."""
        command = mixin._build_plugin_command_with_scope(mock_plugin, "user", "install")

        assert command == ["claude", "plugin", "install", "-s", "user", "test-plugin@test-marketplace"]

    def test_build_install_command_project_scope(self, mixin, mock_plugin):
        """Test building install command with project scope."""
        command = mixin._build_plugin_command_with_scope(mock_plugin, "project", "install")

        assert command == ["claude", "plugin", "install", "-s", "project", "test-plugin@test-marketplace"]

    def test_build_install_command_local_scope(self, mixin, mock_plugin):
        """Test building install command with local scope."""
        command = mixin._build_plugin_command_with_scope(mock_plugin, "local", "install")

        assert command == ["claude", "plugin", "install", "-s", "local", "test-plugin@test-marketplace"]

    def test_build_enable_command_user_scope(self, mixin, mock_plugin):
        """Test building enable command with user scope."""
        command = mixin._build_plugin_command_with_scope(mock_plugin, "user", "enable")

        assert command == ["claude", "plugin", "enable", "-s", "user", "test-plugin@test-marketplace"]

    def test_build_enable_command_project_scope(self, mixin, mock_plugin):
        """Test building enable command with project scope."""
        command = mixin._build_plugin_command_with_scope(mock_plugin, "project", "enable")

        assert command == ["claude", "plugin", "enable", "-s", "project", "test-plugin@test-marketplace"]

    def test_build_enable_command_local_scope(self, mixin, mock_plugin):
        """Test building enable command with local scope."""
        command = mixin._build_plugin_command_with_scope(mock_plugin, "local", "enable")

        assert command == ["claude", "plugin", "enable", "-s", "local", "test-plugin@test-marketplace"]

    def test_build_disable_command_user_scope(self, mixin, mock_plugin):
        """Test building disable command with user scope."""
        command = mixin._build_plugin_command_with_scope(mock_plugin, "user", "disable")

        assert command == ["claude", "plugin", "disable", "-s", "user", "test-plugin@test-marketplace"]

    def test_build_disable_command_project_scope(self, mixin, mock_plugin):
        """Test building disable command with project scope."""
        command = mixin._build_plugin_command_with_scope(mock_plugin, "project", "disable")

        assert command == ["claude", "plugin", "disable", "-s", "project", "test-plugin@test-marketplace"]

    def test_build_disable_command_local_scope(self, mixin, mock_plugin):
        """Test building disable command with local scope."""
        command = mixin._build_plugin_command_with_scope(mock_plugin, "local", "disable")

        assert command == ["claude", "plugin", "disable", "-s", "local", "test-plugin@test-marketplace"]

    def test_build_uninstall_command_user_scope(self, mixin, mock_plugin):
        """Test building uninstall command with user scope."""
        command = mixin._build_plugin_command_with_scope(mock_plugin, "user", "uninstall")

        assert command == ["claude", "plugin", "uninstall", "-s", "user", "test-plugin@test-marketplace"]

    def test_build_uninstall_command_project_scope(self, mixin, mock_plugin):
        """Test building uninstall command with project scope."""
        command = mixin._build_plugin_command_with_scope(mock_plugin, "project", "uninstall")

        assert command == ["claude", "plugin", "uninstall", "-s", "project", "test-plugin@test-marketplace"]

    def test_build_uninstall_command_local_scope(self, mixin, mock_plugin):
        """Test building uninstall command with local scope."""
        command = mixin._build_plugin_command_with_scope(mock_plugin, "local", "uninstall")

        assert command == ["claude", "plugin", "uninstall", "-s", "local", "test-plugin@test-marketplace"]

    def test_build_plugin_command_invalid_action(self, mixin, mock_plugin):
        """Test that invalid action returns empty command."""
        command = mixin._build_plugin_command_with_scope(mock_plugin, "user", "invalid_action")

        assert command == []

    def test_command_structure(self, mixin, mock_plugin):
        """Test that all commands follow the correct structure."""
        # All commands should start with 'claude plugin'
        for action, scope in [
            ("install", "user"),
            ("enable", "project"),
            ("disable", "local"),
            ("uninstall", "user"),
        ]:
            command = mixin._build_plugin_command_with_scope(mock_plugin, scope, action)

            assert command[0] == "claude"
            assert command[1] == "plugin"
            assert command[2] == action
            assert command[3] == "-s"
            assert command[4] in ["user", "project", "local"]
            assert command[5] == mock_plugin.full_plugin_id
