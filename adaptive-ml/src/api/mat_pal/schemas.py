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
    problem_title: str
    problem_statement: str
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


class CatalogTopic(BaseModel):
    id: str
    name: str
    available_problem_count: int
    problem_ids: list[str] = Field(
        default_factory=list
    )


class CatalogDomain(BaseModel):
    id: str
    name: str
    available_problem_count: int
    topics: list[CatalogTopic] = Field(
        default_factory=list
    )


class CatalogSubject(BaseModel):
    id: str
    name: str
    available_problem_count: int
    domains: list[CatalogDomain] = Field(
        default_factory=list
    )


class CatalogResponse(BaseModel):
    subjects: list[CatalogSubject]


class ProblemSummary(BaseModel):
    problem_id: str
    title: str
    subject: str
    domain: str
    topic: str
    problem_type: str
    available: bool = True
    grade: int | None = None
    total_steps: int
    expected_input_type: InputType = "text"


class ProblemDetail(ProblemSummary):
    problem_text: str
    language: str
    skills: list[str]
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )
