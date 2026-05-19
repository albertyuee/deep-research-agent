"""MCP client connection manager.

Manages the lifecycle of MCP server subprocess connections.
Provides a singleton client for tool calls across the agent.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from config.settings import settings


class MCPClient:
    """Long-lived MCP client that connects to the web search server via stdio.

    Lifecycle:
        connect()    — start server subprocess, initialize session
        call_tool()  — invoke a tool on the server
        disconnect() — clean shutdown of session and subprocess
    """

    def __init__(self):
        self._session: ClientSession | None = None
        self._connected = False
        self._stdio_ctx = None
        self._session_ctx = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        """Start the MCP server subprocess and initialize the session."""
        if self._connected:
            return

        if not settings.mcp.tavily_api_key:
            print("[MCP] TAVILY_API_KEY not set, skipping MCP connection",
                  flush=True, file=sys.stderr)
            return

        try:
            # Resolve project root for reliable subprocess launch
            project_root = str(settings.project_root)

            server_params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "mcp_servers.web_search"],
                env={
                    **os.environ,
                    "TAVILY_API_KEY": settings.mcp.tavily_api_key,
                    "PYTHONPATH": project_root,
                },
                cwd=project_root,
            )

            # Enter stdio_client context manager
            self._stdio_ctx = stdio_client(server_params)
            read, write = await self._stdio_ctx.__aenter__()

            # Enter ClientSession context manager
            self._session_ctx = ClientSession(read, write)
            self._session = await self._session_ctx.__aenter__()

            await self._session.initialize()
            self._connected = True

            # Log available tools
            tools_result = await self._session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            print(f"[MCP] Connected. Available tools: {tool_names}",
                  flush=True, file=sys.stderr)

        except Exception as e:
            print(f"[MCP] Failed to connect: {e}", flush=True, file=sys.stderr)
            self._connected = False

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call an MCP tool and return its text output.

        Returns empty string if client is not connected or call fails.
        """
        if not self._connected or not self._session:
            return ""

        try:
            result = await self._session.call_tool(name, arguments)

            # Extract text from the first TextContent block
            for block in result.content:
                if hasattr(block, "text"):
                    return block.text

            return ""

        except Exception as e:
            print(f"[MCP] call_tool '{name}' failed: {e}",
                  flush=True, file=sys.stderr)
            return ""

    async def disconnect(self) -> None:
        """Shut down the MCP session and server subprocess."""
        if not self._connected:
            return

        try:
            if self._session_ctx is not None:
                await self._session_ctx.__aexit__(None, None, None)
            if self._stdio_ctx is not None:
                await self._stdio_ctx.__aexit__(None, None, None)
        except Exception as e:
            print(f"[MCP] Error during disconnect: {e}",
                  flush=True, file=sys.stderr)
        finally:
            self._session = None
            self._session_ctx = None
            self._stdio_ctx = None
            self._connected = False
            print("[MCP] Disconnected", flush=True, file=sys.stderr)


# Global singleton
mcp_client = MCPClient()
