from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchStep(BaseModel):
    """A single step in the research plan."""

    step: int
    sub_query: str
    strategy: str = "hybrid"  # semantic | keyword | hybrid
    rationale: str = ""
    max_retries: int = 3
    hop: int = 1
    depends_on: list[int] = Field(default_factory=list)
    input_slots: list[str] = Field(default_factory=list)
    terminal: bool = False


class ResearchPlan(BaseModel):
    """Structured research plan from query decomposition."""

    original_query: str
    steps: list[ResearchStep] = Field(default_factory=list)

    @classmethod
    def from_decomposition(cls, query: str, sub_queries: list[dict]) -> "ResearchPlan":
        steps = [
            _step_from_sub_query(i, sq)
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


def _step_from_sub_query(index: int, sub_query: dict) -> ResearchStep:
    """Normalize planner output while keeping old planner responses valid."""
    step_number = int(sub_query.get("index", index + 1))
    hop = max(1, int(sub_query.get("hop", 1)))
    depends_on = [
        int(dep)
        for dep in sub_query.get("depends_on", [])
        if str(dep).isdigit() and int(dep) != step_number
    ]
    # A planner can express a sequential hop with hop=2 without explicitly
    # repeating the previous step in depends_on.
    if hop > 1 and not depends_on and step_number > 1:
        depends_on = [step_number - 1]

    return ResearchStep(
        step=step_number,
        sub_query=sub_query.get("question", ""),
        strategy=sub_query.get("strategy", "hybrid"),
        rationale=sub_query.get("rationale", ""),
        max_retries=int(sub_query.get("max_retries", 3)),
        hop=hop,
        depends_on=depends_on,
        input_slots=[str(slot) for slot in sub_query.get("input_slots", [])],
        terminal=bool(sub_query.get("terminal", False)),
    )
