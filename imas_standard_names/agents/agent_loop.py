from typing import Optional, Tuple, List, Union, Any

from rich.prompt import Prompt, IntPrompt
from httpx import AsyncClient
import ssl
import dotenv
from asyncio import run

from imas_standard_names.schema import StandardName  # type: ignore


from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio, MCPServerStreamableHTTP, MCPServerSSE, load_mcp_servers
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel

import logfire as lf
import os



# from imas_standard_names.schema import StandardName

dotenv.load_dotenv(".env")

context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE


client = AsyncClient(verify=context)
lf.configure(token=os.getenv("LOGFIRE_TOKEN"))
lf.instrument_httpx(client=client)
lf.instrument_pydantic_ai()

MCP_SERVER_TYPES = Union[MCPServerStdio | MCPServerStreamableHTTP | MCPServerSSE]
AI_MODELS = Union[AnthropicModel | OpenAIChatModel]
SERVERS = load_mcp_servers(r"imas_standard_names\\agents\\mcp_config.json")
TOOLS = []

REVIEW_QUERY = "You are an expert in using the IMAS Data Dictionary create a review of the standard name as to how well it fits in to the imas data dictionary. give low scores if similar names exist in the data dictionary, or names are not descriptive. only give scores above 0.7 for names which could be included in the imas data dictionary"


from typing import Callable, Awaitable

def build_default_model() -> AnthropicModel:
    return AnthropicModel(
        model_name="claude-3-haiku-20240307",
        provider=AnthropicProvider(http_client=AsyncClient(verify=False)),
    )


# =========================
#  Define Agent structures
# =========================
class Review(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    message: str = ""
    PASS: float = 0.7

    @property
    def passed(self) -> bool:
        return self.score >= self.PASS
    

async def main():
    print("IMAS Standard Name Generator")
    query:str = Prompt.ask(">", default="Using your knowledge of the IMAS data dictionary search for current names relating to poloidal flux and generate a new name to add to the data dictionary, limit searches to a maximum of 5 results")
    num_names:int = IntPrompt.ask("Enter number of names to generate", default=1)

    standard_name_agent = Agent[Tuple[List[StandardName],Optional[StandardName],Optional[Review]],StandardName](
        model=build_default_model(),
        output_type=StandardName, #type: ignore
        ) # type: ignore

    ai_review_agent = Agent[StandardName,Review](
        model=build_default_model(),
        output_type=Review,
        ) # type: ignore

    history:List[StandardName] = []
    # generate initial candidates (sequential async awaits)
    candidate_results = [await standard_name_agent.run(query, deps=(history, None, None)) for _ in range(num_names)]
    candidates:List[StandardName] = [r.output for r in candidate_results]
    
    review_results = [await ai_review_agent.run(REVIEW_QUERY, deps=c) for c in candidates]
    reviews:List[Review] = [r.output for r in review_results]
    print("Starting candidates:")
    while reviews:
        for c,r in zip(candidates,reviews):
            print(f"- {c.name}: {type(c)} scored at {r.score:.2f}")
            print(c)        
        history += [c.model_copy() for c,r in zip(candidates,reviews) if r.passed]
        
        improved_results = [await standard_name_agent.run(query, deps=(history, name, review)) for name, review in zip(candidates,reviews) if not review.passed]
        candidates = [r.output for r in improved_results]
        
        review_results = [await ai_review_agent.run(REVIEW_QUERY, deps=c) for c in candidates]
        reviews = [r.output for r in review_results]

        


if __name__ == "__main__":
    run(main())


