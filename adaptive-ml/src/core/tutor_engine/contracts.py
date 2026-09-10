from dataclasses import dataclass, field
from typing import Any, Literal


ExpectedInputType = Literal[
    "text",
    "number",
    "math",
    "latex",
    "multiple_choice",
    "vector",
    "matrix",
    "units",
]


@dataclass
class StudentSubmission:
    """
    A student's submission to the tutor.

    The same structure can later be used by:
    - primary-school math
    - calculus
    - ODEs
    - linear algebra
    - physics
    - the web frontend
    """

    answer: str

    input_type: ExpectedInputType = "text"

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class EvaluationResult:
    """
    Result of evaluating one student submission.
    """

    correct: bool

    status: str

    feedback: str

    error_type: str | None = None

    suggestion: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class TutorResponse:
    """
    Standard response returned by a MAT-PAL tutor engine.

    Frontends should be able to render this without
    needing to know which mathematical subject produced it.
    """

    status: str

    feedback: str

    current_step: int

    total_steps: int

    completed: bool

    hint_available: bool = False

    suggestion: str | None = None

    expected_input_type: ExpectedInputType = "text"

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class SessionState:
    """
    Generic state that can be exposed through the MAT-PAL API.
    """

    session_id: str

    subject: str

    topic: str

    problem_id: str

    current_step: int

    total_steps: int

    completed: bool

    attempts: int = 0

    hints_used: int = 0

    mastery: float | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )