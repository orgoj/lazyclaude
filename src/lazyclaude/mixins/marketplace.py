"""Marketplace mixin for LazyClaude application."""

import logging
import os
import shlex
import subprocess
from typing import TYPE_CHECKING

from textual import work

from lazyclaude.models.customization import (
    ConfigLevel,
    Customization,
    CustomizationType,
    PluginInfo,
)
from lazyclaude.models.marketplace import MarketplacePlugin
from lazyclaude.services.opener import open_github_source, open_in_file_explorer
from lazyclaude.widgets.marketplace_modal import MarketplaceModal

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from lazyclaude.services.discovery import ConfigDiscoveryService
    from lazyclaude.services.marketplace_loader import MarketplaceLoader
    from lazyclaude.services.plugin_loader import PluginLoader
    from lazyclaude.widgets.combined_panel import CombinedPanel
    from lazyclaude.widgets.detail_pane import MainPane
    from lazyclaude.widgets.filter_input import FilterInput
    from lazyclaude.widgets.status_panel import StatusPanel
    from lazyclaude.widgets.type_panel import TypePanel


class MarketplaceMixin:
    """Mixin providing marketplace browser functionality."""

    _marketplace_modal: MarketplaceModal | None
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
    _panel_before_selector: "TypePanel | None"
    _combined_before_selector: bool

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
                self._marketplace_modal.show()

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

        if self._marketplace_modal:
            self._marketplace_modal.hide(preserve_state=True)

        self._update_panels()  # type: ignore[attr-defined]
        self._update_subtitle()  # type: ignore[attr-defined]
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
        self.refresh_bindings()  # type: ignore[attr-defined]

        if self._main_pane:
            self._main_pane.customization = None

        if self._marketplace_modal:
            self._marketplace_modal.show(preserve_state=True)

    def action_exit_preview(self) -> None:
        """Exit plugin preview mode (visible binding for Esc in preview)."""
        self._exit_plugin_preview()

    def on_marketplace_modal_plugin_preview(
        self, message: MarketplaceModal.PluginPreview
    ) -> None:
        """Handle plugin preview request from marketplace modal."""
        self._enter_plugin_preview(message.plugin)

    @work(thread=True)
    def _run_plugin_command(self, cmd: list[str], success_msg: str) -> None:
        """Run a plugin command in a background worker."""
        # Check if debug mode is enabled
        debug_mode = getattr(self, "debug_mode", False)

        if debug_mode:
            logger.debug(
                f"[PLUGIN COMMAND] Starting: cmd={cmd}, success_msg={success_msg}"
            )

        try:
            # Convert command list to properly escaped shell string
            cmd_str = shlex.join(cmd)

            if debug_mode:
                logger.debug(f"[PLUGIN COMMAND] Executing: {cmd_str}")

            result = subprocess.run(
                cmd_str, capture_output=True, text=True, check=True, shell=True
            )

            if debug_mode:
                logger.debug("[PLUGIN COMMAND] SUCCESS")
                logger.debug(f"[PLUGIN COMMAND] Return code: {result.returncode}")
                logger.debug(f"[PLUGIN COMMAND] Stdout: {result.stdout}")
                if result.stderr:
                    logger.debug(f"[PLUGIN COMMAND] Stderr: {result.stderr}")

            self.call_from_thread(self._on_plugin_command_success, success_msg)  # type: ignore[attr-defined]

            if debug_mode:
                logger.debug("[PLUGIN COMMAND] Success callback called")
        except subprocess.CalledProcessError as e:
            if debug_mode:
                logger.debug("[PLUGIN COMMAND] CALLED PROCESS ERROR")
                logger.debug(f"[PLUGIN COMMAND] Return code: {e.returncode}")
                logger.debug(f"[PLUGIN COMMAND] Stdout: {e.stdout}")
                logger.debug(f"[PLUGIN COMMAND] Stderr: {e.stderr}")

            error_msg = f"Failed: {e.stderr or str(e)}"
            self.call_from_thread(self._on_plugin_command_error, error_msg)  # type: ignore[attr-defined]
        except FileNotFoundError:
            if debug_mode:
                logger.debug("[PLUGIN COMMAND] FILE NOT ERROR - Claude CLI not found")

            self.call_from_thread(self._on_plugin_command_error, "Claude CLI not found")  # type: ignore[attr-defined]
        except Exception as e:
            if debug_mode:
                logger.debug(
                    f"[PLUGIN COMMAND] UNEXPECTED ERROR: {type(e).__name__}: {e}"
                )
                import traceback

                logger.debug(f"[PLUGIN COMMAND] Traceback:\n{traceback.format_exc()}")

            error_msg = f"Error: {str(e)}"
            self.call_from_thread(self._on_plugin_command_error, error_msg)  # type: ignore[attr-defined]

    def _on_plugin_command_success(self, success_msg: str) -> None:
        """Handle successful plugin command completion."""
        self.notify(success_msg, severity="information")  # type: ignore[attr-defined]
        if self._marketplace_modal:
            self._marketplace_modal.refresh_tree()
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

        if self._marketplace_modal:
            self._marketplace_modal.refresh_tree()

    def on_marketplace_modal_open_plugin_folder(
        self, message: MarketplaceModal.OpenPluginFolder
    ) -> None:
        """Handle opening plugin folder from marketplace modal."""
        plugin = message.plugin

        if not plugin.install_path or not plugin.install_path.exists():
            self.notify("Plugin folder not found", severity="warning")  # type: ignore[attr-defined]
            return

        editor = os.environ.get("EDITOR", "vi")
        subprocess.Popen([editor, str(plugin.install_path)], shell=True)

    def on_marketplace_modal_open_plugin_source(
        self, message: MarketplaceModal.OpenPluginSource
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

    def on_marketplace_modal_open_marketplace_source(
        self, message: MarketplaceModal.OpenMarketplaceSource
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

    def on_marketplace_modal_marketplace_update(
        self, message: MarketplaceModal.MarketplaceUpdate
    ) -> None:
        """Handle marketplace update request."""
        marketplace = message.marketplace
        self.notify(f"Updating {marketplace.entry.name}...", severity="information")  # type: ignore[attr-defined]
        cmd = ["claude", "plugin", "marketplace", "update", marketplace.entry.name]
        self._run_plugin_command(cmd, f"Updated {marketplace.entry.name}")

    def on_marketplace_modal_plugin_update(
        self, message: MarketplaceModal.PluginUpdate
    ) -> None:
        """Handle plugin update request."""
        plugin = message.plugin
        self.notify(f"Updating {plugin.name}...", severity="information")  # type: ignore[attr-defined]
        cmd = ["claude", "plugin", "update", plugin.full_plugin_id]
        self._run_plugin_command(cmd, f"Updated {plugin.name}")

    def on_marketplace_modal_modal_closed(
        self,
        message: MarketplaceModal.ModalClosed,  # noqa: ARG002
    ) -> None:
        """Handle marketplace modal close."""
        self._restore_focus_after_selector()  # type: ignore[attr-defined]

    def on_marketplace_modal_scope_selected(
        self, message: MarketplaceModal.ScopeSelected
    ) -> None:
        """Handle scope selection for plugin action."""
        plugin = message.plugin
        scope = message.scope
        action = message.action

        # Debug logging
        debug_mode = getattr(self, "debug_mode", False)
        if debug_mode:
            logger.debug(
                f"[MARKETPLACE] Scope selected: plugin={plugin.full_plugin_id}, scope={scope}, action={action}"
            )

        try:
            # Build command with scope
            cmd = self._build_plugin_command_with_scope(plugin, scope, action)

            if debug_mode:
                logger.debug(f"[MARKETPLACE] Built command: {cmd}")

            # Determine messages
            action_msg = f"{action.capitalize()}ing {plugin.name}..."
            success_msg = f"{action.capitalize()}ed {plugin.name}"

            if debug_mode:
                logger.debug(f"[MARKETPLACE] About to notify: {action_msg}")

            self.notify(action_msg, severity="information", timeout=2.0)  # type: ignore[attr-defined]

            if debug_mode:
                logger.debug("[MARKETPLACE] About to run plugin command")

            self._run_plugin_command(cmd, success_msg)

            if debug_mode:
                logger.debug("[MARKETPLACE] Plugin command started in background")
        except Exception as e:
            if debug_mode:
                logger.debug(
                    f"[MARKETPLACE] ERROR in on_marketplace_modal_scope_selected: {type(e).__name__}: {e}"
                )
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

    def _get_plugin_scope_status(self, plugin: MarketplacePlugin) -> dict[str, str]:
        """Get installation/enabled status for a plugin across all scopes.

        Args:
            plugin: The plugin to check

        Returns:
            Dict mapping scope names to status:
            "enabled", "disabled", or "not_installed"
        """
        if not self._plugin_loader:
            return {
                "user": "not_installed",
                "project": "not_installed",
                "local": "not_installed",
            }

        registry = self._plugin_loader.load_registry()
        plugin_id = plugin.full_plugin_id

        status: dict[str, str] = {}

        # Check each scope
        for scope_type, scope_key in [
            ("user", "user"),
            ("project", "project"),
            ("local", "local"),
        ]:
            # Check if installed in this scope
            installations = registry.installed.get(plugin_id, [])
            installed = any(
                inst.scope == scope_type
                and (
                    scope_type == "user"
                    or self._plugin_loader._matches_current_project(inst.project_path)
                )
                for inst in installations
            )

            if not installed:
                status[scope_key] = "not_installed"
                continue

            # Check enabled status
            if scope_type == "user":
                enabled = registry.user_enabled.get(plugin_id, True)
            elif scope_type == "project":
                enabled = registry.project_enabled.get(plugin_id, True)
            else:  # local
                enabled = registry.local_enabled.get(plugin_id, True)

            status[scope_key] = "enabled" if enabled else "disabled"

        return status
