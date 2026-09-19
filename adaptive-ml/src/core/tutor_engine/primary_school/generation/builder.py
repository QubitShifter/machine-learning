from typing import Any

from src.core.tutor_engine.primary_school.problem_types import (
    AnswerFormat,
    PrimarySchoolProblem,
    ProblemType,
    SolutionStep,
    SolutionStepType,
)


INTEGER_INPUT = "number"
INTEGER_FORMAT = AnswerFormat.INTEGER.value


def integer_step(
    *,
    step_number: int,
    skill_id: str,
    expected_answer: int,
    prompt_key: str,
    hint_key: str,
    params: dict[str, Any],
    operation: str | None = None,
    step_type: SolutionStepType = SolutionStepType.CALCULATION,
) -> dict[str, Any]:
    return {
        "step_number": step_number,
        "skill_id": skill_id,
        "expected_answer": expected_answer,
        "prompt_key": prompt_key,
        "hint_key": hint_key,
        "params": params,
        "operation": operation,
        "step_type": step_type.value,
        "input_type": INTEGER_INPUT,
        "answer_format": INTEGER_FORMAT,
    }


def build_problem_from_specs(
    *,
    problem_id: str,
    grade: int,
    topic: str,
    problem_type: ProblemType,
    language: str,
    skills: list[str],
    known: dict[str, Any],
    unknown: dict[str, Any],
    strategy: str,
    final_answer: int,
    step_specs: list[dict[str, Any]],
    metadata: dict[str, Any],
    title: str = "",
    problem_text: str = "",
) -> PrimarySchoolProblem:
    steps = [
        SolutionStep(
            step_number=spec["step_number"],
            skill_id=spec["skill_id"],
            prompt="",
            expected_answer=spec["expected_answer"],
            hint=None,
            operation=spec.get("operation"),
            step_type=SolutionStepType(
                spec.get(
                    "step_type",
                    SolutionStepType.CALCULATION.value,
                )
            ),
            input_type=spec.get("input_type", INTEGER_INPUT),
            answer_format=spec.get(
                "answer_format",
                INTEGER_FORMAT,
            ),
            metadata={
                "prompt_key": spec["prompt_key"],
                "hint_key": spec["hint_key"],
                "params": spec.get("params") or {},
            },
        )
        for spec in step_specs
    ]
    payload = {
        **metadata,
        "generated": True,
        "answer_format": INTEGER_FORMAT,
        "step_specs": step_specs,
    }
    return PrimarySchoolProblem(
        problem_id=problem_id,
        grade=grade,
        topic=topic,
        problem_type=problem_type,
        title=title,
        language=language,
        problem_text=problem_text,
        skills=skills,
        known=known,
        unknown=unknown,
        strategy=strategy,
        solution_steps=steps,
        final_answer=final_answer,
        metadata=payload,
    )
