from pathlib import Path

import asyncio
import dotenv
import logfire
import nest_asyncio
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

# This is a workaround for the asyncio event loop issue in Jupyter notebooks
nest_asyncio.apply()

# Load environment variables from .env file
project_root = Path(__file__).parent.parent.absolute()
dotenv_path = project_root / ".env"
dotenv.load_dotenv(dotenv_path=dotenv_path)

# Set up logging
logfire.configure(send_to_logfire="if-token-present")

# Create an MCPServer instance with the docker command
mcp_imas = MCPServerStdio("docker", args=["run", "-i", "--rm", "mcp-imas"])

agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    mcp_servers=[mcp_imas],
    system_prompt="Be concise.",
    instrument=True,
)


async def main():
    async with agent.run_mcp_servers():
        # Run the agent with the MCP server
        result = await agent.run("list all the IDSs defined by the IMAS DD.")
        print(result.output)
        return result.output


# This function can be called directly from IPython
def run_query(query="list all the IDSs defined by the IMAS DD."):
    """Run a query with the agent. Works in both scripts and interactive sessions."""
    try:
        # Try using asyncio.run (works in scripts)
        return asyncio.run(run_single_query(query))
    except RuntimeError:
        # If we're in an interactive session with an existing event loop
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(run_single_query(query))


async def run_single_query(query):
    """Helper function to run a single query."""
    async with agent.run_mcp_servers():
        result = await agent.run(query)
        return result.output


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
