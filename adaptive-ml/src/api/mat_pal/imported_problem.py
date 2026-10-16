from fastapi import HTTPException

from src.api.mat_pal.generated_problem_store import (
    add_generated_problem,
)
from src.api.mat_pal.problem_generation import (
    _generated_problem_id,
)
from src.api.mat_pal.schemas import (
    ConfirmedProblemRequest,
    ImportedProblemResponse,
)
from src.api.mat_pal.tutor_registry import (
    TutorRegistration,
)
from src.core.imported_problem.compiler import (
    compile_imported_problem,
    resolve_imported_language,
)
from src.core.imported_problem.contracts import (
    ConfirmedProblem,
)
from src.core.imported_problem.errors import (
    ImportedPlanParseError,
    ImportedPlannerRequestError,
    ImportedPlannerTimeoutError,
    ImportedPlannerUnavailableError,
    ImportedProblemCompileError,
    UnsupportedImportedProblem,
)
from src.core.imported_problem.planner import (
    get_imported_planner,
)
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.problem_types import (
    PrimarySchoolProblem,
)


DETAIL_NOT_SUPPORTED = "unsupported_problem_type"
DETAIL_UNAVAILABLE = "Imported problem planner unavailable."
DETAIL_TIMEOUT = "Imported problem planner timed out."
DETAIL_PARSE = "Imported solution plan could not be parsed."
DETAIL_INVALID = "Confirmed problem could not be compiled."
DETAIL_EMPTY = "transcription must not be empty"
DETAIL_LATEX_TOO_LONG = (
    "A latex expression exceeds the allowed length."
)
MAX_LATEX_CHARS = 500
TOPIC_NAMES = {
    "arithmetic": "Arithmetic",
    "unknown_numbers": "Unknown Numbers",
    "story_problems": "Story Problems",
}


def create_problem_from_confirmed(
    request: ConfirmedProblemRequest,
) -> ImportedProblemResponse:
    confirmed = to_confirmed_problem(request)
    planner = get_imported_planner()
    if not planner.is_available():
        raise HTTPException(
            status_code=503,
            detail=DETAIL_UNAVAILABLE,
        )

    try:
        plan = planner.plan(confirmed)
        problem = compile_imported_problem(confirmed, plan)
    except UnsupportedImportedProblem as error:
        raise HTTPException(
            status_code=422,
            detail=DETAIL_NOT_SUPPORTED,
        ) from error
    except ImportedPlanParseError as error:
        raise HTTPException(
            status_code=422,
            detail=DETAIL_PARSE,
        ) from error
    except ImportedPlannerTimeoutError as error:
        raise HTTPException(
            status_code=504,
            detail=DETAIL_TIMEOUT,
        ) from error
    except (
        ImportedPlannerUnavailableError,
        ImportedPlannerRequestError,
    ) as error:
        raise HTTPException(
            status_code=503,
            detail=DETAIL_UNAVAILABLE,
        ) from error
    except ImportedProblemCompileError as error:
        raise HTTPException(
            status_code=422,
            detail=DETAIL_INVALID,
        ) from error

    registration = to_tutor_registration(problem)
    add_generated_problem(registration)
    return ImportedProblemResponse(
        problem_id=registration.problem_id,
        topic=registration.topic,
        language=registration.language,
        title=registration.title,
    )


def to_confirmed_problem(
    request: ConfirmedProblemRequest,
) -> ConfirmedProblem:
    transcription = request.transcription.strip()
    if not transcription:
        raise HTTPException(
            status_code=422,
            detail=DETAIL_EMPTY,
        )
    latex: list[str] = []
    for item in request.latex_expressions:
        if len(item) > MAX_LATEX_CHARS:
            raise HTTPException(
                status_code=422,
                detail=DETAIL_LATEX_TOO_LONG,
            )
        latex.append(item)
    return ConfirmedProblem(
        transcription=transcription,
        language=resolve_imported_language(request.language),
        latex_expressions=tuple(latex),
        topic_hint=_optional_hint(request.topic_hint),
        problem_type_hint=_optional_hint(
            request.problem_type_hint
        ),
    )


def to_tutor_registration(
    problem: PrimarySchoolProblem,
) -> TutorRegistration:
    problem_id = _generated_problem_id("imported")
    problem.problem_id = problem_id
    first_step = problem.solution_steps[0]
    public_metadata = {
        "imported": True,
        "source": "image",
        "generated": True,
    }
    return TutorRegistration(
        problem_id=problem_id,
        title=problem.title,
        problem_statement=problem.problem_text,
        subject="mathematics",
        domain="primary_school",
        topic=problem.topic,
        topic_name=TOPIC_NAMES.get(
            problem.topic,
            problem.topic,
        ),
        problem_type=problem.problem_type.value,
        total_steps=problem.get_number_of_steps(),
        expected_input_type=(
            first_step.input_type or "number"
        ),
        skills=tuple(problem.skills),
        metadata=public_metadata,
        catalog_visible=False,
        language=problem.language,
        grade=problem.grade,
        create_engine=(
            lambda language="en", current=problem:
                PrimarySchoolTutorEngine(problem=current)
        ),
    )


def _optional_hint(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None
