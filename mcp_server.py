import argparse
import asyncio
import logging
import os
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

DEFAULT_TIMEOUT = float(os.getenv("PIPELINE_TIMEOUT", "120.0"))


@app.tool(
    name="handle_prompt",
    description="Processes a prompt through the AKILI-SPECS Leader-Implementer-Reviewer multi-agent system.",
)
async def handle_prompt(prompt: str) -> str:
    """Entry point tool that dispatches a prompt to the AKILI-SPECS orchestrator."""
    logger.info("Received prompt in handle_prompt tool: %s", prompt[:80])
    orchestrator = Orchestrator()
    try:
        result = await asyncio.wait_for(orchestrator.run(prompt), timeout=DEFAULT_TIMEOUT)
        return result
    except asyncio.TimeoutError:
        logger.warning("Pipeline timed out after %.1fs", DEFAULT_TIMEOUT)
        partial_parts = [
            f"### Pipeline Timed Out ({DEFAULT_TIMEOUT}s limit reached)\n",
            "The multi-agent pipeline exceeded the execution time limit.\n",
        ]
        if orchestrator.completed_results:
            partial_parts.append(
                f"**Completed {len(orchestrator.completed_results)} partial task(s) before timeout:**\n"
            )
            for res in orchestrator.completed_results:
                partial_parts.append(f"#### Task: {res.task_id}\n{res.content}\n")
        else:
            partial_parts.append(
                "Execution timed out during initial decomposition or early task processing. No partial tasks completed."
            )
        return "\n".join(partial_parts)
    except Exception as e:
        logger.error("Pipeline execution encountered an error: %s", e, exc_info=True)
        return f"Error executing AKILI-SPECS pipeline: {type(e).__name__}: {str(e)}"


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
