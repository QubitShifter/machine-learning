import json
from pathlib import Path

from src.core.tutor_engine.primary_school.problem_types import (
    PrimarySchoolProblem,
    ProblemType,
    SolutionStep,
    SolutionStepType,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[4]


DEFAULT_PROBLEM_FILE = (
    PROJECT_ROOT
    / "math"
    / "primary-school"
    / "grade4"
    / "word_problems"
    / "reverse_reasoning.json"
)


def infer_step_type(
    step_data: dict,
) -> SolutionStepType:
    """
    Infer a general tutoring step type from the skill id.
    """

    skill_id = step_data.get(
        "skill",
        "",
    )

    if "identify_known" in skill_id:
        return SolutionStepType.IDENTIFY_KNOWN

    if "identify_unknown" in skill_id:
        return SolutionStepType.IDENTIFY_UNKNOWN

    if "reverse_" in skill_id:
        return SolutionStepType.CALCULATION

    return SolutionStepType.REASONING


def build_solution_step(
    step_data: dict,
) -> SolutionStep:
    """
    Convert one JSON solution-step dictionary into
    a SolutionStep object.
    """

    return SolutionStep(
        step_number=step_data["step"],
        skill_id=step_data["skill"],
        prompt=step_data["prompt"],
        expected_answer=step_data[
            "expected_answer"
        ],
        hint=step_data.get(
            "hint"
        ),
        operation=step_data.get(
            "operation"
        ),
        step_type=infer_step_type(
            step_data
        ),
    )


def build_problem(
    problem_data: dict,
) -> PrimarySchoolProblem:
    """
    Convert one raw problem dictionary into a
    PrimarySchoolProblem object.
    """

    solution_steps = [
        build_solution_step(
            step_data
        )
        for step_data in problem_data[
            "solution_steps"
        ]
    ]

    return PrimarySchoolProblem(
        problem_id=problem_data["id"],
        grade=problem_data["grade"],
        topic=problem_data["topic"],
        problem_type=ProblemType(
            problem_data["problem_type"]
        ),
        title=problem_data["title"],
        language=problem_data["language"],
        problem_text=problem_data[
            "problem_text"
        ],
        skills=problem_data["skills"],
        known=problem_data["known"],
        unknown=problem_data["unknown"],
        strategy=problem_data["strategy"],
        solution_steps=solution_steps,
        final_answer=problem_data[
            "final_answer"
        ],
    )


def load_reverse_reasoning_problems(
    file_path: Path | None = None,
) -> list[PrimarySchoolProblem]:
    """
    Load all reverse-reasoning problems from JSON.
    """

    if file_path is None:
        file_path = DEFAULT_PROBLEM_FILE

    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(
            file
        )

    raw_problems = data.get(
        "problems",
        [],
    )

    return [
        build_problem(
            problem_data
        )
        for problem_data in raw_problems
    ]


def load_reverse_reasoning_problem(
    problem_id: str,
    file_path: Path | None = None,
) -> PrimarySchoolProblem:
    """
    Load one reverse-reasoning problem by id.
    """

    problems = (
        load_reverse_reasoning_problems(
            file_path=file_path
        )
    )

    for problem in problems:
        if problem.problem_id == problem_id:
            return problem

    raise ValueError(
        f"Problem not found: {problem_id}"
    )