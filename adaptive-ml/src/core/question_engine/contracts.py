from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Protocol


AnswerSource = Literal["local", "model", "web", "fallback"]


class QuestionRoute(Enum):
    LOCAL_ONLY = "local_only"
    MODEL_ONLY = "model_only"
    MODEL_WITH_WEB = "model_with_web"


@dataclass(frozen=True)
class QuestionTurn:
    question: str
    answer: str
    answer_source: AnswerSource


@dataclass(frozen=True)
class TutorSource:
    title: str
    url: str
    domain: str | None = None
    snippet: str | None = None


@dataclass(frozen=True)
class TutorQuestionContext:
    language: str
    subject: str
    domain: str
    topic: str
    problem_id: str
    problem_title: str
    problem_statement: str
    current_step: int
    total_steps: int
    current_prompt: str
    expected_input_type: str
    tutor_metadata: dict[str, Any] = field(
        default_factory=dict,
    )
    recent_question_history: tuple[QuestionTurn, ...] = ()
    session_id: str | None = None
    student_id: str | None = None


@dataclass(frozen=True)
class TutorQuestionRequest:
    question: str


@dataclass(frozen=True)
class TutorModelAnswer:
    text: str
    language: str


@dataclass(frozen=True)
class TutorQuestionResult:
    answer: str
    answer_source: AnswerSource
    sources: tuple[TutorSource, ...] = ()
    used_web: bool = False
    route: QuestionRoute = QuestionRoute.MODEL_ONLY
    metadata: dict[str, Any] = field(
        default_factory=dict,
    )


class TutorModelProvider(Protocol):
    def is_available(self) -> bool:
        ...

    def answer(
        self,
        *,
        question: str,
        context: TutorQuestionContext,
        sources: tuple[TutorSource, ...] = (),
        prompt: str = "",
    ) -> TutorModelAnswer:
        ...


class WebSearchProvider(Protocol):
    def is_available(self) -> bool:
        ...

    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
    ) -> tuple[TutorSource, ...]:
        ...
