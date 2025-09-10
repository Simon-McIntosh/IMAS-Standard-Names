import dotenv
import logfire
import nest_asyncio

from pathlib import Path

from httpx import AsyncClient, Timeout

from pydantic_ai import Agent
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.mcp import MCPServerStdio, MCPServer, MCPServerSSE


class IMASConnect:
    """Class to manage connection to IMAS MCP server and run queries."""
    def __init__(self, **kwargs):
        """
        Initializes the IMAS connection class.
        - Sets up placeholders for MCP IMAS, agent, and model.
        - Initializes asynchronous HTTP clients for model and server communication with custom timeout and SSL verification disabled.
        - Applies nest_asyncio to allow nested event loops.
        - Loads environment variables from a .env file located at the project root.
        - Configures logging with Logfire, sending logs if a token is present.
        """

        self.mcp_imas = None
        self.agent = None
        self.model = None

        # persistent clients (extended timeout)
        self.model_client = AsyncClient(verify=False, timeout=Timeout(30.0))
        self.server_client = AsyncClient(verify=False, timeout=Timeout(30.0))

        # store basic init config for rebuilds
        self._config = kwargs.copy()

        nest_asyncio.apply()

        # Load environment variables from .env file
        project_root = Path(__file__).parent.parent.absolute()
        dotenv_path = project_root / ".env"
        dotenv.load_dotenv(dotenv_path=dotenv_path)

        # Set up logging
        logfire.configure(send_to_logfire="if-token-present")

        server_choice = kwargs.get("mcp_server", "remote_sse")
        model_provider = kwargs.get("model_provider", "anthropic")

        if server_choice == "uv":
            self._setup_mcp_uv()
        elif server_choice == "remote_sse":
            self._connect_remote_mcp_sse(kwargs.get("host"), kwargs.get("port"))
        elif server_choice == "custom":
            self._connect_mcp(kwargs.get("server"))

        if model_provider == "anthropic":
            self._setup_anthropic_model(kwargs.get("model_name", "claude-3-haiku-20240307"))
        self._setup_agent(kwargs.get("system_prompt","You are an expert in Fusion and utilizing the IMAS data dictionary."), output_type=kwargs.get("output_type", str))

    def _setup_mcp_uv(self):
        """
        Initializes and configures the MCPServerStdio instance for the 'uv' server.
        This method sets up the MCP server with specific arguments to run the 'imas-mcp'
        application in active mode, disables rich output, and sets the log level to DEBUG.
        Attributes:
            mcp_imas (MCPServerStdio): The configured MCP server instance for 'uv'.
        """
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
    def _connect_remote_mcp_sse(self, host: str, port: int):
        """
        Establishes a remote connection to an MCP server using Server-Sent Events (SSE).
        Args:
            host (str): The hostname or IP address of the remote MCP server.
            port (int): The port number on which the MCP server is listening.
        Side Effects:
            Initializes the `self.mcp_imas` attribute with an instance of `MCPServerSSE`
            configured to connect to the specified host and port using SSE.
        Dependencies:
            Requires `pydantic_ai.mcp.MCPServerSSE` and `self.server_client`.
        Example:
            connect_remote_mcp_sse('localhost', 8080)
        """

        self.mcp_imas = MCPServerSSE(f'{host}:{port}/sse', http_client=self.server_client)

    def _connect_mcp(self,server: MCPServer):
        """
        Establishes a connection to the specified MCPServer instance.
        Parameters:
            server (MCPServer): The MCPServer instance to connect to.
        Sets:
            self.mcp_imas: Stores the provided MCPServer instance for further interactions.
        """

        self.mcp_imas = server

    def _setup_anthropic_model(self, model_name: str = "claude-3-haiku-20240307"):
        """
        Initializes and sets up an Anthropic language model for use within the application.
        Args:
            model_name (str, optional): The name of the Anthropic model to initialize. 
                Defaults to "claude-3-haiku-20240307".
        Side Effects:
            Sets the `self.model` attribute to an instance of `AnthropicModel` configured 
            with the specified model name and provider.
        """
        
        self.model = AnthropicModel(model_name, provider = AnthropicProvider(http_client=self.model_client))

    def _setup_agent(self,system_prompt,output_type):
        """
        Initializes the agent with the configured model and MCP server.
        Raises:
            ValueError: If the MCP server or model is not set up.
        Sets:
            self.agent: An Agent instance configured with the specified model and MCP server,
                        using a concise system prompt and instrumentation enabled.
        """
        
        self.agent = Agent(
            model=self.model,
            mcp_servers=[self.mcp_imas],
            system_prompt=system_prompt,
            instrument=True,
            output_type=output_type
        )

    # --- helper to re-create agent if model/server clients were closed ---
    def ensure(self):
        recreate = False
        if self.server_client is None or getattr(self.server_client, 'is_closed', False):
            self.server_client = AsyncClient(verify=False, timeout=Timeout(30.0))
            recreate = True
        if self.model_client is None or getattr(self.model_client, 'is_closed', False):
            self.model_client = AsyncClient(verify=False, timeout=Timeout(30.0))
            recreate = True
        if recreate:
            # rebuild server & agent minimally
            choice = self._config.get("mcp_server", "remote_sse")
            if choice == "uv":
                self._setup_mcp_uv()
            elif choice == "remote_sse":
                self._connect_remote_mcp_sse(self._config.get("host"), self._config.get("port"))
            elif choice == "custom":
                self._connect_mcp(self._config.get("server"))
            if self._config.get("model_provider", "anthropic") == "anthropic":
                self._setup_anthropic_model(self._config.get("model_name", "claude-3-haiku-20240307"))
            self._setup_agent(self._config.get("system_prompt"), self._config.get("output_type", str))

    def run(self, prompt: str):
        self.ensure()
        return self.agent.run_sync(prompt)
    



