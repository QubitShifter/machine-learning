import random

from src.core.tutor_engine.primary_school.generation.builder import (
    build_problem_from_specs,
    integer_step,
)
from src.core.tutor_engine.primary_school.generation.errors import (
    PrimarySchoolGenerationError,
)
from src.core.tutor_engine.primary_school.generation.expr import (
    ArithmeticExpr,
    combine,
    expr_from_dict,
    leaf,
)
from src.core.tutor_engine.primary_school.problem_types import (
    PrimarySchoolProblem,
    ProblemType,
)


MAX_GENERATION_ATTEMPTS = 24

_BOUNDS = {
    1: {
        "min_value": 1,
        "max_value": 12,
        "max_result": 24,
        "max_intermediate": 24,
    },
    2: {
        "min_value": 1,
        "max_value": 10,
        "max_result": 80,
        "max_intermediate": 80,
    },
    3: {
        "min_value": 1,
        "max_value": 12,
        "max_result": 144,
        "max_intermediate": 144,
    },
}


def generate_arithmetic_problem(
    difficulty: int = 1,
    seed: int | None = None,
    rng: random.Random | None = None,
    language: str = "en",
    max_attempts: int = MAX_GENERATION_ATTEMPTS,
    attempt_builder=None,
) -> PrimarySchoolProblem:
    if difficulty not in _BOUNDS:
        raise PrimarySchoolGenerationError(
            f"Unsupported arithmetic difficulty {difficulty}."
        )

    chooser = rng or random.Random(seed)
    builder = attempt_builder or _attempt_arithmetic
    last_error = "Could not generate a valid arithmetic problem."

    for _ in range(max_attempts):
        try:
            problem = builder(difficulty, chooser)
            verify_arithmetic_problem(problem)
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


def verify_arithmetic_problem(
    problem: PrimarySchoolProblem,
) -> None:
    tree = expr_from_dict(problem.known["expr"])
    recomputed = tree.evaluate()
    if recomputed != problem.final_answer:
        raise ValueError("Arithmetic answer does not match the tree.")
    if tree.render() != problem.known["expression"]:
        raise ValueError("Displayed expression does not match the tree.")

    bounds = _BOUNDS[problem.metadata["difficulty"]]
    for value in tree.values():
        if not (
            bounds["min_value"]
            <= value
            <= bounds["max_value"]
        ):
            raise ValueError("Operand is outside difficulty bounds.")
    for value in tree.intermediates():
        if value < 0 or value > bounds["max_intermediate"]:
            raise ValueError("Intermediate is outside difficulty bounds.")
    if (
        recomputed < 0
        or recomputed > bounds["max_result"]
    ):
        raise ValueError("Result is outside difficulty bounds.")

    expected_steps = [
        spec["expected_answer"]
        for spec in problem.metadata["step_specs"]
    ]
    if expected_steps[-1] != recomputed:
        raise ValueError("Last step is not the final value.")
    if any(
        not isinstance(value, int) or isinstance(value, bool)
        for value in expected_steps
    ):
        raise ValueError("Step answers must be integers.")


def _attempt_arithmetic(
    difficulty: int,
    rng: random.Random,
) -> PrimarySchoolProblem:
    bounds = _BOUNDS[difficulty]
    if difficulty == 1:
        tree, inner = _simple_binary(rng, bounds)
        shape = "simple_binary"
    elif difficulty == 2:
        tree, inner = _order_of_operations(rng, bounds)
        shape = "order_of_operations"
    else:
        tree, inner = _parentheses(rng, bounds)
        shape = "parentheses"

    final = tree.evaluate()
    expression = tree.render()
    known = {
        "expr": tree.to_dict(),
        "expression": expression,
        "inner_value": inner,
        "final_value": final,
        "shape": shape,
    }
    step_specs = _step_specs(shape, known)
    return build_problem_from_specs(
        problem_id="grade4_arithmetic",
        grade=4,
        topic="arithmetic",
        problem_type=ProblemType.ARITHMETIC,
        language="en",
        skills=_skills_for_shape(shape),
        known=known,
        unknown={"name": "value"},
        strategy="evaluate_expression",
        final_answer=final,
        step_specs=step_specs,
        metadata={
            "family": "arithmetic",
            "difficulty": difficulty,
            "shape": shape,
        },
    )


def _simple_binary(rng: random.Random, bounds: dict):
    op = rng.choice(("+", "-"))
    left = rng.randint(bounds["min_value"], bounds["max_value"])
    right = rng.randint(bounds["min_value"], bounds["max_value"])
    if op == "-" and right > left:
        left, right = right, left
    tree = combine(op, leaf(left), leaf(right))
    value = tree.evaluate()
    _require_bounds(value, bounds)
    return tree, value


def _order_of_operations(rng: random.Random, bounds: dict):
    a = rng.randint(bounds["min_value"], bounds["max_value"])
    b = rng.randint(bounds["min_value"], min(6, bounds["max_value"]))
    c = rng.randint(bounds["min_value"], min(6, bounds["max_value"]))
    if rng.choice((True, False)):
        inner_tree = combine("*", leaf(b), leaf(c))
        tree = combine("+", leaf(a), inner_tree)
    else:
        inner_tree = combine("*", leaf(a), leaf(b))
        tree = combine("+", inner_tree, leaf(c))
    inner = inner_tree.evaluate()
    final = tree.evaluate()
    _require_bounds(inner, bounds)
    _require_bounds(final, bounds)
    if inner == final:
        raise ValueError("Inner value equals the final value.")
    return tree, inner


def _parentheses(rng: random.Random, bounds: dict):
    a = rng.randint(bounds["min_value"], bounds["max_value"])
    b = rng.randint(bounds["min_value"], bounds["max_value"])
    c = rng.randint(2, min(8, bounds["max_value"]))
    if rng.choice((True, False)):
        if b > a:
            a, b = b, a
        inner_tree = combine("-", leaf(a), leaf(b))
    else:
        inner_tree = combine("+", leaf(a), leaf(b))
    tree = combine("*", inner_tree, leaf(c))
    inner = inner_tree.evaluate()
    final = tree.evaluate()
    _require_bounds(inner, bounds)
    _require_bounds(final, bounds)
    if inner == final:
        raise ValueError("Inner value equals the final value.")
    return tree, inner


def _require_bounds(value: int, bounds: dict) -> None:
    if value < 0 or value > bounds["max_result"]:
        raise ValueError("Value is outside difficulty bounds.")
    if value > bounds["max_intermediate"]:
        raise ValueError("Intermediate is outside difficulty bounds.")


def _skills_for_shape(shape: str) -> list[str]:
    if shape == "simple_binary":
        return [
            "grade4_arithmetic_addition",
            "grade4_arithmetic_subtraction",
        ]
    return [
        "grade4_arithmetic_multiplication",
        "grade4_arithmetic_order",
    ]


def _step_specs(shape: str, known: dict) -> list[dict]:
    expression = known["expression"]
    final = known["final_value"]
    inner = known["inner_value"]
    if shape == "simple_binary":
        return [
            integer_step(
                step_number=1,
                skill_id="grade4_arithmetic_addition",
                expected_answer=final,
                prompt_key="gen.arithmetic.prompt.value",
                hint_key="gen.arithmetic.hint.compute",
                params={"expression": expression},
                operation=expression,
            )
        ]

    if shape == "order_of_operations":
        return [
            integer_step(
                step_number=1,
                skill_id="grade4_arithmetic_multiplication",
                expected_answer=inner,
                prompt_key="gen.arithmetic.prompt.inner_product",
                hint_key="gen.arithmetic.hint.multiply_first",
                params={"expression": expression},
            ),
            integer_step(
                step_number=2,
                skill_id="grade4_arithmetic_order",
                expected_answer=final,
                prompt_key="gen.arithmetic.prompt.value",
                hint_key="gen.arithmetic.hint.add_product",
                params={"expression": expression},
                operation=expression,
            ),
        ]

    return [
        integer_step(
            step_number=1,
            skill_id="grade4_arithmetic_addition",
            expected_answer=inner,
            prompt_key="gen.arithmetic.prompt.inner_paren",
            hint_key="gen.arithmetic.hint.parentheses",
            params={"expression": expression},
        ),
        integer_step(
            step_number=2,
            skill_id="grade4_arithmetic_multiplication",
            expected_answer=final,
            prompt_key="gen.arithmetic.prompt.value",
            hint_key="gen.arithmetic.hint.multiply_inner",
            params={"expression": expression},
            operation=expression,
        ),
    ]
