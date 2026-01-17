"""CLI interface for plugin management."""

import argparse
import json as json_module
import sys
from pathlib import Path

from lazyclaude.models.marketplace import PluginState
from lazyclaude.services.unified_data_loader import UnifiedDataLoader


def run_cli(args: argparse.Namespace) -> int:
    """Run CLI command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error, 2 for invalid args)
    """
    command_map = {
        "list": handle_list,
        "enable": handle_enable,
        "disable": handle_disable,
    }

    handler = command_map.get(args.cli_command)
    if not handler:
        print(f"Unknown command: {args.cli_command}", file=sys.stderr)
        return 2

    return handler(args)


def handle_list(args: argparse.Namespace) -> int:
    """Handle 'list' command.

    Args:
        args: Parsed arguments with filters

    Returns:
        Exit code
    """
    try:
        # Resolve paths at start (no cwd usage downstream)
        user_config = args.user_config or Path.home() / ".claude"
        if not args.directory:
            print(
                "✗ Error: --directory argument is required for CLI mode",
                file=sys.stderr,
            )
            return 1
        project_root = Path(args.directory)
        project_config = project_root / ".claude"

        # Use unified data loader
        loader = UnifiedDataLoader(
            user_config_path=user_config,
            project_config_path=project_config,
            project_root=project_root,
        )

        # Load all marketplaces and plugins
        marketplaces = loader.load_marketplace_states()

        # Flatten plugins from all marketplaces
        all_plugins: list[PluginState] = []
        for mp in marketplaces:
            all_plugins.extend(mp.plugins)

        # Apply filters
        filtered_plugins = all_plugins

        if args.installed:
            filtered_plugins = [
                p for p in filtered_plugins if p.is_accessible_in_current_project
            ]

        if args.enabled:
            filtered_plugins = [p for p in filtered_plugins if p.effective_enabled]

        if args.marketplace:
            filtered_plugins = [
                p for p in filtered_plugins if p.marketplace_name == args.marketplace
            ]

        if args.query:
            query_lower = args.query.lower()
            filtered_plugins = [
                p
                for p in filtered_plugins
                if query_lower in p.name.lower()
                or query_lower in (p.description or "").lower()
            ]

        # Output plugins
        if args.json:
            output_json(filtered_plugins)
        elif args.names_only:
            output_names_only(filtered_plugins)
        else:
            output_plain(filtered_plugins)

        return 0

    except Exception as e:
        if args.json:
            print(
                json_module.dumps({"success": False, "error": str(e)}),
                file=sys.stderr,
            )
        else:
            print(f"✗ Error: {e}", file=sys.stderr)
        return 1


def output_plain(plugins: list[PluginState]) -> None:
    """Output plugins in plain text format (verbose).

    Args:
        plugins: List of PluginState objects
    """
    for plugin in plugins:
        # Format: name@marketplace  version  user/project/local  description
        scopes = plugin.format_scope_display()
        version = (
            plugin.user.version
            or plugin.project.version
            or plugin.local.version
            or "---"
        )
        print(f"{plugin.plugin_id:<35} {version:<10} {scopes:<15} {plugin.description}")


def output_json(plugins: list[PluginState]) -> None:
    """Output plugins in JSON format.

    Args:
        plugins: List of PluginState objects
    """
    output = [
        {
            "name": p.name,
            "marketplace": p.marketplace_name,
            "version": p.user.version
            or p.project.version
            or p.local.version
            or "not_installed",
            "description": p.description,
            "source_path": p.source_path,
            "scopes": {
                "user": {
                    "installed": p.user.installed,
                    "enabled": p.user.enabled,
                    "version": p.user.version,
                    "install_path": str(p.user.install_path)
                    if p.user.install_path
                    else None,
                },
                "project": {
                    "installed": p.project.installed,
                    "enabled": p.project.enabled,
                    "version": p.project.version,
                    "install_path": str(p.project.install_path)
                    if p.project.install_path
                    else None,
                },
                "local": {
                    "installed": p.local.installed,
                    "enabled": p.local.enabled,
                    "version": p.local.version,
                    "install_path": str(p.local.install_path)
                    if p.local.install_path
                    else None,
                },
            },
        }
        for p in plugins
    ]
    print(json_module.dumps(output, indent=2))


def output_names_only(plugins: list[PluginState]) -> None:
    """Output only plugin names (one per line).

    Args:
        plugins: List of PluginState objects
    """
    for plugin in plugins:
        print(plugin.plugin_id)


def handle_enable(args: argparse.Namespace) -> int:
    """Handle 'enable' command.

    Args:
        args: Parsed arguments with scope and plugin_id

    Returns:
        Exit code
    """
    return toggle_plugin(args, enabled=True)


def handle_disable(args: argparse.Namespace) -> int:
    """Handle 'disable' command.

    Args:
        args: Parsed arguments with scope and plugin_id

    Returns:
        Exit code
    """
    return toggle_plugin(args, enabled=False)


def toggle_plugin(args: argparse.Namespace, enabled: bool) -> int:
    """Enable or disable a plugin in specific scope.

    Args:
        args: Parsed arguments with scope, plugin_id, user_config, directory
        enabled: True to enable, False to disable

    Returns:
        Exit code
    """
    try:
        # Resolve paths at start (no cwd usage downstream)
        user_config = args.user_config or Path.home() / ".claude"
        if not args.directory:
            print(
                "✗ Error: --directory argument is required for CLI mode",
                file=sys.stderr,
            )
            return 1
        project_root = Path(args.directory)

        if args.scope == "user":
            settings_path = user_config / "settings.json"
        elif args.scope == "project":
            settings_path = project_root / ".claude" / "settings.json"
        else:  # local
            settings_path = project_root / ".claude" / "settings.local.json"

        # Ensure parent directory exists
        settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or create settings
        if settings_path.exists():
            settings = json_module.loads(settings_path.read_text())
        else:
            settings = {}

        # Update enabledPlugins
        if "enabledPlugins" not in settings:
            settings["enabledPlugins"] = {}

        settings["enabledPlugins"][args.plugin_id] = enabled

        # Write back
        settings_path.write_text(json_module.dumps(settings, indent=2) + "\n")

        # Output success
        action = "Enabled" if enabled else "Disabled"
        if args.json:
            print(
                json_module.dumps(
                    {
                        "success": True,
                        "plugin": args.plugin_id,
                        "scope": args.scope,
                        "action": action.lower(),
                    }
                )
            )
        else:
            print(f"✓ {action} {args.plugin_id} in {args.scope} scope")

        return 0

    except Exception as e:
        if args.json:
            print(
                json_module.dumps({"success": False, "error": str(e)}),
                file=sys.stderr,
            )
        else:
            print(f"✗ Error: {e}", file=sys.stderr)
        return 1
