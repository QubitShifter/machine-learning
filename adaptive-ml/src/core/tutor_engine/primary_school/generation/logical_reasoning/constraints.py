from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    AllDifferent,
    Constraint,
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
    HARD_MAX_DISTRIBUTION_QUANTITY,
    InInterval,
    LOGIC_SLOT_COUNT,
    LogicCandidate,
    LogicDomain,
    LogicalPuzzleSpec,
    LogicalReasoningVerificationError,
    MAX_DISTRIBUTION_BOXES,
    MAX_ENUMERATED_CANDIDATES,
    MIN_DISTRIBUTION_BOXES,
    NUMBER_MAX,
    NUMBER_MIN,
    NumberCandidate,
    NumberDomain,
    NumberParity,
    NotPlacedAt,
    ORDER_TENS_EQ,
    ORDER_TENS_GT,
    ORDER_TENS_LT,
    PlacedAt,
    SUPPORTED_DIGIT_ORDERS,
    SUPPORTED_FAMILIES,
)


def validate_spec(spec: LogicalPuzzleSpec) -> None:
    if spec.family not in SUPPORTED_FAMILIES:
        raise LogicalReasoningVerificationError(
            "unknown_family",
            f"Unsupported logical family: {spec.family}",
        )
    _validate_domain(spec)
    if not spec.constraints:
        raise LogicalReasoningVerificationError(
            "empty_constraints",
            "A logical puzzle needs at least one constraint.",
        )
    for constraint in spec.constraints:
        _validate_constraint(constraint, spec)


def validate_candidate(candidate, spec: LogicalPuzzleSpec) -> None:
    validate_spec(spec)
    _validate_candidate(candidate, spec)


def candidate_satisfies(
    constraint: Constraint,
    candidate,
    spec: LogicalPuzzleSpec,
) -> bool:
    validate_candidate(candidate, spec)
    return _evaluate(constraint, candidate, spec)


def holds_all(candidate, spec: LogicalPuzzleSpec) -> bool:
    return all(
        _evaluate(constraint, candidate, spec)
        for constraint in spec.constraints
    )


def _validate_domain(spec: LogicalPuzzleSpec) -> None:
    domain = spec.domain
    if spec.family == FAMILY_NUMBER_DETECTIVE:
        if not isinstance(domain, NumberDomain):
            raise LogicalReasoningVerificationError(
                "invalid_domain",
                "Number Detective needs a number domain.",
            )
        if domain.minimum != NUMBER_MIN or domain.maximum != NUMBER_MAX:
            raise LogicalReasoningVerificationError(
                "invalid_domain",
                "Number Detective domain must be 10 through 99.",
            )
        return
    if spec.family == FAMILY_DISTRIBUTION:
        if not isinstance(domain, DistributionDomain):
            raise LogicalReasoningVerificationError(
                "invalid_domain",
                "Distribution puzzles need a distribution domain.",
            )
        names = domain.names
        if len(names) < MIN_DISTRIBUTION_BOXES or len(names) > MAX_DISTRIBUTION_BOXES:
            raise LogicalReasoningVerificationError(
                "invalid_domain",
                "Distribution puzzles need two or three named quantities.",
            )
        if len(set(names)) != len(names) or any(
            not name or not str(name).isidentifier()
            for name in names
        ):
            raise LogicalReasoningVerificationError(
                "invalid_domain",
                "Distribution quantity names must be unique identifiers.",
            )
        if domain.minimum < 1:
            raise LogicalReasoningVerificationError(
                "invalid_domain",
                "Distribution quantities must be positive.",
            )
        if domain.maximum < domain.minimum:
            raise LogicalReasoningVerificationError(
                "invalid_domain",
                "Distribution maximum is below the minimum.",
            )
        if domain.maximum > HARD_MAX_DISTRIBUTION_QUANTITY:
            raise LogicalReasoningVerificationError(
                "domain_too_large",
                "Distribution maximum exceeds the configured bound.",
            )
        span = domain.maximum - domain.minimum + 1
        estimated = span ** len(names)
        if estimated > MAX_ENUMERATED_CANDIDATES:
            raise LogicalReasoningVerificationError(
                "domain_too_large",
                "Distribution domain would enumerate too many candidates.",
            )
        return
    if not isinstance(domain, LogicDomain):
        raise LogicalReasoningVerificationError(
            "invalid_domain",
            "Logic Detective needs a logic domain.",
        )
    if (
        len(domain.objects) != LOGIC_SLOT_COUNT
        or len(domain.positions) != LOGIC_SLOT_COUNT
    ):
        raise LogicalReasoningVerificationError(
            "invalid_domain",
            "Logic Detective needs three objects and three positions.",
        )
    if len(set(domain.objects)) != LOGIC_SLOT_COUNT:
        raise LogicalReasoningVerificationError(
            "invalid_domain",
            "Logic Detective objects must be unique.",
        )
    if len(set(domain.positions)) != LOGIC_SLOT_COUNT:
        raise LogicalReasoningVerificationError(
            "invalid_domain",
            "Logic Detective positions must be unique.",
        )
    if any(not str(name).isidentifier() for name in domain.objects):
        raise LogicalReasoningVerificationError(
            "invalid_domain",
            "Logic Detective objects must be identifiers.",
        )
    if any(
        not isinstance(position, int) or isinstance(position, bool)
        or position < 1
        for position in domain.positions
    ):
        raise LogicalReasoningVerificationError(
            "invalid_domain",
            "Logic Detective positions must be positive integers.",
        )


def _validate_constraint(constraint: Constraint, spec: LogicalPuzzleSpec) -> None:
    family = spec.family
    if family == FAMILY_NUMBER_DETECTIVE:
        _validate_number_constraint(constraint)
        return
    if family == FAMILY_DISTRIBUTION:
        _validate_distribution_constraint(constraint, spec.domain)
        return
    _validate_logic_constraint(constraint, spec.domain)


def _validate_number_constraint(constraint: Constraint) -> None:
    if isinstance(constraint, DigitSum):
        if not _is_positive_int(constraint.total) or constraint.total > 18:
            raise LogicalReasoningVerificationError(
                "invalid_constraint",
                "Digit sum must be an integer from 1 through 18.",
            )
        return
    if isinstance(constraint, DigitDifference):
        if not _is_int(constraint.amount) or abs(constraint.amount) > 9:
            raise LogicalReasoningVerificationError(
                "invalid_constraint",
                "Digit difference must be an integer from -9 through 9.",
            )
        return
    if isinstance(constraint, DigitOrder):
        if constraint.relation not in SUPPORTED_DIGIT_ORDERS:
            raise LogicalReasoningVerificationError(
                "invalid_constraint",
                "Unsupported digit-order relation.",
            )
        return
    if isinstance(constraint, NumberParity):
        if not isinstance(constraint.even, bool):
            raise LogicalReasoningVerificationError(
                "invalid_constraint",
                "Parity must be a boolean even flag.",
            )
        return
    if isinstance(constraint, DivisibleBy):
        if not _is_positive_int(constraint.divisor) or constraint.divisor < 2:
            raise LogicalReasoningVerificationError(
                "invalid_constraint",
                "Divisor must be an integer greater than or equal to 2.",
            )
        return
    if isinstance(constraint, InInterval):
        if not _is_int(constraint.low) or not _is_int(constraint.high):
            raise LogicalReasoningVerificationError(
                "invalid_constraint",
                "Interval bounds must be integers.",
            )
        if constraint.low > constraint.high:
            raise LogicalReasoningVerificationError(
                "invalid_constraint",
                "Interval low is greater than high.",
            )
        return
    raise LogicalReasoningVerificationError(
        "invalid_constraint",
        "Constraint does not belong to Number Detective.",
    )


def _validate_distribution_constraint(
    constraint: Constraint,
    domain: DistributionDomain,
) -> None:
    names = set(domain.names)
    if isinstance(constraint, DistTotal):
        if not _is_positive_int(constraint.total):
            raise LogicalReasoningVerificationError(
                "invalid_constraint",
                "Distribution total must be a positive integer.",
            )
        return
    if isinstance(constraint, DistMoreThan):
        _require_named_pair(constraint.left, constraint.right, names)
        if not _is_positive_int(constraint.extra):
            raise LogicalReasoningVerificationError(
                "invalid_constraint",
                "Additive extra must be a positive integer.",
            )
        return
    if isinstance(constraint, DistTimes):
        _require_named_pair(constraint.left, constraint.right, names)
        if not _is_positive_int(constraint.factor) or constraint.factor < 2:
            raise LogicalReasoningVerificationError(
                "invalid_constraint",
                "Multiplicative factor must be an integer of at least 2.",
            )
        return
    raise LogicalReasoningVerificationError(
        "invalid_constraint",
        "Constraint does not belong to Distribution Puzzles.",
    )


def _validate_logic_constraint(
    constraint: Constraint,
    domain: LogicDomain,
) -> None:
    objects = set(domain.objects)
    positions = set(domain.positions)
    if isinstance(constraint, AllDifferent):
        return
    if isinstance(constraint, (PlacedAt, NotPlacedAt)):
        if constraint.item not in objects:
            raise LogicalReasoningVerificationError(
                "unknown_object",
                f"Unknown object: {constraint.item}",
            )
        if constraint.position not in positions:
            raise LogicalReasoningVerificationError(
                "unknown_position",
                f"Unknown position: {constraint.position}",
            )
        return
    raise LogicalReasoningVerificationError(
        "invalid_constraint",
        "Constraint does not belong to Logic Detective.",
    )


def _require_named_pair(left: str, right: str, names: set[str]) -> None:
    if left not in names or right not in names:
        raise LogicalReasoningVerificationError(
            "unknown_quantity",
            "Constraint refers to an unknown quantity.",
        )
    if left == right:
        raise LogicalReasoningVerificationError(
            "invalid_constraint",
            "A quantity cannot be related to itself.",
        )


def _validate_candidate(candidate, spec: LogicalPuzzleSpec) -> None:
    domain = spec.domain
    if spec.family == FAMILY_NUMBER_DETECTIVE:
        if not isinstance(candidate, NumberCandidate):
            raise LogicalReasoningVerificationError(
                "invalid_candidate",
                "Number Detective candidate must be a two-digit number.",
            )
        if candidate.value < domain.minimum or candidate.value > domain.maximum:
            raise LogicalReasoningVerificationError(
                "invalid_candidate",
                "Number Detective candidate is outside 10–99.",
            )
        return
    if spec.family == FAMILY_DISTRIBUTION:
        if not isinstance(candidate, DistributionCandidate):
            raise LogicalReasoningVerificationError(
                "invalid_candidate",
                "Distribution candidate must assign named quantities.",
            )
        assigned = tuple(name for name, _ in candidate.quantities)
        if assigned != domain.names:
            raise LogicalReasoningVerificationError(
                "invalid_candidate",
                "Distribution candidate names do not match the domain.",
            )
        for _, value in candidate.quantities:
            if (
                not _is_positive_int(value)
                or value < domain.minimum
                or value > domain.maximum
            ):
                raise LogicalReasoningVerificationError(
                    "invalid_candidate",
                    "Distribution quantity is outside the declared bounds.",
                )
        return
    if not isinstance(candidate, LogicCandidate):
        raise LogicalReasoningVerificationError(
            "invalid_candidate",
            "Logic Detective candidate must assign objects to positions.",
        )
    assigned = tuple(name for name, _ in candidate.assignment)
    if assigned != domain.objects:
        raise LogicalReasoningVerificationError(
            "invalid_candidate",
            "Logic Detective objects do not match the domain.",
        )
    for _, position in candidate.assignment:
        if position not in domain.positions:
            raise LogicalReasoningVerificationError(
                "invalid_candidate",
                "Logic Detective position is not in the domain.",
            )


def _evaluate(constraint: Constraint, candidate, spec: LogicalPuzzleSpec) -> bool:
    if isinstance(candidate, NumberCandidate):
        return _evaluate_number(constraint, candidate)
    if isinstance(candidate, DistributionCandidate):
        return _evaluate_distribution(constraint, candidate)
    return _evaluate_logic(constraint, candidate)


def _evaluate_number(constraint: Constraint, candidate: NumberCandidate) -> bool:
    if isinstance(constraint, DigitSum):
        return candidate.tens + candidate.units == constraint.total
    if isinstance(constraint, DigitDifference):
        return candidate.tens - candidate.units == constraint.amount
    if isinstance(constraint, DigitOrder):
        if constraint.relation == ORDER_TENS_GT:
            return candidate.tens > candidate.units
        if constraint.relation == ORDER_TENS_LT:
            return candidate.tens < candidate.units
        if constraint.relation == ORDER_TENS_EQ:
            return candidate.tens == candidate.units
        return False
    if isinstance(constraint, NumberParity):
        is_even = candidate.value % 2 == 0
        return is_even is constraint.even
    if isinstance(constraint, DivisibleBy):
        return candidate.value % constraint.divisor == 0
    if isinstance(constraint, InInterval):
        return constraint.low <= candidate.value <= constraint.high
    return False


def _evaluate_distribution(
    constraint: Constraint,
    candidate: DistributionCandidate,
) -> bool:
    if isinstance(constraint, DistTotal):
        total = sum(value for _, value in candidate.quantities)
        return total == constraint.total
    if isinstance(constraint, DistMoreThan):
        return candidate.get(constraint.left) == (
            candidate.get(constraint.right) + constraint.extra
        )
    if isinstance(constraint, DistTimes):
        return candidate.get(constraint.left) == (
            candidate.get(constraint.right) * constraint.factor
        )
    return False


def _evaluate_logic(constraint: Constraint, candidate: LogicCandidate) -> bool:
    if isinstance(constraint, AllDifferent):
        positions = candidate.positions()
        return len(set(positions)) == len(positions)
    if isinstance(constraint, PlacedAt):
        return candidate.position_of(constraint.item) == constraint.position
    if isinstance(constraint, NotPlacedAt):
        return candidate.position_of(constraint.item) != constraint.position
    return False


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_positive_int(value) -> bool:
    return _is_int(value) and value > 0
