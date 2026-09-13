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
    student_id: str = "local_student"


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
    generation_available: bool = False
    supported_difficulties: list[int] = Field(
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
    generated: bool = False
    generation_available: bool = False
    supported_difficulties: list[int] = Field(
        default_factory=list
    )


class ProblemDetail(ProblemSummary):
    problem_text: str
    language: str
    skills: list[str]
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class GenerateProblemRequest(BaseModel):
    subject: str
    domain: str
    topic: str
    difficulty: int = 1
    seed: int | None = None


class AdaptiveRecommendationRequest(BaseModel):
    subject: str | None = None
    domain: str | None = None
    student_id: str = "local_student"


class AdaptiveRecommendationResponse(BaseModel):
    recommendation_available: bool
    reason: str
    subject: str | None = None
    domain: str | None = None
    topic: str | None = None
    topic_name: str | None = None
    difficulty: int | None = None
    mastery: float | None = None
    mastery_key: str | None = None
    generation_available: bool = False
    problem_id: str | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class TopicProgress(BaseModel):
    subject: str
    domain: str
    topic: str
    topic_name: str
    mastery_key: str
    mastery: float
    mastery_label: str
    questions_completed: int
    first_attempt_streak: int
    last_total_attempts: int
    last_incorrect_attempts: int
    last_hints_used: int
    last_first_attempt_success: bool
    last_completed: bool
    generation_available: bool
    supported_difficulties: list[int] = Field(
        default_factory=list
    )
    recommended_difficulty: int | None = None
    problem_id: str | None = None
    recent_session_count: int = 0
    recent_first_attempt_success_rate: float = 0.0
    recent_hint_rate: float = 0.0
    recent_incorrect_rate: float = 0.0
    recent_average_attempts_per_step: float = 0.0
    recent_trend: str = "insufficient_history"
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class StudentProgressResponse(BaseModel):
    student_id: str
    topics: list[TopicProgress]
    recommendation: AdaptiveRecommendationResponse
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )
