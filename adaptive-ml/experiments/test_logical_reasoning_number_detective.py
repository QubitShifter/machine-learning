from random import Random

from src.core.tutor_engine.primary_school.generation.errors import (
    PrimarySchoolGenerationError,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning import (
    DigitDifference,
    DigitSum,
    FAMILY_NUMBER_DETECTIVE,
    InInterval,
    LogicalPuzzleSpec,
    LogicalReasoningVerificationError,
    NumberCandidate,
    NumberDomain,
    NumberParity,
    PRIVATE_PUZZLE_FIELDS,
    candidate_satisfies,
    generate_number_detective,
    satisfying_candidates,
    verify_unique_solution,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.number_detective import (
    PUBLIC_CLUE_KEYS,
    PUBLIC_NUMBER_DETECTIVE_KEYS,
    NumberDetectivePuzzle,
    _build_from_intended,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    NUMBER_MAX,
    NUMBER_MIN,
)


SWEEP_PER_DIFFICULTY = 100
BOUNDARY_VALUES = (10, 11, 20, 55, 64, 90, 91, 99)


def expect_generation_error(fn):
    try:
        fn()
    except PrimarySchoolGenerationError:
        return
    raise AssertionError("Expected PrimarySchoolGenerationError")


def independent_matches(spec):
    matches = []
    for value in range(NUMBER_MIN, NUMBER_MAX + 1):
        candidate = NumberCandidate(value)
        if all(
            _independent_clue_holds(constraint, candidate)
            for constraint in spec.constraints
        ):
            matches.append(value)
    return matches


def _independent_clue_holds(constraint, candidate):
    tens = candidate.value // 10
    units = candidate.value % 10
    kind = constraint.kind
    if kind == "digit_sum":
        return tens + units == constraint.total
    if kind == "digit_diff":
        return tens - units == constraint.amount
    if kind == "digit_order":
        if constraint.relation == "tens_gt_units":
            return tens > units
        if constraint.relation == "tens_lt_units":
            return tens < units
        return tens == units
    if kind == "parity":
        return (candidate.value % 2 == 0) is constraint.even
    if kind == "divisible_by":
        return candidate.value % constraint.divisor == 0
    if kind == "in_interval":
        return constraint.low <= candidate.value <= constraint.high
    raise AssertionError(f"Unsupported clue kind {kind}")


def assert_puzzle_valid(puzzle, difficulty):
    assert puzzle.family == FAMILY_NUMBER_DETECTIVE
    assert puzzle.difficulty == difficulty
    assert NUMBER_MIN <= puzzle.intended.value <= NUMBER_MAX
    spec = puzzle.spec
    assert spec.family == FAMILY_NUMBER_DETECTIVE
    for constraint in spec.constraints:
        assert candidate_satisfies(constraint, puzzle.intended, spec)
    verified = verify_unique_solution(spec, puzzle.intended)
    assert verified.unique == puzzle.intended
    assert len(verified.satisfying) == 1
    matches = independent_matches(spec)
    assert matches == [puzzle.intended.value]
    engine_matches = tuple(
        candidate.value for candidate in satisfying_candidates(spec)
    )
    assert engine_matches == (puzzle.intended.value,)
    counts = puzzle.elimination
    assert counts[0] == 90
    assert counts[-1] == 1
    assert all(
        counts[index] > counts[index + 1]
        for index in range(len(counts) - 1)
    )
    assert counts[1] > 1
    _assert_difficulty_contract(puzzle, difficulty)
    _assert_public_view_is_private(puzzle)


def _assert_difficulty_contract(puzzle, difficulty):
    kinds = tuple(item.kind for item in puzzle.spec.constraints)
    counts = puzzle.elimination
    if difficulty == 1:
        assert len(kinds) == 2
        assert set(kinds) == {"digit_sum", "digit_diff"}
        assert "in_interval" not in kinds
        assert "divisible_by" not in kinds
        return
    assert kinds[-1] == "in_interval"
    assert not ({"digit_sum", "digit_diff"} <= set(kinds))
    if difficulty == 2:
        assert len(kinds) == 3
        assert kinds[0] in {"digit_sum", "digit_diff"}
        assert counts[2] > 1
        return
    assert kinds[0] in {"digit_order", "parity"}
    assert len(kinds) in (3, 4)
    assert counts[2] > 1
    if len(kinds) == 4:
        assert counts[3] > 1
    else:
        assert counts[1] >= 9


def _assert_public_view_is_private(puzzle):
    view = puzzle.public_view()
    assert set(view) == PUBLIC_NUMBER_DETECTIVE_KEYS
    assert PRIVATE_PUZZLE_FIELDS.isdisjoint(view)
    assert "intended" not in view
    assert "solution" not in view
    assert "elimination" not in view
    assert "candidates" not in view
    assert puzzle.intended.value not in view.values()
    for clue in view["clues"]:
        allowed = PUBLIC_CLUE_KEYS[clue["kind"]]
        assert set(clue) == allowed
        assert PRIVATE_PUZZLE_FIELDS.isdisjoint(clue)
        if clue["kind"] == "digit_diff":
            assert clue["absolute_amount"] == abs(clue["amount"])
            if clue["amount"] > 0:
                assert clue["comparison"] == "tens_greater"
            elif clue["amount"] < 0:
                assert clue["comparison"] == "units_greater"
            else:
                assert clue["comparison"] == "equal"


def assert_generated_puzzles_are_valid():
    for difficulty in (1, 2, 3):
        for seed in range(12):
            puzzle = generate_number_detective(
                difficulty=difficulty,
                seed=seed,
            )
            assert_puzzle_valid(puzzle, difficulty)


def assert_same_seed_is_reproducible():
    for difficulty in (1, 2, 3):
        first = generate_number_detective(difficulty=difficulty, seed=7)
        second = generate_number_detective(difficulty=difficulty, seed=7)
        assert first.spec == second.spec
        assert first.intended == second.intended
        assert first.elimination == second.elimination
        assert first.public_view() == second.public_view()


def assert_seeds_vary():
    values = {
        generate_number_detective(difficulty=1, seed=seed).intended.value
        for seed in range(20)
    }
    assert len(values) > 5


def assert_boundary_numbers_generate():
    rng = Random(0)
    for value in BOUNDARY_VALUES:
        intended = NumberCandidate(value)
        for difficulty in (1, 2, 3):
            puzzle = _build_from_intended(difficulty, intended, Random(value))
            assert puzzle.intended.value == value
            assert_puzzle_valid(puzzle, difficulty)
            if value % 10 == 0:
                assert puzzle.intended.units == 0
            if value // 10 == value % 10:
                diff = [
                    clue
                    for clue in puzzle.spec.constraints
                    if clue.kind == "digit_diff"
                ]
                if diff:
                    assert diff[0].amount == 0
    negative = _build_from_intended(
        1,
        NumberCandidate(19),
        rng,
    )
    diff = [
        clue
        for clue in negative.spec.constraints
        if clue.kind == "digit_diff"
    ][0]
    assert diff.amount == 1 - 9
    public = negative.public_view()
    clue = [item for item in public["clues"] if item["kind"] == "digit_diff"][0]
    assert clue["comparison"] == "units_greater"
    assert clue["absolute_amount"] == 8


def assert_difficulty_is_not_clue_count_alone():
    d1 = generate_number_detective(difficulty=1, seed=3)
    d2 = generate_number_detective(difficulty=2, seed=3)
    d3 = generate_number_detective(difficulty=3, seed=3)
    assert len(d1.spec.constraints) == 2
    assert len(d2.spec.constraints) == 3
    assert d2.spec.constraints[0].kind != d3.spec.constraints[0].kind or (
        d2.elimination[1] != d3.elimination[1]
    )
    assert d1.spec.constraints[0].kind in {"digit_sum", "digit_diff"}
    assert d2.spec.constraints[0].kind in {"digit_sum", "digit_diff"}
    assert d3.spec.constraints[0].kind in {"digit_order", "parity"}
    assert d2.elimination[1] > 1
    assert d3.elimination[1] >= 9


def assert_invalid_configuration_fails():
    expect_generation_error(
        lambda: generate_number_detective(difficulty=0, seed=1)
    )
    expect_generation_error(
        lambda: generate_number_detective(difficulty=4, seed=1)
    )
    expect_generation_error(
        lambda: generate_number_detective(
            difficulty=1,
            seed=1,
            max_attempts=0,
        )
    )


def assert_exhausted_budget_fails():
    def failing_builder(difficulty, rng):
        raise LogicalReasoningVerificationError(
            "no_template",
            "forced failure",
        )

    expect_generation_error(
        lambda: generate_number_detective(
            difficulty=1,
            seed=1,
            max_attempts=2,
            attempt_builder=failing_builder,
        )
    )


def assert_incorrect_intended_is_rejected():
    good = generate_number_detective(difficulty=1, seed=4)

    def wrong_intended(difficulty, rng):
        return NumberDetectivePuzzle(
            spec=good.spec,
            intended=NumberCandidate(
                10 if good.intended.value != 10 else 11
            ),
            difficulty=1,
            elimination=good.elimination,
        )

    expect_generation_error(
        lambda: generate_number_detective(
            difficulty=1,
            seed=4,
            max_attempts=1,
            attempt_builder=wrong_intended,
        )
    )


def assert_ambiguous_constraints_are_rejected():
    spec = LogicalPuzzleSpec(
        family=FAMILY_NUMBER_DETECTIVE,
        domain=NumberDomain(),
        constraints=(DigitSum(10), NumberParity(True)),
    )

    def ambiguous(difficulty, rng):
        return NumberDetectivePuzzle(
            spec=spec,
            intended=NumberCandidate(64),
            difficulty=1,
            elimination=(90, 9, 4),
        )

    expect_generation_error(
        lambda: generate_number_detective(
            difficulty=1,
            seed=1,
            max_attempts=1,
            attempt_builder=ambiguous,
        )
    )
    try:
        verify_unique_solution(spec, NumberCandidate(64))
    except LogicalReasoningVerificationError as error:
        assert error.code == "multiple_solutions"
    else:
        raise AssertionError("Ambiguous clues must fail verification.")


def assert_impossible_quality_requirement_fails():
    def tiny_interval(difficulty, rng):
        intended = NumberCandidate(64)
        spec = LogicalPuzzleSpec(
            family=FAMILY_NUMBER_DETECTIVE,
            domain=NumberDomain(),
            constraints=(
                DigitSum(10),
                DigitDifference(2),
                InInterval(64, 64),
            ),
        )
        return NumberDetectivePuzzle(
            spec=spec,
            intended=intended,
            difficulty=2,
            elimination=(90, 9, 1, 1),
        )

    expect_generation_error(
        lambda: generate_number_detective(
            difficulty=2,
            seed=1,
            max_attempts=1,
            attempt_builder=tiny_interval,
        )
    )


def assert_generation_sweep():
    report = []
    for difficulty in (1, 2, 3):
        successes = []
        exhausted = 0
        retries = 0
        for index in range(SWEEP_PER_DIFFICULTY):
            seed = difficulty * 1000 + index
            try:
                puzzle = generate_number_detective(
                    difficulty=difficulty,
                    seed=seed,
                )
            except PrimarySchoolGenerationError:
                exhausted += 1
                continue
            assert_puzzle_valid(puzzle, difficulty)
            successes.append(puzzle)
            retries += puzzle.attempts_used - 1
        identities = {
            (item.intended.value, item.spec.constraints)
            for item in successes
        }
        values = {item.intended.value for item in successes}
        stats = {
            "difficulty": difficulty,
            "attempts": SWEEP_PER_DIFFICULTY,
            "successful": len(successes),
            "exhausted": exhausted,
            "internal_retries": retries,
            "unique_puzzles": len(identities),
            "unique_answers": len(values),
        }
        report.append(stats)
        assert exhausted == 0, stats
        assert len(successes) == SWEEP_PER_DIFFICULTY, stats
        assert len(identities) > 20, stats
        assert len(values) > 10, stats
        print(
            "Number Detective sweep "
            f"d{difficulty}: attempts={stats['attempts']} "
            f"successful={stats['successful']} "
            f"exhausted={stats['exhausted']} "
            f"internal_retries={stats['internal_retries']} "
            f"unique_puzzles={stats['unique_puzzles']} "
            f"unique_answers={stats['unique_answers']}"
        )
    return report


def main():
    assert_generated_puzzles_are_valid()
    assert_same_seed_is_reproducible()
    assert_seeds_vary()
    assert_boundary_numbers_generate()
    assert_difficulty_is_not_clue_count_alone()
    assert_invalid_configuration_fails()
    assert_exhausted_budget_fails()
    assert_incorrect_intended_is_rejected()
    assert_ambiguous_constraints_are_rejected()
    assert_impossible_quality_requirement_fails()
    assert_generation_sweep()
    print("logical_reasoning_number_detective tests passed")


if __name__ == "__main__":
    main()
