from __future__ import annotations
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from pydantic_graph import BaseNode, Graph, GraphRunContext, End

from imas_standard_names.workflow.imas_connect import IMASConnect

# =============================
# Core Data Models (simplified)
# =============================

class GenerationRequest(BaseModel):
    """User (human) instruction for a generation cycle.

    Captures what concept to generate standard names for, how many names,
    and optional additional context.
    """

    concept: str = Field(default="", description="Concept or physical quantity focus")
    context: str = Field(default="", description="Additional explanatory context / constraints")
    num_names: int = Field(default=5, description="Number of standard names to generate")


class Review(BaseModel):
    """Automated evaluation of a candidate standard name."""

    score: float = Field(ge=0.0, le=1.0)
    message: str | None = None

    PASS_THRESHOLD: float = 0.72

    @property
    def passed(self) -> bool:
        return self.score >= self.PASS_THRESHOLD


class StandardName(BaseModel):
    """A generated or approved IMAS standard name candidate."""

    name: str = Field(default = "", description="The proposed IMAS standard name")
    description: str = Field(default = "", description="A description of the standard name")
    attempt: int = 0
    review: Review | None = None

    MAX_ATTEMPTS: int = 2

    @property
    def passed(self)-> bool:
        return self.review is not None and self.review.passed

    @property
    def final(self) -> bool:
        return self.passed or (self.attempt >= self.MAX_ATTEMPTS)



class State(BaseModel):
    """Mutable graph state for the interactive flow."""

    request: GenerationRequest | None = Field(default=None, description="User generation request")
    candidates: list[StandardName] = Field(default_factory=list, description="Current candidate standard names")
    rejections: list[StandardName] = Field(default_factory=list, description="History of rejected standard names, by user or AI")

    @property
    def done(self) -> bool:
        return bool(self.candidates) and all(c.final for c in self.candidates)

# =============================
# LLM Connections (centralized)
# =============================

try:
    with open(".github/prompts/standard-name-generator.prompt.md", "r", encoding="utf-8") as f:
        GENERATOR_SYSTEM_PROMPT = f.read().strip()
except FileNotFoundError:
    GENERATOR_SYSTEM_PROMPT = "You generate candidate IMAS standard names. Use the IMAS data dictionary MCP to check for reference standard names which are approved - while limiting the search result number to avoid a rate limit of 10000 tokens per minute. "

try:
    with open(".github/prompts/standard-name-ai-reviewer.prompt.md", "r", encoding="utf-8") as f:
        AI_REVIEWER_SYSTEM_PROMPT = f.read().strip()
except FileNotFoundError:
    AI_REVIEWER_SYSTEM_PROMPT = "You are an autonomous review agent for proposed IMAS standard names, scoring them on a scale of 0.0 to 1.0, where 1.0 indicates full approval and 0.0 indicates complete rejection, approval of the name begins at 0.7. You consider factors such as relevance to the concept, clarity, adherence to IMAS naming conventions, and avoidance of ambiguity or overlap with existing standard names. Use the MCP server to search the IMAS data dictionary - while limiting the search result number to avoid a rate limit of 10000 tokens per minute - which should be used as a reference for scoring above 0.7. After scoring, provide a prompt for an LLM to improve the standard name."

try:
    with open(".github/prompts/standard-name-human-request.prompt.md", "r", encoding="utf-8") as f:
        HUMAN_REQUEST_SYSTEM_PROMPT = f.read().strip()
except FileNotFoundError:
    HUMAN_REQUEST_SYSTEM_PROMPT = "You parse user instructions and obtain clarifications as needed on the concept for which standard names are being generated, the amount of standard names to generate and any additional context or constraints."

try:
    with open(".github/prompts/standard-name-human-reviewer.prompt.md", "r", encoding="utf-8") as f:
        HUMAN_REVIEWER_SYSTEM_PROMPT = f.read().strip()
except FileNotFoundError:
    HUMAN_REVIEWER_SYSTEM_PROMPT = "You parse user instructions to extract the review pertaining to each standard name. You score the feedback on a scale of 0.0 to 1.0, where 1.0 indicates full approval and 0.0 indicates complete rejection, approval of the name begins at 0.7. Closely inspect the human input to not assign passing scores when the user asks for regeneration. Using the user provided feedback write a prompt for an LLM to improve the standard_name to include in the feedback message."


generate_connect = IMASConnect(
    host="http://127.0.0.1", 
    port=8080, 
    system_prompt=GENERATOR_SYSTEM_PROMPT,
    output_type=StandardName
    )
ai_review_connect = IMASConnect(
    host="http://127.0.0.1", 
    port=8080, 
    system_prompt=AI_REVIEWER_SYSTEM_PROMPT,
    output_type=Review
    )
human_review_connect = IMASConnect(
    host="http://127.0.0.1", 
    port=8080, 
    system_prompt=HUMAN_REVIEWER_SYSTEM_PROMPT,
    output_type=Review
    )

request_connect = IMASConnect(
    host="http://127.0.0.1", 
    port=8080, 
    system_prompt=HUMAN_REQUEST_SYSTEM_PROMPT,
    output_type=GenerationRequest
    )

# =============================
# Graph Nodes
# =============================

@dataclass
class GenerateNames(BaseNode[State]):
    async def run(self, ctx: GraphRunContext[State]) -> AIReview:
        if ctx.state.request and ctx.state.request.num_names != len(ctx.state.candidates):
            existing = ctx.state.candidates
            desired = ctx.state.request.num_names
            ctx.state.candidates = [existing[i] if i < len(existing) else StandardName() for i in range(desired)]

        for idx, c in enumerate(ctx.state.candidates):
            if c.passed:
                continue
            ctx.state.rejections.append(c.model_copy())
            prompt = (
                f"Iterate on the proposed IMAS standard name {c} for the request {ctx.state.request}. "
                f"Current candidate names are {','.join([c.name for c in ctx.state.candidates])}."
                f"Previous names which were not acceptable were: {', '.join(r.name for r in ctx.state.rejections if r.name)}"
                f"Generate a new candidate name while avoiding previous rejections and names already proposed."
            )
            result = await generate_connect.run(prompt)
            generated = result.output
            generated.attempt = c.attempt + 1
            generated.review = None
            ctx.state.candidates[idx] = generated
        return AIReview()

@dataclass
class AIReview(BaseNode[State]):
    async def run(self, ctx: GraphRunContext[State]) -> GenerateNames | HumanReview:
        for c in ctx.state.candidates:
            if c.passed:
                continue
            result =  await ai_review_connect.run(
                f"Review the proposed IMAS standard name '{c}' for the request {ctx.state.request}. The current candidate names are {",".join([c.name for c in ctx.state.candidates])}"
            )
            c.review = result.output
        if not ctx.state.done:
            print("\n=== AI Review rejects ===")
            for c in ctx.state.candidates:
                if not c.passed:
                    print(f" - {c.name}:\t {c.review.score:.2f}")
            return GenerateNames()
        return HumanReview()

@dataclass
class HumanReview(BaseNode[State]):
    async def run(self, ctx: GraphRunContext[State]) -> GenerateNames | HumanReview | Finalize:
        query = ""
        if ctx.state.request is None:
            print("\n=== IMAS Standard Name Generator ===")
            print("Enter instruction (e.g. 'Generate 3 names for poloidal flux, avoid existing: poloidal_flux').")
            while not query:
                query = input("> ").strip()
            result = await request_connect.run(query)
            ctx.state.request = result.output
            return GenerateNames()
        print("Provide feedback / approvals (press Enter to continue generation). Current candidates are:")
        for c in ctx.state.candidates:
            score_display = f"{c.review.score:.2f}" if c.review else "--"
            print(f" - {c.name or '<empty>'}:\t {score_display}")
        query = input("> ").strip()
        if query:
            for i, c in enumerate(ctx.state.candidates):
                result = await human_review_connect.run(
                    f"Capture the human review feedback '{query}' for the standard name '{c}' (index {i})."
                )
                ctx.state.candidates[i].review = result.output.model_copy()
                ctx.state.candidates[i].attempt = 0

        if ctx.state.done:
            print("All names approved, no further generation needed.")
            return Finalize()
        return GenerateNames()
@dataclass
class Finalize(BaseNode[State]):
    async def run(self, ctx: GraphRunContext[State]) -> End:
        print("\n=== Final Approved Standard Names ===")
        approved = [c for c in ctx.state.candidates if c.passed]
        if not approved:
            print("No approved standard names.")
        else:
            for c in approved:
                print(f" - {c.name}: {c.description or 'No description provided.'}")
        return End(approved)


# =============================
# Graph Definition & Runner
# =============================

standard_name_graph = Graph(
    nodes=(HumanReview, GenerateNames, AIReview, Finalize),
    state_type=State,
)


async def run_standard_name_flow(concept: str = "", context: str = "", existing: list[str] | None = None) -> list[str]:
    """Run interactive generation & review loop.

    If concept omitted, user will be prompted. Returns list of approved names.
    """
    existing = existing or []
    state = State()
    await standard_name_graph.run(HumanReview(), state=state)
    # Collect approved names from final state
    return [c.name for c in state.candidates if c.passed]


def main():  # pragma: no cover
    import asyncio
    final = asyncio.run(run_standard_name_flow())


if __name__ == "__main__":  # pragma: no cover
    main()
