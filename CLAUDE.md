# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LazyClaude is a TUI application for visualizing Claude Code customizations (Slash Commands, Subagents, Skills, Memory Files, MCPs, Hooks). Built with the Textual framework following lazygit-style keyboard ergonomics.

## Active Technologies

- **Language**: Python 3.11+
- **Framework**: Textual (TUI), Rich (formatting), PyYAML (frontmatter parsing)
- **Testing**: pytest, pytest-asyncio, pytest-textual-snapshot
- **Package Manager**: uv

## Commands

### Setup & Running

```bash
uv sync                         # Install dependencies
uv run lazyclaude              # Run application
uv run lazyclaude --debug      # Run with debug logging to /tmp/lazyclaude.log
uv run lazyclaude -m           # Run starting in marketplace view mode
uv run pre-commit install      # Install git hooks for quality gates

# Watch debug log in another terminal:
tail -f /tmp/lazyclaude.log
```

### Pre-commit Hooks

```bash
uv run pre-commit run --all-files      # Run all hooks manually
```

Git hooks run automatically before commit and enforce: ruff format, ruff lint, mypy checks, and pytest.

## Code Style

- Type hints required for all public functions
- Linting via ruff, formatting via ruff format
- No emojis in code/comments
- Comments explain WHY not WHAT (add comments only when logic isn't self-evident)

## Constitution Principles

All code MUST comply with these principles (see `docs/constitution.md`):

1. **Keyboard-First**: Every action has a keyboard shortcut, vim-like navigation
2. **Panel Layout**: Multi-panel structure with clear focus indicators
3. **Contextual Navigation**: Enter drills down, Esc goes back
4. **Modal Minimalism**: No modals for simple operations
5. **Textual Framework**: All widgets extend Textual base classes
6. **UV Packaging**: uv for package management, uvx for distribution

## Keybinding Conventions

| Key | Action | Scope |
|-----|--------|-------|
| `q` | Quit | Global |
| `?` | Help | Global |
| `r` | Refresh | Global |
| `/` | Search | Global |
| `e` | Open in $EDITOR | Global |
| `c` | Copy to level | Global |
| `m` | Move to level | Global |
| `C` | Copy path to clipboard | Global |
| `Ctrl+u` | Open user config (~/.claude, ~/.claude.json) | Global |
| `M` | Cycle view mode (Normal → Marketplace → ...) | Global |
| `a`/`u`/`p`/`P` | Filter: All/User/Project/Plugin | Global |
| `D` | Toggle disabled plugins | Global |
| `[`/`]` | Switch content/metadata view | Global |
| `Tab` | Switch between panels | Global |
| `0`-`6` | Focus panel by number | Global |
| `j`/`k` | Navigate up/down | List |
| `d`/`u` | Page down/up | Detail pane |
| `g`/`G` | Go to top/bottom | List |
| `Enter` | Drill down | Context |
| `Esc` | Back | Context |
| `I`/`E`/`D`/`U` | Install/Enable/Disable/Uninstall plugin | Marketplace |
| `A` | Add marketplace | Marketplace |
| `i` | Toggle installed-only filter | Marketplace |
| `n` | Toggle enabled-only filter | Marketplace |
| `u` | Update marketplace or plugin | Marketplace |
| `p` | Preview plugin (installed only) | Marketplace |
| `e` | Edit - open plugin folder (installed only) | Marketplace |
| `o` | Open source URL | Marketplace |
| `L`/`H` | Expand/Collapse all marketplaces | Marketplace |

## Architecture

### Data Flow

```
User Input → App (app.py) → TypePanel widgets → SelectionChanged message
                ↓                                        ↓
         ConfigDiscoveryService                   MainPane updates
                ↓
         Parsers (slash_command, subagent, skill, memory_file, mcp, hook)
                ↓
         Customization models
```

1. `ConfigDiscoveryService` discovers files from multiple sources (User, Project, Plugin)
2. Type-specific parsers in `services/parsers/` extract frontmatter metadata and content
3. `Customization` objects are created with `ConfigLevel` (USER, PROJECT, PROJECT_LOCAL, PLUGIN)
4. Selection changes emit `TypePanel.SelectionChanged` messages handled by `App` to update `MainPane`

### Widget Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ LazyClaude App                                                          │
├────────────────────────┬────────────────────────────────────────────────┤
│ #sidebar (Container)   │ MainPane                                       │
│ ┌────────────────────┐ │ ┌────────────────────────────────────────────┐ │
│ │ StatusPanel        │ │ │ Content/Metadata view for selected item    │ │
│ │ Path | Filter      │ │ │ Switchable with [ / ]                      │ │
│ └────────────────────┘ │ │                                            │ │
│ ┌────────────────────┐ │ │ Supports:                                  │ │
│ │ TypePanel [1]      │ │ │ - Syntax highlighting                      │ │
│ │ Slash Commands     │ │ │ - Markdown rendering                       │ │
│ └────────────────────┘ │ │ - File tree for skills                     │ │
│ ┌────────────────────┐ │ │ - Memory file refs (@path)                 │ │
│ │ TypePanel [2]      │ │ │                                            │ │
│ │ Subagents          │ │ │                                            │ │
│ └────────────────────┘ │ │                                            │ │
│ ┌────────────────────┐ │ │                                            │ │
│ │ TypePanel [3]      │ │ │                                            │ │
│ │ Skills             │ │ │                                            │ │
│ └────────────────────┘ │ │                                            │ │
│ ┌────────────────────┐ │ │                                            │ │
│ │ CombinedPanel      │ │ │                                            │ │
│ │ [4]Mem [5]MCP [6]H │ │ │                                            │ │
│ └────────────────────┘ │ └────────────────────────────────────────────┘ │
├────────────────────────┴────────────────────────────────────────────────┤
│ AppFooter (shows mode and context)                                      │
└─────────────────────────────────────────────────────────────────────────┘

View modes (switched with M key):
- Normal: Default customization browser view (sidebar + detail pane)
- Marketplace: Plugin marketplace browser view (full-screen tree)

Modal overlays (hidden by default, dock: bottom):
- FilterInput: Search/filter (activated with /)
- LevelSelector: Copy/move target selection (activated with c/m)
- DeleteConfirm: Delete confirmation (activated with d)
- ScopeSelector: Plugin scope selection (User/Project/Local)
- MarketplaceConfirm: Marketplace action confirmation
- MarketplaceSourceInput: Add marketplace source input
```

### Widget Responsibilities

| Widget | File | Purpose |
|--------|------|---------|
| `TypePanel` | `widgets/type_panel.py` | Single-type list panel (Commands, Subagents, Skills) with expandable trees |
| `CombinedPanel` | `widgets/combined_panel.py` | Multi-type tabbed panel (Memory, MCPs, Hooks) |
| `MainPane` | `widgets/detail_pane.py` | Content/metadata detail view with syntax highlighting |
| `StatusPanel` | `widgets/status_panel.py` | Shows current path and filter status |
| `FilterInput` | `widgets/filter_input.py` | Search input modal |
| `LevelSelector` | `widgets/level_selector.py` | Target level selector for copy/move |
| `DeleteConfirm` | `widgets/delete_confirm.py` | Delete confirmation modal |
| `ErrorModal` | `widgets/error_modal.py` | Persistent error display (Esc to dismiss) |
| `PluginConfirm` | `widgets/plugin_confirm.py` | Plugin toggle confirmation modal |
| `MarketplaceView` | `widgets/marketplace_view.py` | Marketplace browser view (full-screen tree) with plugin preview (p) and edit (e) for installed plugins |
| `MarketplaceInfoPanel` | `widgets/marketplace_info_panel.py` | Info panel showing marketplace/plugin metadata with scrollable content (2:1 tree-to-panel ratio) |
| `ScopeSelector` | `widgets/scope_selector.py` | Plugin scope selection (User/Project/Local) |
| `MarketplaceConfirm` | `widgets/marketplace_confirm.py` | Marketplace action confirmation |
| `MarketplaceSourceInput` | `widgets/marketplace_source_input.py` | Add marketplace source input |
| `AppFooter` | `widgets/app_footer.py` | Dynamic footer with mode and view-specific content |

### Shared Helpers

`widgets/helpers/rendering.py` contains shared rendering utilities:
- `render_memory_item()` - Renders memory file tree items
- `build_memory_flat_items()` - Builds flat list from nested memory refs

### CustomizationTypes

SLASH_COMMAND, SUBAGENT, SKILL, MEMORY_FILE, MCP, HOOK

### ConfigLevels

- USER: `~/.claude/` - User's global configuration
- PROJECT: `./.claude/` - Project-specific files checked into version control
- PROJECT_LOCAL: `./.claude/local/` - Project-local files (not version controlled)
- PLUGIN: `~/.claude/plugins/` - Installed third-party plugin extensions

### Plugin & Marketplace System

**Data Sources:**
- `~/.claude/plugins/known_marketplaces.json` - Index of registered marketplaces
- `<marketplace_install_location>/.claude-plugin/marketplace.json` - Per-marketplace plugin catalog
- `~/.claude/plugins/installed_plugins.json` - Registry of installed plugins with paths and versions

**Key Models (`models/marketplace.py`):**
- `MarketplaceSource` - Source type (github/directory), repo, path
- `MarketplaceEntry` - Marketplace name, source, install_location, description, owner, metadata
- `MarketplacePlugin` - Plugin metadata including full_plugin_id (`name@marketplace`), install state, install_path, author, homepage, repository, license, category, keywords
- `Marketplace` - Entry + list of plugins

**Services:**
- `MarketplaceLoader` (`services/marketplace_loader.py`) - Loads marketplaces and determines plugin install/enabled state from PluginLoader registry
- `PluginLoader` (`services/plugin_loader.py`) - Manages installed_plugins.json registry, resolves install paths

**Marketplace View (`widgets/marketplace_view.py`):**
- Accessed via view mode cycle (`M` key) - full-screen view replacing normal view
- Uses Textual Tree widget: marketplaces as expandable roots, plugins as leaves
- Info panel below tree (2:1 ratio) showing marketplace/plugin metadata from marketplace.json
- Status icons: `[I:upl E:up D:l]` format showing installed/enabled/disabled scopes (u=user, p=project, l=local)
- Bindings:
  - `I` (install), `E` (enable), `D` (disable), `U` (uninstall) - plugin actions with scope selector
  - `A` (add marketplace source), `u` (update marketplace/plugin)
  - `i` (toggle installed-only filter), `n` (toggle enabled-only filter)
  - `p` (preview plugin), `e` (open plugin/marketplace folder in editor), `o` (open source URL)
  - `j/k` (nav), `h/l` (collapse/expand), `L/H` (expand/collapse all)
- Emits messages: `PluginAction`, `PluginUninstall`, `OpenPluginFolder`, `OpenMarketplaceFolder`, `ViewClosed`, `FooterChanged`, `MarketplaceUpdate`, `MarketplaceAdd`, `MarketplaceRemove`
- `e` key on marketplace opens install directory in $EDITOR

**Plugin Preview Mode:**
- Activated by pressing `p` on an **installed** plugin in marketplace view
- Switches app to NORMAL view mode via `_switch_mode(ViewMode.NORMAL)`
- Shows plugin's customizations in sidebar panels (commands, skills, subagents, etc.)
- Status panel displays "Preview: PluginName (version)"
- Main pane shows plugin's README.md if available
- Footer switches to normal mode bindings
- **Esc key** exits preview and returns to marketplace view
- **M key** during preview exits preview (doesn't cycle modes)
- Only works on installed plugins (shows warning otherwise)
- Preview state tracked by `_plugin_preview_mode` boolean flag (not a separate ViewMode)

**Scope Selector (`widgets/scope_selector.py`):**
- Activated when installing, enabling, or disabling plugins
- Presents User/Project/Local scope options with status icons
- Key bindings: `1`/`u` (user), `2`/`p` (project), `3`/`l` (local), `Esc` (cancel)
- Shows current plugin state in each scope with icons: [✓] enabled, [✗] disabled, [ ] not installed
- Emits `ScopeSelected` message with plugin, scope, and action

**View Mode System (`models/view_mode.py`):**
- `ViewMode` enum defines available modes: NORMAL, MARKETPLACE
- `M` key cycles through modes via `action_cycle_mode()`
- Each view mode switches visibility of entire UI containers
- `AppFooter` displays current mode and context-specific content

**Plugin Scopes:**
Plugins can be installed, enabled, or disabled at three scopes:
- **User** (`~/.claude/`) - Personal installation, available across all projects
- **Project** (`./.claude/`) - Team-shared installation, version controlled
- **Local** (`./.claude/local/`) - Local installation, not version controlled

**Plugin Actions (via Claude CLI):**
```bash
claude plugin install <plugin_id> --scope user|project|local  # Install from marketplace
claude plugin enable <plugin_id> --scope user|project|local   # Enable disabled plugin
claude plugin disable <plugin_id> --scope user|project|local  # Disable enabled plugin
claude plugin uninstall <plugin_id>                          # Remove installed plugin
```

Commands run in background workers (`@work(thread=True)`) to keep UI responsive.

## Implementation Principles

**Simplicity over Generality**
- Don't add features, refactoring, or improvements beyond what's requested
- One-time operations don't need helpers or abstractions
- Don't add docstrings or comments to code you didn't change
- Trust internal code and framework guarantees; validate only at system boundaries (user input, external APIs)

**Documentation Updates**
- Every feature change MUST include documentation updates
- Update relevant sections in CLAUDE.md (keybindings, widget responsibilities, etc.)

## Mandatory Testing & Commit Rules

**KRITICKÁ PRAVIDLA - VŽDY DODRŽOVAT:**

1. **NEKOMITOVAT BEZ SCHVÁLENÍ** - Nikdy neudělej `git commit` dokud uživatel neschválí změny!
   - Změny mohou být rollbacknuty (`git reset HEAD~1`)
   - Vždy čekej na explicitní potvrzení od uživatele

2. **VŽDY TESTOVAT SPUŠTĚNÍ** - Po jakýchkoli změnách v kódu:
   ```bash
   timeout 5 uv run lazyclaude --debug 2>&1 || true
   ```
   - Testuješ že aplikace: a) spustí se, b) nepadne hned, c) --debug funguje
   - Timeout 5 sekund zajistí že se nezasekneš
   - Pokud nefunguje -> opravit a testovat znovu

3. **POSTUP PŘED COMMITEM:**
   ```
   a) Udělat změny
   b) Spustit: timeout 5 uv run lazyclaude --debug 2>&1 || true
   c) Počkat na schválení uživatelem
   d) Teprve pak commitnout
   ```

4. **SUBPROCESS SHELL COMMANDS** - Specifické pro tento projekt:
   - Při použití `subprocess.run(..., shell=True)` MUSÍŠ převést list na string
   - Správně: `cmd_str = shlex.join(cmd); subprocess.run(cmd_str, ..., shell=True)`
   - Špatně: `subprocess.run(cmd, ..., shell=True)` - spustí se jen první element!

5. **QUALITY GATES** - Před commitem vždy:
   ```bash
   uv run ruff format src/     # Format
   uv run ruff check src/      # Lint
   uv run mypy src/            # Typecheck
   uv run pytest               # Tests
   ```
