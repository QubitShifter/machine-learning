from itertools import product
from random import Random
from time import perf_counter

from src.core.tutor_engine.primary_school.generation.errors import (
    PrimarySchoolGenerationError,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning import (
    DistMoreThan,
    DistTimes,
    DistTotal,
    DistributionCandidate,
    DistributionDomain,
    FAMILY_DISTRIBUTION,
    LogicalPuzzleSpec,
    LogicalReasoningVerificationError,
    PRIVATE_PUZZLE_FIELDS,
    candidate_satisfies,
    generate_distribution_puzzle,
    satisfying_candidates,
    verify_unique_solution,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.distribution_puzzles import (
    PUBLIC_CLUE_KEYS,
    PUBLIC_DISTRIBUTION_KEYS,
    ArithmeticBlueprint,
    ArithmeticStep,
    DistributionPuzzle,
    verify_blueprint,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    DEFAULT_DISTRIBUTION_MAX,
)


SWEEP_PER_DIFFICULTY = 100


def expect_generation_error(fn):
    try:
        fn()
    except PrimarySchoolGenerationError:
        return
    raise AssertionError("Expected PrimarySchoolGenerationError")


def independent_matches(spec):
    domain = spec.domain
    names = domain.names
    matches = []
    for combo in product(
        range(domain.minimum, domain.maximum + 1),
        repeat=len(names),
    ):
        values = dict(zip(names, combo))
        if all(
            _independent_clue_holds(constraint, values)
            for constraint in spec.constraints
        ):
            matches.append(combo)
    return matches


def _independent_clue_holds(constraint, values):
    kind = constraint.kind
    if kind == "total":
        return sum(values.values()) == constraint.total
    if kind == "more_than":
        return values[constraint.left] == (
            values[constraint.right] + constraint.extra
        )
    if kind == "times_as_many":
        return values[constraint.left] == (
            values[constraint.right] * constraint.factor
        )
    raise AssertionError(f"Unsupported clue kind {kind}")


def assignment_map(candidate):
    return {name: value for name, value in candidate.quantities}


def assert_puzzle_valid(puzzle, difficulty):
    assert puzzle.family == FAMILY_DISTRIBUTION
    assert puzzle.difficulty == difficulty
    domain = puzzle.spec.domain
    assert domain.minimum == 1
    assert domain.maximum == DEFAULT_DISTRIBUTION_MAX
    values = assignment_map(puzzle.intended)
    assert set(values) == set(domain.names)
    for value in values.values():
        assert isinstance(value, int)
        assert not isinstance(value, bool)
        assert 2 <= value <= DEFAULT_DISTRIBUTION_MAX
    for constraint in puzzle.spec.constraints:
        assert candidate_satisfies(constraint, puzzle.intended, puzzle.spec)
        if constraint.kind == "times_as_many":
            assert values[constraint.left] == (
                values[constraint.right] * constraint.factor
            )
            assert values[constraint.left] > values[constraint.right]
        if constraint.kind == "more_than":
            assert values[constraint.left] == (
                values[constraint.right] + constraint.extra
            )
            assert values[constraint.left] > values[constraint.right]
    verified = verify_unique_solution(puzzle.spec, puzzle.intended)
    assert verified.unique == puzzle.intended
    assert len(verified.satisfying) == 1
    matches = independent_matches(puzzle.spec)
    assert matches == [tuple(values[name] for name in domain.names)]
    engine_matches = satisfying_candidates(puzzle.spec)
    assert engine_matches == (puzzle.intended,)
    reconstructed = verify_blueprint(
        puzzle.blueprint,
        puzzle.spec,
        puzzle.intended,
    )
    assert reconstructed == values
    _assert_difficulty_contract(puzzle, difficulty)
    _assert_public_view_is_private(puzzle)


def _assert_difficulty_contract(puzzle, difficulty):
    names = puzzle.spec.domain.names
    times = [
        item for item in puzzle.spec.constraints if item.kind == "times_as_many"
    ]
    more = [
        item for item in puzzle.spec.constraints if item.kind == "more_than"
    ]
    if difficulty == 1:
        assert names == ("box_a", "box_b")
        assert len(puzzle.spec.constraints) == 2
        assert len(times) + len(more) == 1
        assert puzzle.blueprint.template_id in (
            "two_multiplicative",
            "two_additive",
        )
        assert len(puzzle.blueprint.steps) <= 4
        return
    assert names == ("box_a", "box_b", "box_c")
    assert len(times) == 1 and len(more) == 1
    if difficulty == 2:
        assert puzzle.blueprint.template_id == "three_shared_reference"
        assert more[0].right == times[0].right
        assert more[0].left != times[0].right
        assert any(
            step.purpose == "shared_reference"
            for step in puzzle.blueprint.steps
        )
        assert len(puzzle.blueprint.steps) == 5
        return
    assert puzzle.blueprint.template_id == "three_chain"
    assert more[0].left == times[0].right
    assert more[0].right != times[0].right
    purposes = tuple(step.purpose for step in puzzle.blueprint.steps)
    assert "chain_base" in purposes
    assert "chain_middle" in purposes
    assert len(puzzle.blueprint.steps) >= 7


def _assert_public_view_is_private(puzzle):
    view = puzzle.public_view()
    assert set(view) == PUBLIC_DISTRIBUTION_KEYS
    assert PRIVATE_PUZZLE_FIELDS.isdisjoint(view)
    assert "intended" not in view
    assert "solution" not in view
    assert "blueprint" not in view
    assert "quantities" not in view
    assert puzzle.intended.quantities not in view.values()
    for clue in view["clues"]:
        assert set(clue) == PUBLIC_CLUE_KEYS[clue["kind"]]
        assert PRIVATE_PUZZLE_FIELDS.isdisjoint(clue)


def assert_generated_puzzles_are_valid():
    for difficulty in (1, 2, 3):
        for seed in range(12):
            puzzle = generate_distribution_puzzle(
                difficulty=difficulty,
                seed=seed,
            )
            assert_puzzle_valid(puzzle, difficulty)


def assert_same_seed_is_reproducible():
    for difficulty in (1, 2, 3):
        first = generate_distribution_puzzle(difficulty=difficulty, seed=11)
        second = generate_distribution_puzzle(difficulty=difficulty, seed=11)
        assert first.spec == second.spec
        assert first.intended == second.intended
        assert first.blueprint == second.blueprint
        assert first.public_view() == second.public_view()


def assert_seeds_vary():
    identities = {
        generate_distribution_puzzle(difficulty=2, seed=seed).intended
        for seed in range(20)
    }
    assert len(identities) > 5


def assert_required_examples_exist():
    examples = {
        1: generate_distribution_puzzle(difficulty=1, seed=0),
        2: generate_distribution_puzzle(difficulty=2, seed=0),
        3: generate_distribution_puzzle(difficulty=3, seed=0),
    }
    assert examples[2].blueprint.template_id != examples[3].blueprint.template_id
    assert len(examples[2].blueprint.steps) != len(examples[3].blueprint.steps)
    return examples


def assert_difficulty_structures_differ():
    d2 = generate_distribution_puzzle(difficulty=2, seed=4)
    d3 = generate_distribution_puzzle(difficulty=3, seed=4)
    assert d2.blueprint.template_id == "three_shared_reference"
    assert d3.blueprint.template_id == "three_chain"
    d2_more = [
        item for item in d2.spec.constraints if item.kind == "more_than"
    ][0]
    d2_times = [
        item for item in d2.spec.constraints if item.kind == "times_as_many"
    ][0]
    d3_more = [
        item for item in d3.spec.constraints if item.kind == "more_than"
    ][0]
    d3_times = [
        item for item in d3.spec.constraints if item.kind == "times_as_many"
    ][0]
    assert d2_more.right == d2_times.right
    assert d3_more.left == d3_times.right


def assert_invalid_configuration_fails():
    expect_generation_error(
        lambda: generate_distribution_puzzle(difficulty=0, seed=1)
    )
    expect_generation_error(
        lambda: generate_distribution_puzzle(difficulty=4, seed=1)
    )
    expect_generation_error(
        lambda: generate_distribution_puzzle(
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
        lambda: generate_distribution_puzzle(
            difficulty=1,
            seed=1,
            max_attempts=2,
            attempt_builder=failing_builder,
        )
    )


def assert_incorrect_intended_is_rejected():
    good = generate_distribution_puzzle(difficulty=1, seed=5)
    wrong_values = []
    for name, value in good.intended.quantities:
        wrong_values.append((name, value + 1 if name == "box_b" else value))
    wrong = DistributionCandidate(quantities=tuple(wrong_values))

    def wrong_intended(difficulty, rng):
        return DistributionPuzzle(
            spec=good.spec,
            intended=wrong,
            difficulty=1,
            blueprint=good.blueprint,
        )

    expect_generation_error(
        lambda: generate_distribution_puzzle(
            difficulty=1,
            seed=5,
            max_attempts=1,
            attempt_builder=wrong_intended,
        )
    )


def assert_ambiguous_and_contradictory_clues_are_rejected():
    names = ("box_a", "box_b")
    domain = DistributionDomain(names=names)
    ambiguous = LogicalPuzzleSpec(
        family=FAMILY_DISTRIBUTION,
        domain=domain,
        constraints=(DistTotal(18),),
    )
    try:
        verify_unique_solution(
            ambiguous,
            DistributionCandidate((("box_a", 12), ("box_b", 6))),
        )
    except LogicalReasoningVerificationError as error:
        assert error.code == "multiple_solutions"
    else:
        raise AssertionError("A total alone must be ambiguous.")

    contradictory = LogicalPuzzleSpec(
        family=FAMILY_DISTRIBUTION,
        domain=domain,
        constraints=(
            DistTotal(18),
            DistTimes("box_a", "box_b", 2),
            DistMoreThan("box_a", "box_b", 3),
        ),
    )
    try:
        verify_unique_solution(
            contradictory,
            DistributionCandidate((("box_a", 12), ("box_b", 6))),
        )
    except LogicalReasoningVerificationError as error:
        assert error.code == "zero_solutions"
    else:
        raise AssertionError("Contradictory clues must be rejected.")


def assert_invalid_factor_and_oversized_domain_fail():
    names = ("box_a", "box_b")
    try:
        verify_unique_solution(
            LogicalPuzzleSpec(
                family=FAMILY_DISTRIBUTION,
                domain=DistributionDomain(names=names),
                constraints=(
                    DistTotal(18),
                    DistTimes("box_a", "box_b", 1),
                ),
            ),
            DistributionCandidate((("box_a", 9), ("box_b", 9))),
        )
    except LogicalReasoningVerificationError as error:
        assert error.code == "invalid_constraint"
    else:
        raise AssertionError("Factor 1 must be rejected.")

    try:
        verify_unique_solution(
            LogicalPuzzleSpec(
                family=FAMILY_DISTRIBUTION,
                domain=DistributionDomain(
                    names=("box_a", "box_b", "box_c"),
                    maximum=21,
                ),
                constraints=(DistTotal(24),),
            ),
            DistributionCandidate(
                (("box_a", 10), ("box_b", 5), ("box_c", 9)),
            ),
        )
    except LogicalReasoningVerificationError as error:
        assert error.code == "domain_too_large"
    else:
        raise AssertionError("Oversized domains must fail closed.")


def assert_blueprint_rejects_hidden_assumptions():
    puzzle = generate_distribution_puzzle(difficulty=2, seed=2)
    bad_steps = puzzle.blueprint.steps[:-1] + (
        ArithmeticStep(
            5,
            "addition",
            ("clue.total", "clue.extra"),
            "qty.box_c",
            "hidden_total_plus_extra",
            puzzle.intended.get("box_c"),
        ),
    )
    try:
        verify_blueprint(
            ArithmeticBlueprint(puzzle.blueprint.template_id, bad_steps),
            puzzle.spec,
            puzzle.intended,
        )
    except LogicalReasoningVerificationError as error:
        assert error.code == "invalid_blueprint"
    else:
        raise AssertionError("Hidden blueprint assumptions must fail.")


def assert_impossible_assignment_fails():
    def zero_box(difficulty, rng):
        spec = LogicalPuzzleSpec(
            family=FAMILY_DISTRIBUTION,
            domain=DistributionDomain(names=("box_a", "box_b")),
            constraints=(
                DistTotal(10),
                DistTimes("box_a", "box_b", 2),
            ),
        )
        return DistributionPuzzle(
            spec=spec,
            intended=DistributionCandidate(
                (("box_a", 0), ("box_b", 10)),
            ),
            difficulty=1,
            blueprint=ArithmeticBlueprint("two_multiplicative", ()),
        )

    expect_generation_error(
        lambda: generate_distribution_puzzle(
            difficulty=1,
            seed=1,
            max_attempts=1,
            attempt_builder=zero_box,
        )
    )


def assert_generation_sweep():
    started = perf_counter()
    report = []
    for difficulty in (1, 2, 3):
        successes = []
        exhausted = 0
        retries = 0
        for index in range(SWEEP_PER_DIFFICULTY):
            seed = difficulty * 1000 + index
            try:
                puzzle = generate_distribution_puzzle(
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
            (item.intended, item.spec.constraints)
            for item in successes
        }
        stats = {
            "difficulty": difficulty,
            "attempts": SWEEP_PER_DIFFICULTY,
            "successful": len(successes),
            "exhausted": exhausted,
            "internal_retries": retries,
            "unique_puzzles": len(identities),
        }
        report.append(stats)
        assert exhausted == 0, stats
        assert len(successes) == SWEEP_PER_DIFFICULTY, stats
        assert len(identities) > 8, stats
        print(
            "Distribution Puzzle sweep "
            f"d{difficulty}: attempts={stats['attempts']} "
            f"successful={stats['successful']} "
            f"exhausted={stats['exhausted']} "
            f"internal_retries={stats['internal_retries']} "
            f"unique_puzzles={stats['unique_puzzles']}"
        )
    elapsed = perf_counter() - started
    print(f"Distribution Puzzle sweep runtime_s={elapsed:.3f}")
    return report, elapsed


def main():
    assert_generated_puzzles_are_valid()
    assert_same_seed_is_reproducible()
    assert_seeds_vary()
    assert_required_examples_exist()
    assert_difficulty_structures_differ()
    assert_invalid_configuration_fails()
    assert_exhausted_budget_fails()
    assert_incorrect_intended_is_rejected()
    assert_ambiguous_and_contradictory_clues_are_rejected()
    assert_invalid_factor_and_oversized_domain_fail()
    assert_blueprint_rejects_hidden_assumptions()
    assert_impossible_assignment_fails()
    assert_generation_sweep()
    print("logical_reasoning_distribution_puzzles tests passed")


if __name__ == "__main__":
    main()
