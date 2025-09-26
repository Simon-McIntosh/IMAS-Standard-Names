import os
from asyncio import run

import dotenv
import logfire as lf
from httpx import AsyncClient
from pydantic_ai import Agent
from pydantic_ai.mcp import (
    MCPServerSSE,
    MCPServerStdio,
    MCPServerStreamableHTTP,
)
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openrouter import OpenRouterProvider
from rich.prompt import IntPrompt, Prompt

from imas_standard_names.agents.load_mcp import load_mcp_servers
from imas_standard_names.agents.schema import Review, State
from imas_standard_names.schema import StandardName  # type: ignore

# from imas_standard_names.schema import StandardName

dotenv.load_dotenv(".env")

lf.configure(token=os.getenv("LOGFIRE_TOKEN"))
lf.instrument_pydantic_ai()

MCP_SERVER_TYPES = MCPServerStdio | MCPServerStreamableHTTP | MCPServerSSE
AI_MODELS = AnthropicModel | OpenAIChatModel
SERVERS = [load_mcp_servers(r".vscode/mcp.json")[-1]]
TOOLS = []

REVIEW_QUERY = "You are an expert in using the IMAS Data Dictionary create a review of the standard name as to how well it fits in to the imas data dictionary. give low scores if similar names exist in the data dictionary, or names are not descriptive. only give scores above 0.7 for names which could be included in the imas data dictionary"


def build_default_model() -> AI_MODELS:
    return OpenAIChatModel(model_name="openai/gpt-5", provider=OpenRouterProvider())


# ===============
#  Define Agents
# ===============
request_agent = Agent[None, State](
    model=build_default_model(), output_type=State, toolsets=SERVERS
)
# standard_name_agent = Agent[
#     tuple[list[StandardName], StandardName | None, Review | None], StandardName
# ](
#     model=build_default_model(),
#     output_type=StandardName,  # type: ignore
#     toolsets=SERVERS,
# )  # type: ignore

ai_review_agent = Agent[StandardName, Review](
    model=build_default_model(), output_type=Review
)  # type: ignore
standard_name_agent = Agent[
    tuple[list[StandardName], StandardName | None, Review | None], StandardName
](
    model=build_default_model(),
    output_type=StandardName,  # type: ignore
    toolsets=SERVERS,
)  # type: ignore

ai_review_agent = Agent[StandardName, Review](
    model=build_default_model(), output_type=Review, toolsets=SERVERS
)  # type: ignore


async def main():
    print("IMAS Standard Name Generator")
    query: str = Prompt.ask(
        ">",
        default="Using your knowledge of the IMAS data dictionary search for current names relating to poloidal flux and generate a new name to add to the data dictionary, limit searches to a maximum of 5 results",
    )
    num_names: int = IntPrompt.ask("Enter number of names to generate", default=1)

    history: list[StandardName] = []
    # generate initial candidates (sequential async awaits)
    candidate_results = [
        await standard_name_agent.run(query, deps=(history, None, None))
        for _ in range(num_names)
    ]
    candidates: list[StandardName] = [r.output for r in candidate_results]
    print(candidates[0])

    review_results = [
        await ai_review_agent.run(REVIEW_QUERY, deps=c) for c in candidates
    ]
    reviews: list[Review] = [r.output for r in review_results]
    print("Starting candidates:")
    while reviews:
        for c, r in zip(candidates, reviews, strict=False):
            print(f"- {c.name}: {type(c)} scored at {r.score:.2f}")
            print(c)
        history += [
            c.model_copy()
            for c, r in zip(candidates, reviews, strict=False)
            if r.passed
        ]

        improved_results = [
            await standard_name_agent.run(query, deps=(history, name, review))
            for name, review in zip(candidates, reviews, strict=False)
            if not review.passed
        ]
        candidates = [r.output for r in improved_results]

        review_results = [
            await ai_review_agent.run(REVIEW_QUERY, deps=c) for c in candidates
        ]
        reviews = [r.output for r in review_results]


if __name__ == "__main__":
    run(main())
