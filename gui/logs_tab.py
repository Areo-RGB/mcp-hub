"""
Logs tab — scrollable log viewer with level filtering and debug toggle.
"""

import os
import threading
from datetime import datetime

import customtkinter as ctk


class LogsTab(ctk.CTkFrame):
    """Tab that shows hub logs with debug filtering options."""

    LOG_COLORS = {
        "INFO": "#2ecc71",
        "WARN": "#f39c12",
        "ERROR": "#e74c3c",
        "DEBUG": "#3498db",
        "HUB": "#9b59b6",
    }

    def __init__(self, master, client, project_root, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.client = client
        self.project_root = project_root
        self.show_debug = False
        self.log_entries = []  # list of (level, text)

        self._build_ui()

    def _build_ui(self):
        # ── Toolbar ──────────────────────────────────────────────────────
        toolbar = ctk.CTkFrame(self, height=36, fg_color="transparent")
        toolbar.pack(fill="x", padx=4, pady=(4, 2))
        toolbar.pack_propagate(False)

        title = ctk.CTkLabel(
            toolbar, text="Hub Logs", font=ctk.CTkFont(size=13, weight="bold")
        )
        title.pack(side="left", padx=4)

        # Debug toggle
        self.debug_var = ctk.BooleanVar(value=False)
        debug_chk = ctk.CTkCheckBox(
            toolbar,
            text="Show DEBUG",
            variable=self.debug_var,
            command=self._on_debug_toggle,
            width=24,
            height=24,
        )
        debug_chk.pack(side="left", padx=(16, 4))

        # Level filter
        self.level_filter = ctk.CTkOptionMenu(
            toolbar,
            values=["ALL", "INFO", "WARN", "ERROR", "DEBUG", "HUB"],
            width=100,
            command=self._on_filter_change,
        )
        self.level_filter.set("ALL")
        self.level_filter.pack(side="left", padx=4)

        # Clear button
        clear_btn = ctk.CTkButton(
            toolbar,
            text="Clear",
            width=70,
            fg_color="transparent",
            border_width=1,
            command=self._clear_logs,
        )
        clear_btn.pack(side="right", padx=4)

        # Open log file button
        open_log_btn = ctk.CTkButton(
            toolbar,
            text="Open Log File",
            width=100,
            fg_color="transparent",
            border_width=1,
            command=self._open_log_file,
        )
        open_log_btn.pack(side="right", padx=4)

        # ── Log text area ────────────────────────────────────────────────
        self.log_text = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled",
            wrap="word",
        )
        self.log_text.pack(fill="both", expand=True, padx=4, pady=(0, 4))

    # ── Public API ───────────────────────────────────────────────────────

    def append_log(self, level, message):
        """Add a log entry. Called from the main thread."""
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_entries.append((level, message))

        # Apply current filter
        if not self._passes_filter(level):
            return

        self._write_line(ts, level, message)

    # ── Internals ────────────────────────────────────────────────────────

    def _passes_filter(self, level):
        if level == "DEBUG" and not self.show_debug:
            return False
        selected = self.level_filter.get()
        if selected != "ALL" and level != selected:
            return False
        return True

    def _write_line(self, ts, level, message):
        color = self.LOG_COLORS.get(level, "white")
        line = f"[{ts}] [{level}] {message}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def _redraw(self):
        """Rewrite all visible log entries applying current filters."""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        for level, msg in self.log_entries:
            if self._passes_filter(level):
                ts = datetime.now().strftime("%H:%M:%S")
                self._write_line(ts, level, msg)

    def _on_debug_toggle(self):
        self.show_debug = self.debug_var.get()
        self._redraw()

    def _on_filter_change(self, value):
        self._redraw()

    def _clear_logs(self):
        self.log_entries.clear()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _open_log_file(self):
        """Try to open the MCP Hub log file."""
        import platform as plat
        import subprocess

        # XDG state path or fallback
        xdg = os.environ.get("XDG_STATE_HOME", os.path.join(os.path.expanduser("~"), ".local", "state"))
        log_path = os.path.join(xdg, "mcp-hub", "logs", "mcp-hub.log")
        if not os.path.isfile(log_path):
            log_path = os.path.join(os.path.expanduser("~"), ".mcp-hub", "logs", "mcp-hub.log")
        if not os.path.isfile(log_path):
            self.append_log("WARN", f"Log file not found at expected paths")
            return
        try:
            if plat.system() == "Windows":
                os.startfile(log_path)
            elif plat.system() == "Darwin":
                subprocess.Popen(["open", log_path])
            else:
                subprocess.Popen(["xdg-open", log_path])
        except Exception as e:
            self.append_log("ERROR", f"Could not open log file: {e}")
