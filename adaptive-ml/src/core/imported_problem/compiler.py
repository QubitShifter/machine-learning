from src.core.i18n.locale import normalize_locale
from src.core.imported_problem.contracts import (
    ConfirmedProblem,
    StructuredSolutionPlan,
    SUPPORTED_TOPICS,
)
from src.core.imported_problem.errors import (
    ImportedProblemCompileError,
    UnsupportedImportedProblem,
)
from src.core.tutor_engine.primary_school.problem_types import (
    AnswerFormat,
    PrimarySchoolProblem,
    ProblemType,
    SolutionStep,
    SolutionStepType,
)


TOPIC_META = {
    "arithmetic": (
        "Arithmetic",
        ProblemType.ARITHMETIC,
        "evaluate_expression",
    ),
    "unknown_numbers": (
        "Unknown Numbers",
        ProblemType.UNKNOWN_NUMBER,
        "inverse_operation",
    ),
    "story_problems": (
        "Story Problems",
        ProblemType.WORD_PROBLEM,
        "dependent_calculations",
    ),
}
DEFAULT_TITLES = {
    "arithmetic": {
        "en": "Arithmetic problem",
        "bg": "Аритметична задача",
    },
    "unknown_numbers": {
        "en": "Unknown number",
        "bg": "Неизвестно число",
    },
    "story_problems": {
        "en": "Story problem",
        "bg": "Текстова задача",
    },
}


def compile_imported_problem(
    confirmed: ConfirmedProblem,
    plan: StructuredSolutionPlan,
) -> PrimarySchoolProblem:
    if (
        not plan.supported
        or plan.normalized_topic not in SUPPORTED_TOPICS
    ):
        raise UnsupportedImportedProblem(
            "unsupported_problem_type"
        )

    transcription = confirmed.transcription.strip()
    if not transcription:
        raise ImportedProblemCompileError(
            "Confirmed transcription is empty."
        )
    if not plan.steps or plan.final_answer is None:
        raise ImportedProblemCompileError(
            "Solution plan is incomplete."
        )
    if plan.steps[-1].expected_answer != plan.final_answer:
        raise ImportedProblemCompileError(
            "Last step must match the final answer."
        )

    locale = resolve_imported_language(confirmed.language)
    topic_name, problem_type, strategy = TOPIC_META[
        plan.normalized_topic
    ]
    title = plan.title.strip() or DEFAULT_TITLES[
        plan.normalized_topic
    ][locale]
    steps = [
        SolutionStep(
            step_number=index,
            skill_id=f"imported_{plan.normalized_topic}",
            prompt=step.instruction,
            expected_answer=step.expected_answer,
            hint=step.hints[0] if step.hints else None,
            step_type=SolutionStepType.CALCULATION,
            input_type="number",
            answer_format=AnswerFormat.INTEGER.value,
        )
        for index, step in enumerate(plan.steps, start=1)
    ]
    return PrimarySchoolProblem(
        problem_id="imported_pending",
        grade=4,
        topic=plan.normalized_topic,
        problem_type=problem_type,
        title=title,
        language=locale,
        problem_text=transcription,
        skills=[f"imported_{plan.normalized_topic}"],
        known={
            "transcription": transcription,
            "normalized_topic": plan.normalized_topic,
        },
        unknown={"name": "answer"},
        strategy=strategy,
        solution_steps=steps,
        final_answer=plan.final_answer,
        metadata={
            "imported": True,
            "source": "image",
            "generated": True,
        },
    )


def resolve_imported_language(language: str) -> str:
    if language in {"en", "bg"}:
        return language
    return normalize_locale(language)
