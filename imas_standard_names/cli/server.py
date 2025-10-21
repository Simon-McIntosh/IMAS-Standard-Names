"""CLI interface for IMAS Standard Names MCP Server."""

import logging
from typing import Literal, cast

import click

from imas_standard_names import __version__
from imas_standard_names.server import Server

# Configure logging
logger = logging.getLogger(__name__)


def _print_version(
    ctx: click.Context, param: click.Parameter, value: bool
) -> None:  # pragma: no cover - simple utility
    """Callback to print only the raw version and exit early."""
    if not value or ctx.resilient_parsing:
        return
    click.echo(__version__)
    ctx.exit()


@click.command()
@click.option(
    "--version",
    is_flag=True,
    callback=_print_version,
    expose_value=False,
    is_eager=True,
    help="Show the imas-mcp version and exit (raw version only).",
)
@click.option(
    "--transport",
    envvar="TRANSPORT",
    default="stdio",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    help="Transport protocol (env: TRANSPORT) (stdio, sse, or streamable-http)",
)
@click.option(
    "--host",
    envvar="HOST",
    default="127.0.0.1",
    help="Host to bind (env: HOST) for sse and streamable-http transports",
)
@click.option(
    "--port",
    envvar="PORT",
    default=8000,
    type=int,
    help="Port to bind (env: PORT) for sse and streamable-http transports",
)
@click.option(
    "--catalog-root",
    envvar="STANDARD_NAMES_CATALOG_ROOT",
    default=None,
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=str),
    help="Custom directory for standard names catalog (env: STANDARD_NAMES_CATALOG_ROOT)",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Set the logging level",
)
def main(
    transport: str,
    host: str,
    port: int,
    catalog_root: str | None,
    log_level: str,
) -> None:
    """Run the AI-enhanced MCP server with configurable transport options.

    Examples:
        # Run with default STDIO transport
        python -m imas_standard_names.cli

        # Run with HTTP transport on custom host/port
        python -m imas_standard_names.cli --transport streamable-http --host 0.0.0.0 --port 9000

        # Run with debug logging
        python -m imas_standard_names.cli --log-level DEBUG

        # Run with HTTP transport on specific port
        python -m imas_standard_names.cli --transport streamable-http --port 8080

        # Run without rich progress output
        python -m imas_standard_names.cli --no-rich

    Note: streamable-http transport uses stateful mode to support
    MCP sampling functionality for enhanced AI interactions.
    """
    # Configure logging based on the provided level
    # Force reconfigure logging by getting the root logger and setting its level
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # Also update all existing handlers
    for handler in root_logger.handlers:
        handler.setLevel(getattr(logging, log_level))

    logger.debug(f"Set logging level to {log_level}")
    logger.debug(f"Starting MCP server with transport={transport}")

    match transport:
        case "stdio":
            logger.debug("Using STDIO transport")
        case "streamable-http":
            logger.info(f"Using streamable-http transport on {host}:{port}")
            logger.info("Stateful HTTP mode enabled to support MCP sampling")
        case _:
            logger.info(f"Using {transport} transport on {host}:{port}")

    # Create and run the mcp server
    server = Server(catalog_root=catalog_root)
    server.run(
        transport=cast(Literal["stdio", "sse", "streamable-http"], transport),
        host=host,
        port=port,
    )


if __name__ == "__main__":
    main()
