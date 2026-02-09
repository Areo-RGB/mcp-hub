"""
HTTP client for the MCP Hub REST API.
"""

import json
import urllib.request
import urllib.error


class MCPHubClient:
    """Thin wrapper around the MCP Hub HTTP API."""

    def __init__(self, host="127.0.0.1", port=3000):
        self.host = host
        self.port = port

    @property
    def base_url(self):
        return f"http://{self.host}:{self.port}"

    # ── Generic helpers ──────────────────────────────────────────────────

    def _get(self, path, timeout=5):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return None

    def _post(self, path, body=None, query="", timeout=10):
        url = f"{self.base_url}{path}{query}"
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return None

    # ── API methods ──────────────────────────────────────────────────────

    def get_health(self):
        """GET /api/health — returns full health payload including servers list."""
        return self._get("/api/health")

    def get_servers(self):
        """GET /api/servers — list all servers with status and capabilities."""
        return self._get("/api/servers")

    def start_server(self, name):
        """POST /api/servers/start — start (and enable) a specific server."""
        return self._post("/api/servers/start", {"server_name": name})

    def stop_server(self, name, disable=False):
        """POST /api/servers/stop — stop a server, optionally setting disabled flag."""
        query = "?disable=true" if disable else ""
        return self._post("/api/servers/stop", {"server_name": name}, query=query)

    def refresh_server(self, name):
        """POST /api/servers/refresh — refresh a server's capabilities."""
        return self._post("/api/servers/refresh", {"server_name": name})

    def restart_hub(self):
        """POST /api/restart — soft restart the entire hub."""
        return self._post("/api/restart")
