"""SketchUp MCP Server - Bridge Claude to SketchUp via MCP protocol."""

import asyncio

__version__ = "0.1.0"


def main():
    """Entry point for the CLI command."""
    from .server import main as async_main
    asyncio.run(async_main())


__all__ = ["main"]