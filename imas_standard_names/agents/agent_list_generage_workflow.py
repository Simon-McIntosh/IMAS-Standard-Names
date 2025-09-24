import os
from asyncio import run

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
# standard_name_agent = Agent[
#     tuple[list[StandardName], StandardName | None, Review | None], StandardName
# ](
#     model=build_default_model(),
#     output_type=StandardName,  # type: ignore
#     toolsets=SERVERS,
# )  # type: ignore

# ai_review_agent = Agent[None, list[Review]](
#     model=build_default_model(), output_type=list[Review], toolsets=SERVERS
# )  # type: ignore

GENERATE_SYSTEM_PROMPT = """"
You are an expert in using the IMAS Data Dictionary and tasked to create new standard names
for the IMAS data dictionary. The names must be descriptive, and follow the IMAS naming conventions,
and being unique in their description of the data they represent - so as to not to be confused
with existing names in the data dictionary. For derived quantities make certain you are
generating the correct standard names for underlying scalar quantities so that the derived validations
can pass.
"""

REVIEW_SYSTEM_PROMPT = """
You are an expert in using the IMAS Data Dictionary tasked to identify how well a standard name
fits into the IMAS data dictionary. You will be provided with a standard name, including its description,
and ared tasked to provide a score between 0 and 1, with scores above 0.7 being names which could be included.

Score on metrics such as:
- How well the name fits into the existing naming conventions
- How descriptive the name is
- How unique the name is compared to existing names in the data dictionary
"""

HUMAN_SYSTEM_PROMPT = """
You are a helpful assistant that helps users in generating standard names for the IMAS data dictionary.
You will be provided with user input and are tasked on extracting key information to help generate
a prompt to pass to an AI agent tasked to generate standard names.

On the first interaction, you are to extract how many names the user wants to generate and
generate a prompt as well as a review scoring 0 for each name to be generated.

On subsequent interactions, the user has been provided with a list of standard names which have been
generated, and will either accept the names, in which case you are to provide a Reivew with a score of 1
for the accepted names. For names which the user has rejected, extract the user's sentiment towards
the name to generate a score, and generate a prompt to guide the generation agent 
to generate a better name.
"""
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


async def main():
    print("IMAS Standard Name Generator")

    query = Prompt.ask(">")

    review_output = await request_agent.run(query)
    reviews: list[Review] = review_output.output

    num_names = len(reviews)

    accepted: list[StandardName] = []
    candidates: list[StandardName] = []

    retries = 0
    MAX_RETRIES = 5
    while len(accepted) < num_names and retries < MAX_RETRIES:
        while any(r.failed for r in reviews) and retries < MAX_RETRIES:
            candidates_output = await standard_name_agent.run(
                build_regenerate_query(
                    list(
                        zip(
                            candidates if candidates else [None] * num_names,
                            reviews,
                            strict=True,
                        )
                    )
                )
            )
            candidates = candidates_output.output
            reviews_output = await ai_review_agent.run(build_review_query(candidates))
            reviews = reviews_output.output

            accepted += [
                c.model_copy()
                for c, r in zip(candidates, reviews, strict=True)
                if r.passed
            ]
            reviews = [r for r in reviews if r.failed]
            candidates = [
                c for c, r in zip(candidates, reviews, strict=True) if r.failed
            ]

            retries += 1
            print(f"Candidates after retry {retries}:")
            for c, r in zip(candidates, reviews, strict=True):
                print(f"- {c.name}: scored at {r.score:.2f}")
        query = Prompt.ask(">")
        review_output = await request_agent.run(query)
        reviews: list[Review] = review_output.output


if __name__ == "__main__":
    run(main())
