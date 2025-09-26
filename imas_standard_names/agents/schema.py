from pydantic import BaseModel, Field


class Review(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    message: str = ""
    PASS: float = 0.7

    @property
    def passed(self) -> bool:
        return self.score >= self.PASS

    @property
    def failed(self) -> bool:
        return self.score < self.PASS

    def __str__(self) -> str:
        return f"The review {'passed' if self.passed else 'failed'} with a score of {self.score:.2f}. {self.message}"


class Request(BaseModel):
    query: str = Field(
        ...,
        description="A engineered prompt to generate a new standard name for the IMAS data dictionary",
    )
    num_names: int = Field(3, description="Number of names to generate (1-10).")
    reviews: list[Review] = Field(..., description="Indices of names to regenerate.")


class State(BaseModel):
    query: str = Field(
        ...,
        description="A engineered prompt to generate a new standard name for the IMAS data dictionary",
    )
    num_names: int = Field(3, description="Number of names to generate (1-10).")
    candidates: list[BaseModel] = Field(
        default_factory=list,
        description="List of standard names which are not yet complete or accepted.",
    )
    reviews: list[Review] = Field(..., description="Indices of names to regenerate.")
    history: list[BaseModel] = Field(
        default_factory=list,
        description="List of standard names",
    )


__all__ = ["Review", "State"]
