"""Marketplace mixin for LazyClaude application."""

import json
import logging
import os
import shlex
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from textual import work
from textual.containers import Container

from lazyclaude.models.customization import (
    ConfigLevel,
    Customization,
    CustomizationType,
    PluginInfo,
)
from lazyclaude.models.marketplace import MarketplacePlugin
from lazyclaude.models.view_mode import ViewMode
from lazyclaude.services.opener import open_github_source, open_in_file_explorer
from lazyclaude.widgets.marketplace_confirm import MarketplaceConfirm
from lazyclaude.widgets.marketplace_source_input import MarketplaceSourceInput
from lazyclaude.widgets.marketplace_view import MarketplaceView

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from lazyclaude.models.settings import AppSettings
    from lazyclaude.services.discovery import ConfigDiscoveryService
    from lazyclaude.services.marketplace_loader import MarketplaceLoader
    from lazyclaude.services.plugin_loader import PluginLoader
    from lazyclaude.widgets.app_footer import AppFooter
    from lazyclaude.widgets.combined_panel import CombinedPanel
    from lazyclaude.widgets.detail_pane import MainPane
    from lazyclaude.widgets.filter_input import FilterInput
    from lazyclaude.widgets.status_panel import StatusPanel
    from lazyclaude.widgets.type_panel import TypePanel


class MarketplaceMixin:
    """Mixin providing marketplace browser functionality."""

    _marketplace_view: MarketplaceView | None
    _marketplace_confirm: MarketplaceConfirm | None
    _marketplace_source_input: MarketplaceSourceInput | None
    _marketplace_loader: "MarketplaceLoader | None"
    _plugin_loader: "PluginLoader | None"
    _plugin_preview_mode: bool
    _previewing_plugin: MarketplacePlugin | None
    _plugin_customizations: list[Customization]
    _search_query: str
    _discovery_service: "ConfigDiscoveryService"
    _main_pane: "MainPane | None"
    _combined_panel: "CombinedPanel | None"
    _status_panel: "StatusPanel | None"
    _filter_input: "FilterInput | None"
    _app_footer: "AppFooter | None"
    _panel_before_selector: "TypePanel | None"
    _combined_before_selector: bool
    _settings: "AppSettings"

    def on_marketplace_view_footer_changed(
        self,
        message: MarketplaceView.FooterChanged,  # noqa: ARG002
    ) -> None:
        """Handle footer change from marketplace view."""
        self._update_footer()  # type: ignore[attr-defined]

    def action_toggle_marketplace(self) -> None:
        """Toggle the marketplace browser modal."""
        if self._marketplace_modal:
            if self._marketplace_modal.is_visible:
                self._marketplace_modal.hide()
                self._restore_focus_after_selector()  # type: ignore[attr-defined]
            else:
                self._panel_before_selector = self._get_focused_panel()  # type: ignore[attr-defined]
                self._combined_before_selector = (
                    self._combined_panel.has_focus if self._combined_panel else False
                )
                self._marketplace_modal.show(
                    auto_collapse=self._settings.marketplace_auto_collapse
                )
            self._update_footer_actions()  # type: ignore[attr-defined]

    def _enter_plugin_preview(self, plugin: MarketplacePlugin) -> None:
        """Enter plugin preview mode - show plugin's customizations in panels."""
        if not self._marketplace_loader:
            self.notify("Marketplace loader not available", severity="error")  # type: ignore[attr-defined]
            return

        plugin_dir = self._marketplace_loader.get_plugin_source_dir(plugin)
        if not plugin_dir or not plugin_dir.exists():
            # If source is a URL, open in browser instead of showing error
            if plugin.source.startswith(("http://", "https://")):
                import webbrowser

                webbrowser.open(plugin.source)
                self.notify(  # type: ignore[attr-defined]
                    f"Opening {plugin.name} source in browser",
                    severity="information",
                )
                return

            self.notify("Plugin source not found", severity="warning")  # type: ignore[attr-defined]
            return

        plugin_info = PluginInfo(
            plugin_id=plugin.full_plugin_id,
            short_name=plugin.name,
            version="preview",
            install_path=plugin_dir,
            is_enabled=plugin.is_enabled,
        )
        self._plugin_customizations = self._discovery_service.discover_from_directory(
            plugin_dir, plugin_info, marketplace_plugin=plugin
        )
        self._previewing_plugin = plugin
        self._plugin_preview_mode = True

        self._switch_mode(ViewMode.NORMAL)  # type: ignore[attr-defined]

        # Focus first panel to activate panel bindings (0-7, Tab)
        if self._panels:  # type: ignore[attr-defined]
            self._panels[0].focus()  # type: ignore[attr-defined]

        self._update_panels()  # type: ignore[attr-defined]
        self._update_subtitle()  # type: ignore[attr-defined]
        self._update_footer_actions()  # type: ignore[attr-defined]
        self.refresh_bindings()  # type: ignore[attr-defined]
        if self._status_panel:
            if plugin.is_installed:
                resolved_version = plugin_dir.name
            else:
                resolved_version = plugin.extra_metadata.get("version", "dev")
            self._status_panel.config_path = (
                f"Preview: {plugin.name} [dim]({resolved_version})[/]"
            )
            self._status_panel.filter_level = "Plugin"

        if self._main_pane:
            readme_path = plugin_dir / "README.md"
            if readme_path.is_file():
                try:
                    readme_content = readme_path.read_text(encoding="utf-8")
                    readme_customization = Customization(
                        name="README.md",
                        type=CustomizationType.MEMORY_FILE,
                        level=ConfigLevel.PLUGIN,
                        path=readme_path,
                        description=f"Plugin documentation for {plugin.name}",
                        content=readme_content,
                        plugin_info=plugin_info,
                    )
                    self._main_pane.customization = readme_customization
                except OSError:
                    self._main_pane.customization = None
            else:
                self._main_pane.customization = None

        if self._combined_panel:
            self._combined_panel.switch_to_type(CustomizationType.MCP)

    def _exit_plugin_preview(self) -> None:
        """Exit plugin preview mode and return to marketplace."""
        self._plugin_preview_mode = False
        self._previewing_plugin = None
        self._plugin_customizations = []
        self._search_query = ""
        if self._filter_input:
            self._filter_input.clear()
        self._update_panels()  # type: ignore[attr-defined]
        self._update_subtitle()  # type: ignore[attr-defined]
        self._update_status_panel()  # type: ignore[attr-defined]
        self._update_footer_actions()  # type: ignore[attr-defined]
        self.refresh_bindings()  # type: ignore[attr-defined]

        if self._main_pane:
            self._main_pane.customization = None

        # Switch to MARKETPLACE view and preserve marketplace state (filters, cursor position)
        self._view_mode = ViewMode.MARKETPLACE  # type: ignore[attr-defined]
        normal_view = self.query_one("#normal-view", Container)  # type: ignore[attr-defined]
        normal_view.remove_class("visible")  # type: ignore[attr-defined]
        if self._marketplace_view:
            self._marketplace_view.add_class("visible")
            self._marketplace_view.show(preserve_state=True)

    def action_exit_preview(self) -> None:
        """Exit plugin preview mode (visible binding for Esc in preview)."""
        self._exit_plugin_preview()

    def on_marketplace_view_plugin_preview(
        self, message: MarketplaceView.PluginPreview
    ) -> None:
        """Handle plugin preview request from marketplace modal."""
        self._enter_plugin_preview(message.plugin)

    def _execute_single_command(self, cmd: list[str], success_msg: str) -> None:
        """Execute a single plugin command (must be called from worker thread)."""
        cmd_str = shlex.join(cmd)
        project_root = getattr(self._discovery_service, "project_root", None)
        logger.debug(f"[PLUGIN CMD] {cmd_str} (cwd={project_root})")

        try:
            result = subprocess.run(
                cmd_str,
                capture_output=True,
                text=True,
                check=True,
                shell=True,
                cwd=project_root,
            )
            logger.debug(f"[PLUGIN CMD] -> OK: {result.stdout.strip()}")
            self.call_from_thread(self._on_plugin_command_success, success_msg)  # type: ignore[attr-defined]
        except subprocess.CalledProcessError as e:
            logger.debug(f"[PLUGIN CMD] -> FAILED: {e.stderr}")
            error_msg = f"Failed: {e.stderr or str(e)}"
            self.call_from_thread(self._on_plugin_command_error, error_msg)  # type: ignore[attr-defined]
        except FileNotFoundError:
            logger.debug("[PLUGIN CMD] -> FAILED: Claude CLI not found")
            self.call_from_thread(self._on_plugin_command_error, "Claude CLI not found")  # type: ignore[attr-defined]
        except Exception as e:
            logger.debug(f"[PLUGIN CMD] -> FAILED: {type(e).__name__}: {e}")
            error_msg = f"Error: {str(e)}"
            self.call_from_thread(self._on_plugin_command_error, error_msg)  # type: ignore[attr-defined]

    @work(thread=True)
    def _run_plugin_command(self, cmd: list[str], success_msg: str) -> None:
        """Run a plugin command in a background worker."""
        self._execute_single_command(cmd, success_msg)

    @work(thread=True)
    def _run_plugin_commands_sequential(
        self, commands: list[tuple[list[str], str]]
    ) -> None:
        """Run multiple plugin commands sequentially in a background worker."""
        for cmd, success_msg in commands:
            self._execute_single_command(cmd, success_msg)

    @work(thread=True)
    def _run_enable_disable_with_fallback(
        self,
        plugin_id: str,
        scope: str,
        action: str,
        success_msg: str,
    ) -> None:
        """Try CLI for enable/disable, fall back to JSON editing if CLI fails.

        This handles the case where a plugin is installed at user scope
        but we want to disable it at project scope via settings override.
        """
        cmd = ["claude", "plugin", action, "-s", scope, plugin_id]
        cmd_str = shlex.join(cmd)
        project_root = getattr(self._discovery_service, "project_root", None)
        logger.debug(f"[PLUGIN CMD] {cmd_str} (cwd={project_root})")

        try:
            result = subprocess.run(
                cmd_str,
                capture_output=True,
                text=True,
                check=True,
                shell=True,
                cwd=project_root,
            )
            logger.debug(f"[PLUGIN CMD] -> OK: {result.stdout.strip()}")
            self.call_from_thread(self._on_plugin_command_success, success_msg)  # type: ignore[attr-defined]
        except subprocess.CalledProcessError as e:
            error_text = e.stderr or str(e)
            logger.debug(f"[PLUGIN CMD] -> FAILED: {error_text}")

            # CLI failed - always try JSON fallback for enable/disable
            # This handles scope mismatches without relying on specific error messages
            logger.debug("[PLUGIN CMD] CLI failed, trying JSON fallback")
            enabled = action == "enable"
            success = self._edit_enabled_plugins_json(plugin_id, scope, enabled)
            if success:
                self.call_from_thread(  # type: ignore[attr-defined]
                    self._on_plugin_command_success,
                    f"{success_msg} (via settings)",
                )
            else:
                self.call_from_thread(  # type: ignore[attr-defined]
                    self._on_plugin_command_error,
                    f"CLI failed: {error_text}; JSON fallback also failed",
                )
        except FileNotFoundError:
            logger.debug("[PLUGIN CMD] -> FAILED: Claude CLI not found")
            self.call_from_thread(self._on_plugin_command_error, "Claude CLI not found")  # type: ignore[attr-defined]
        except Exception as e:
            logger.debug(f"[PLUGIN CMD] -> FAILED: {type(e).__name__}: {e}")
            self.call_from_thread(self._on_plugin_command_error, f"Error: {str(e)}")  # type: ignore[attr-defined]

    def _edit_enabled_plugins_json(
        self, plugin_id: str, scope: str, enabled: bool
    ) -> bool:
        """Edit enabledPlugins in the appropriate settings.json file.

        Args:
            plugin_id: Plugin identifier
            scope: "user", "project", or "local"
            enabled: True to enable, False to disable

        Returns:
            True if successful, False otherwise
        """
        # Determine which settings file to edit
        if scope == "user":
            settings_path = Path.home() / ".claude" / "settings.json"
        elif scope == "project":
            project_root = getattr(self._discovery_service, "project_root", None)
            if not project_root:
                logger.debug("[JSON EDIT] No project root found")
                return False
            settings_path = project_root / ".claude" / "settings.json"
        else:  # local
            project_root = getattr(self._discovery_service, "project_root", None)
            if not project_root:
                logger.debug("[JSON EDIT] No project root found")
                return False
            settings_path = project_root / ".claude" / "settings.local.json"

        logger.debug(f"[JSON EDIT] Editing {settings_path}")

        try:
            # Ensure directory exists
            settings_path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing settings or create empty
            if settings_path.is_file():
                data = json.loads(settings_path.read_text(encoding="utf-8"))
            else:
                data = {}

            # Ensure enabledPlugins exists
            if "enabledPlugins" not in data:
                data["enabledPlugins"] = {}

            # Set the enabled state
            data["enabledPlugins"][plugin_id] = enabled

            # Write back
            settings_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            logger.debug(f"[JSON EDIT] Set {plugin_id}={enabled} in {settings_path}")
            return True

        except (OSError, json.JSONDecodeError) as e:
            logger.debug(f"[JSON EDIT] Failed: {e}")
            return False

    def _on_plugin_command_success(self, success_msg: str) -> None:
        """Handle successful plugin command completion."""
        self.notify(success_msg, severity="information")  # type: ignore[attr-defined]
        if self._marketplace_view:
            self._marketplace_view.refresh_tree()
        self.action_refresh()  # type: ignore[attr-defined]

    def _on_plugin_command_error(self, error_msg: str) -> None:
        """Handle plugin command error."""
        # Parse CLI error to extract meaningful message
        if "not installed" in error_msg.lower():
            self.notify("Plugin not installed in specified scope", severity="error")  # type: ignore[attr-defined]
        elif "already enabled" in error_msg.lower():
            self.notify("Plugin already enabled in specified scope", severity="warning")  # type: ignore[attr-defined]
        elif "already disabled" in error_msg.lower():
            self.notify(  # type: ignore[attr-defined]
                "Plugin already disabled in specified scope", severity="warning"
            )
        else:
            self.notify(error_msg, severity="error")  # type: ignore[attr-defined]

        if self._marketplace_view:
            self._marketplace_view.refresh_tree()

    def on_marketplace_view_open_plugin_folder(
        self, message: MarketplaceView.OpenPluginFolder
    ) -> None:
        """Handle opening plugin folder from marketplace modal."""
        plugin = message.plugin

        if not plugin.install_path or not plugin.install_path.exists():
            self.notify("Plugin folder not found", severity="error")  # type: ignore[attr-defined]
            return

        editor = os.environ.get("EDITOR", "vi")
        cmd_str = shlex.join([editor, str(plugin.install_path)])
        subprocess.Popen(cmd_str, shell=True)

    def on_marketplace_view_open_marketplace_folder(
        self, message: MarketplaceView.OpenMarketplaceFolder
    ) -> None:
        """Handle opening marketplace install directory."""
        marketplace = message.marketplace
        install_path = marketplace.entry.install_location

        if not install_path or not install_path.exists():
            self.notify("Marketplace folder not found", severity="error")  # type: ignore[attr-defined]
            return

        editor = os.environ.get("EDITOR", "vi")
        cmd_str = shlex.join([editor, str(install_path)])
        subprocess.Popen(cmd_str, shell=True)

    def on_marketplace_view_open_plugin_source(
        self, message: MarketplaceView.OpenPluginSource
    ) -> None:
        """Handle opening plugin source location from marketplace modal."""
        plugin = message.plugin
        marketplace = message.marketplace
        source_type = marketplace.entry.source.source_type

        if source_type == "directory":
            if plugin.is_installed and plugin.install_path:
                path = plugin.install_path
            else:
                # Skip if source is a full URL (not a local path)
                if plugin.source.startswith(("http://", "https://")):
                    self.notify(  # type: ignore[attr-defined]
                        f"Cannot open file explorer for remote URL: {plugin.source}",
                        severity="warning",
                    )
                    return
                path = (marketplace.entry.install_location / plugin.source).resolve()

            success, error = open_in_file_explorer(path)
            if not success:
                self.notify(error or "Failed to open", severity="warning")  # type: ignore[attr-defined]
        elif source_type == "github":
            repo = marketplace.entry.source.repo
            if repo:
                open_github_source(repo, plugin.source)
            else:
                self.notify("GitHub repository not configured", severity="warning")  # type: ignore[attr-defined]
        else:
            self.notify(f"Unknown source type: {source_type}", severity="warning")  # type: ignore[attr-defined]

    def on_marketplace_view_open_marketplace_source(
        self, message: MarketplaceView.OpenMarketplaceSource
    ) -> None:
        """Handle opening marketplace source location."""
        marketplace = message.marketplace
        source_type = marketplace.entry.source.source_type

        if source_type == "directory":
            success, error = open_in_file_explorer(marketplace.entry.install_location)
            if not success:
                self.notify(error or "Failed to open", severity="warning")  # type: ignore[attr-defined]
        elif source_type == "github":
            repo = marketplace.entry.source.repo
            if repo:
                open_github_source(repo)
            else:
                self.notify("GitHub repository not configured", severity="warning")  # type: ignore[attr-defined]
        else:
            self.notify(f"Unknown source type: {source_type}", severity="warning")  # type: ignore[attr-defined]

    def on_marketplace_view_marketplace_update(
        self, message: MarketplaceView.MarketplaceUpdate
    ) -> None:
        """Handle marketplace update request."""
        marketplace = message.marketplace
        self.notify(f"Updating {marketplace.entry.name}...", severity="information")  # type: ignore[attr-defined]
        cmd = ["claude", "plugin", "marketplace", "update", marketplace.entry.name]
        self._run_plugin_command(cmd, f"Updated {marketplace.entry.name}")

    def on_marketplace_view_marketplace_add(
        self, message: MarketplaceView.MarketplaceAdd
    ) -> None:
        """Handle marketplace add request."""
        source = message.source
        self.notify(f"Adding marketplace from {source}...", severity="information")  # type: ignore[attr-defined]
        cmd = ["claude", "plugin", "marketplace", "add", source]
        self._run_plugin_command(cmd, f"Added marketplace from {source}")

    def on_marketplace_view_plugin_update(
        self, message: MarketplaceView.PluginUpdate
    ) -> None:
        """Handle plugin update request - update in all installed scopes."""
        plugin = message.plugin

        # Find installed scopes (enabled or disabled means installed)
        installed_scopes = [
            scope
            for scope, status in plugin.scope_status.items()
            if status in ("enabled", "disabled")
        ]

        if not installed_scopes:
            self.notify("Plugin not installed in any scope", severity="warning")  # type: ignore[attr-defined]
            return

        scope_names = ", ".join(installed_scopes)
        self.notify(  # type: ignore[attr-defined]
            f"Updating {plugin.name} in {len(installed_scopes)} scope(s): {scope_names}",
            severity="information",
        )

        # Build commands for each installed scope
        commands = [
            (
                ["claude", "plugin", "update", "-s", scope, plugin.full_plugin_id],
                f"Updated {plugin.name} ({scope})",
            )
            for scope in installed_scopes
        ]

        self._run_plugin_commands_sequential(commands)

    def on_marketplace_view_scope_selected(
        self, message: MarketplaceView.ScopeSelected
    ) -> None:
        """Handle scope selection for plugin action."""
        plugin = message.plugin
        scope = message.scope
        action = message.action

        try:
            action_msg = f"{action.capitalize()}ing {plugin.name}..."
            success_msg = f"{action.capitalize()}ed {plugin.name}"
            self.notify(action_msg, severity="information", timeout=2.0)  # type: ignore[attr-defined]

            # Use fallback method for enable/disable (handles scope overrides)
            if action in ("enable", "disable"):
                self._run_enable_disable_with_fallback(
                    plugin.full_plugin_id, scope, action, success_msg
                )
            else:
                cmd = self._build_plugin_command_with_scope(plugin, scope, action)
                self._run_plugin_command(cmd, success_msg)
        except Exception as e:
            logger.debug(f"[MARKETPLACE] ERROR: {type(e).__name__}: {e}")
            self.notify(f"Error preparing plugin command: {e}", severity="error")  # type: ignore[attr-defined]

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

    def on_marketplace_view_marketplace_remove(
        self, message: MarketplaceView.MarketplaceRemove
    ) -> None:
        """Handle marketplace remove request - show confirmation."""
        if self._marketplace_confirm:
            self._marketplace_confirm.show(message.marketplace)

    def on_marketplace_view_marketplace_add_request(
        self,
        message: MarketplaceView.MarketplaceAddRequest,  # noqa: ARG002
    ) -> None:
        """Handle request to add marketplace - show source input."""
        if self._marketplace_source_input:
            self._marketplace_source_input.show()

    def on_marketplace_confirm_remove_confirmed(
        self, message: MarketplaceConfirm.RemoveConfirmed
    ) -> None:
        """Handle confirmed marketplace removal."""
        marketplace = message.marketplace
        self.notify(f"Removing {marketplace.entry.name}...", severity="information")  # type: ignore[attr-defined]
        cmd = ["claude", "plugin", "marketplace", "remove", marketplace.entry.name]
        self._run_plugin_command(cmd, f"Removed {marketplace.entry.name}")
        if self._marketplace_view:
            self._marketplace_view.call_after_refresh(  # type: ignore[attr-defined]
                self._marketplace_view.focus_tree
            )

    def on_marketplace_confirm_remove_cancelled(
        self,
        message: MarketplaceConfirm.RemoveCancelled,  # noqa: ARG002
    ) -> None:
        """Handle marketplace removal cancellation."""
        if self._marketplace_view:
            self._marketplace_view.call_after_refresh(  # type: ignore[attr-defined]
                self._marketplace_view.focus_tree
            )

    def on_marketplace_source_input_source_submitted(
        self, message: MarketplaceSourceInput.SourceSubmitted
    ) -> None:
        """Handle marketplace source submission."""
        source = message.source
        self.notify(f"Adding marketplace from {source}...", severity="information")  # type: ignore[attr-defined]
        cmd = ["claude", "plugin", "marketplace", "add", source]
        self._run_plugin_command(cmd, "Added marketplace")
        if self._marketplace_view:
            self._marketplace_view.focus_tree()

    def on_marketplace_source_input_source_cancelled(
        self,
        message: MarketplaceSourceInput.SourceCancelled,  # noqa: ARG002
    ) -> None:
        """Handle marketplace source input cancellation."""
        if self._marketplace_view:
            self._marketplace_view.focus_tree()
