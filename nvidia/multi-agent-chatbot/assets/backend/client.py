#
# SPDX-FileCopyrightText: Copyright (c) 1993-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Multi-Server MCP Client for connecting to multiple MCP servers.

This module provides a unified client interface for connecting to and managing
multiple Model Context Protocol (MCP) servers. It handles server configuration,
initialization, and tool retrieval across different server types.
"""

import os
import shlex
from urllib.parse import urlsplit, urlunsplit
from typing import List, Optional, Dict, Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp.types import Tool


class MCPClient:
    """Client for managing connections to multiple MCP servers.
    
    Provides a unified interface for connecting to and interacting with
    various MCP servers including RAG, image understanding, and weather services.
    """
    
    def __init__(
        self,
        include_base: bool = True,
        include_revit: bool = True,
        revit_override: Dict[str, Any] | None = None,
    ):
        """Initialize the MCP client with predefined server configurations."""
        self.server_configs: Dict[str, Any] = {}
        if include_base:
            self.server_configs.update(self._build_base_configs())

        if include_revit:
            revit_config = self._normalize_revit_config(
                revit_override or self._build_revit_config_from_env()
            )
            if revit_config:
                self.server_configs["revit-mcp-server"] = revit_config
        self.mcp_client: MultiServerMCPClient | None = None

    @staticmethod
    def _build_base_configs() -> Dict[str, Any]:
        return {
            "image-understanding-server": {
                "command": "python",
                "args": ["tools/mcp_servers/image_understanding.py"],
                "transport": "stdio",
            },
            "code-generation-server": {
                "command": "python",
                "args": ["tools/mcp_servers/code_generation.py"],
                "transport": "stdio",
            },
            "rag-server": {
                "command": "python",
                "args": ["tools/mcp_servers/rag.py"],
                "transport": "stdio",
            },
            "weather-server": {
                "command": "python",
                "args": ["tools/mcp_servers/weather_test.py"],
                "transport": "stdio",
            },
        }

    @classmethod
    def build_revit_url_config(cls, url: str, transport: str | None = None) -> Dict[str, Any]:
        normalized_transport = cls._normalize_revit_transport(url, transport, default="streamable_http")
        normalized_url = cls._normalize_revit_url(url, normalized_transport)
        return {
            "transport": normalized_transport,
            "url": normalized_url,
        }

    @classmethod
    def build_revit_config_from_env(cls) -> Dict[str, Any] | None:
        return cls._build_revit_config_from_env()

    @classmethod
    def _build_revit_config_from_env(cls) -> Dict[str, Any] | None:
        """Optionally build config for a Revit MCP server via environment variables.
        
        Supported setups:
        - Streamable HTTP transport: set REVIT_MCP_URL (and optional REVIT_MCP_TRANSPORT)
        - stdio transport: set REVIT_MCP_MAIN (path to main.py) or REVIT_MCP_COMMAND/REVIT_MCP_ARGS
        """
        revit_url = os.getenv("REVIT_MCP_URL")
        transport_env = os.getenv("REVIT_MCP_TRANSPORT")
        if revit_url:
            return cls.build_revit_url_config(revit_url, transport_env)
        
        revit_main = os.getenv("REVIT_MCP_MAIN")
        command = os.getenv("REVIT_MCP_COMMAND")
        args_env = os.getenv("REVIT_MCP_ARGS")
        
        if not any([revit_main, command, args_env]):
            return None
        
        if not command:
            command = "uv"
        
        if not args_env:
            if not revit_main:
                raise ValueError("REVIT_MCP_MAIN is required when REVIT_MCP_ARGS is not set.")
            args = ["run", "--with", "mcp[cli]", "mcp", "run", revit_main]
        else:
            args = shlex.split(args_env)
        
        return {
            "command": command,
            "args": args,
            "transport": cls._normalize_transport(transport_env, default="stdio"),
        }

    @staticmethod
    def _normalize_transport(value: str | None, default: str) -> str:
        """Normalize MCP transport names for client configs."""
        if not value:
            return default
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in {"streamable_http", "streamable"}:
            return "streamable_http"
        if normalized in {"http", "sse"}:
            return "sse"
        if normalized in {"stdio"}:
            return "stdio"
        return normalized

    @classmethod
    def _normalize_revit_transport(
        cls, url: str | None, transport: str | None, default: str
    ) -> str:
        """Normalize transport using URL heuristics when ambiguous."""
        if transport:
            raw = transport.strip().lower().replace("-", "_").replace(" ", "_")
            if raw == "http":
                # Prefer streamable_http unless URL strongly suggests SSE (e.g., port 8010).
                if url:
                    parts = urlsplit(url)
                    if parts.port == 8010:
                        return "sse"
                return "streamable_http"
            return cls._normalize_transport(transport, default=default)

        if url:
            parts = urlsplit(url)
            # Heuristic: port 8010 is commonly used for SSE mode.
            if parts.port == 8010:
                return "sse"
        return default

    @staticmethod
    def _normalize_revit_url(url: str, transport: str) -> str:
        """Normalize MCP URL path for the chosen transport."""
        if not url:
            return url
        parts = urlsplit(url)
        path = parts.path or "/"
        if transport in {"streamable_http", "sse"}:
            if path.rstrip("/") in {"", "/"}:
                path = "/mcp"
        return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))

    @classmethod
    def _normalize_revit_config(cls, config: Dict[str, Any] | None) -> Dict[str, Any] | None:
        if not config:
            return None
        normalized = dict(config)
        if "url" in normalized:
            normalized["transport"] = cls._normalize_transport(
                normalized.get("transport"), default="streamable_http"
            )
        elif "command" in normalized:
            normalized["transport"] = cls._normalize_transport(
                normalized.get("transport"), default="stdio"
            )
        return normalized

    async def init(self):
        """Initialize the multi-server MCP client.
        
        Returns:
            MCPClient: Self for method chaining
            
        Raises:
            Exception: If client initialization fails
        """
        self.mcp_client = MultiServerMCPClient(self.server_configs)
        return self

    async def get_tools(self):
        """Retrieve available tools from all connected MCP servers.
        
        Returns:
            List[Tool]: List of available tools from all servers
            
        Raises:
            RuntimeError: If client is not initialized
            Exception: If tool retrieval fails
        """
        if not self.mcp_client:
            raise RuntimeError("MCP client not initialized. Call `await init()` first.")
        
        try:
            tools = await self.mcp_client.get_tools()
            return tools
        except Exception as error:
            # Retry once if the Revit MCP URL might be redirecting between /mcp and /mcp/
            retried = False
            if self._maybe_toggle_revit_mcp_trailing_slash():
                retried = True
                try:
                    tools = await self.mcp_client.get_tools()
                    return tools
                except Exception:
                    pass
            if retried:
                print("Error encountered connecting to MCP server after retrying /mcp vs /mcp/.\n")
            else:
                print("Error encountered connecting to MCP server. Is the server running? Is your config server path correct?\n")
            raise error

    @staticmethod
    def _alternate_mcp_url(url: str) -> Optional[str]:
        if not url:
            return None
        parts = urlsplit(url)
        path = parts.path or "/"
        if path.endswith("/mcp/"):
            new_path = path[:-1]
        elif path.endswith("/mcp"):
            new_path = path + "/"
        else:
            return None
        return urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))

    def _maybe_toggle_revit_mcp_trailing_slash(self) -> bool:
        config = self.server_configs.get("revit-mcp-server")
        if not config:
            return False
        url = config.get("url")
        if not url:
            return False
        alt_url = self._alternate_mcp_url(url)
        if not alt_url or alt_url == url:
            return False
        new_config = dict(config)
        new_config["url"] = alt_url
        self.server_configs["revit-mcp-server"] = new_config
        # Reinitialize the client with the toggled URL
        self.mcp_client = MultiServerMCPClient(self.server_configs)
        return True
