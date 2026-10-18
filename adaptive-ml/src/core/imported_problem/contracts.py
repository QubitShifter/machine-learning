from dataclasses import dataclass
from typing import Protocol


PLAN_SCHEMA_ID = "matpal.imported_problem_plan.v1"
SUPPORTED_TOPICS = (
    "arithmetic",
    "unknown_numbers",
    "story_problems",
)
UNSUPPORTED_REASON = "unsupported_problem_type"


@dataclass(frozen=True)
class ConfirmedProblem:
    transcription: str
    language: str
    latex_expressions: tuple[str, ...] = ()
    topic_hint: str | None = None
    problem_type_hint: str | None = None


@dataclass(frozen=True)
class PlannedStep:
    instruction: str
    expected_answer: int
    hints: tuple[str, ...]
    result_latex: str | None = None


@dataclass(frozen=True)
class StructuredSolutionPlan:
    supported: bool
    normalized_topic: str
    title: str
    statement: str
    final_answer: int | None
    steps: tuple[PlannedStep, ...]
    unsupported_reason: str | None = None


class ImportedProblemPlanner(Protocol):
    def is_available(self) -> bool:
        ...

    def plan(
        self,
        confirmed: ConfirmedProblem,
    ) -> StructuredSolutionPlan:
        ...
