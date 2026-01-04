"""Tests for CLI interface."""

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
