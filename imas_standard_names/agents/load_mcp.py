"""
This module creates an alternative to pydantic_ai's built-in MCP server loader
that loads from the "server" attribute in the mcp config file
"""

from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Discriminator, Field, Tag
from pydantic_ai.mcp import (
    MCPServerSSE,
    MCPServerStdio,
    MCPServerStreamableHTTP,
)


def _mcp_server_discriminator(value: dict[str, Any]) -> str | None:
    if "url" in value:
        if value["url"].endswith("/sse"):
            return "sse"
        return "streamable-http"
    return "stdio"


class MCPServerConfig(BaseModel):
    """Configuration for MCP servers."""

    mcp_servers: Annotated[
        dict[
            str,
            Annotated[
                Annotated[MCPServerStdio, Tag("stdio")]
                | Annotated[MCPServerStreamableHTTP, Tag("streamable-http")]
                | Annotated[MCPServerSSE, Tag("sse")],
                Discriminator(_mcp_server_discriminator),
            ],
        ],
        Field(alias="servers"),
    ]


def load_mcp_servers(
    config_path: str | Path,
) -> list[MCPServerStdio | MCPServerStreamableHTTP | MCPServerSSE]:
    """Load MCP servers from a configuration file.

    Args:
        config_path: The path to the configuration file.

    Returns:
        A list of MCP servers.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValidationError: If the configuration file does not match the schema.
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file {config_path} not found")

    config = MCPServerConfig.model_validate_json(config_path.read_bytes())
    return list(config.mcp_servers.values())
