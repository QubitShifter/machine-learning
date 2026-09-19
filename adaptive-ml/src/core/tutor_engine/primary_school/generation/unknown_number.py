import random

from src.core.tutor_engine.primary_school.generation.builder import (
    build_problem_from_specs,
    integer_step,
)
from src.core.tutor_engine.primary_school.generation.errors import (
    PrimarySchoolGenerationError,
)
from src.core.tutor_engine.primary_school.problem_types import (
    PrimarySchoolProblem,
    ProblemType,
)


MAX_GENERATION_ATTEMPTS = 24
_FORMS = {
    1: ("x+a=b",),
    2: ("x+a=b", "x-a=b"),
    3: ("x+a=b", "x-a=b", "a*x=b"),
}
_BOUNDS = {
    1: {"x": (1, 15), "a": (1, 12)},
    2: {"x": (1, 30), "a": (1, 20)},
    3: {"x": (2, 12), "a": (2, 12)},
}


def generate_unknown_number_problem(
    difficulty: int = 1,
    seed: int | None = None,
    rng: random.Random | None = None,
    language: str = "en",
    max_attempts: int = MAX_GENERATION_ATTEMPTS,
    attempt_builder=None,
) -> PrimarySchoolProblem:
    if difficulty not in _BOUNDS:
        raise PrimarySchoolGenerationError(
            f"Unsupported unknown-number difficulty {difficulty}."
        )

    chooser = rng or random.Random(seed)
    builder = attempt_builder or _attempt_unknown
    last_error = (
        "Could not generate a valid unknown-number problem."
    )

    for _ in range(max_attempts):
        try:
            problem = builder(difficulty, chooser)
            verify_unknown_number_problem(problem)
            from src.core.tutor_engine.primary_school.generation.localize import (
                localize_generated_primary_school,
            )

            return localize_generated_primary_school(
                problem,
                language,
            )
        except ValueError as error:
            last_error = str(error)

    raise PrimarySchoolGenerationError(last_error)


def verify_unknown_number_problem(
    problem: PrimarySchoolProblem,
) -> None:
    known = problem.known
    form = known["form"]
    a = known["a"]
    b = known["b"]
    x = known["x"]
    if not all(isinstance(value, int) for value in (a, b, x)):
        raise ValueError("Unknown-number values must be integers.")
    if isinstance(a, bool) or a == 0:
        raise ValueError("Coefficient a must be a nonzero integer.")
    if form == "x+a=b":
        if x + a != b:
            raise ValueError("Substitution failed for x + a = b.")
    elif form == "x-a=b":
        if x - a != b:
            raise ValueError("Substitution failed for x - a = b.")
    elif form == "a*x=b":
        if a * x != b:
            raise ValueError("Substitution failed for a × x = b.")
    else:
        raise ValueError(f"Unsupported form: {form}")

    if _solve(form, a, b) != x:
        raise ValueError("Solution is not unique or does not match.")
    if x == a:
        raise ValueError("Unknown equals the known addend.")
    if problem.final_answer != x:
        raise ValueError("Final answer is not the unknown.")
    last_expected = problem.metadata["step_specs"][-1][
        "expected_answer"
    ]
    if last_expected != x:
        raise ValueError("Last step is not the unknown.")


def _solve(form: str, a: int, b: int) -> int:
    if form == "x+a=b":
        return b - a
    if form == "x-a=b":
        return b + a
    if form == "a*x=b":
        if b % a != 0:
            raise ValueError("Division is not exact.")
        return b // a
    raise ValueError(f"Unsupported form: {form}")


def _attempt_unknown(
    difficulty: int,
    rng: random.Random,
) -> PrimarySchoolProblem:
    bounds = _BOUNDS[difficulty]
    form = rng.choice(_FORMS[difficulty])
    x = rng.randint(*bounds["x"])
    a = rng.randint(*bounds["a"])
    if form == "a*x=b" and a == 0:
        raise ValueError("Zero coefficient.")
    if x == a:
        raise ValueError("Unknown equals the known addend.")

    if form == "x+a=b":
        b = x + a
        equation = f"x + {a} = {b}"
        known_prompt = "gen.unknown.prompt.known_addend"
        known_hint = "gen.unknown.hint.known_addend"
        solve_hint = "gen.unknown.hint.inverse_add"
    elif form == "x-a=b":
        if x < a:
            raise ValueError("Negative difference.")
        b = x - a
        equation = f"x - {a} = {b}"
        known_prompt = "gen.unknown.prompt.known_subtrahend"
        known_hint = "gen.unknown.hint.known_subtrahend"
        solve_hint = "gen.unknown.hint.inverse_sub"
    else:
        b = a * x
        equation = f"{a} × x = {b}"
        known_prompt = "gen.unknown.prompt.known_factor"
        known_hint = "gen.unknown.hint.known_factor"
        solve_hint = "gen.unknown.hint.inverse_mul"

    known = {
        "form": form,
        "a": a,
        "b": b,
        "x": x,
        "equation": equation,
    }
    step_specs = [
        integer_step(
            step_number=1,
            skill_id="grade4_unknown_number",
            expected_answer=a,
            prompt_key=known_prompt,
            hint_key=known_hint,
            params={"equation": equation},
        ),
        integer_step(
            step_number=2,
            skill_id="grade4_unknown_number",
            expected_answer=x,
            prompt_key="gen.unknown.prompt.solve",
            hint_key=solve_hint,
            params={"equation": equation},
            operation=equation,
        ),
    ]
    return build_problem_from_specs(
        problem_id="grade4_unknown_number",
        grade=4,
        topic="unknown_numbers",
        problem_type=ProblemType.UNKNOWN_NUMBER,
        language="en",
        skills=["grade4_unknown_number"],
        known=known,
        unknown={"name": "x"},
        strategy="inverse_operation",
        final_answer=x,
        step_specs=step_specs,
        metadata={
            "family": "unknown_number",
            "difficulty": difficulty,
            "form": form,
        },
    )
