from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchStep(BaseModel):
    """A single step in the research plan."""

    step: int
    sub_query: str
    strategy: str = "hybrid"  # semantic | keyword | hybrid
    rationale: str = ""
    max_retries: int = 3


class ResearchPlan(BaseModel):
    """Structured research plan from query decomposition."""

    original_query: str
    steps: list[ResearchStep] = Field(default_factory=list)

    @classmethod
    def from_decomposition(cls, query: str, sub_queries: list[dict]) -> "ResearchPlan":
        steps = [
            ResearchStep(
                step=sq.get("index", i + 1),
                sub_query=sq.get("question", ""),
                strategy=sq.get("strategy", "hybrid"),
                rationale=sq.get("rationale", ""),
            )
            for i, sq in enumerate(sub_queries)
        ]
        return cls(original_query=query, steps=steps)

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def get_step(self, step_number: int) -> ResearchStep | None:
        for s in self.steps:
            if s.step == step_number:
                return s
        return None
