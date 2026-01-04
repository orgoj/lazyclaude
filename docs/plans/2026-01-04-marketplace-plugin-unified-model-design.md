# Marketplace & Plugin Unified Data Model

**Date:** 2026-01-04
**Status:** Design
**Author:** Michael Heca

## Problem Statement

Current marketplace and plugin data model has inconsistencies between CLI and TUI display:
- CLI shows plugins as enabled when they're NOT installed in current project
- TUI shows correct state but may have duplicate filtering logic
- Data spread across multiple files (installed_plugins.json, settings.json × 3 scopes, known_marketplaces.json)
- No single source of truth for plugin/marketplace state computation

## Goals

1. **Single source of truth** - One unified model for all plugin/marketplace state
2. **Read-only display layer** - Model serves only for display, not persistence
3. **Simple reload** - After CLI commands modify settings.json, full reload creates fresh model
4. **Hierarchical structure** - Marketplaces contain plugins (for TUI tree)
5. **Scope-aware** - Properly handle user/project/local hierarchy

## Data Model

### Core Structures

```python
@dataclass
class ScopeState:
    """State of plugin/marketplace in one scope (user/project/local)"""
    installed: bool
    enabled: bool | None  # None = no override in settings.json
    install_path: Path | None = None
    version: str | None = None

@dataclass
class MarketplaceState:
    """Unified marketplace state across all scopes"""
    name: str
    source_url: str  # GitHub repo or directory path
    description: str = ""
    author: dict | None = None  # {"name": "...", "email": "...", "url": "..."}

    # Marketplace has only installed (automatically enabled when installed)
    user: ScopeState
    project: ScopeState
    local: ScopeState  # Probably never used, but kept for consistency

    # Children
    plugins: list[PluginState] = field(default_factory=list)

@dataclass
class PluginState:
    """Unified plugin state across all scopes"""
    plugin_id: str  # "name@marketplace"
    name: str  # Just name without @marketplace
    marketplace_name: str  # Reference to parent

    # Plugin has installed + enabled
    user: ScopeState
    project: ScopeState
    local: ScopeState

    # Metadata from marketplace.json
    description: str = ""
    author: dict | None = None
    source: str = ""  # Relative source within marketplace
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None
    category: str | None = None
    keywords: list[str] | None = None
```

### Computed Properties

```python
@dataclass
class PluginState:
    # ... basic attributes ...

    @property
    def is_installed_anywhere(self) -> bool:
        """Is plugin installed in any scope?"""
        return self.user.installed or self.project.installed or self.local.installed

    @property
    def is_accessible_in_current_project(self) -> bool:
        """Is plugin accessible in current project?

        - user installed → YES (available everywhere)
        - project installed → YES (in this project)
        - local installed → YES (in this project)
        """
        return (
            self.user.installed or
            self.project.installed or
            self.local.installed
        )

    @property
    def effective_enabled(self) -> bool:
        """Effective enabled state based on hierarchy local > project > user.

        Returns last non-null enabled value, or True if no override.
        """
        # Check local → project → user (first non-null wins)
        if self.local.enabled is not None:
            return self.local.enabled
        if self.project.enabled is not None:
            return self.project.enabled
        if self.user.enabled is not None:
            return self.user.enabled

        # Default: if installed, it's enabled
        return self.is_installed_anywhere
```

## Scope Hierarchy

### Installed Hierarchy (Accessibility)

- **user installed** → accessible to user/project/local (everywhere)
- **project installed** → accessible to project/local (NOT user)
- **local installed** → accessible to local only

### Enabled Hierarchy (Override Resolution)

**Last non-null wins** (local > project > user):

Examples:
- user=true, project=null, local=false → **false**
- user=false, project=true, local=null → **true**
- user=true, project=null, local=null → **true**

Override can exist without installation in that scope:
- user: installed=true, enabled=true
- project: installed=false, enabled=false → **valid** (disables user plugin in this project)

## Display Format

### New Format: `user/project/local`

Each scope shows:
- `Ie` = installed + enabled
- `Id` = installed + disabled
- `e` = override enabled (not installed, but enabled=true in settings.json)
- `d` = override disabled (not installed, but enabled=false in settings.json)
- `-` = nothing (not installed, no override)

**Examples:**
- `Ie/-/-` = only user installed+enabled
- `Id/e/-` = user installed+disabled, project override enabled
- `Ie/Id/Ie` = all installed+enabled except project disabled
- `Ie/Ie/-` = user and project installed+enabled

**Marketplace format** (only installed, no enabled):
- `I/-/-` = only user installed
- `I/I/-` = user and project installed

## Loading Logic

### Data Sources (on disk)

1. `~/.claude/plugins/known_marketplaces.json` - marketplace registry
2. `<marketplace_location>/.claude-plugin/marketplace.json` - plugin catalog per marketplace
3. `~/.claude/plugins/installed_plugins.json` - installation registry
4. `~/.claude/settings.json` - user scope enabled overrides
5. `.claude/settings.json` - project scope enabled overrides
6. `.claude/settings.local.json` - local scope enabled overrides

### Loading Sequence

```python
class UnifiedDataLoader:
    def __init__(
        self,
        user_config_path: Path,
        project_config_path: Path,
        project_root: Path,
    ):
        self.user_config_path = user_config_path
        self.project_config_path = project_config_path
        self.project_root = project_root

    def load_marketplace_states(self) -> list[MarketplaceState]:
        """Load marketplaces with their plugins - hierarchical structure for TUI tree"""

        # 1. Load installed_plugins.json
        installed = self._load_installed_plugins()
        # → dict[plugin_id, list[Installation]]

        # 2. Load settings.json from 3 scopes
        user_enabled = self._load_enabled_plugins(
            self.user_config_path / "settings.json"
        )
        project_enabled = self._load_enabled_plugins(
            self.project_config_path / "settings.json"
        )
        local_enabled = self._load_enabled_plugins(
            self.project_config_path / "settings.local.json"
        )
        # → dict[plugin_id, bool]

        # 3. Load known_marketplaces.json
        marketplace_entries = self._load_known_marketplaces()

        # 4. For each marketplace:
        #    - Load its marketplace.json → list of plugins
        #    - Create MarketplaceState
        #    - For each plugin create PluginState (with data from installed_plugins + settings)
        #    - Add PluginState to MarketplaceState.plugins

        marketplaces = []
        for entry in marketplace_entries:
            marketplace = MarketplaceState(
                name=entry.name,
                source_url=entry.source.repo or entry.source.path,
                description=entry.description,
                author=entry.owner,
                user=self._build_marketplace_scope_state(entry.name, "user", installed),
                project=self._build_marketplace_scope_state(entry.name, "project", installed),
                local=self._build_marketplace_scope_state(entry.name, "local", installed),
                plugins=[],
            )

            # Load plugins for this marketplace
            plugin_metadata_list = self._load_marketplace_plugins(entry)
            for plugin_meta in plugin_metadata_list:
                plugin_id = f"{plugin_meta['name']}@{entry.name}"

                plugin = PluginState(
                    plugin_id=plugin_id,
                    name=plugin_meta['name'],
                    marketplace_name=entry.name,
                    user=self._build_plugin_scope_state(
                        plugin_id, "user", installed, user_enabled
                    ),
                    project=self._build_plugin_scope_state(
                        plugin_id, "project", installed, project_enabled
                    ),
                    local=self._build_plugin_scope_state(
                        plugin_id, "local", installed, local_enabled
                    ),
                    description=plugin_meta.get('description', ''),
                    # ... other metadata
                )
                marketplace.plugins.append(plugin)

            marketplaces.append(marketplace)

        return marketplaces

    def _build_plugin_scope_state(
        self,
        plugin_id: str,
        scope: str,  # "user" | "project" | "local"
        installed_data: dict[str, list[Installation]],
        enabled_map: dict[str, bool],
    ) -> ScopeState:
        """Build ScopeState for one scope from disk data"""

        installations = installed_data.get(plugin_id, [])

        # Find installation in this scope
        matching_install = None
        for inst in installations:
            if inst.scope == scope:
                # For project/local must match project_path
                if scope in ("project", "local"):
                    if inst.project_path == str(self.project_root.resolve()):
                        matching_install = inst
                        break
                else:  # user scope
                    matching_install = inst
                    break

        # installed = found installation in this scope
        installed = matching_install is not None

        # enabled = value from settings.json enabledPlugins
        # None = not in settings.json (no override)
        enabled = enabled_map.get(plugin_id)  # bool | None

        return ScopeState(
            installed=installed,
            enabled=enabled,
            install_path=Path(matching_install.install_path) if matching_install else None,
            version=matching_install.version if matching_install else None,
        )
```

## Display Formatting

```python
@dataclass
class PluginState:
    # ... previous attributes ...

    def format_scope_display(self) -> str:
        """Format status as 'user/project/local' e.g: 'Ie/Id/-'"""
        return f"{self._format_scope('user')}/{self._format_scope('project')}/{self._format_scope('local')}"

    def _format_scope(self, scope_name: str) -> str:
        """Format one scope as: Ie/Id/e/d/-"""
        scope = getattr(self, scope_name)  # self.user / self.project / self.local

        if scope.installed:
            # Installed in this scope
            if scope.enabled is False:
                return "Id"  # Installed + disabled override
            else:
                return "Ie"  # Installed + enabled (or no override)
        else:
            # Not installed, but possible override in settings.json
            if scope.enabled is True:
                return "e"  # Override enabled
            elif scope.enabled is False:
                return "d"  # Override disabled
            else:
                return "-"  # Nothing

@dataclass
class MarketplaceState:
    # ... previous attributes ...

    def format_scope_display(self) -> str:
        """Marketplace has only installed (automatically enabled)"""
        return f"{self._format_scope('user')}/{self._format_scope('project')}/{self._format_scope('local')}"

    def _format_scope(self, scope_name: str) -> str:
        scope = getattr(self, scope_name)
        return "I" if scope.installed else "-"  # Only installed/not installed
```

## CLI/TUI Integration

### Data Flow

```
Disk files → UnifiedDataLoader → MarketplaceState[] (with nested PluginState[])
                                        ↓
                        ┌───────────────┴───────────────┐
                        ↓                               ↓
                    CLI Display                     TUI Display
                (flat list view)                  (tree view)
```

### CLI Commands (Write Operations)

CLI commands modify settings.json directly, then trigger reload:

```python
def handle_enable(plugin_id: str, scope: str):
    # 1. Write to appropriate settings.json
    settings_path = get_settings_path(scope)  # user/project/local
    settings = load_json(settings_path)
    settings['enabledPlugins'][plugin_id] = True
    save_json(settings_path, settings)

    # 2. Reload unified model (happens automatically on next CLI invocation)
    # No need to update in-memory model - it's read-only
```

### Filtering

Both CLI and TUI use same filtering on unified model:

```python
def filter_plugins(
    marketplaces: list[MarketplaceState],
    installed_only: bool = False,
    enabled_only: bool = False,
) -> list[PluginState]:
    """Filter plugins across all marketplaces"""
    all_plugins = []
    for mp in marketplaces:
        all_plugins.extend(mp.plugins)

    if installed_only:
        all_plugins = [p for p in all_plugins if p.is_accessible_in_current_project]

    if enabled_only:
        all_plugins = [p for p in all_plugins if p.effective_enabled]

    return all_plugins
```

## Migration Path

### Phase 1: Create Unified Model (No Breaking Changes)

1. Create new `UnifiedDataLoader` class
2. Create `MarketplaceState` and `PluginState` dataclasses
3. Keep existing `MarketplaceLoader` and `PluginLoader` for backward compatibility
4. Add tests for unified model loading

### Phase 2: Migrate CLI

1. Update CLI to use `UnifiedDataLoader`
2. Update display formatting to new `user/project/local` format
3. Remove old formatting logic from CLI
4. Verify CLI tests pass

### Phase 3: Migrate TUI

1. Update TUI to use `UnifiedDataLoader`
2. Update marketplace tree to use `MarketplaceState.plugins` hierarchy
3. Remove duplicate filtering logic from TUI widgets
4. Update display to use `format_scope_display()`
5. Verify TUI tests pass

### Phase 4: Cleanup

1. Remove old `MarketplaceLoader` and `PluginLoader` (if fully replaced)
2. Remove `PluginDataProvider` wrapper (if no longer needed)
3. Update documentation

## Benefits

1. **Correctness** - CLI and TUI always show same state (single source of truth)
2. **Simplicity** - Clear separation between data loading and display
3. **Maintainability** - All scope logic in one place
4. **Testability** - Easy to test unified model independently
5. **Performance** - Load once, display many times (CLI/TUI use same model)

## Open Questions

None - design validated with user.
