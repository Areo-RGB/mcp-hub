"""
Servers tab — displays each connected MCP server as a card with a collapsible
list of its exposed tools and an enable / disable toggle.
"""

import threading
import customtkinter as ctk


class ToolsList(ctk.CTkFrame):
    """Collapsible list of tools for a single MCP server card."""

    def __init__(self, master, tools=None, **kwargs):
        super().__init__(master, **kwargs)
        self.tools = tools or []
        self.expanded = False

        self.toggle_btn = ctk.CTkButton(
            self,
            text=f"Tools ({len(self.tools)})  ▸",
            width=160,
            height=26,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            text_color=("gray30", "gray70"),
            hover_color=("gray85", "gray25"),
            anchor="w",
            command=self._toggle,
        )
        self.toggle_btn.pack(anchor="w", padx=4, pady=(2, 0))

        self.list_frame = ctk.CTkFrame(self, fg_color="transparent")
        # hidden by default

    def _toggle(self):
        if self.expanded:
            self.list_frame.pack_forget()
            self.toggle_btn.configure(text=f"Tools ({len(self.tools)})  ▸")
        else:
            self.list_frame.pack(fill="x", padx=12, pady=(0, 4))
            self.toggle_btn.configure(text=f"Tools ({len(self.tools)})  ▾")
        self.expanded = not self.expanded

    def set_tools(self, tools):
        self.tools = tools or []
        self.toggle_btn.configure(
            text=f"Tools ({len(self.tools)})  {'▾' if self.expanded else '▸'}"
        )
        # Clear previous entries
        for w in self.list_frame.winfo_children():
            w.destroy()
        for tool in self.tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "")
            short = (desc[:80] + "...") if len(desc) > 80 else desc
            lbl = ctk.CTkLabel(
                self.list_frame,
                text=f"  •  {name}",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            )
            lbl.pack(fill="x", anchor="w")
            if short:
                dlbl = ctk.CTkLabel(
                    self.list_frame,
                    text=f"      {short}",
                    font=ctk.CTkFont(size=11),
                    text_color="gray",
                    anchor="w",
                )
                dlbl.pack(fill="x", anchor="w")


class ServerCard(ctk.CTkFrame):
    """Single MCP server card with status, enable/disable switch, and tools."""

    def __init__(self, master, server_data, client, on_toggle=None, **kwargs):
        super().__init__(master, corner_radius=8, border_width=1, **kwargs)
        self.server_data = server_data
        self.client = client
        self.on_toggle = on_toggle
        self.server_name = server_data.get("name", "unknown")

        self._build(server_data)

    def _build(self, data):
        status = data.get("status", "unknown")
        disabled = data.get("disabled", False)
        tools = data.get("tools", [])
        resources = data.get("resources", [])
        prompts = data.get("prompts", [])

        # ── Header row ───────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 2))

        name_lbl = ctk.CTkLabel(
            header,
            text=self.server_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        name_lbl.pack(side="left")

        # Status badge
        color_map = {
            "connected": "#2ecc71",
            "connecting": "orange",
            "disconnected": "gray",
            "disabled": "#e74c3c",
            "error": "#e74c3c",
        }
        display_status = "disabled" if disabled else status
        badge_color = color_map.get(display_status, "gray")
        badge = ctk.CTkLabel(
            header,
            text=f" {display_status.upper()} ",
            font=ctk.CTkFont(size=10),
            fg_color=badge_color,
            corner_radius=4,
            text_color="white",
        )
        badge.pack(side="left", padx=(8, 0))

        # Enable / Disable switch
        self.enabled_var = ctk.BooleanVar(value=not disabled)
        switch = ctk.CTkSwitch(
            header,
            text="Enabled",
            variable=self.enabled_var,
            width=40,
            command=self._on_switch,
            onvalue=True,
            offvalue=False,
        )
        switch.pack(side="right")

        # ── Info row ─────────────────────────────────────────────────────
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(fill="x", padx=14, pady=(0, 2))

        transport = data.get("type") or ("remote" if data.get("url") else "stdio")
        meta_text = f"Transport: {transport}    Resources: {len(resources)}    Prompts: {len(prompts)}"
        meta_lbl = ctk.CTkLabel(
            info, text=meta_text, font=ctk.CTkFont(size=11), text_color="gray", anchor="w"
        )
        meta_lbl.pack(anchor="w")

        # ── Collapsible tools list ───────────────────────────────────────
        self.tools_list = ToolsList(self, tools=tools, fg_color="transparent")
        self.tools_list.pack(fill="x", padx=6, pady=(0, 6))

    def _on_switch(self):
        enabled = self.enabled_var.get()

        def do():
            if enabled:
                self.client.start_server(self.server_name)
            else:
                self.client.stop_server(self.server_name, disable=True)
            if self.on_toggle:
                self.after(0, self.on_toggle)

        threading.Thread(target=do, daemon=True).start()

    def update_data(self, data):
        """Rebuild the card content with fresh data."""
        self.server_data = data
        for w in self.winfo_children():
            w.destroy()
        self._build(data)


class ServersTab(ctk.CTkFrame):
    """Tab that shows all connected MCP servers as cards."""

    def __init__(self, master, client, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.client = client
        self.cards: dict[str, ServerCard] = {}

        # Scrollable container
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

        # Empty-state label
        self.empty_label = ctk.CTkLabel(
            self.scroll,
            text="No servers connected.\nStart the hub to see MCP servers here.",
            text_color="gray",
            font=ctk.CTkFont(size=13),
        )
        self.empty_label.pack(pady=40)

    def refresh(self, servers_list):
        """Redraw cards from a fresh list of server data dicts."""
        current_names = {s.get("name") for s in servers_list}
        existing_names = set(self.cards.keys())

        # Remove cards for servers that no longer exist
        for name in existing_names - current_names:
            card = self.cards.pop(name)
            card.destroy()

        # Hide empty label if we have servers
        if servers_list:
            self.empty_label.pack_forget()
        else:
            if not self.empty_label.winfo_ismapped():
                self.empty_label.pack(pady=40)
            return

        for sdata in servers_list:
            name = sdata.get("name")
            if name in self.cards:
                self.cards[name].update_data(sdata)
            else:
                card = ServerCard(
                    self.scroll,
                    sdata,
                    self.client,
                    on_toggle=lambda: None,
                )
                card.pack(fill="x", padx=4, pady=4)
                self.cards[name] = card
