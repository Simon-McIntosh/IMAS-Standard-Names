from pathlib import Path

from httpx import AsyncClient, Timeout
import asyncio
import dotenv
import logfire
import nest_asyncio
from pydantic_ai import Agent
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.mcp import MCPServerStdio, MCPServer

# MODEL = "anthropic:claude-opus-4-1-20250805"

class IMASConnect:
    """Class to manage connection to IMAS MCP server and run queries."""
    def __init__(self):
        self.mcp_imas = None
        self.agent = None
        self.model = None

        self.model_client=AsyncClient(verify=False,timeout=Timeout(10.0))
        self.server_client=AsyncClient(verify=False,timeout=Timeout(10.0))


        nest_asyncio.apply()

        # Load environment variables from .env file
        project_root = Path(__file__).parent.parent.absolute()
        dotenv_path = project_root / ".env"
        dotenv.load_dotenv(dotenv_path=dotenv_path)

        # Set up logging
        logfire.configure(send_to_logfire="if-token-present")

    def setup_mcp_docker(self):
        self.mcp_imas = MCPServerStdio(
            "uv",
            args=[
                "run",
                "--active",
                "imas-mcp",
                "--no-rich",
                "--log-level",
                "DEBUG"
            ],

        )
    def connect_remote_mcp_sse(self, host: str, port: int):
        from pydantic_ai.mcp import MCPServerSSE
        self.mcp_imas = MCPServerSSE(f'{host}:{port}/sse', http_client=self.server_client)

    def connect_mcp(self,server: MCPServer):
        self.mcp_imas = server

    def setup_anthropic_model(self, model_name: str = "claude-3-haiku-20240307"):
        self.model = AnthropicModel(model_name, provider = AnthropicProvider(http_client=self.model_client))

    def setup_agent(self):
        if self.mcp_imas is None:
            raise ValueError("MCP server not set up. Setup the mcp server first.")
        if self.model is None:
            raise ValueError("Model not set up. Setup the model first.")
        self.agent = Agent(
            model=self.model,
            mcp_servers=[self.mcp_imas],
            system_prompt="Be concise.",
            instrument=True,
        )
    



# async def main():
#     async with agent.run_mcp_servers():
#         # Run the agent with the MCP server
#         result = await agent.run("list all the IDSs defined by the IMAS DD.")
#         print(result.output)
#         return result.output


# # This function can be called directly from IPython
# def run_query(query="list all the IDSs defined by the IMAS DD."):
#     """Run a query with the agent. Works in both scripts and interactive sessions."""
#     try:
#         # Try using asyncio.run (works in scripts)
#         return asyncio.run(run_single_query(query))
#     except RuntimeError:
#         # If we're in an interactive session with an existing event loop
#         loop = asyncio.get_event_loop()
#         return loop.run_until_complete(run_single_query(query))


# async def run_single_query(query):
#     """Helper function to run a single query."""
#     async with agent.run_mcp_servers():
#         result = await agent.run(query)
#         return result.output


# # Run the main function
# if __name__ == "__main__":
#     asyncio.run(main())
