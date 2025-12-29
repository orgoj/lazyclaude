"""Entry point for running lazyclaude as a module."""

import argparse
import logging
import sys
import traceback
from pathlib import Path
from tempfile import gettempdir

from lazyclaude import __version__
from lazyclaude.app import create_app

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="[%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


class TextualLogHandler(logging.Handler):
    """Custom logging handler that sends log records to Textual DebugOverlay."""

    def __init__(self) -> None:
        super().__init__()
        self._overlay = None  # Will be set later
        self._app = None  # Will be set later for call_from_thread

    def set_overlay(self, overlay, app) -> None:  # type: ignore[no-untyped-def]
        """Set the DebugOverlay widget and app reference."""
        self._overlay = overlay
        self._app = app

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the DebugOverlay."""
        if self._overlay is not None:
            try:
                message = self.format(record)

                # Always use call_from_thread to be safe from any thread
                if self._app is not None:
                    self._app.call_from_thread(self._overlay.log_message, message)  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                # Don't raise exceptions in logging
                pass


def main() -> None:
    """Run the LazyClaude application."""
    parser = argparse.ArgumentParser(
        prog="lazyclaude",
        description="A lazygit-style TUI for visualizing Claude Code customizations",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=Path,
        default=None,
        help="Project directory to scan for customizations (default: current directory)",
    )
    parser.add_argument(
        "-u",
        "--user-config",
        type=Path,
        default=None,
        help="Override user config path (default: ~/.claude)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (log exceptions to stderr with tracebacks)",
    )
    parser.add_argument(
        "-m",
        "--marketplace",
        action="store_true",
        help="Open marketplace browser immediately after start",
    )

    args = parser.parse_args()

    # Setup debug handlers if --debug flag is set
    textual_handler = None
    if args.debug:
        # Create debug log file with fixed path for easy tail -f
        debug_log_path = Path(gettempdir()) / "lazyclaude.log"

        # Add file handler for debug output
        file_handler = logging.FileHandler(debug_log_path, mode="w")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
        )
        logging.getLogger().addHandler(file_handler)

        # Remove stderr StreamHandler from basicConfig so debug goes ONLY to file
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if (
                isinstance(handler, logging.StreamHandler)
                and handler.stream == sys.stderr
            ):
                root_logger.removeHandler(handler)

        # Create Textual overlay handler (will be connected after app creation)
        textual_handler = TextualLogHandler()
        textual_handler.setLevel(logging.DEBUG)
        textual_handler.setFormatter(
            logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
        )
        logging.getLogger().addHandler(textual_handler)

        # Set global logging level to DEBUG AFTER removing stderr handler
        logging.getLogger().setLevel(logging.DEBUG)

        logger.debug("LazyClaude debug session started")
        logger.debug(f"Debug log: {debug_log_path}")
        logger.debug(f"[MAIN] cwd: {Path.cwd()}")
        logger.debug(f"[MAIN] --directory arg: {args.directory}")

    project_config_path = None
    if args.directory:
        project_config_path = args.directory / ".claude"

    try:
        logger.debug(f"[MAIN] project_config_path: {project_config_path}")
        logger.debug("[MAIN] Creating app instance")
        app = create_app(
            user_config_path=args.user_config,
            project_config_path=project_config_path,
            open_marketplace=args.marketplace,
        )

        # Store debug flag in app for other modules to access
        app.debug_mode = args.debug  # type: ignore[attr-defined]
        logger.debug(f"[MAIN] debug_mode set to: {app.debug_mode}")

        # Debug logging only to file, NOT to TUI overlay
        if args.debug and textual_handler is not None:
            logger.debug("[MAIN] Debug logging enabled to file")

        logger.debug("[MAIN] About to run app")
        app.run()
        logger.debug("[MAIN] App exited normally")

    except KeyboardInterrupt:
        logger.debug("[MAIN] KeyboardInterrupt caught")
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as error:
        # Always print traceback to stderr on unhandled exception
        logger.debug(f"[MAIN] FATAL ERROR: {type(error).__name__}: {error}")
        logger.debug(f"[MAIN] Traceback:\n{traceback.format_exc()}")
        print(
            f"\n{'=' * 60}\nFATAL ERROR: {type(error).__name__}: {error}\n{'=' * 60}",
            file=sys.stderr,
        )
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
