# MCP Hub GUI — Setup & Debugging Guide

This document covers how to set up, run, and debug the MCP Hub desktop GUI wrapper.

---

## Prerequisites

| Dependency | Version | Notes |
|------------|---------|-------|
| **Node.js** | >= 18 | Required for the MCP Hub backend |
| **Python** | >= 3.9 | Required for the GUI (CustomTkinter) |
| **pip** | any | Comes with Python |
| **npm** | >= 9 | Comes with Node.js |

---

## Quick Start

### 1. Install Node dependencies (MCP Hub backend)

```bash
npm install
```

### 2. Install Python GUI dependencies

```bash
npm run gui:install
```

This runs `pip install -r gui/requirements.txt`, which installs:

- **customtkinter** >= 5.2.0 — modern themed Tkinter wrapper

### 3. Configure your MCP servers

Edit `mcp-servers.json` in the project root. Each server entry supports a `disabled` flag:

```jsonc
{
  "mcpServers": {
    "my-server": {
      "url": "http://localhost:8080/sse",
      "headers": { "Authorization": "Bearer ${API_TOKEN}" },
      "disabled": false  // set to true to skip this server on startup
    },
    "local-tool": {
      "command": "npx",
      "args": ["my-mcp-tool"],
      "disabled": false
    }
  }
}
```

- **`disabled: true`** — the hub will skip connecting to this server on startup.
- You can also toggle servers on/off at runtime from the GUI's enable/disable switch. The switch calls the hub API to stop the server with `?disable=true`, which persists the flag back to config.

### 4. Launch the GUI

```bash
npm run gui
```

Or directly:

```bash
python gui/app.py
```

---

## GUI Overview

### Toolbar

| Control | Purpose |
|---------|---------|
| **Start Hub** / **Stop Hub** | Launches or terminates the `mcp-hub` Node process |
| **Port** field | Set the HTTP port before starting (default: 3000) |
| **Open Config** | Opens `mcp-servers.json` in your system editor |

### Servers Tab

- Displays one **card** per MCP server defined in config.
- Each card shows:
  - Server name and connection status badge (`CONNECTED`, `DISABLED`, etc.)
  - Transport type, resource count, and prompt count
  - **Enable/Disable switch** — toggles the `disabled` flag via the hub API
  - **Collapsible tools list** — click "Tools (N)" to expand/collapse the tool names and descriptions

### Logs Tab

- Streams `stdout` from the hub process in real time.
- **Show DEBUG** checkbox — toggles debug-level entries.
- **Level filter** dropdown — filter by `ALL`, `INFO`, `WARN`, `ERROR`, `DEBUG`, or `HUB`.
- **Clear** — wipes the log view.
- **Open Log File** — opens the persistent log file (`~/.local/state/mcp-hub/logs/mcp-hub.log` or `~/.mcp-hub/logs/`).

---

## Architecture

```
┌──────────────────────────────┐
│   gui/app.py (CustomTkinter) │  ← Python desktop app
│   ├── servers_tab.py         │
│   ├── logs_tab.py            │
│   └── hub_client.py          │  ← HTTP client for REST API
└──────────┬───────────────────┘
           │  HTTP (localhost:PORT)
           ▼
┌──────────────────────────────┐
│  MCP Hub  (Node.js)          │  ← Backend process
│  src/utils/cli.js            │
│  src/server.js               │
│  src/MCPHub.js               │
└──────────────────────────────┘
```

The GUI spawns the hub as a child process and communicates via:

1. **REST API** — `GET /api/health`, `GET /api/servers`, `POST /api/servers/start`, `POST /api/servers/stop?disable=true`, etc.
2. **stdout streaming** — hub process output is piped into the Logs tab.

---

## Debugging

### Hub won't start

1. Check the **Logs tab** for errors from the Node process.
2. Verify Node.js is installed: `node --version`.
3. Ensure dependencies are installed: `npm install`.
4. Check port availability — if port 3000 is taken, change it in the Port field.

### GUI won't launch

1. Verify Python version: `python --version` (>= 3.9).
2. Reinstall GUI deps: `pip install -r gui/requirements.txt`.
3. On Linux you may need `tkinter` system package:
   - Debian/Ubuntu: `sudo apt install python3-tk`
   - Fedora: `sudo dnf install python3-tkinter`
4. On Windows, tkinter ships with the standard Python installer — make sure "tcl/tk" was checked.

### Servers show as DISCONNECTED

1. Check the server's config in `mcp-servers.json` — is the `url` reachable?
2. For stdio servers, is the `command` in your PATH?
3. Look at the hub log file for connection errors:
   ```bash
   # Linux / macOS
   cat ~/.local/state/mcp-hub/logs/mcp-hub.log | tail -50

   # Windows (PowerShell)
   Get-Content "$env:LOCALAPPDATA\mcp-hub\logs\mcp-hub.log" -Tail 50
   ```

### Enable/Disable switch doesn't work

- The switch calls `POST /api/servers/stop?disable=true` or `POST /api/servers/start`. Make sure the hub is running.
- If the hub is running but the API is unresponsive, check for port mismatches between the GUI's Port field and the actual hub port.

### Debug logging

- Enable the **Show DEBUG** checkbox in the Logs tab.
- The hub itself supports debug output through its structured logger. Check the log file for `"type":"debug"` entries.

---

## File Reference

| File | Purpose |
|------|---------|
| `gui/app.py` | Main application window, hub lifecycle, polling |
| `gui/hub_client.py` | HTTP client wrapping the MCP Hub REST API |
| `gui/servers_tab.py` | Server cards with collapsible tool lists and enable/disable |
| `gui/logs_tab.py` | Log viewer with level filtering and debug toggle |
| `gui/requirements.txt` | Python dependencies (customtkinter) |
| `mcp-servers.json` | MCP server configuration (edit this) |
| `agent.md` | This file |

---

## Common Config Patterns

### Disable a server without removing it

```json
{
  "mcpServers": {
    "expensive-server": {
      "url": "https://api.example.com/mcp",
      "disabled": true
    }
  }
}
```

### Multiple config files (global + project)

```bash
node src/utils/cli.js --port 3000 \
  --config ~/.config/mcphub/global.json \
  --config ./.mcphub/project.json \
  --watch
```

Later files override earlier ones. The GUI uses the single `mcp-servers.json` in the project root by default.
