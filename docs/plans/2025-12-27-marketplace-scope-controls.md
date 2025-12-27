# Marketplace Scope Controls Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign marketplace plugin controls to match Claude CLI model with separate Install/Uninstall/Enable/Disable operations, each with scope selector

**Architecture:** Replace single toggle action (i) with four distinct actions (I/E/D/U) using scope selectors. Remove state-based menu logic, show universal menu for all plugins. Validate actions in scope selector based on current installation/enabled status per scope.

**Tech Stack:** Python 3.11+, Textual (TUI), pytest, pyfakefs, Claude CLI (subprocess calls)

---

## Overview

Current marketplace mixes install/enable/disable into single 'i' action. Claude CLI has separate commands:
- `claude plugin install -s <scope> <plugin>`
- `claude plugin uninstall -s <scope> <plugin>`
- `claude plugin enable -s <scope> <plugin>`
- `claude plugin disable -s <scope> <plugin>`

This redesign aligns lazyclaude TUI with CLI model.

### Key Changes

1. **Universal menu** - Always show I/E/D/U options regardless of plugin state
2. **Separate actions** - I=Install, E=Enable, D=Disable, U=Uninstall (Shift+key bindings)
3. **Scope selector validation** - Disable action on PROJECT/LOCAL always allowed (CLI handles edge cases)
4. **Remove legacy code** - Delete action_toggle_plugin(), old i/d bindings

### Scope Status Icons

- `[✓]` = enabled in scope
- `[✗]` = disabled in scope
- `[ ]` = not installed in scope

---

## Task 1: Add new Shift+key bindings to MarketplaceModal

**Files:**
- Modify: `src/lazyclaude/widgets/marketplace_modal.py:20-36`

**Step 1: Add new bindings**

```python
BINDINGS = [
    Binding("escape", "close_or_cancel", "Close", show=False),
    Binding("/", "search", "Search", show=False),
    # New bindings with Shift+keys
    Binding("I", "install_plugin", "Install", show=False),
    Binding("E", "enable_plugin", "Enable", show=False),
    Binding("D", "disable_plugin", "Disable", show=False),
    Binding("U", "uninstall_plugin", "Uninstall", show=False),
    # Existing bindings (keep lowercase e, u)
    Binding("p", "preview_plugin", "Preview", show=False),
    Binding("e", "open_plugin_folder", "Edit", show=False),
    Binding("o", "open_source", "Open", show=False),
    Binding("u", "update_marketplace", "Update", show=False),
    # Navigation bindings (unchanged)
    Binding("j", "cursor_down", "Down", show=False),
    Binding("k", "cursor_up", "Up", show=False),
    Binding("space", "toggle_node", "Toggle", show=False),
    Binding("right", "expand_node", "Expand", show=False),
    Binding("l", "expand_node", "Expand", show=False),
    Binding("left", "collapse_node", "Collapse", show=False),
    Binding("h", "collapse_node", "Collapse", show=False),
]
```

**Step 2: Verify no duplicate keys**

Check: No key conflicts (I/E/D/U are new, e/u/p/o remain unchanged)

**Step 3: Commit**

```bash
git add src/lazyclaude/widgets/marketplace_modal.py
git commit -m "feat: add I/E/D/U Shift+key bindings for marketplace actions"
```

---

## Task 2: Simplify footer to universal menu

**Files:**
- Modify: `src/lazyclaude/widgets/marketplace_modal.py:189-212`

**Step 1: Replace state-based footer with universal footer**

Find `_update_footer()` method, replace entire implementation:

```python
def _update_footer(self, data: MarketplacePlugin | Marketplace | None) -> None:
    """Update footer based on selected item."""
    footer = self.query_one("#marketplace-footer", Static)

    if isinstance(data, MarketplacePlugin):
        # Universal menu - always show all options
        footer.update(
            "[bold]p[/] Preview  [bold]I[/] Install  [bold]E[/] Enable  "
            "[bold]D[/] Disable  [bold]u[/] Update  [bold]U[/] Uninstall  "
            "[bold]e[/] Edit  [bold]o[/] Open  [bold]/[/] Search  [bold]Esc[/] Close"
        )
    elif isinstance(data, Marketplace):
        footer.update(
            "[bold]Space[/] Toggle  [bold]u[/] Update  [bold]o[/] Open  "
            "[bold]/[/] Search  [bold]Esc[/] Close"
        )
    else:
        footer.update("[bold]/[/] Search  [bold]Esc[/] Close")
```

**Step 2: Test footer rendering**

Run: `uv run lazyclaude --directory /tmp`
Navigate to marketplace, press M, verify footer shows all options

**Step 3: Commit**

```bash
git add src/lazyclaude/widgets/marketplace_modal.py
git commit -m "refactor: simplify to universal footer menu"
```

---

## Task 3: Add new action methods

**Files:**
- Modify: `src/lazyclaude/widgets/marketplace_modal.py:418-446`

**Step 1: Remove old action_toggle_plugin method**

Delete entire `action_toggle_plugin()` method (lines 418-432)

**Step 2: Rename action_uninstall_plugin to action_uninstall**

Rename `action_uninstall_plugin` to `action_uninstall` for consistency (optional but cleaner):

```python
def action_uninstall(self) -> None:
    """Uninstall the selected plugin with scope selector."""
    if not self._tree:
        return

    node = self._tree.cursor_node
    if node is None:
        return

    data = node.data
    if isinstance(data, MarketplacePlugin) and self._scope_selector:
        self._scope_selector.show(data, data.scope_status, action="uninstall")
```

**Step 3: Add action_install method**

```python
def action_install_plugin(self) -> None:
    """Install the selected plugin with scope selector."""
    if not self._tree:
        return

    node = self._tree.cursor_node
    if node is None:
        return

    data = node.data
    if isinstance(data, MarketplacePlugin) and self._scope_selector:
        self._scope_selector.show(data, data.scope_status, action="install")
```

**Step 4: Add action_enable method**

```python
def action_enable_plugin(self) -> None:
    """Enable the selected plugin with scope selector."""
    if not self._tree:
        return

    node = self._tree.cursor_node
    if node is None:
        return

    data = node.data
    if isinstance(data, MarketplacePlugin) and self._scope_selector:
        self._scope_selector.show(data, data.scope_status, action="enable")
```

**Step 5: Add action_disable method**

```python
def action_disable_plugin(self) -> None:
    """Disable the selected plugin with scope selector."""
    if not self._tree:
        return

    node = self._tree.cursor_node
    if node is None:
        return

    data = node.data
    if isinstance(data, MarketplacePlugin) and self._scope_selector:
        self._scope_selector.show(data, data.scope_status, action="disable")
```

**Step 6: Test new actions**

Run: `uv run lazyclaude`, press M, select plugin, press I/E/D/U, verify scope selector appears

**Step 7: Commit**

```bash
git add src/lazyclaude/widgets/marketplace_modal.py
git commit -m "refactor: add dedicated I/E/D/U action methods, remove toggle"
```

---

## Task 4: Update scope selector validation logic

**Files:**
- Modify: `src/lazyclaude/widgets/scope_selector.py:143-182`

**Step 1: Replace _select_scope with new validation logic**

Replace entire `_select_scope()` method:

```python
def _select_scope(self, scope: str) -> None:
    """Handle scope selection."""
    if not self._plugin:
        return

    status = self._scope_status.get(scope, "not_installed")
    action = self._action

    # Validate action against current status
    if status == "enabled":
        # Already enabled - can't enable again
        if action == "enable":
            self._show_warning(f"Plugin already enabled in {scope.capitalize()} scope")
            return
        # Can disable enabled plugin
        elif action == "disable":
            pass  # Use the disable action
    elif status == "disabled":
        # Disabled - can enable
        if action == "enable":
            pass  # Use the enable action
        # Can't disable disabled plugin
        elif action == "disable":
            self._show_warning(f"Plugin already disabled in {scope.capitalize()} scope")
            return
    elif status == "not_installed":
        if scope == "user":
            # User scope: can't disable what's not installed
            if action == "disable":
                self._show_warning(f"Plugin not installed in {scope.capitalize()} scope")
                return
            elif action == "install":
                pass  # Install
            elif action == "enable":
                action = "install"  # Enable = install when not installed
        else:
            # Project/Local scopes: allow disable (may override user enable)
            # Allow all actions, CLI will handle validation
            if action == "install":
                pass  # Install
            elif action == "enable":
                action = "install"  # Enable = install
            # disable is always allowed for project/local
            elif action == "disable":
                pass  # Disable
            elif action == "uninstall":
                pass  # Uninstall

    self.hide()
    self.post_message(self.ScopeSelected(self._plugin, scope, action))
```

**Step 2: Test validation scenarios**

Test cases:
1. User scope enabled + E → warning
2. User scope not_installed + D → warning
3. Project scope not_installed + D → allowed
4. Any scope + I → allowed

**Step 3: Commit**

```bash
git add src/lazyclaude/widgets/scope_selector.py
git commit -m "feat: update scope selector validation for I/E/D/U actions"
```

---

## Task 5: Add uninstall to CLI command builder

**Files:**
- Modify: `src/lazyclaude/mixins/marketplace.py:320-337`

**Step 1: Add uninstall case to _build_plugin_command_with_scope**

Add `elif action == "uninstall":` case:

```python
def _build_plugin_command_with_scope(
    self, plugin: MarketplacePlugin, scope: str, action: str
) -> list[str]:
    """Build claude CLI command with scope parameter."""
    plugin_id = plugin.full_plugin_id

    if action == "install":
        cmd = ["claude", "plugin", "install", "-s", scope, plugin_id]
    elif action == "enable":
        cmd = ["claude", "plugin", "enable", "-s", scope, plugin_id]
    elif action == "disable":
        cmd = ["claude", "plugin", "disable", "-s", scope, plugin_id]
    elif action == "uninstall":
        cmd = ["claude", "plugin", "uninstall", "-s", scope, plugin_id]
    else:
        cmd = []

    return cmd
```

**Step 2: Verify command format**

Commands should match Claude CLI syntax:
- `claude plugin install -s user plugin@marketplace`
- `claude plugin uninstall -s project plugin@marketplace`

**Step 3: Commit**

```bash
git add src/lazyclaude/mixins/marketplace.py
git commit -m "feat: add uninstall command to CLI builder"
```

---

## Task 6: Remove deprecated handlers

**Files:**
- Modify: `src/lazyclaude/mixins/marketplace.py:153-173`

**Step 1: Delete deprecated handlers**

Remove these methods (already marked as deprecated):
- `on_marketplace_modal_plugin_toggled()`
- `on_marketplace_modal_plugin_uninstall()`

**Step 2: Verify no references**

Check: `grep -r "plugin_toggled\|plugin_uninstall" src/`

Should return nothing (only scope_selected remains)

**Step 3: Commit**

```bash
git add src/lazyclaude/mixins/marketplace.py
git commit -m "refactor: remove deprecated plugin toggle/uninstall handlers"
```

---

## Task 7: Update CLI error handling for better messages

**Files:**
- Modify: `src/lazyclaude/mixins/marketplace.py:175-186`

**Step 1: Improve error message format**

Update `_on_plugin_command_error()`:

```python
def _on_plugin_command_error(self, error_msg: str) -> None:
    """Handle plugin command error."""
    # Parse CLI error to extract meaningful message
    if "not installed" in error_msg.lower():
        self.notify(f"Plugin not installed in specified scope", severity="error")
    elif "already enabled" in error_msg.lower():
        self.notify(f"Plugin already enabled in specified scope", severity="warning")
    elif "already disabled" in error_msg.lower():
        self.notify(f"Plugin already disabled in specified scope", severity="warning")
    else:
        self.notify(error_msg, severity="error")

    if self._marketplace_modal:
        self._marketplace_modal.refresh_tree()
```

**Step 2: Test error messages**

Test scenarios that trigger CLI errors, verify user-friendly messages

**Step 3: Commit**

```bash
git add src/lazyclaude/mixins/marketplace.py
git commit -m "feat: improve CLI error messages for user clarity"
```

---

## Task 8: Run quality gates

**Files:**
- All modified files

**Step 1: Format code**

Run: `uv run ruff format src/`

**Step 2: Lint code**

Run: `uv run ruff check src/`

**Step 3: Type check**

Run: `uv run mypy src/`

**Step 4: Run tests**

Run: `uv run pytest`

**Step 5: Fix any issues**

Address all format/lint/type/test failures before proceeding

**Step 6: Commit**

```bash
git add -A
git commit -m "chore: pass all quality gates"
```

---

## Task 9: Manual testing checklist

**Files:**
- Application runtime

**Step 1: Test Install (I)**

1. Run: `uv run lazyclaude`
2. Press `M` to open marketplace
3. Select plugin not installed in any scope
4. Press `I`
5. Verify: Scope selector appears with all scopes active
6. Select scope 1/2/3
7. Verify: Plugin installs in selected scope
8. Verify: Success notification shown
9. Verify: Marketplace tree updates

**Step 2: Test Enable (E)**

1. Select plugin installed but disabled
2. Press `E`
3. Verify: Scope selector shows status icons
4. Try selecting enabled scope
5. Verify: Warning "Already enabled in X scope"
6. Select disabled/not_installed scope
7. Verify: Plugin enables in selected scope
8. Verify: Success notification shown

**Step 3: Test Disable (D)**

1. Select plugin enabled in USER scope
2. Press `D`
3. Verify: Scope selector shows status icons
4. Select PROJECT scope (not_installed)
5. Verify: Selector allows this (no warning)
6. Verify: CLI command executes
7. Verify: Success/error message from CLI

**Step 4: Test Uninstall (U)**

1. Select plugin installed in some scope
2. Press `U`
3. Verify: Scope selector shows installation status
4. Try selecting not_installed scope
5. Verify: Warning "Not installed in X scope"
6. Select installed scope
7. Verify: Plugin uninstalls from selected scope
8. Verify: Success notification shown

**Step 5: Test all keys work**

1. Verify: `I` always works (even if installed)
2. Verify: `E` always works (even if disabled)
3. Verify: `D` always works (even if not_installed in project/local)
4. Verify: `U` always works (if installed somewhere)
5. Verify: `p` preview works
6. Verify: `e` edit folder works
7. Verify: `o` open source works
8. Verify: `u` update works
9. Verify: `Esc` closes marketplace

**Step 6: Test edge cases**

1. Enable in same scope twice → Second attempt shows warning
2. Disable in same scope twice → Second attempt shows warning
3. Install in multiple scopes sequentially → All work
4. Enable in all three scopes → All work
5. Disable in project when user enabled → Works (CLI handles)

**Step 7: Document any issues**

Create list of bugs/edge cases found during testing

---

## Task 10: Final verification and cleanup

**Files:**
- Documentation, code comments

**Step 1: Update CLAUDE.md if needed**

Check if `docs/constitution.md` or CLAUDE.md references need updates

**Step 2: Verify no TODO comments remain**

Run: `grep -r "TODO" src/lazyclaude/widgets/scope_selector.py src/lazyclaude/mixins/marketplace.py`

Remove or address TODOs

**Step 3: Check for dead code**

Run: `grep -r "toggle_plugin\|action_toggled\|action_uninstall" src/`

Ensure no orphaned references

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete marketplace scope controls redesign

- Replace toggle action with dedicated I/E/D/U actions
- Universal menu always shows all options
- Scope selector validates actions per scope
- Aligns with Claude CLI command model
- Removes legacy toggle code

All quality gates pass. Manual testing complete.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Testing Notes

### Unit Tests Needed

If adding tests, create:
- `tests/unit/widgets/test_scope_selector.py` - Test validation logic
- `tests/unit/mixins/test_marketplace.py` - Test CLI command building

### Integration Tests

Use existing:
- `tests/integration/marketplace/` - Add scenarios for I/E/D/U actions

### Manual Test Focus

Focus on user experience:
- Clear scope selector icons
- Helpful warning messages
- No app crashes
- CLI errors surfaced clearly

---

## Success Criteria

✅ All four actions (I/E/D/U) work correctly
✅ Scope selector appears for all actions
✅ Validation prevents invalid operations with clear warnings
✅ PROJECT/LOCAL disable allowed even when not_installed
✅ No regressions in existing functionality (preview, edit, open, update)
✅ All quality gates pass (format, lint, type, tests)
✅ Manual testing confirms expected behavior

---

## Dependencies

**Required Skills:**
- @superpowers:executing-plans (for task-by-task execution)

**Related Documentation:**
- `docs/constitution.md` - Keyboard-first principles
- `CLAUDE.md` - Project architecture
- Marketplace modal code: `src/lazyclaude/widgets/marketplace_modal.py`
- Scope selector code: `src/lazyclaude/widgets/scope_selector.py`
