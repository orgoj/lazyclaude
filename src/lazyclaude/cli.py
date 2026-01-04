"""CLI interface for plugin management."""

import argparse
import json as json_module
import sys
from pathlib import Path

from lazyclaude.models.marketplace import MarketplacePlugin
from lazyclaude.services.plugin_data_provider import PluginDataProvider


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
        project_root = Path(args.directory) if args.directory else Path.cwd()

        # Use unified data provider
        provider = PluginDataProvider(
            user_config_path=user_config,
            project_root=project_root,
        )

        # Use unified filtering
        filtered_plugins = provider.get_filtered_plugins(
            installed_only=args.installed,
            enabled_only=args.enabled,
            marketplace=args.marketplace,
            query=args.query,
        )

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


def output_plain(plugins: list[MarketplacePlugin]) -> None:
    """Output plugins in plain text format (verbose).

    Args:
        plugins: List of MarketplacePlugin objects
    """
    for plugin in plugins:
        # Format: name@marketplace  version  [scopes]  description
        scopes = format_scope_status(plugin.scope_status)
        print(
            f"{plugin.full_plugin_id:<35} {plugin.installed_version or '---':<10} {scopes:<25} {plugin.description}"
        )


def output_json(plugins: list[MarketplacePlugin]) -> None:
    """Output plugins in JSON format.

    Args:
        plugins: List of MarketplacePlugin objects
    """
    output = [
        {
            "name": p.name,
            "marketplace": p.marketplace_name,
            "version": p.installed_version or "not_installed",
            "description": p.description,
            "scopes": p.scope_status,
        }
        for p in plugins
    ]
    print(json_module.dumps(output, indent=2))


def output_names_only(plugins: list[MarketplacePlugin]) -> None:
    """Output only plugin names (one per line).

    Args:
        plugins: List of MarketplacePlugin objects
    """
    for plugin in plugins:
        print(plugin.full_plugin_id)


def format_scope_status(scope_status: dict[str, str]) -> str:
    """Format scope status dict into display string.

    Args:
        scope_status: Dict with keys 'user', 'project', 'local'

    Returns:
        Formatted string like "[I:u]" or "[I:up E:u]" or "[I:u E:p D:l]"
        Only includes sections that have values.
        Shows both direct enables and override enables.
    """
    installed = "".join(
        k[0] for k, v in scope_status.items() if v in ("enabled", "disabled")
    )
    enabled = "".join(
        k[0] for k, v in scope_status.items() if v in ("enabled", "override_enabled")
    )
    disabled = "".join(k[0] for k, v in scope_status.items() if v == "disabled")

    parts = []
    if installed:
        parts.append(f"I:{installed}")
    if enabled:
        parts.append(f"E:{enabled}")
    if disabled:
        parts.append(f"D:{disabled}")

    return f"[{' '.join(parts)}]"


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
        project_root = Path(args.directory) if args.directory else Path.cwd()

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
