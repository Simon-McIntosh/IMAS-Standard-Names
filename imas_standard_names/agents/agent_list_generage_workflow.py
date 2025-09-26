import json
import os
from asyncio import run
from pathlib import Path

import dotenv
import logfire as lf
from pydantic_ai import Agent
from pydantic_ai.mcp import (
    MCPServerSSE,
    MCPServerStdio,
    MCPServerStreamableHTTP,
)
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from rich.prompt import Prompt

from imas_standard_names.agents.load_mcp import load_mcp_servers
from imas_standard_names.agents.schema import Review
from imas_standard_names.schema import StandardName  # type: ignore

# from imas_standard_names.schema import StandardName

dotenv.load_dotenv(".env")

lf.configure(token=os.getenv("LOGFIRE_TOKEN"))
lf.instrument_pydantic_ai()

MCP_SERVER_TYPES = MCPServerStdio | MCPServerStreamableHTTP | MCPServerSSE
AI_MODELS = AnthropicModel | OpenAIChatModel
SERVERS = [load_mcp_servers(r".vscode/mcp.json")[-1]]
TOOLS = []


def build_default_model() -> AI_MODELS:
    return OpenAIChatModel(model_name="openai/gpt-5", provider=OpenRouterProvider())


# ===============
#  Define Agents
# ===============

_generate_md = (
    Path(__file__).resolve().parent.parent.parent
    / ".github"
    / "prompts"
    / "workflows"
    / "list_generate_workflow"
    / "generate.md"
)
GENERATE_SYSTEM_PROMPT: str = _generate_md.read_text(encoding="utf-8")


_review_md = (
    Path(__file__).resolve().parent.parent.parent
    / ".github"
    / "prompts"
    / "workflows"
    / "list_generate_workflow"
    / "review.md"
)
REVIEW_SYSTEM_PROMPT: str = _review_md.read_text(encoding="utf-8")


_human_md = (
    Path(__file__).resolve().parent.parent.parent
    / ".github"
    / "prompts"
    / "workflows"
    / "list_generate_workflow"
    / "human.md"
)
HUMAN_SYSTEM_PROMPT: str = _human_md.read_text(encoding="utf-8")


request_agent = Agent[None, list[Review]](
    model=build_default_model(),
    output_type=list[Review],
    system_prompt=HUMAN_SYSTEM_PROMPT,
)

standard_name_agent = Agent[None, list[StandardName]](
    model=build_default_model(),
    output_type=list[StandardName],  # type: ignore
    toolsets=SERVERS,
    system_prompt=GENERATE_SYSTEM_PROMPT,
)

ai_review_agent = Agent[None, list[Review]](
    model=build_default_model(),
    output_type=list[Review],
    toolsets=SERVERS,
    system_prompt=REVIEW_SYSTEM_PROMPT,
)  # type: ignore


def build_regenerate_query(reviews: list[tuple[StandardName | None, Review]]) -> str:
    return (
        "The following reviews were generated for failing standard names, consider the following reviews"
        + "\n".join(
            "\n Was reviewed with \n".join([str(c), str(r)]) for c, r in reviews
        )
        + f"\n\n Generate a new list of {len(reviews)} standard names which adress the issues raised in the reviews."
    )


def build_review_query(candidates: list[StandardName]) -> str:
    return (
        "The following standard names were generated, provide a review for each name\n"
        + "\n".join(str(c) for c in candidates)
    )


def build_human_review_query(query, names: list[StandardName]) -> str:
    return (
        f"The user provided the feedback: '{query}' for the following standard names (in order): "
        + "\n".join(str(c) for c in names)
        + f"\n Create an engeneered prompt as a review for each of the {len(names)} names, to capture user sentiment of the name. Score above 0.7 if the user approves the name"
    )


async def main():
    print("IMAS Standard Name Generator")

    query = Prompt.ask(
        ">", default="generate a list of 3 standard scalar names for poloidal flux"
    )

    review_output = await request_agent.run(query)
    reviews: list[Review] = review_output.output

    num_names = len(reviews)

    print(f"Initial reviews for {num_names}:")
    for r in reviews:
        print(f"- scored at {r.score:.2f}")
        print(r.message)
        print()

    accepted: list[StandardName] = []
    candidates: list[StandardName] = []

    pairs: list[tuple[StandardName | None, Review]] = list(
        zip([None] * num_names, reviews, strict=True)
    )

    retries = 0
    MAX_RETRIES = 5
    while len(accepted) < num_names and retries < MAX_RETRIES:
        ai_accepted = []
        while (pairs != []) and retries < MAX_RETRIES:
            candidates_output = await standard_name_agent.run(
                build_regenerate_query(pairs)
            )
            candidates = candidates_output.output
            reviews_output = await ai_review_agent.run(build_review_query(candidates))

            pairs = list(zip(candidates, reviews_output.output, strict=True))
            ai_accepted += [
                c.model_copy() for c, r in pairs if r.passed and c is not None
            ]
            pairs = [p for p in pairs if p[1].failed]
            retries += 1

            print(f"Candidates after retry {retries}:")
            for c, r in pairs:
                print(f"- {c.name if c else 'NONE'}: scored at {r.score:.2f}")
        print(f"Candidates after retry {retries}:")
        for c in ai_accepted:
            print(f"- {c.name}")

        query = Prompt.ask(">")
        review_output = await request_agent.run(
            build_human_review_query(query, ai_accepted)
        )
        pairs = list(zip(ai_accepted, review_output.output, strict=True))
        accepted += [c.model_copy() for c, r in pairs if r.passed and c is not None]
        pairs = [p for p in pairs if p[1].failed]

        print("Human reviews")
        print("--------------")
        for c, r in pairs:
            print(f"- {c.name if c is not None else 'None'}: scored at {r.score:.2f}")
    print(f"Accepted {len(accepted)} names:")
    for c in accepted:
        print(f"- {c.name}: {type(c)}")
        print(c)
    print("--------------")


if __name__ == "__main__":
    run(main())
