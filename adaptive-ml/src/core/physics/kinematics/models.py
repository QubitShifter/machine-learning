from dataclasses import dataclass, field
from typing import Literal

from src.core.tutor_engine.contracts import (
    ExpectedInputType,
)


StepKind = Literal[
    "quantity",
    "formula",
    "summary",
]


@dataclass(frozen=True)
class KinematicsQuantities:
    v0: float | None = None
    v: float | None = None
    a: float | None = None
    t: float | None = None
    dx: float | None = None


@dataclass(frozen=True)
class KinematicsStep:
    prompt: str
    hint: str
    kind: StepKind
    input_type: ExpectedInputType = "units"
    quantity: str | None = None
    unit: str | None = None
    formula_id: str | None = None
    expected_text: str | None = None


@dataclass(frozen=True)
class KinematicsProblem:
    problem_id: str
    title: str
    statement: str
    difficulty: int
    quantities: KinematicsQuantities
    steps: tuple[KinematicsStep, ...]
    unknown: str
    metadata: dict = field(default_factory=dict)

    def total_steps(self) -> int:
        return len(self.steps)
