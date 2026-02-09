"""
MCP Hub GUI - A CustomTkinter wrapper for MCP Hub.
Provides a desktop interface to manage MCP servers, view tools, and monitor logs.
"""

import sys
import os
import json
import subprocess
import threading
import time
import platform
import urllib.request
import urllib.error
from datetime import datetime

import customtkinter as ctk

from hub_client import MCPHubClient
from servers_tab import ServersTab
from logs_tab import LogsTab

# ── Appearance ───────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Constants ────────────────────────────────────────────────────────────────
DEFAULT_PORT = 3000
CONFIG_FILENAME = "mcp-servers.json"


def find_project_root():
    """Walk up from this file to find the project root (where package.json lives)."""
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isfile(os.path.join(d, "package.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.dirname(os.path.abspath(__file__))


PROJECT_ROOT = find_project_root()


class MCPHubApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("MCP Hub Manager")
        self.geometry("960x680")
        self.minsize(800, 560)

        self.hub_process = None
        self.hub_running = False
        self.port = DEFAULT_PORT
        self.config_path = os.path.join(PROJECT_ROOT, CONFIG_FILENAME)
        self.client = MCPHubClient(port=self.port)

        self._build_ui()
        self._poll_health()

    # ── UI construction ──────────────────────────────────────────────────

    def _build_ui(self):
        # Top toolbar
        toolbar = ctk.CTkFrame(self, height=48, corner_radius=0)
        toolbar.pack(fill="x", padx=0, pady=(0, 4))
        toolbar.pack_propagate(False)

        self.start_btn = ctk.CTkButton(
            toolbar, text="Start Hub", width=120, command=self._toggle_hub
        )
        self.start_btn.pack(side="left", padx=(12, 6), pady=8)

        self.status_label = ctk.CTkLabel(
            toolbar, text="Stopped", text_color="gray"
        )
        self.status_label.pack(side="left", padx=6)

        config_btn = ctk.CTkButton(
            toolbar,
            text="Open Config",
            width=120,
            fg_color="transparent",
            border_width=1,
            command=self._open_config,
        )
        config_btn.pack(side="right", padx=(6, 12), pady=8)

        port_label = ctk.CTkLabel(toolbar, text="Port:")
        port_label.pack(side="right", padx=(6, 2))

        self.port_entry = ctk.CTkEntry(toolbar, width=70, placeholder_text="3000")
        self.port_entry.insert(0, str(self.port))
        self.port_entry.pack(side="right", padx=(0, 6))

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.tabview.add("Servers")
        self.tabview.add("Logs")

        self.servers_tab = ServersTab(self.tabview.tab("Servers"), self.client)
        self.servers_tab.pack(fill="both", expand=True)

        self.logs_tab = LogsTab(self.tabview.tab("Logs"), self.client, PROJECT_ROOT)
        self.logs_tab.pack(fill="both", expand=True)

    # ── Hub lifecycle ────────────────────────────────────────────────────

    def _read_port(self):
        """Read port from entry, fallback to default."""
        try:
            val = int(self.port_entry.get().strip())
            if 1 <= val <= 65535:
                return val
        except ValueError:
            pass
        return DEFAULT_PORT

    def _toggle_hub(self):
        if self.hub_running:
            self._stop_hub()
        else:
            self._start_hub()

    def _start_hub(self):
        self.port = self._read_port()
        self.client.port = self.port

        self.status_label.configure(text="Starting...", text_color="orange")
        self.start_btn.configure(state="disabled")
        self.logs_tab.append_log("INFO", f"Starting MCP Hub on port {self.port}...")

        def run():
            try:
                node_cmd = "node"
                cli_path = os.path.join(PROJECT_ROOT, "src", "utils", "cli.js")
                cmd = [
                    node_cmd,
                    cli_path,
                    "--port",
                    str(self.port),
                    "--config",
                    self.config_path,
                    "--watch",
                ]
                self.hub_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=PROJECT_ROOT,
                    creationflags=subprocess.CREATE_NO_WINDOW
                    if platform.system() == "Windows"
                    else 0,
                )
                self.hub_running = True
                self.after(0, lambda: self.start_btn.configure(state="normal", text="Stop Hub"))
                self.after(0, lambda: self.status_label.configure(text="Running", text_color="#2ecc71"))
                self.after(0, lambda: self.logs_tab.append_log("INFO", "Hub process started"))

                # Stream stdout to log tab
                for line in iter(self.hub_process.stdout.readline, b""):
                    text = line.decode("utf-8", errors="replace").rstrip()
                    if text:
                        self.after(0, lambda t=text: self.logs_tab.append_log("HUB", t))

                # Process exited
                self.hub_process.wait()
                self.hub_running = False
                self.after(0, lambda: self.start_btn.configure(state="normal", text="Start Hub"))
                self.after(0, lambda: self.status_label.configure(text="Stopped", text_color="gray"))
                self.after(0, lambda: self.logs_tab.append_log("INFO", "Hub process exited"))
            except Exception as e:
                self.hub_running = False
                self.after(0, lambda: self.start_btn.configure(state="normal", text="Start Hub"))
                self.after(0, lambda: self.status_label.configure(text="Error", text_color="red"))
                self.after(0, lambda: self.logs_tab.append_log("ERROR", str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _stop_hub(self):
        self.logs_tab.append_log("INFO", "Stopping MCP Hub...")
        if self.hub_process:
            try:
                self.hub_process.terminate()
                self.hub_process.wait(timeout=5)
            except Exception:
                self.hub_process.kill()
            self.hub_process = None
        self.hub_running = False
        self.start_btn.configure(text="Start Hub")
        self.status_label.configure(text="Stopped", text_color="gray")

    # ── Config ───────────────────────────────────────────────────────────

    def _open_config(self):
        """Open the config JSON in the system default editor."""
        path = self.config_path
        if not os.path.isfile(path):
            self.logs_tab.append_log("WARN", f"Config file not found: {path}")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.logs_tab.append_log("ERROR", f"Could not open config: {e}")

    # ── Polling ──────────────────────────────────────────────────────────

    def _poll_health(self):
        """Poll the hub /api/health endpoint to refresh the servers tab."""
        if self.hub_running:
            def fetch():
                try:
                    data = self.client.get_health()
                    if data:
                        self.after(0, lambda: self.servers_tab.refresh(data.get("servers", [])))
                except Exception:
                    pass
            threading.Thread(target=fetch, daemon=True).start()
        self.after(3000, self._poll_health)

    # ── Cleanup ──────────────────────────────────────────────────────────

    def destroy(self):
        if self.hub_process:
            try:
                self.hub_process.terminate()
                self.hub_process.wait(timeout=3)
            except Exception:
                try:
                    self.hub_process.kill()
                except Exception:
                    pass
        super().destroy()


if __name__ == "__main__":
    app = MCPHubApp()
    app.mainloop()
