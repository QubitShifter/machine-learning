from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProblemType(Enum):
    """
    Supported primary-school problem families.

    More types can be added later without changing
    the generic tutor architecture.
    """

    REVERSE_REASONING = "reverse_reasoning"
    NUMBER_PATTERN = "number_pattern"
    OPERATION_CHAIN = "operation_chain"
    ARITHMETIC = "arithmetic"
    UNKNOWN_NUMBER = "unknown_number"
    FRACTION = "fraction"
    GEOMETRY = "geometry"
    WORD_PROBLEM = "word_problem"


class AnswerFormat(Enum):
    """
    How a step answer is graded.

    Independent of the mathematical family.
    """

    LEGACY_NUMERIC = "legacy_numeric"
    INTEGER = "integer"


class SolutionStepType(Enum):
    """
    General categories of tutoring steps.
    """

    IDENTIFY_KNOWN = "identify_known"
    IDENTIFY_UNKNOWN = "identify_unknown"
    CHOOSE_STRATEGY = "choose_strategy"
    CALCULATION = "calculation"
    REASONING = "reasoning"
    VERIFY = "verify"


@dataclass
class SolutionStep:
    """
    One teachable step in a problem solution.
    """

    step_number: int
    skill_id: str
    prompt: str
    expected_answer: Any

    hint: str | None = None
    operation: str | None = None

    step_type: SolutionStepType = (
        SolutionStepType.CALCULATION
    )

    input_type: str | None = None
    answer_format: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class PrimarySchoolProblem:
    """
    Standard representation of a primary-school
    mathematics problem.

    Different solvers should convert their problems
    into this common representation.
    """

    problem_id: str
    grade: int
    topic: str
    problem_type: ProblemType
    title: str
    language: str
    problem_text: str

    skills: list[str]

    known: dict[str, Any]
    unknown: dict[str, Any]

    strategy: str

    solution_steps: list[SolutionStep]

    final_answer: Any

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def get_step(
        self,
        step_number: int,
    ) -> SolutionStep | None:
        """
        Return a solution step by its step number.
        """

        for step in self.solution_steps:
            if step.step_number == step_number:
                return step

        return None

    def get_number_of_steps(
        self,
    ) -> int:
        """
        Return the total number of tutoring steps.
        """

        return len(
            self.solution_steps
        )

    def get_skill_ids(
        self,
    ) -> list[str]:
        """
        Return all skills associated with the problem.
        """

        return list(
            self.skills
        )