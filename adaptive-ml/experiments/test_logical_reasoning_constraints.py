from src.core.tutor_engine.primary_school.generation.logical_reasoning import (
    AllDifferent,
    DigitDifference,
    DigitOrder,
    DigitSum,
    DistMoreThan,
    DistTimes,
    DistTotal,
    DistributionCandidate,
    DistributionDomain,
    DivisibleBy,
    FAMILY_DISTRIBUTION,
    FAMILY_LOGIC_DETECTIVE,
    FAMILY_NUMBER_DETECTIVE,
    InInterval,
    LogicCandidate,
    LogicDomain,
    LogicalPuzzleSpec,
    LogicalReasoningVerificationError,
    NumberCandidate,
    NumberDomain,
    NumberParity,
    NotPlacedAt,
    PRIVATE_PUZZLE_FIELDS,
    PlacedAt,
    assert_public_view_is_safe,
    candidate_satisfies,
    enumerate_candidates,
    satisfying_candidates,
    validate_spec,
    verify_unique_solution,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    HARD_MAX_DISTRIBUTION_QUANTITY,
    NUMBER_MAX,
    NUMBER_MIN,
    ORDER_TENS_EQ,
    ORDER_TENS_GT,
    ORDER_TENS_LT,
)


NUMBER_DOMAIN = NumberDomain()
DIST_NAMES = ("first", "second", "third")
LOGIC_OBJECTS = ("red", "green", "blue")
LOGIC_POSITIONS = (1, 2, 3)


def expect_code(code, fn):
    try:
        fn()
    except LogicalReasoningVerificationError as exc:
        assert exc.code == code, (exc.code, code, str(exc))
        return
    raise AssertionError(f"Expected error code {code}")


def number_spec(*constraints):
    return LogicalPuzzleSpec(
        family=FAMILY_NUMBER_DETECTIVE,
        domain=NUMBER_DOMAIN,
        constraints=constraints,
    )


def dist_spec(names, maximum, *constraints, minimum=1):
    return LogicalPuzzleSpec(
        family=FAMILY_DISTRIBUTION,
        domain=DistributionDomain(
            names=names,
            minimum=minimum,
            maximum=maximum,
        ),
        constraints=constraints,
    )


def logic_spec(*constraints, objects=LOGIC_OBJECTS, positions=LOGIC_POSITIONS):
    return LogicalPuzzleSpec(
        family=FAMILY_LOGIC_DETECTIVE,
        domain=LogicDomain(objects=objects, positions=positions),
        constraints=constraints,
    )


def dist_candidate(names, values):
    return DistributionCandidate(tuple(zip(names, values)))


def logic_candidate(objects, positions):
    return LogicCandidate(tuple(zip(objects, positions)))


def assert_number_domain_enumeration():
    spec = number_spec(DigitSum(10))
    candidates = enumerate_candidates(spec)
    values = tuple(item.value for item in candidates)
    assert values == tuple(range(NUMBER_MIN, NUMBER_MAX + 1))
    assert len(candidates) == 90
    assert candidates[0].tens == 1 and candidates[0].units == 0
    assert candidates[-1].tens == 9 and candidates[-1].units == 9


def assert_distribution_enumeration_bounds():
    names = ("left", "right")
    spec = dist_spec(names, 4, DistTotal(5))
    candidates = enumerate_candidates(spec)
    assert len(candidates) == 16
    seen = set()
    for candidate in candidates:
        values = tuple(value for _, value in candidate.quantities)
        assert candidate.quantities[0][0] == "left"
        assert all(1 <= value <= 4 for value in values)
        seen.add(values)
    assert seen == {
        (left, right)
        for left in range(1, 5)
        for right in range(1, 5)
    }


def assert_logic_enumeration_and_all_different():
    spec = logic_spec(AllDifferent())
    candidates = enumerate_candidates(spec)
    assert len(candidates) == 27
    distinct = tuple(
        item
        for item in candidates
        if candidate_satisfies(AllDifferent(), item, spec)
    )
    assert len(distinct) == 6
    positions = tuple(item.positions() for item in distinct)
    assert set(positions) == {
        (1, 2, 3),
        (1, 3, 2),
        (2, 1, 3),
        (2, 3, 1),
        (3, 1, 2),
        (3, 2, 1),
    }


def assert_number_constraint_evaluation():
    spec = number_spec(
        DigitSum(10),
        DigitDifference(2),
        DigitOrder(ORDER_TENS_GT),
        NumberParity(True),
        DivisibleBy(4),
        InInterval(60, 70),
    )
    good = NumberCandidate(64)
    near = NumberCandidate(46)
    other = NumberCandidate(65)
    edge_low = NumberCandidate(10)
    edge_high = NumberCandidate(99)

    assert candidate_satisfies(DigitSum(10), good, spec)
    assert not candidate_satisfies(DigitSum(10), other, spec)
    assert candidate_satisfies(DigitDifference(2), good, spec)
    assert candidate_satisfies(DigitDifference(-2), near, spec)
    assert not candidate_satisfies(DigitDifference(2), near, spec)
    assert candidate_satisfies(DigitOrder(ORDER_TENS_GT), good, spec)
    assert candidate_satisfies(DigitOrder(ORDER_TENS_LT), near, spec)
    assert candidate_satisfies(
        DigitOrder(ORDER_TENS_EQ),
        NumberCandidate(55),
        spec,
    )
    assert not candidate_satisfies(DigitOrder(ORDER_TENS_GT), near, spec)
    assert candidate_satisfies(NumberParity(True), good, spec)
    assert not candidate_satisfies(NumberParity(False), good, spec)
    assert candidate_satisfies(DivisibleBy(4), good, spec)
    assert not candidate_satisfies(DivisibleBy(5), good, spec)
    assert candidate_satisfies(InInterval(60, 70), good, spec)
    assert not candidate_satisfies(InInterval(60, 70), near, spec)
    assert candidate_satisfies(DigitSum(1), edge_low, spec)
    assert candidate_satisfies(DigitSum(18), edge_high, spec)
    assert candidate_satisfies(InInterval(10, 10), edge_low, spec)
    assert not candidate_satisfies(InInterval(11, 99), edge_low, spec)


def assert_distribution_constraint_evaluation():
    names = DIST_NAMES
    spec = dist_spec(
        names,
        20,
        DistTotal(24),
        DistTimes("first", "second", 2),
        DistMoreThan("third", "second", 4),
    )
    good = dist_candidate(names, (10, 5, 9))
    bad = dist_candidate(names, (10, 5, 8))
    assert candidate_satisfies(DistTotal(24), good, spec)
    assert not candidate_satisfies(DistTotal(24), bad, spec)
    assert candidate_satisfies(DistTimes("first", "second", 2), good, spec)
    assert not candidate_satisfies(DistTimes("first", "second", 3), good, spec)
    assert candidate_satisfies(DistMoreThan("third", "second", 4), good, spec)
    assert not candidate_satisfies(DistMoreThan("third", "second", 4), bad, spec)


def assert_logic_constraint_evaluation():
    spec = logic_spec(
        PlacedAt("red", 1),
        NotPlacedAt("green", 1),
        AllDifferent(),
    )
    unique = logic_candidate(LOGIC_OBJECTS, (1, 2, 3))
    swapped = logic_candidate(LOGIC_OBJECTS, (1, 3, 2))
    collision = logic_candidate(LOGIC_OBJECTS, (1, 1, 2))
    assert candidate_satisfies(PlacedAt("red", 1), unique, spec)
    assert not candidate_satisfies(PlacedAt("red", 2), unique, spec)
    assert candidate_satisfies(NotPlacedAt("green", 1), unique, spec)
    assert not candidate_satisfies(NotPlacedAt("green", 2), unique, spec)
    assert candidate_satisfies(AllDifferent(), unique, spec)
    assert candidate_satisfies(AllDifferent(), swapped, spec)
    assert not candidate_satisfies(AllDifferent(), collision, spec)


def assert_unique_number_solution_is_accepted():
    spec = number_spec(DigitSum(10), DigitDifference(2))
    result = verify_unique_solution(spec, NumberCandidate(64))
    assert result.unique == NumberCandidate(64)
    assert result.satisfying == (NumberCandidate(64),)


def assert_zero_multiple_and_wrong_intended_are_rejected():
    zero = number_spec(DigitSum(18), InInterval(10, 11))
    expect_code(
        "zero_solutions",
        lambda: verify_unique_solution(zero, NumberCandidate(10)),
    )

    many = number_spec(DigitSum(10))
    expect_code(
        "multiple_solutions",
        lambda: verify_unique_solution(many, NumberCandidate(64)),
    )

    unique = number_spec(DigitSum(10), DigitDifference(2))
    expect_code(
        "intended_mismatch",
        lambda: verify_unique_solution(unique, NumberCandidate(46)),
    )


def assert_redundant_clues_do_not_fake_uniqueness():
    redundant = number_spec(DigitSum(10), DigitSum(10), NumberParity(True))
    assert len(satisfying_candidates(redundant)) > 1
    expect_code(
        "multiple_solutions",
        lambda: verify_unique_solution(redundant, NumberCandidate(64)),
    )
    unique = number_spec(
        DigitSum(10),
        DigitDifference(2),
        DigitSum(10),
        NumberParity(True),
    )
    verify_unique_solution(unique, NumberCandidate(64))


def assert_contradictory_clues_are_rejected():
    spec = number_spec(DigitSum(10), DigitSum(11))
    expect_code(
        "zero_solutions",
        lambda: verify_unique_solution(spec, NumberCandidate(64)),
    )


def assert_unique_distribution_solution():
    names = DIST_NAMES
    spec = dist_spec(
        names,
        20,
        DistTotal(24),
        DistTimes("first", "second", 2),
        DistMoreThan("third", "second", 4),
    )
    intended = dist_candidate(names, (10, 5, 9))
    result = verify_unique_solution(spec, intended)
    assert result.unique == intended
    assert len(result.satisfying) == 1


def assert_logic_requires_unique_complete_assignment():
    target_only = logic_spec(PlacedAt("red", 3), AllDifferent())
    satisfying = satisfying_candidates(target_only)
    assert len(satisfying) == 2
    red_positions = {item.position_of("red") for item in satisfying}
    assert red_positions == {3}
    expect_code(
        "multiple_solutions",
        lambda: verify_unique_solution(
            target_only,
            logic_candidate(LOGIC_OBJECTS, (3, 1, 2)),
        ),
    )

    unique = logic_spec(
        PlacedAt("red", 1),
        PlacedAt("green", 2),
        AllDifferent(),
    )
    intended = logic_candidate(LOGIC_OBJECTS, (1, 2, 3))
    result = verify_unique_solution(unique, intended)
    assert result.unique == intended
    assert result.unique.position_of("blue") == 3


def assert_invalid_parameters_fail_closed():
    expect_code(
        "invalid_domain",
        lambda: validate_spec(
            LogicalPuzzleSpec(
                family=FAMILY_NUMBER_DETECTIVE,
                domain=NumberDomain(minimum=11, maximum=99),
                constraints=(DigitSum(10),),
            )
        ),
    )
    expect_code(
        "invalid_constraint",
        lambda: validate_spec(number_spec(DigitSum(0))),
    )
    expect_code(
        "invalid_constraint",
        lambda: validate_spec(number_spec(DigitSum(19))),
    )
    expect_code(
        "invalid_constraint",
        lambda: validate_spec(number_spec(DigitDifference(10))),
    )
    expect_code(
        "invalid_constraint",
        lambda: validate_spec(number_spec(DigitOrder("units_gt_tens"))),
    )
    expect_code(
        "invalid_constraint",
        lambda: validate_spec(number_spec(DivisibleBy(1))),
    )
    expect_code(
        "invalid_constraint",
        lambda: validate_spec(number_spec(DivisibleBy(True))),
    )
    expect_code(
        "invalid_constraint",
        lambda: validate_spec(number_spec(InInterval(20, 10))),
    )
    expect_code(
        "empty_constraints",
        lambda: validate_spec(number_spec()),
    )
    expect_code(
        "invalid_constraint",
        lambda: validate_spec(number_spec(DistTotal(10))),
    )
    expect_code(
        "invalid_domain",
        lambda: validate_spec(
            dist_spec(("only",), 5, DistTotal(5)),
        ),
    )
    expect_code(
        "invalid_domain",
        lambda: validate_spec(
            dist_spec(("left", "right"), 5, DistTotal(5), minimum=0),
        ),
    )
    expect_code(
        "unknown_quantity",
        lambda: validate_spec(
            dist_spec(("left", "right"), 5, DistMoreThan("left", "other", 1)),
        ),
    )
    expect_code(
        "invalid_constraint",
        lambda: validate_spec(
            dist_spec(("left", "right"), 5, DistTimes("left", "right", 1)),
        ),
    )
    expect_code(
        "invalid_constraint",
        lambda: validate_spec(
            dist_spec(("left", "right"), 5, DistTimes("left", "right", -2)),
        ),
    )
    expect_code(
        "invalid_constraint",
        lambda: validate_spec(
            dist_spec(("left", "right"), 5, DistMoreThan("left", "left", 1)),
        ),
    )
    expect_code(
        "unknown_object",
        lambda: validate_spec(logic_spec(PlacedAt("yellow", 1))),
    )
    expect_code(
        "unknown_position",
        lambda: validate_spec(logic_spec(NotPlacedAt("red", 4))),
    )
    expect_code(
        "invalid_domain",
        lambda: validate_spec(
            logic_spec(
                AllDifferent(),
                objects=("red", "green"),
                positions=(1, 2),
            )
        ),
    )


def assert_oversized_domains_fail_safely():
    expect_code(
        "domain_too_large",
        lambda: enumerate_candidates(
            dist_spec(DIST_NAMES, 21, DistTotal(24)),
        ),
    )
    expect_code(
        "domain_too_large",
        lambda: validate_spec(
            dist_spec(
                DIST_NAMES,
                HARD_MAX_DISTRIBUTION_QUANTITY + 1,
                DistTotal(24),
            )
        ),
    )


def assert_verification_is_deterministic():
    spec = number_spec(
        DigitSum(10),
        DigitDifference(2),
        NumberParity(True),
        InInterval(10, 99),
    )
    first = verify_unique_solution(spec, NumberCandidate(64))
    second = verify_unique_solution(spec, NumberCandidate(64))
    assert first.unique == second.unique
    assert first.satisfying == second.satisfying
    assert enumerate_candidates(spec) == enumerate_candidates(spec)
    shuffled = number_spec(
        InInterval(10, 99),
        NumberParity(True),
        DigitDifference(2),
        DigitSum(10),
    )
    assert satisfying_candidates(spec) == satisfying_candidates(shuffled)


def assert_public_private_boundary():
    spec = number_spec(DigitSum(10), DigitDifference(2))
    view = spec.public_view()
    assert set(view) == {"family", "domain", "clues"}
    assert PRIVATE_PUZZLE_FIELDS.isdisjoint(view)
    assert "intended" not in view
    assert "solution" not in view
    assert_public_view_is_safe(view)
    for clue in view["clues"]:
        assert "kind" in clue
        assert callable(clue.get("kind")) is False
        assert PRIVATE_PUZZLE_FIELDS.isdisjoint(clue)

    leaked = dict(view)
    leaked["intended"] = NumberCandidate(64)
    expect_code(
        "private_leak",
        lambda: assert_public_view_is_safe(leaked),
    )


def main():
    assert_number_domain_enumeration()
    assert_distribution_enumeration_bounds()
    assert_logic_enumeration_and_all_different()
    assert_number_constraint_evaluation()
    assert_distribution_constraint_evaluation()
    assert_logic_constraint_evaluation()
    assert_unique_number_solution_is_accepted()
    assert_zero_multiple_and_wrong_intended_are_rejected()
    assert_redundant_clues_do_not_fake_uniqueness()
    assert_contradictory_clues_are_rejected()
    assert_unique_distribution_solution()
    assert_logic_requires_unique_complete_assignment()
    assert_invalid_parameters_fail_closed()
    assert_oversized_domains_fail_safely()
    assert_verification_is_deterministic()
    assert_public_private_boundary()
    print("logical_reasoning_constraints tests passed")


if __name__ == "__main__":
    main()
