import argparse
import asyncio
import logging
import sys
from orchestrator import Orchestrator

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp_server")

# Instantiate the server named "BlindSpot Auditor"
app = MCPServer("BlindSpot Auditor")


@app.tool(
    name="handle_prompt",
    description="Processes a prompt through the AKILI-SPECS Leader-Implementer-Reviewer multi-agent system.",
)
async def handle_prompt(prompt: str) -> str:
    """Entry point tool that dispatches a prompt to the AKILI-SPECS orchestrator."""
    logger.info("Received prompt in handle_prompt tool: %s", prompt[:80])
    orchestrator = Orchestrator()
    result = await orchestrator.run(prompt)
    return result


def main():
    parser = argparse.ArgumentParser(description="BlindSpot Auditor MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    args = parser.parse_args()

    logger.info("Starting BlindSpot Auditor MCP Server on %s transport...", args.transport)
    app.run(transport=args.transport)


if __name__ == "__main__":
    main()
