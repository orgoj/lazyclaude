# LazyClaude CLI Interface Design

**Date:** 2026-01-04
**Status:** Approved

## Overview

Add CLI interface to lazyclaude for plugin/marketplace management, addressing gaps in Claude Code CLI (e.g., enabling project-scoped plugins installed at user scope).

## Motivation

Claude Code CLI cannot:
- Enable a plugin for project scope when installed at user scope
- Provide flexible scope management across user/project/local

LazyClaude CLI provides thin wrapper over existing TUI logic to expose these capabilities via command line.

## CLI Command Structure

```bash
lazyclaude cli <command> [options] [args]
```

### Commands

- `list` - List plugins from marketplaces
- `install` - Install plugin to specific scope
- `enable` - Enable plugin in specific scope
- `disable` - Disable plugin in specific scope
- `uninstall` - Uninstall plugin from specific scope
- `update` - Update marketplace or plugin
- `add-marketplace` - Add new marketplace source

### Global Flags

- `--json` - Output in JSON format (default: plain text)
- `-d, --directory PATH` - Project directory (default: current)
- `-u, --user-config PATH` - Override user config path

### Command-Specific Options

**`list`:**
- `-i, --installed` - Show only installed plugins
- `-e, --enabled` - Show only enabled plugins
- `-m, --marketplace NAME` - Filter by marketplace
- `-q, --query TEXT` - Search/filter by name or description
- `-n, --names-only` - Output only plugin names (one per line)

**`install/enable/disable/uninstall`:**
- `-s, --scope SCOPE` - Target scope: user/project/local (required)

**`update`:**
- `-m, --marketplace NAME` - Update specific marketplace (optional, updates all if omitted)

## Output Formats

### Default (verbose with scope icons)

```bash
$ lazyclaude cli list -i
plugin1@marketplace1              1.0.0    [I:u E:up D:l]   Example plugin
plugin2@marketplace2              2.1.0    [I:u E:p  D:  ]   Another plugin
handbook@cc-handbook              3.0.0    [I:p E:p  D:  ]   CC Handbook
```

Legend: `[I:u E:up D:l]` means:
- Installed: u=user
- Enabled: u=user, p=project
- Disabled: l=local

### Names Only (`--names-only`)

```bash
$ lazyclaude cli list -i -n
plugin1@marketplace1
plugin2@marketplace2
handbook@cc-handbook
```

### JSON Format (`--json`)

```json
[
  {
    "name": "plugin1",
    "marketplace": "marketplace1",
    "version": "1.0.0",
    "description": "Example plugin",
    "scopes": {
      "user": "enabled",
      "project": "override_enabled",
      "local": "disabled"
    }
  }
]
```

### Operation Results

**Plain text:**
- Success: `✓ Enabled plugin1@marketplace1 in project scope`
- Error: `✗ Error: Plugin not found`

**JSON:**
```json
{"success": true, "plugin": "plugin1@marketplace1", "scope": "project", "action": "enable"}
{"success": false, "error": "Plugin not found"}
```

## Architecture

### Entry Point Routing

Modify `__main__.py` to add subcommand routing:

```python
def main() -> None:
    parser = argparse.ArgumentParser(prog="lazyclaude")
    subparsers = parser.add_subparsers(dest='command')

    # TUI mode (default - no subcommand)
    # existing args: --version, --directory, --debug, --marketplace

    # CLI mode
    cli_parser = subparsers.add_parser('cli', help='CLI interface')
    # ... cli subcommands setup

    args = parser.parse_args()

    if args.command == 'cli':
        from lazyclaude.cli import run_cli
        sys.exit(run_cli(args))
    else:
        # existing TUI logic
        app = create_app(...)
        app.run()
```

### New Module: `src/lazyclaude/cli.py`

**Responsibilities:**
- `run_cli(args)` - Main CLI dispatcher
- Parse CLI arguments and route to appropriate handlers
- Format output (plain text vs JSON)
- Handle errors and exit codes

**Reuses existing services:**
- `MarketplaceLoader` - Load marketplaces/plugins
- `PluginLoader` - Registry operations
- Direct JSON file manipulation for settings.json, installed_plugins.json

**No new business logic** - thin wrapper only. All heavy lifting (scope detection, registry management) already exists in existing services.

## Usage Examples

### Basic Operations

```bash
# List all plugins
lazyclaude cli list

# List installed, search for "handbook"
lazyclaude cli list -i -q handbook

# Install to project scope
lazyclaude cli install -s project handbook@cc-handbook

# Enable plugin (installed in user) for project scope
lazyclaude cli enable -s project plugin@marketplace

# Disable in specific scope
lazyclaude cli disable -s user plugin@marketplace

# Uninstall from project
lazyclaude cli uninstall -s project plugin@marketplace

# Get JSON output
lazyclaude cli list -i --json
```

## Edge Cases

1. **Plugin installed in user, enable for project**
   → Writes override to `.claude/settings.json`: `enabledPlugins: {"plugin@marketplace": true}`

2. **Plugin not installed, try to enable**
   → Error: "Plugin not installed. Install first with: lazyclaude cli install -s <scope> plugin@marketplace"

3. **No marketplace found**
   → Error: "No marketplaces configured. Add with: lazyclaude cli add-marketplace"

4. **Scope required but missing**
   → Error: "Scope required. Use -s/--scope: user, project, or local"

5. **JSON output on error**
   → `{"success": false, "error": "..."}`

## Exit Codes

- `0` - Success
- `1` - Generic error
- `2` - Invalid arguments

## Design Principles

- **Thin wrapper** - Reuse existing TUI services, no logic duplication
- **Fork-friendly** - Minimal changes to core, easy to sync with upstream
- **Explicit scope** - Always require `-s/--scope` for operations to avoid ambiguity
- **Plain by default** - Human-readable output, `--json` for scripts
- **YAGNI** - Only implement requested commands, no extras
