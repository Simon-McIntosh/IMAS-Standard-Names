import dotenv
import logfire
from pydantic import AliasChoices, BaseModel
from pydantic_ai import Agent, mcp
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from imas_standard_names.schema import Kind, Name

# Monkey patch mcp servers and rebuild
mcp.MCPServerConfig.model_fields["mcp_servers"].validation_alias = AliasChoices(
    "mcpServers", "servers"
)
mcp.MCPServerConfig.model_rebuild(force=True)

dotenv.load_dotenv(".env")

logfire.configure()
logfire.instrument_pydantic_ai()


servers = mcp.load_mcp_servers(".vscode/mcp.json")


class StandardName(BaseModel):
    name: Name


model = OpenAIChatModel(
    "anthropic/claude-sonnet-4",
    provider=OpenRouterProvider(),
)
agent = Agent(model, toolsets=servers, deps_type=Kind, output_type=list[StandardName])

if __name__ == "__main__":
    result = agent.run_sync(
        "@imas-sn generate a list of standard names from the following IDS paths"
        "use search_imas mcp tool\n"
        "time_slice/boundary/type\n"
        "time_slice/boundary/outline/r\n"
        "time_slice/boundary/outline/z\n"
        "time_slice/boundary/psi_norm\n"
        "time_slice/boundary/psi\n"
        "time_slice/boundary/geometric_axis/r\n"
        "time_slice/boundary/geometric_axis/z\n"
        "time_slice/boundary/minor_radius\n"
        "time_slice/boundary/elongation\n"
        "time_slice/boundary/elongation_upper\n"
        "time_slice/boundary/elongation_lower\n",
        deps=Kind.scalar,
    )
    print(result.output)
    print(result.usage())
