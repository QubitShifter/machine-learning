from itertools import permutations
from time import perf_counter

from src.core.tutor_engine.primary_school.generation.errors import (
    PrimarySchoolGenerationError,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning import (
    AllDifferent,
    FAMILY_LOGIC_DETECTIVE,
    LogicCandidate,
    LogicDomain,
    LogicalPuzzleSpec,
    LogicalReasoningVerificationError,
    NotPlacedAt,
    PRIVATE_PUZZLE_FIELDS,
    PlacedAt,
    candidate_satisfies,
    enumerate_candidates,
    generate_logic_detective,
    satisfying_candidates,
    verify_unique_solution,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.logic_detective import (
    OBJECTS,
    POSITIONS,
    PUBLIC_CLUE_KEYS,
    PUBLIC_LOGIC_KEYS,
    DeductionBlueprint,
    DeductionStep,
    LogicDetectivePuzzle,
    verify_blueprint,
)


SWEEP_PER_DIFFICULTY = 100


def expect_generation_error(fn):
    try:
        fn()
    except PrimarySchoolGenerationError:
        return
    raise AssertionError("Expected PrimarySchoolGenerationError")


def independent_bijections():
    return tuple(
        LogicCandidate(tuple(zip(OBJECTS, perm)))
        for perm in permutations(POSITIONS)
    )


def independent_matches(spec):
    matches = []
    for candidate in independent_bijections():
        if all(
            _independent_clue_holds(constraint, candidate)
            for constraint in spec.constraints
        ):
            matches.append(candidate)
    return matches


def _independent_clue_holds(constraint, candidate):
    if constraint.kind == "all_different":
        positions = candidate.positions()
        return len(set(positions)) == len(positions)
    if constraint.kind == "placed_at":
        return candidate.position_of(constraint.item) == constraint.position
    if constraint.kind == "not_placed_at":
        return candidate.position_of(constraint.item) != constraint.position
    raise AssertionError(f"Unsupported clue kind {constraint.kind}")


def display_clues(spec):
    return tuple(
        clue
        for clue in spec.constraints
        if clue.kind != "all_different"
    )


def assert_puzzle_valid(puzzle, difficulty):
    assert puzzle.family == FAMILY_LOGIC_DETECTIVE
    assert puzzle.difficulty == difficulty
    assert puzzle.spec.domain.objects == OBJECTS
    assert puzzle.spec.domain.positions == POSITIONS
    assigned = dict(puzzle.intended.assignment)
    assert set(assigned) == set(OBJECTS)
    assert set(assigned.values()) == set(POSITIONS)
    display = display_clues(puzzle.spec)
    for clue in display:
        assert candidate_satisfies(clue, puzzle.intended, puzzle.spec)
        if clue.kind == "placed_at":
            assert clue.item != puzzle.target_object
    verified = verify_unique_solution(puzzle.spec, puzzle.intended)
    assert verified.unique == puzzle.intended
    assert len(verified.satisfying) == 1
    matches = independent_matches(puzzle.spec)
    assert matches == [puzzle.intended]
    assert satisfying_candidates(puzzle.spec) == (puzzle.intended,)
    reconstructed = verify_blueprint(
        puzzle.blueprint,
        puzzle.spec,
        puzzle.intended,
    )
    assert reconstructed == assigned
    assert reconstructed[puzzle.target_object] == puzzle.target_position
    _assert_difficulty_contract(puzzle, difficulty)
    _assert_public_view_is_private(puzzle)


def _assert_difficulty_contract(puzzle, difficulty):
    display = display_clues(puzzle.spec)
    placed = tuple(c for c in display if c.kind == "placed_at")
    excluded = tuple(c for c in display if c.kind == "not_placed_at")
    counts = puzzle.elimination
    assert counts[0] == 6
    assert counts[-1] == 1
    assert all(counts[i] > counts[i + 1] for i in range(len(counts) - 1))
    kinds = tuple(step.kind for step in puzzle.blueprint.steps)
    if difficulty == 1:
        assert len(display) == 2
        assert len(placed) == 1 and len(excluded) == 1
        assert counts[1] > 1
        assert puzzle.blueprint.template_id == "direct_elimination"
        assert kinds.count("direct_placement") == 1
        return
    assert len(display) == 3
    assert counts[1] > 1 and counts[2] > 1
    if difficulty == 2:
        assert len(placed) == 1 and len(excluded) == 2
        assert puzzle.blueprint.template_id == "connected_elimination"
        assert "occupied_elimination" in kinds
        return
    assert placed == ()
    assert len(excluded) == 3
    assert puzzle.blueprint.template_id == "exclusion_chain"
    assert "direct_placement" not in kinds
    assert (
        kinds.count("only_remaining_position")
        + kinds.count("only_remaining_object")
        >= 3
    )


def _assert_public_view_is_private(puzzle):
    view = puzzle.public_view()
    assert set(view) == PUBLIC_LOGIC_KEYS
    assert PRIVATE_PUZZLE_FIELDS.isdisjoint(view)
    assert "intended" not in view
    assert "blueprint" not in view
    assert "elimination" not in view
    assert "target_position" not in view
    assert puzzle.intended.assignment not in view.values()
    assert view["target_object"] == puzzle.target_object
    for clue in view["clues"]:
        assert set(clue) == PUBLIC_CLUE_KEYS[clue["kind"]]
        assert clue["kind"] != "all_different"


def assert_domain_has_six_permutations():
    spec = LogicalPuzzleSpec(
        family=FAMILY_LOGIC_DETECTIVE,
        domain=LogicDomain(objects=OBJECTS, positions=POSITIONS),
        constraints=(AllDifferent(),),
    )
    raw = enumerate_candidates(spec)
    assert len(raw) == 27
    bijections = independent_bijections()
    assert len(bijections) == 6
    distinct = tuple(
        item
        for item in raw
        if candidate_satisfies(AllDifferent(), item, spec)
    )
    assert set(distinct) == set(bijections)


def assert_generated_puzzles_are_valid():
    for difficulty in (1, 2, 3):
        for seed in range(8):
            puzzle = generate_logic_detective(
                difficulty=difficulty,
                seed=seed,
            )
            assert_puzzle_valid(puzzle, difficulty)


def assert_same_seed_is_reproducible():
    for difficulty in (1, 2, 3):
        first = generate_logic_detective(difficulty=difficulty, seed=9)
        second = generate_logic_detective(difficulty=difficulty, seed=9)
        assert first.spec == second.spec
        assert first.intended == second.intended
        assert first.blueprint == second.blueprint
        assert first.target_object == second.target_object
        assert first.public_view() == second.public_view()


def assert_seeds_vary():
    arrangements = {
        generate_logic_detective(difficulty=2, seed=seed).intended
        for seed in range(16)
    }
    targets = {
        generate_logic_detective(difficulty=2, seed=seed).target_object
        for seed in range(16)
    }
    structures = {
        generate_logic_detective(difficulty=2, seed=seed).spec.constraints
        for seed in range(16)
    }
    assert len(arrangements) > 1
    assert len(targets) > 1
    assert len(structures) > 1


def assert_target_only_uniqueness_is_rejected():
    spec = LogicalPuzzleSpec(
        family=FAMILY_LOGIC_DETECTIVE,
        domain=LogicDomain(objects=OBJECTS, positions=POSITIONS),
        constraints=(
            AllDifferent(),
            PlacedAt("red", 3),
        ),
    )
    intended = LogicCandidate(
        (("red", 3), ("blue", 1), ("green", 2)),
    )
    satisfying = satisfying_candidates(spec)
    assert len(satisfying) == 2
    try:
        verify_unique_solution(spec, intended)
    except LogicalReasoningVerificationError as error:
        assert error.code == "multiple_solutions"
    else:
        raise AssertionError("Target-only uniqueness must be rejected.")


def assert_contradictory_and_invalid_assignments_fail():
    domain = LogicDomain(objects=OBJECTS, positions=POSITIONS)
    contradictory = LogicalPuzzleSpec(
        family=FAMILY_LOGIC_DETECTIVE,
        domain=domain,
        constraints=(
            AllDifferent(),
            PlacedAt("red", 1),
            NotPlacedAt("red", 1),
        ),
    )
    try:
        verify_unique_solution(
            contradictory,
            LogicCandidate((("red", 1), ("blue", 2), ("green", 3))),
        )
    except LogicalReasoningVerificationError as error:
        assert error.code == "zero_solutions"
    else:
        raise AssertionError("Contradictory clues must be rejected.")

    collision = LogicCandidate(
        (("red", 1), ("blue", 1), ("green", 2)),
    )
    unique_spec = LogicalPuzzleSpec(
        family=FAMILY_LOGIC_DETECTIVE,
        domain=domain,
        constraints=(
            AllDifferent(),
            PlacedAt("red", 1),
            PlacedAt("blue", 2),
        ),
    )
    try:
        verify_unique_solution(unique_spec, collision)
    except LogicalReasoningVerificationError as error:
        assert error.code in {"invalid_candidate", "intended_mismatch"}
    else:
        raise AssertionError("A colliding assignment must be rejected.")


def assert_blueprint_rejects_tampered_deduction():
    puzzle = generate_logic_detective(difficulty=1, seed=1)
    first = puzzle.blueprint.steps[0]
    tampered = DeductionStep(
        step_number=first.step_number,
        kind="direct_placement",
        item=first.item,
        position=first.position,
        before_positions=first.before_positions,
        after_positions=first.after_positions,
        uses_clues=(99,),
        uses_steps=(),
    )
    try:
        verify_blueprint(
            DeductionBlueprint(
                puzzle.blueprint.template_id,
                (tampered,) + puzzle.blueprint.steps[1:],
            ),
            puzzle.spec,
            puzzle.intended,
        )
    except LogicalReasoningVerificationError as error:
        assert error.code == "invalid_blueprint"
    else:
        raise AssertionError("Tampered deductions must fail.")


def assert_invalid_configuration_fails():
    expect_generation_error(
        lambda: generate_logic_detective(difficulty=0, seed=1)
    )
    expect_generation_error(
        lambda: generate_logic_detective(difficulty=4, seed=1)
    )
    expect_generation_error(
        lambda: generate_logic_detective(
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
        lambda: generate_logic_detective(
            difficulty=1,
            seed=1,
            max_attempts=2,
            attempt_builder=failing_builder,
        )
    )


def assert_incorrect_intended_is_rejected():
    good = generate_logic_detective(difficulty=1, seed=3)
    pairs = list(good.intended.assignment)
    swapped = LogicCandidate(
        (
            (pairs[0][0], pairs[1][1]),
            (pairs[1][0], pairs[0][1]),
            pairs[2],
        )
    )

    def wrong_intended(difficulty, rng):
        return LogicDetectivePuzzle(
            spec=good.spec,
            intended=swapped,
            difficulty=1,
            target_object=good.target_object,
            target_position=swapped.position_of(good.target_object),
            blueprint=good.blueprint,
            elimination=good.elimination,
        )

    expect_generation_error(
        lambda: generate_logic_detective(
            difficulty=1,
            seed=3,
            max_attempts=1,
            attempt_builder=wrong_intended,
        )
    )


def assert_generation_sweep():
    started = perf_counter()
    for difficulty in (1, 2, 3):
        successes = []
        exhausted = 0
        retries = 0
        for index in range(SWEEP_PER_DIFFICULTY):
            seed = difficulty * 1000 + index
            try:
                puzzle = generate_logic_detective(
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
            (item.intended, item.spec.constraints, item.target_object)
            for item in successes
        }
        arrangements = {item.intended for item in successes}
        print(
            "Logic Detective sweep "
            f"d{difficulty}: attempts={SWEEP_PER_DIFFICULTY} "
            f"successful={len(successes)} "
            f"exhausted={exhausted} "
            f"internal_retries={retries} "
            f"unique_puzzles={len(identities)} "
            f"unique_arrangements={len(arrangements)}"
        )
        assert exhausted == 0
        assert len(successes) == SWEEP_PER_DIFFICULTY
        assert len(identities) > 8
        assert len(arrangements) > 1
    print(
        "Logic Detective sweep runtime_s="
        f"{perf_counter() - started:.3f}"
    )


def main():
    assert_domain_has_six_permutations()
    assert_generated_puzzles_are_valid()
    assert_same_seed_is_reproducible()
    assert_seeds_vary()
    assert_target_only_uniqueness_is_rejected()
    assert_contradictory_and_invalid_assignments_fail()
    assert_blueprint_rejects_tampered_deduction()
    assert_invalid_configuration_fails()
    assert_exhausted_budget_fails()
    assert_incorrect_intended_is_rejected()
    assert_generation_sweep()
    print("logical_reasoning_logic_detective tests passed")


if __name__ == "__main__":
    main()
