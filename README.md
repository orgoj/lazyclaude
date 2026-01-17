<p align="center">
  <img src="assets/logo.png" alt="LazyClaude" width="150">
</p>

# LazyClaude

> **Note:** This is a fork of [NikiforovAll/lazyclaude](https://github.com/NikiforovAll/lazyclaude). See "About This Fork" below for details on changes and differences.

A lazygit-style TUI for visualizing Claude Code customizations.

## About This Fork

This fork started as a simple modification to add scope selection to the marketplace dialog, but evolved into a significant rewrite with additional features that go beyond the original project and even the official `claude plugin` CLI.

### Key Differences from Upstream

- **Plugin CLI mode** (`lazyclaude cli`) - CLI interface for plugin management (plugins only, not general customizations):
  - `lazyclaude cli list` - List all plugins with rich filtering options
  - `lazyclaude cli enable/disable` - Enable/disable plugins at specific scopes
  - JSON output for scripting/integration
  - Filtering by installation status, enabled state, marketplace, and search queries

- **Multi-scope plugin support:**
  - User scope (`~/.claude/settings.json`) - Personal installations
  - Project scope (`./.claude/settings.json`) - Team-shared, version controlled
  - Local scope (`./.claude/settings.local.json`) - Local, not version controlled

- **Enhanced TUI features:**
  - Scope selector dialog when enabling/disabling/resetting plugins
  - Reset (`R`) removes plugin setting from a scope (inherits from parent scope)
  - Visual status indicators for plugin state across all scopes
  - Preview mode for installed plugins (explore customizations, README)

**Status:** This fork has diverged significantly from upstream. Merging back to the original repository is unlikely. For the original upstream project, see [NikiforovAll/lazyclaude](https://github.com/NikiforovAll/lazyclaude).

![Demo](assets/demo.png)

## Install

```bash
uvx lazyclaude
```

## Quick Tour

### First Launch
Launch LazyClaude to explore all your Claude Code customizations in one place. Navigate with `j`/`k`, switch panels with `1-6`, and toggle views with `[`/`]`.

![First Launch](docs/assets/first-launch.gif)

### Filter by Level
Press `a`/`u`/`p`/`P` to filter customizations by configuration level (All/User/Project/Plugin).

![Filter Workflow](docs/assets/demo-filter-workflow.gif)

### Browse Marketplace
Press `M` to open the marketplace browser. Install plugins with `i`, preview installed plugins with `p`, and manage installations.

![Marketplace Install](docs/assets/demo-marketplace-install.gif)

### Preview Installed Plugins
Press `p` in the marketplace on an installed plugin to explore its customizations (commands, skills, subagents). Main pane shows README, sidebar displays plugin contents. Press `Esc` to return to marketplace.

![Preview Plugin](docs/assets/demo-preview-plugin.gif)

📖 **[Full User Guide](docs/user-guide.md)** for detailed workflows and keyboard shortcuts.

### CLI Mode (Plugins Only)

This fork includes a CLI interface for **plugin management only** (not available in upstream):

```bash
# List plugins
lazyclaude cli list                       # List all plugins (verbose)
lazyclaude cli list -i                    # Installed only
lazyclaude cli list -e                    # Enabled only
lazyclaude cli list -q handbook           # Search by name/description
lazyclaude cli list -m marketplace-name   # Filter by marketplace
lazyclaude cli list -n                    # Names only (plain list)
lazyclaude cli --json list                # JSON output for scripting

# Enable/disable plugins (with scope selection)
lazyclaude cli enable -s project plugin@marketplace   # Enable in project scope
lazyclaude cli disable -s user plugin@marketplace     # Disable in user scope
lazyclaude cli enable -s local plugin@marketplace     # Enable in local scope
```

**Output Format:** `plugin@marketplace  version  user/project/local  description`

Status indicators for each scope:
- `Ie` - Installed and enabled
- `Id` - Installed but disabled
- `e` - Not installed, but marked as enabled in settings (pre-install)
- `d` - Not installed, but marked as disabled in settings
- `-` - Not installed and not in settings

Example: `Ie/-/-` = installed+enabled in user scope, not in project/local

**Scopes:**
- `user` - Personal installation at `~/.claude/` (available across all projects)
- `project` - Team-shared at `./.claude/` (version controlled)
- `local` - Local at `./.claude/settings.local.json` (not version controlled)

**JSON Output (`--json list`):**

```json
{
  "name": "plugin-name",
  "marketplace": "marketplace-name",
  "version": "1.0.0",
  "description": "Plugin description",
  "source_path": "/path/to/plugin/source",
  "scopes": {
    "user": {
      "installed": true,
      "enabled": true,
      "version": "1.0.0",
      "install_path": "/home/user/.claude/plugins/cache/marketplace/plugin/1.0.0"
    },
    "project": {
      "installed": false,
      "enabled": null,
      "version": null,
      "install_path": null
    },
    "local": {
      "installed": false,
      "enabled": null,
      "version": null,
      "install_path": null
    }
  }
}
```

- `source_path` - Plugin source location (local path for directory marketplaces, URL for GitHub)
- `install_path` - Per-scope installation path (`null` when not installed in that scope)

## Development

```bash
uv sync              # Install dependencies
uv run lazyclaude    # Run app
```

Publish:

```bash
export UV_PUBLISH_TOKEN=<your_token>
uv build
uv publish
```

See: <https://docs.astral.sh/uv/guides/package/>
