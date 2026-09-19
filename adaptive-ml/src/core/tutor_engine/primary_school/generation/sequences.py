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
_BOUNDS = {
    1: {
        "start": (1, 12),
        "diff": (1, 5),
        "shown": 4,
        "add": (1, 8),
        "mul": (2, 4),
        "max_value": 80,
    },
    2: {
        "start": (2, 20),
        "diff": (2, 8),
        "shown": 5,
        "add": (1, 12),
        "mul": (2, 5),
        "max_value": 160,
    },
    3: {
        "start": (2, 15),
        "diff": (3, 9),
        "shown": 4,
        "add": (1, 9),
        "mul": (2, 5),
        "max_value": 200,
    },
}


def generate_sequence_or_chain_problem(
    difficulty: int = 1,
    seed: int | None = None,
    rng: random.Random | None = None,
    language: str = "en",
    max_attempts: int = MAX_GENERATION_ATTEMPTS,
    attempt_builder=None,
) -> PrimarySchoolProblem:
    if difficulty not in _BOUNDS:
        raise PrimarySchoolGenerationError(
            f"Unsupported sequence difficulty {difficulty}."
        )

    chooser = rng or random.Random(seed)
    builder = attempt_builder or _attempt_sequence_or_chain
    last_error = (
        "Could not generate a valid sequence or chain problem."
    )

    for _ in range(max_attempts):
        try:
            problem = builder(difficulty, chooser)
            verify_sequence_or_chain_problem(problem)
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


def verify_sequence_or_chain_problem(
    problem: PrimarySchoolProblem,
) -> None:
    variant = problem.known["variant"]
    if variant == "sequence":
        _verify_sequence(problem)
        return
    if variant == "chain":
        _verify_chain(problem)
        return
    raise ValueError(f"Unknown variant: {variant}")


def _verify_sequence(problem: PrimarySchoolProblem) -> None:
    terms = list(problem.known["terms"])
    difference = problem.known["difference"]
    nxt = problem.known["next_term"]
    if difference == 0:
        raise ValueError("Common difference must be nonzero.")
    if len(terms) < 3:
        raise ValueError("Sequence is too short.")
    rebuilt = [
        terms[0] + index * difference
        for index in range(len(terms))
    ]
    if rebuilt != terms:
        raise ValueError("Terms are not an arithmetic sequence.")
    if terms[-1] + difference != nxt:
        raise ValueError("Next term is inconsistent.")
    if problem.final_answer != nxt:
        raise ValueError("Final answer is not the next term.")
    specs = problem.metadata["step_specs"]
    if specs[0]["expected_answer"] != difference:
        raise ValueError("First step is not the common difference.")
    if specs[-1]["expected_answer"] != nxt:
        raise ValueError("Last step is not the next term.")


def _verify_chain(problem: PrimarySchoolProblem) -> None:
    start = problem.known["start"]
    ops = [
        (item[0], int(item[1]))
        for item in problem.known["ops"]
    ]
    intermediates = list(problem.known["intermediates"])
    result = problem.known["result"]
    values = _apply_ops(start, ops)
    if values[1:] != intermediates:
        raise ValueError("Forward intermediates are inconsistent.")
    if values[-1] != result:
        raise ValueError("Forward result is inconsistent.")
    recovered = _reverse_ops(result, ops)
    if recovered != start:
        raise ValueError("Reverse operations do not recover start.")
    direction = problem.known["direction"]
    if direction == "forward":
        expected_final = result
    elif direction == "reverse":
        expected_final = start
    else:
        raise ValueError("Unknown chain direction.")
    if problem.final_answer != expected_final:
        raise ValueError("Final answer does not match chain direction.")
    last_expected = problem.metadata["step_specs"][-1][
        "expected_answer"
    ]
    if last_expected != expected_final:
        raise ValueError("Last step does not match chain direction.")


def _apply_ops(start: int, ops: list[tuple[str, int]]) -> list[int]:
    current = start
    values = [current]
    for op, amount in ops:
        current = _apply_op(current, op, amount)
        values.append(current)
    return values


def _reverse_ops(result: int, ops: list[tuple[str, int]]) -> int:
    current = result
    for op, amount in reversed(ops):
        current = _undo_op(current, op, amount)
    return current


def _apply_op(value: int, op: str, amount: int) -> int:
    if op == "+":
        return value + amount
    if op == "-":
        result = value - amount
        if result < 0:
            raise ValueError("Chain subtraction went negative.")
        return result
    if op == "*":
        if amount == 0:
            raise ValueError("Zero multiplier.")
        return value * amount
    raise ValueError(f"Unsupported chain op: {op}")


def _undo_op(value: int, op: str, amount: int) -> int:
    if op == "+":
        result = value - amount
        if result < 0:
            raise ValueError("Reverse addition went negative.")
        return result
    if op == "-":
        return value + amount
    if op == "*":
        if amount == 0 or value % amount != 0:
            raise ValueError("Reverse multiplication is not exact.")
        return value // amount
    raise ValueError(f"Unsupported chain op: {op}")


def _attempt_sequence_or_chain(
    difficulty: int,
    rng: random.Random,
) -> PrimarySchoolProblem:
    if difficulty == 1:
        return _attempt_sequence(difficulty, rng)
    if difficulty == 2:
        return _attempt_chain(difficulty, rng, reverse=False)
    if rng.choice((True, False)):
        return _attempt_sequence(difficulty, rng)
    return _attempt_chain(difficulty, rng, reverse=True)


def _attempt_sequence(
    difficulty: int,
    rng: random.Random,
) -> PrimarySchoolProblem:
    bounds = _BOUNDS[difficulty]
    start = rng.randint(*bounds["start"])
    difference = rng.randint(*bounds["diff"])
    shown = bounds["shown"]
    terms = [
        start + index * difference
        for index in range(shown)
    ]
    nxt = terms[-1] + difference
    if nxt > bounds["max_value"]:
        raise ValueError("Sequence term exceeds bounds.")
    sequence_text = ", ".join(str(term) for term in terms)
    known = {
        "variant": "sequence",
        "terms": terms,
        "difference": difference,
        "next_term": nxt,
        "sequence_text": sequence_text,
    }
    step_specs = [
        integer_step(
            step_number=1,
            skill_id="grade4_number_sequence",
            expected_answer=difference,
            prompt_key="gen.sequence.prompt.difference",
            hint_key="gen.sequence.hint.difference",
            params={"sequence": sequence_text},
        ),
        integer_step(
            step_number=2,
            skill_id="grade4_number_sequence",
            expected_answer=nxt,
            prompt_key="gen.sequence.prompt.next",
            hint_key="gen.sequence.hint.next",
            params={"sequence": sequence_text},
        ),
    ]
    return build_problem_from_specs(
        problem_id="grade4_number_patterns",
        grade=4,
        topic="number_patterns",
        problem_type=ProblemType.NUMBER_PATTERN,
        language="en",
        skills=["grade4_number_sequence"],
        known=known,
        unknown={"name": "next_term"},
        strategy="arithmetic_sequence",
        final_answer=nxt,
        step_specs=step_specs,
        metadata={
            "family": "number_patterns",
            "variant": "sequence",
            "difficulty": difficulty,
        },
    )


def _attempt_chain(
    difficulty: int,
    rng: random.Random,
    reverse: bool,
) -> PrimarySchoolProblem:
    bounds = _BOUNDS[difficulty]
    start = rng.randint(*bounds["start"])
    addend = rng.randint(*bounds["add"])
    multiplier = rng.randint(*bounds["mul"])
    ops: list[tuple[str, int]] = [
        ("+", addend),
        ("*", multiplier),
    ]
    if difficulty == 3:
        extra = rng.randint(*bounds["add"])
        ops.append(("+", extra))

    values = _apply_ops(start, ops)
    intermediates = values[1:]
    result = values[-1]
    if result > bounds["max_value"]:
        raise ValueError("Chain result exceeds bounds.")
    if _reverse_ops(result, ops) != start:
        raise ValueError("Chain reverse check failed.")

    chain_text = _render_chain(
        start,
        ops,
        result,
        hide_start=reverse,
    )
    direction = "reverse" if reverse else "forward"
    known = {
        "variant": "chain",
        "direction": direction,
        "start": start,
        "ops": [[op, amount] for op, amount in ops],
        "intermediates": intermediates,
        "result": result,
        "chain_text": chain_text,
    }
    if reverse:
        step_specs = _reverse_chain_steps(
            ops,
            intermediates,
            result,
            start,
            chain_text,
        )
        final_answer = start
        unknown = {"name": "start"}
        strategy = "reverse_operation_chain"
    else:
        step_specs = _forward_chain_steps(
            intermediates,
            result,
            chain_text,
        )
        final_answer = result
        unknown = {"name": "result"}
        strategy = "forward_operation_chain"

    return build_problem_from_specs(
        problem_id="grade4_number_patterns",
        grade=4,
        topic="number_patterns",
        problem_type=ProblemType.OPERATION_CHAIN,
        language="en",
        skills=["grade4_operation_chain"],
        known=known,
        unknown=unknown,
        strategy=strategy,
        final_answer=final_answer,
        step_specs=step_specs,
        metadata={
            "family": "number_patterns",
            "variant": "chain",
            "direction": direction,
            "difficulty": difficulty,
        },
    )


def _render_chain(
    start: int,
    ops: list[tuple[str, int]],
    result: int,
    hide_start: bool,
) -> str:
    symbols = {"+": "+", "-": "-", "*": "×"}
    first = "?" if hide_start else str(start)
    parts = [first]
    for op, amount in ops:
        parts.append(f"{symbols[op]}{amount}")
    last = str(result) if hide_start else "?"
    parts.append(last)
    return " → ".join(parts)


def _forward_chain_steps(
    intermediates: list[int],
    result: int,
    chain_text: str,
) -> list[dict]:
    specs = []
    for index, value in enumerate(intermediates, start=1):
        is_last = index == len(intermediates)
        specs.append(
            integer_step(
                step_number=index,
                skill_id="grade4_operation_chain",
                expected_answer=value,
                prompt_key=(
                    "gen.chain.prompt.result"
                    if is_last
                    else "gen.chain.prompt.after_step"
                ),
                hint_key=(
                    "gen.chain.hint.last_forward"
                    if is_last
                    else "gen.chain.hint.next_forward"
                ),
                params={
                    "chain": chain_text,
                    "step_number": index,
                },
            )
        )
    if specs[-1]["expected_answer"] != result:
        raise ValueError("Forward chain last step mismatch.")
    return specs


def _reverse_chain_steps(
    ops: list[tuple[str, int]],
    intermediates: list[int],
    result: int,
    start: int,
    chain_text: str,
) -> list[dict]:
    specs = []
    current = result
    undone = []
    for index, (op, amount) in enumerate(reversed(ops), start=1):
        current = _undo_op(current, op, amount)
        undone.append(current)
        is_last = index == len(ops)
        specs.append(
            integer_step(
                step_number=index,
                skill_id="grade4_operation_chain",
                expected_answer=current,
                prompt_key=(
                    "gen.chain.prompt.start"
                    if is_last
                    else "gen.chain.prompt.undo"
                ),
                hint_key=_reverse_hint_key(op),
                params={
                    "chain": chain_text,
                    "amount": amount,
                    "result": result,
                },
            )
        )
    if undone[-1] != start:
        raise ValueError("Reverse chain last step mismatch.")
    return specs


def _reverse_hint_key(op: str) -> str:
    if op == "+":
        return "gen.chain.hint.undo_add"
    if op == "-":
        return "gen.chain.hint.undo_sub"
    return "gen.chain.hint.undo_mul"
