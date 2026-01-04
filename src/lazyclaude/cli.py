"""CLI interface for plugin management."""

import argparse
import json as json_module
import sys
from pathlib import Path

from lazyclaude.models.marketplace import MarketplacePlugin
from lazyclaude.services.marketplace_loader import MarketplaceLoader
from lazyclaude.services.plugin_loader import PluginLoader


def run_cli(args: argparse.Namespace) -> int:
    """Run CLI command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, 1 for error, 2 for invalid args)
    """
    if args.cli_command == "list":
        return handle_list(args)

    print(f"Unknown command: {args.cli_command}", file=sys.stderr)
    return 2


def handle_list(args: argparse.Namespace) -> int:
    """Handle 'list' command.

    Args:
        args: Parsed arguments with filters

    Returns:
        Exit code
    """
    try:
        # Setup paths
        user_config = args.user_config or Path.home() / ".claude"
        project_root = Path(args.directory) if args.directory else Path.cwd()
        project_config = project_root / ".claude" if project_root else None

        # Load marketplaces
        plugin_loader = PluginLoader(
            user_config_path=user_config,
            project_config_path=project_config,
            project_root=project_root,
        )
        marketplace_loader = MarketplaceLoader(
            user_config_path=user_config,
            plugin_loader=plugin_loader,
        )

        marketplaces = marketplace_loader.load_marketplaces()

        # Collect all plugins
        all_plugins = []
        for marketplace in marketplaces:
            if marketplace.plugins:
                all_plugins.extend(marketplace.plugins)

        # Apply filters
        filtered_plugins = all_plugins

        if args.installed:
            filtered_plugins = [p for p in filtered_plugins if p.is_installed]

        if args.enabled:
            filtered_plugins = [p for p in filtered_plugins if p.is_enabled]

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


def output_plain(plugins: list[MarketplacePlugin]) -> None:
    """Output plugins in plain text format (verbose).

    Args:
        plugins: List of MarketplacePlugin objects
    """
    for plugin in plugins:
        # Format: name@marketplace  version  [scopes]  description
        scopes = format_scope_status(plugin.scope_status)
        print(
            f"{plugin.full_plugin_id:<35} {plugin.installed_version or '---':<10} {scopes:<20} {plugin.description}"
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
        Formatted string like "[I:u E:up D:l]"
    """
    installed = "".join(
        k[0] for k, v in scope_status.items() if v in ("enabled", "disabled")
    )
    enabled = "".join(k[0] for k, v in scope_status.items() if v == "enabled")
    disabled = "".join(k[0] for k, v in scope_status.items() if v == "disabled")

    return f"[I:{installed} E:{enabled} D:{disabled}]"
