# LazyClaude User Guide

A keyboard-driven TUI for visualizing and managing Claude Code customizations.

## Table of Contents

- [LazyClaude User Guide](#lazyclaude-user-guide)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Getting Started](#getting-started)
    - [First Launch](#first-launch)
  - [Understanding the Interface](#understanding-the-interface)
    - [Customization Types](#customization-types)
    - [Configuration Levels](#configuration-levels)
    - [Panel Layout](#panel-layout)
  - [Core Workflows](#core-workflows)
    - [1. Viewing and Filtering Configurations](#1-viewing-and-filtering-configurations)
    - [2. Editing Customizations](#2-editing-customizations)
    - [3. Managing Configurations Across Levels](#3-managing-configurations-across-levels)
      - [Copy vs Move](#copy-vs-move)
      - [Scenario A: Customize Plugin Content](#scenario-a-customize-plugin-content)
      - [Scenario B: Share Configuration with Team](#scenario-b-share-configuration-with-team)
    - [4. Working with Marketplace](#4-working-with-marketplace)
      - [Browse and Install Plugins](#browse-and-install-plugins)
      - [Preview Plugin Content](#preview-plugin-content)
      - [Manage Installed Plugins](#manage-installed-plugins)
  - [Keyboard Reference](#keyboard-reference)
    - [Global Bindings](#global-bindings)
    - [Navigation](#navigation)
    - [Panel Actions](#panel-actions)
    - [Configuration Management](#configuration-management)
    - [Filtering](#filtering)
    - [Marketplace](#marketplace)
  - [Tips and Best Practices](#tips-and-best-practices)
    - [Configuration Strategy](#configuration-strategy)
    - [Efficient Workflows](#efficient-workflows)
    - [Keyboard Shortcuts Memorization](#keyboard-shortcuts-memorization)

## Introduction

LazyClaude is a terminal user interface (TUI) for managing Claude Code customizations. It provides a visual way to explore, edit, and organize your slash commands, subagents, skills, memory files, MCPs, and hooks across different configuration levels.

**Key Features:**
- Visual exploration of all Claude Code customizations
- Multi-level configuration management (user, project, plugin)
- Copy and move configurations between levels
- Marketplace browser for discovering and installing plugins
- Preview installed plugin content to understand customizations
- Keyboard-driven workflow inspired by lazygit

## Getting Started

```bash
# Basic usage
uvx lazyclaude

# Start with marketplace browser open
uvx lazyclaude --marketplace

# Enable debug mode (logs to /tmp/lazyclaude.log)
uvx lazyclaude --debug

# Specify project directory
uvx lazyclaude --directory /path/to/project

# Show version
uvx lazyclaude --version
```

### First Launch

When you first launch LazyClaude, you'll see:
- Left sidebar with panels for each customization type
- Right pane showing content of selected item
- Status bar showing current path and filter state
- Footer with keyboard shortcuts

![First Launch](./assets/first-launch.gif)

**Quick Start:**
1. Use `j`/`k` or arrow keys to navigate
2. Press `1-6` or `Tab` to switch between panels
3. Press `[` / `]` to toggle between content and metadata views
4. Press `?` for help, `q` to quit

## Understanding the Interface

### Customization Types

LazyClaude organizes Claude Code customizations into six types:

| Type               | Panel | Description                               |
| ------------------ | ----- | ----------------------------------------- |
| **Slash Commands** | `[1]` | Custom commands like `/commit`, `/review` |
| **Subagents**      | `[2]` | Specialized agents for specific tasks     |
| **Skills**         | `[3]` | Reusable workflows and procedures         |
| **Memory Files**   | `[4]` | Context files referenced with `@`         |
| **MCPs**           | `[5]` | Model Context Protocol servers            |
| **Hooks**          | `[6]` | Event-driven automations                  |

### Configuration Levels

Customizations exist at different levels, allowing you to control scope and sharing:

| Level             | Location             | Purpose                            | Version Control |
| ----------------- | -------------------- | ---------------------------------- | --------------- |
| **User**          | `~/.claude/`         | Personal global configurations     | No              |
| **Project**       | `./.claude/`         | Project-specific, shared with team | Yes (git)       |
| **Project Local** | `./.claude/local/`   | Project-specific, machine-local    | No              |
| **Plugin**        | `~/.claude/plugins/` | Installed marketplace extensions   | No              |

### Panel Layout

```
┌─────────────────────────────────────────────────────┐
│ Status: lazyclaude | All                            │
├──────────────────────┬──────────────────────────────┤
│ [1] Slash Commands   │                              │
│   handbook:commit    │    Content / Metadata        │
│   open-files         │    (toggle with [ / ])       │
│   reflect            │                              │
│                      │    Syntax highlighting       │
│ [2] Subagents        │    Markdown rendering        │
│   handbook:review    │    File trees for skills     │
│   git-diff-analyzer  │                              │
│                      │                              │
│ [3] Skills           │                              │
│   quality-gates      │                              │
│   uspp:uspp-monitor  │                              │
│                      │                              │
│ [4] Memory | [5] MCP │                              │
│     [6] Hooks        │                              │
└──────────────────────┴──────────────────────────────┘
│ Quit | Help | Edit | Copy | Move | Search | Market  │
└─────────────────────────────────────────────────────┘
```

## Core Workflows

### 1. Viewing and Filtering Configurations

**Use Case:** Understand what customizations are available and where they're defined.

**Steps:**
1. Launch LazyClaude: `uv run lazyclaude`
2. Press `1-6` to focus different customization types
3. Use filter keys to narrow view:
   - `a` - Show All levels
   - `u` - Show only User level
   - `p` - Show only Project level
   - `P` - Show only Plugin level
4. Press `D` to toggle visibility of disabled plugins
5. Navigate items with `j`/`k` or arrow keys
6. Press `[` / `]` to switch between content and metadata views

![Filter Workflow Demo](./assets/demo-filter-workflow.gif)

**Tips:**
- Status bar shows current filter (e.g., `lazyclaude | Project`)
- Combine filters with panel navigation for efficient browsing
- Use `/` to search within current view

### 2. Editing Customizations

**Use Case:** Modify a customization to change its behavior.

**Steps:**
1. Navigate to the customization you want to edit
2. Press `e` to open in your `$EDITOR`
3. Make your changes and save
4. Press `r` to refresh LazyClaude and see updates


**Requirements:**
- `$EDITOR` environment variable must be set (e.g., `export EDITOR=vim`)
- Write permissions for the target file

**Tip:** Use `C` to copy the file path to clipboard for external editing

### 3. Managing Configurations Across Levels

**Use Case:** Copy customizations between levels to share with team, customize plugin content, or reorganize configurations.

This is one of LazyClaude's most powerful features, enabling several common scenarios:
- Install a plugin and customize it for personal use
- Share personal configurations with your team
- Promote local configs to version control
- Reorganize configuration hierarchy

#### Copy vs Move

| Operation | Key | Behavior                                    | Use When                             |
| --------- | --- | ------------------------------------------- | ------------------------------------ |
| **Copy**  | `c` | Creates duplicate at target, keeps original | Customizing plugins, sharing configs |
| **Move**  | `m` | Removes original, creates at target         | Reorganizing, promoting configs      |

#### Scenario A: Customize Plugin Content

**Goal:** Install a marketplace plugin and customize it for your personal workflow.

**Steps:**
1. Press `M` to open marketplace
2. Install the plugin (see [Working with Marketplace](#4-working-with-marketplace))
3. Press `Esc` to close marketplace
4. Press `P` to filter to Plugin level
5. Navigate to the plugin customization you want to customize
6. Press `c` to initiate copy operation
7. Select `User` as target level
8. Press `u` to filter to User level and verify the copy
9. Press `e` to edit your personal copy

**Example Flow:**
```
Plugin → Copy → User → Edit
```

**Why Copy Instead of Edit?**
- Preserves original plugin for updates
- Allows personal customization without conflicts
- Can revert by deleting user copy

#### Scenario B: Share Configuration with Team

**Goal:** Share a useful personal configuration with your team by adding it to version control.

**Steps:**
1. Press `u` to filter to User level
2. Navigate to the customization you want to share
3. Press `c` to initiate copy operation
4. Select `Project` as target level
5. The customization is now in `./.claude/`
6. Press `p` to filter to Project level and verify
7. Commit to git:
   ```bash
   git add .claude/
   git commit -m "Add custom slash command"
   git push
   ```


**Example Flow:**
```
User → Copy → Project → Git Commit
```

**Benefits:**
- Team gets access to your custom workflows
- Configuration is version controlled
- Changes can be reviewed via pull requests


### 4. Working with Marketplace

**Use Case:** Discover, install, preview, and manage marketplace plugins.

The marketplace is accessed via **view mode** - press `M` to cycle between Normal and Marketplace views. The marketplace view replaces the main interface with a full-screen plugin browser.

#### Browse and Install Plugins

**Steps:**
1. Press `M` to switch to Marketplace view (or start with `--marketplace` flag)
2. Navigate with `j`/`k` to browse marketplaces and plugins
3. Press `l` or `Enter` to expand a marketplace tree
4. Press `h` to collapse a marketplace tree
5. Find a plugin you want to install
6. Press `I` (Shift+i) to install
7. Select the scope for installation:
   - **User** (`1` or `u`) - Install for current user only
   - **Project** (`2` or `p`) - Install for current project
   - **Local** (`3` or `l`) - Install locally (not version controlled)
8. Wait for installation to complete
9. Press `Esc` to return to Normal view
10. Press `P` to filter to Plugin level and explore

![Marketplace Install Demo](./assets/demo-marketplace-install.gif)

**Marketplace Status Icons:**

Plugins show their installation state across scopes:
- `[I:upl]` - Installed and enabled in user, project, and/or local scopes
- `[E:upl]` - Enabled in specific scopes (u=user, p=project, l=local)
- `[D:upl]` - Disabled in specific scopes
- Example: `[I:u E:p D:l]` = installed in user, enabled in project, disabled in local

**Marketplace Actions:**
- `I` (Shift+i) - Install plugin (prompts for scope selection)
- `E` (Shift+e) - Enable plugin (prompts for scope selection)
- `D` - Disable plugin (prompts for scope selection)
- `U` (Shift+u) - Uninstall plugin
- `i` - Toggle installed-only filter
- `n` - Toggle enabled-only filter
- `p` - Preview installed plugin content
- `e` - Open installed plugin folder in file manager
- `o` - Open plugin source URL in browser
- `u` - Update marketplace or plugin
- `A` (Shift+a) - Add new marketplace source
- `L` (Shift+l) - Expand all marketplaces
- `H` - Collapse all marketplaces
- `/` - Search/filter within marketplace

#### Preview Plugin Content

**Use Case:** Explore an installed plugin's contents to understand what customizations it provides (commands, skills, subagents, MCPs, hooks, memory files).

**Steps:**
1. Press `M` to switch to Marketplace view
2. Navigate to an **installed** plugin (e.g., `handbook-glab@cc-handbook`)
3. Press `p` to enter preview mode
4. App switches to NORMAL view mode and displays plugin customizations in sidebar panels
5. Main pane shows plugin's README.md (if available)
6. Status panel displays "Preview: PluginName (version)"
7. Use `1-6` to explore different customization types
8. Press `[` / `]` to view content and metadata
9. Press `Esc` to exit preview mode and return to Marketplace view

**Note:** Preview only works on installed plugins. If you press `p` on an uninstalled plugin, you'll see a warning message.

![Preview Plugin Demo](./assets/demo-preview-plugin.gif)

**Preview Mode Features:**
- View all customizations included in a plugin
- Read content and metadata without installing
- Understand plugin structure and capabilities
- Navigate as if plugin were installed (read-only)

**When to Preview:**
- Evaluating plugins before installation
- Checking if plugin meets your needs
- Understanding plugin structure
- Learning from plugin implementations

#### Manage Installed Plugins

**Steps:**
1. Press `M` to switch to Marketplace view
2. Navigate to an installed plugin (marked with scope status icons)
3. Use management actions:
   - `E` (Shift+e) - Enable plugin at specific scope
   - `D` - Disable plugin at specific scope
   - `U` (Shift+u) - Uninstall plugin
   - `e` - Open installed plugin folder
   - `o` - Open source URL in browser
   - `u` - Update plugin
4. Press `Esc` to return to Normal view

**Plugin States by Scope:**

Each plugin can have different states in different scopes:
- **User scope** (`~/.claude/`) - Personal installation
- **Project scope** (`./.claude/`) - Team-shared installation
- **Local scope** (`./.claude/local/`) - Local-only installation

A plugin can be:
- **Installed** - Present in one or more scopes
- **Enabled** - Active and loaded by Claude Code
- **Disabled** - Present but not loaded

Example: A plugin might be enabled in User scope but disabled in Project scope.

#### Add Marketplace Sources

**Steps:**
1. Press `M` to switch to Marketplace view
2. Press `A` (Shift+a) to add marketplace source
3. Enter marketplace source:
   - **GitHub**: `github:user/repo` (e.g., `github:anthropics/cclaude-marketplace`)
   - **Directory**: Absolute path to local marketplace
4. Press `Enter` to add
5. Marketplace loads and appears in the tree

**Use Cases:**
- Add custom marketplace for your organization
- Test marketplace changes from local clone
- Access private marketplace repositories

## Keyboard Reference

### Global Bindings

| Key   | Action  | Description                |
| ----- | ------- | -------------------------- |
| `q`   | Quit    | Exit LazyClaude            |
| `?`   | Help    | Show help screen           |
| `r`   | Refresh | Reload configurations      |
| `/`   | Search  | Search/filter current view |
| `Esc` | Back    | Return to previous context |

### Navigation

| Key       | Action      | Description             |
| --------- | ----------- | ----------------------- |
| `j` / `↓` | Down        | Move selection down     |
| `k` / `↑` | Up          | Move selection up       |
| `g`       | Top         | Jump to first item      |
| `G`       | Bottom      | Jump to last item       |
| `d`       | Page Down   | Scroll detail pane down |
| `u`       | Page Up     | Scroll detail pane up   |
| `Tab`     | Next Panel  | Switch to next panel    |
| `0-6`     | Focus Panel | Jump directly to panel  |

### Panel Actions

| Key     | Action        | Description              |
| ------- | ------------- | ------------------------ |
| `[`     | Content View  | Show content             |
| `]`     | Metadata View | Show metadata            |
| `Enter` | Drill Down    | Expand tree or open item |

### Configuration Management

| Key      | Action      | Description                 |
| -------- | ----------- | --------------------------- |
| `e`      | Edit        | Open in `$EDITOR`           |
| `c`      | Copy        | Copy to another level       |
| `m`      | Move        | Move to another level       |
| `C`      | Copy Path   | Copy file path to clipboard |
| `Ctrl+u` | User Config | Open `~/.claude/`           |

### Filtering

| Key | Action          | Description                |
| --- | --------------- | -------------------------- |
| `a` | All             | Show all levels            |
| `u` | User            | Show only user level       |
| `p` | Project         | Show only project level    |
| `P` | Plugin          | Show only plugin level     |
| `D` | Toggle Disabled | Show/hide disabled plugins |

### Marketplace

| Key              | Action                  | Description                              |
| ---------------- | ----------------------- | ---------------------------------------- |
| `M`              | Cycle View Mode         | Switch between Normal and Marketplace views |
| `I` (Shift+i)    | Install Plugin          | Install plugin at selected scope         |
| `E` (Shift+e)    | Enable Plugin           | Enable plugin at selected scope          |
| `D`              | Disable Plugin          | Disable plugin at selected scope         |
| `U` (Shift+u)    | Uninstall Plugin        | Remove plugin                            |
| `A` (Shift+a)    | Add Marketplace         | Add new marketplace source               |
| `i`              | Toggle Installed Filter | Show only installed plugins              |
| `n`              | Toggle Enabled Filter   | Show only enabled plugins                |
| `p`              | Preview Plugin          | Preview installed plugin content         |
| `e`              | Open Folder             | Open installed plugin folder             |
| `o`              | Open Source             | Open plugin source URL in browser        |
| `u`              | Update                  | Update marketplace or plugin             |
| `h` / `l`        | Collapse/Expand         | Collapse/Expand marketplace tree          |
| `H`              | Collapse All            | Collapse all marketplace trees           |
| `L` (Shift+l)    | Expand All              | Expand all marketplace trees             |
| `1`/`2`/`3`      | Select Scope            | Select user/project/local scope          |
| `u`/`p`/`l`      | Select Scope (alt)      | Select user/project/local scope (alt)    |

### Scope Selection

When installing, enabling, or disabling plugins, a scope selector appears:

| Key        | Action       | Description                      |
| ---------- | ------------ | -------------------------------- |
| `1` / `u`  | User Scope   | Select user-level installation   |
| `2` / `p`  | Project Scope| Select project-level installation|
| `3` / `l`  | Local Scope  | Select local-level installation  |
| `Esc`      | Cancel       | Cancel scope selection           |

## Tips and Best Practices

### Configuration Strategy

**User Level** (`~/.claude/`)
- Personal preferences and workflows
- Custom commands for your coding style
- Experiments and prototypes
- Plugins you want in all projects

**Project Level** (`./.claude/`)
- Team-shared commands and skills
- Project-specific conventions
- Standardized workflows
- Version-controlled configurations
- Plugins needed by the team

**Project Local** (`./.claude/local/`)
- Local development overrides
- Temporary experiments
- Machine-specific configurations
- Not version controlled

**Plugin Level** (`~/.claude/plugins/`)
- Install from marketplace
- Keep originals untouched
- Copy to user level to customize
- Scope: install per-user, per-project, or locally

### Understanding View Modes

LazyClaude uses a **view mode system** that switches the entire interface:

1. **Normal View** (default)
   - Shows sidebar with customization panels
   - Detail pane for selected items
   - Use for browsing and editing customizations

2. **Marketplace View**
   - Full-screen plugin browser
   - Tree of marketplaces and plugins
   - Use for installing and managing plugins

Press `M` to cycle between view modes. The footer shows the current mode.

### Efficient Workflows

**Quick Copy Pattern:**
```
[P]lugin → navigate → [c]opy → User
[u]ser → navigate → [e]dit
```

**Share with Team:**
```
[u]ser → navigate → [c]opy → Project
git add .claude/ && git commit
```

**Browse and Install:**
```
[M] → [l]expand → navigate → [I]nstall → select scope
[Esc] → [P]lugin → verify
```

**Preview Installed Plugin:**
```
[M] → navigate to installed plugin → [p]review
Explore in panels (commands, skills, etc.)
[Esc] → return to marketplace
```

**Install Plugin for Project:**
```
[M] → navigate to plugin → [I]nstall → [2/p] for Project scope
```

**Install Plugin for Personal Use:**
```
[M] → navigate to plugin → [I]nstall → [1/u] for User scope
```

### Debug Mode

Enable debug mode when troubleshooting or reporting issues:

```bash
uvx lazyclaude --debug
# Or
uv run lazyclaude --debug
```

Debug mode:
- Logs detailed information to `/tmp/lazyclaude.log`
- Includes tracebacks for errors
- Useful for bug reports and troubleshooting

Watch the log in another terminal:
```bash
tail -f /tmp/lazyclaude.log
```

### Keyboard Shortcuts Memorization

**By Frequency:**
1. `j`/`k` - Navigation (most used)
2. `1-6` - Panel switching
3. `[`/`]` - View toggling
4. `e` - Edit (daily use)
5. `c` - Copy (common operation)
6. `M` - Cycle view modes (occasional)

**By Category:**
- **Navigation**: `j`, `k`, `g`, `G`, `Tab`, `0-6`
- **Viewing**: `[`, `]`, `a`, `u`, `p`, `P`, `D`
- **Actions**: `e`, `c`, `m`, `C`
- **Global**: `q`, `?`, `r`, `/`, `Esc`, `M`
- **Marketplace**: `I`, `E`, `D`, `U`, `A`, `p`

---

**Version:** 0.11.0
**Last Updated:** 2025-12-30
