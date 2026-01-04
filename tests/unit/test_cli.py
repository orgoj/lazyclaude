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
        with patch(
            "sys.argv", ["lazyclaude", "cli", "-u", str(fake_home / ".claude"), "list"]
        ), pytest.raises(SystemExit) as exc_info:
            from lazyclaude.__main__ import main

            main()

        # Assert: Verify output
        captured = capsys.readouterr()
        assert "test-plugin@test-marketplace" in captured.out
        assert exc_info.value.code == 0
