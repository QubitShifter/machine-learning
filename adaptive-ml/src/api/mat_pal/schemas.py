from typing import Any, Literal

from pydantic import BaseModel, Field


InputType = Literal[
    "text",
    "number",
    "math",
    "latex",
    "multiple_choice",
    "vector",
    "matrix",
    "units",
]


class StartSessionRequest(BaseModel):
    problem_id: str = Field(
        examples=["grade4_reverse_reasoning_001"]
    )


class AnswerRequest(BaseModel):
    answer: str
    input_type: InputType = "text"
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class SessionResponse(BaseModel):
    session_id: str
    problem_id: str
    status: str
    feedback: str
    current_step: int
    total_steps: int
    completed: bool
    hint_available: bool
    expected_input_type: InputType = "text"
    suggestion: str | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )
