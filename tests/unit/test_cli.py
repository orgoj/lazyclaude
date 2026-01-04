"""Tests for CLI interface."""

from pathlib import Path
from unittest.mock import patch

import pytest

from lazyclaude.__main__ import main


class TestCLIRouting:
    """Test CLI subcommand routing from __main__.py."""

    def test_cli_subcommand_calls_run_cli(self) -> None:
        """When 'cli' subcommand is used, run_cli is called."""
        with (
            patch("sys.argv", ["lazyclaude", "cli", "list"]),
            patch("lazyclaude.cli.run_cli") as mock_run_cli,
        ):
            mock_run_cli.return_value = 0

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            mock_run_cli.assert_called_once()


class TestListCommand:
    """Test the 'list' CLI command."""

    def test_list_command_outputs_plugin_names(
        self, capsys, fake_home: Path, fs
    ) -> None:
        """List command outputs plugin names in plain text format."""
        # Arrange: Create marketplace structure
        plugins_dir = fake_home / ".claude" / "plugins"
        fs.create_dir(plugins_dir)

        marketplace_file = plugins_dir / "known_marketplaces.json"
        fs.create_file(
            marketplace_file,
            contents='{"test-marketplace": {"source": {"source": "directory", "path": "/fake/marketplace"}, "installLocation": "/fake/marketplace"}}',
        )

        marketplace_json = Path("/fake/marketplace/.claude-plugin/marketplace.json")
        fs.create_file(
            marketplace_json,
            contents='{"plugins": [{"name": "test-plugin", "description": "Test", "source": ".", "version": "1.0.0"}]}',
        )

        # Act: Run list command
        with (
            patch(
                "sys.argv",
                ["lazyclaude", "cli", "-u", str(fake_home / ".claude"), "list"],
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            from lazyclaude.__main__ import main

            main()

        # Assert: Verify output
        captured = capsys.readouterr()
        assert "test-plugin@test-marketplace" in captured.out
        assert exc_info.value.code == 0


class TestListFilters:
    """Test list command filtering options."""

    def test_list_installed_only_filter(self, capsys, fake_home: Path, fs) -> None:
        """List with --installed shows only installed plugins."""
        # Arrange: Create marketplace with installed and not-installed plugins
        plugins_dir = fake_home / ".claude" / "plugins"
        fs.create_dir(plugins_dir)

        # installed_plugins.json
        installed_file = plugins_dir / "installed_plugins.json"
        fs.create_file(
            installed_file,
            contents='{"plugins": {"plugin1@test": [{"scope": "user", "installPath": "/fake/plugin1", "version": "1.0.0"}]}}',
        )

        # marketplace with 2 plugins
        marketplace_file = plugins_dir / "known_marketplaces.json"
        fs.create_file(
            marketplace_file,
            contents='{"test": {"source": {"source": "directory"}, "installLocation": "/fake/marketplace"}}',
        )

        marketplace_json = Path("/fake/marketplace/.claude-plugin/marketplace.json")
        fs.create_file(
            marketplace_json,
            contents='{"plugins": [{"name": "plugin1", "source": "."}, {"name": "plugin2", "source": "."}]}',
        )

        # Act
        with (
            patch(
                "sys.argv",
                ["lazyclaude", "cli", "-u", str(fake_home / ".claude"), "list", "-i"],
            ),
            pytest.raises(SystemExit),
        ):
            from lazyclaude.__main__ import main

            main()

        # Assert: Only installed plugin shown
        captured = capsys.readouterr()
        assert "plugin1@test" in captured.out
        assert "plugin2@test" not in captured.out

    def test_list_query_filter(self, capsys, fake_home: Path, fs) -> None:
        """List with --query filters by name/description."""
        # Arrange
        plugins_dir = fake_home / ".claude" / "plugins"
        fs.create_dir(plugins_dir)

        marketplace_file = plugins_dir / "known_marketplaces.json"
        fs.create_file(
            marketplace_file,
            contents='{"test": {"source": {"source": "directory"}, "installLocation": "/fake/marketplace"}}',
        )

        marketplace_json = Path("/fake/marketplace/.claude-plugin/marketplace.json")
        fs.create_file(
            marketplace_json,
            contents='{"plugins": [{"name": "handbook", "description": "Handbook"}, {"name": "other", "description": "Other"}]}',
        )

        # Act
        with (
            patch(
                "sys.argv",
                [
                    "lazyclaude",
                    "cli",
                    "-u",
                    str(fake_home / ".claude"),
                    "list",
                    "-q",
                    "handbook",
                ],
            ),
            pytest.raises(SystemExit),
        ):
            from lazyclaude.__main__ import main

            main()

        # Assert
        captured = capsys.readouterr()
        assert "handbook@test" in captured.out
        assert "other@test" not in captured.out

    def test_list_enabled_only_filter(self, capsys, fake_home: Path, fs) -> None:
        """List with --enabled shows only enabled plugins."""
        # Arrange: Create marketplace with plugins, one enabled, one disabled
        plugins_dir = fake_home / ".claude" / "plugins"
        fs.create_dir(plugins_dir)

        # installed_plugins.json - both plugins installed
        installed_file = plugins_dir / "installed_plugins.json"
        fs.create_file(
            installed_file,
            contents='{"plugins": {"plugin1@test": [{"scope": "user", "installPath": "/fake/plugin1", "version": "1.0.0"}], "plugin2@test": [{"scope": "user", "installPath": "/fake/plugin2", "version": "1.0.0"}]}}',
        )

        # settings.json - disable plugin2
        settings_file = fake_home / ".claude" / "settings.json"
        fs.create_file(
            settings_file,
            contents='{"enabledPlugins": {"plugin2@test": false}}',
        )

        # marketplace with 2 plugins
        marketplace_file = plugins_dir / "known_marketplaces.json"
        fs.create_file(
            marketplace_file,
            contents='{"test": {"source": {"source": "directory"}, "installLocation": "/fake/marketplace"}}',
        )

        marketplace_json = Path("/fake/marketplace/.claude-plugin/marketplace.json")
        fs.create_file(
            marketplace_json,
            contents='{"plugins": [{"name": "plugin1", "source": "."}, {"name": "plugin2", "source": "."}]}',
        )

        # Act
        with (
            patch(
                "sys.argv",
                ["lazyclaude", "cli", "-u", str(fake_home / ".claude"), "list", "-e"],
            ),
            pytest.raises(SystemExit),
        ):
            from lazyclaude.__main__ import main

            main()

        # Assert: Only enabled plugin shown
        captured = capsys.readouterr()
        assert "plugin1@test" in captured.out
        assert "plugin2@test" not in captured.out

    def test_list_marketplace_filter(self, capsys, fake_home: Path, fs) -> None:
        """List with --marketplace filters by marketplace name."""
        # Arrange: Create 2 marketplaces with different plugins
        plugins_dir = fake_home / ".claude" / "plugins"
        fs.create_dir(plugins_dir)

        marketplace_file = plugins_dir / "known_marketplaces.json"
        fs.create_file(
            marketplace_file,
            contents='{"market1": {"source": {"source": "directory"}, "installLocation": "/fake/market1"}, "market2": {"source": {"source": "directory"}, "installLocation": "/fake/market2"}}',
        )

        market1_json = Path("/fake/market1/.claude-plugin/marketplace.json")
        fs.create_file(
            market1_json,
            contents='{"plugins": [{"name": "plugin1", "source": "."}]}',
        )

        market2_json = Path("/fake/market2/.claude-plugin/marketplace.json")
        fs.create_file(
            market2_json,
            contents='{"plugins": [{"name": "plugin2", "source": "."}]}',
        )

        # Act
        with (
            patch(
                "sys.argv",
                [
                    "lazyclaude",
                    "cli",
                    "-u",
                    str(fake_home / ".claude"),
                    "list",
                    "-m",
                    "market1",
                ],
            ),
            pytest.raises(SystemExit),
        ):
            from lazyclaude.__main__ import main

            main()

        # Assert: Only market1 plugins shown
        captured = capsys.readouterr()
        assert "plugin1@market1" in captured.out
        assert "plugin2@market2" not in captured.out

    def test_list_names_only_output(self, capsys, fake_home: Path, fs) -> None:
        """List with --names-only outputs only plugin names."""
        # Arrange
        plugins_dir = fake_home / ".claude" / "plugins"
        fs.create_dir(plugins_dir)

        marketplace_file = plugins_dir / "known_marketplaces.json"
        fs.create_file(
            marketplace_file,
            contents='{"test": {"source": {"source": "directory"}, "installLocation": "/fake/marketplace"}}',
        )

        marketplace_json = Path("/fake/marketplace/.claude-plugin/marketplace.json")
        fs.create_file(
            marketplace_json,
            contents='{"plugins": [{"name": "plugin1", "description": "Description here", "source": "."}]}',
        )

        # Act
        with (
            patch(
                "sys.argv",
                ["lazyclaude", "cli", "-u", str(fake_home / ".claude"), "list", "-n"],
            ),
            pytest.raises(SystemExit),
        ):
            from lazyclaude.__main__ import main

            main()

        # Assert: Only plugin name (no description or version)
        captured = capsys.readouterr()
        assert captured.out.strip() == "plugin1@test"
        assert "Description here" not in captured.out
