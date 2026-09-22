"""Number Detective generator.

Difficulty contract
-------------------
Difficulty measures deduction, not the size of the secret number.

Level 1
    Exactly two clues: digit sum and tens-minus-units difference.
    The first clue leaves more than one two-digit candidate.
    Both clues together determine a unique number.
    No divisibility and no interval.

Level 2
    Exactly three clues.
    Digit sum and digit difference are not used together, because that
    pair already unique-determines the number and would make a third
    clue cosmetic.
    Remaining counts are strictly decreasing: 90 -> a -> b -> 1
    with a > 1 and b > 1. Every clue contributes.
    Typical shape: a digit property, a second filter, then an interval
    that isolates the remaining set.

Level 3
    Three or four clues, ending with an interval.
    The first clue is a broad filter: parity or digit order.
    Digit sum and digit difference are not used together.
    Remaining counts are strictly decreasing and unique only at the
    last clue. Four-clue items keep more than one candidate after the
    third clue. Three-clue items must leave at least nine candidates
    after the first clue.

Candidate-elimination counts are private diagnostics. They are not
part of the public puzzle view.
"""

from dataclasses import dataclass, replace
import random

from src.core.tutor_engine.primary_school.generation.errors import (
    PrimarySchoolGenerationError,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.constraints import (
    candidate_satisfies,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    DigitDifference,
    DigitOrder,
    DigitSum,
    DivisibleBy,
    FAMILY_NUMBER_DETECTIVE,
    InInterval,
    LogicalPuzzleSpec,
    LogicalReasoningVerificationError,
    NUMBER_MAX,
    NUMBER_MIN,
    NumberCandidate,
    NumberDomain,
    NumberParity,
    ORDER_TENS_EQ,
    ORDER_TENS_GT,
    ORDER_TENS_LT,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.verify import (
    assert_public_view_is_safe,
    satisfying_candidates,
    verify_unique_solution,
)


MAX_GENERATION_ATTEMPTS = 32
MIN_INTERVAL_SPAN = 20
MAX_INTERVAL_SPAN = 45
GRADE_DIVISORS = (3, 4, 5, 6, 7, 8, 9, 10)
PUBLIC_NUMBER_DETECTIVE_KEYS = frozenset(
    {"family", "difficulty", "domain", "clues"}
)
PUBLIC_CLUE_KEYS = {
    "digit_sum": frozenset({"kind", "total"}),
    "digit_diff": frozenset(
        {"kind", "amount", "absolute_amount", "comparison"}
    ),
    "digit_order": frozenset({"kind", "relation"}),
    "parity": frozenset({"kind", "even"}),
    "divisible_by": frozenset({"kind", "divisor"}),
    "in_interval": frozenset({"kind", "low", "high"}),
}

_D2_PREFIXES = (
    ("digit_sum", "parity"),
    ("digit_sum", "digit_order"),
    ("digit_diff", "parity"),
    ("digit_sum", "divisible_by"),
    ("digit_diff", "divisible_by"),
)
_D3_PREFIXES_FOUR = (
    ("digit_order", "parity", "divisible_by"),
    ("digit_order", "parity", "digit_sum"),
    ("parity", "digit_order", "divisible_by"),
    ("parity", "digit_sum", "digit_order"),
    ("digit_order", "digit_sum", "parity"),
    ("parity", "digit_diff", "divisible_by"),
)
_D3_PREFIXES_THREE = (
    ("parity", "digit_diff"),
    ("parity", "digit_sum"),
    ("digit_order", "digit_sum"),
    ("digit_order", "digit_diff"),
    ("parity", "divisible_by"),
    ("digit_order", "divisible_by"),
)


@dataclass(frozen=True)
class NumberDetectivePuzzle:
    spec: LogicalPuzzleSpec
    intended: NumberCandidate
    difficulty: int
    elimination: tuple[int, ...]
    attempts_used: int = 1

    @property
    def family(self) -> str:
        return self.spec.family

    def public_view(self) -> dict:
        view = {
            "family": FAMILY_NUMBER_DETECTIVE,
            "difficulty": self.difficulty,
            "domain": {
                "type": "number",
                "minimum": NUMBER_MIN,
                "maximum": NUMBER_MAX,
            },
            "clues": tuple(
                _public_clue(constraint)
                for constraint in self.spec.constraints
            ),
        }
        extra = set(view) - PUBLIC_NUMBER_DETECTIVE_KEYS
        if extra:
            raise LogicalReasoningVerificationError(
                "private_leak",
                "Public Number Detective view has extra fields: "
                + ", ".join(sorted(extra)),
            )
        assert_public_view_is_safe(view)
        return view


def generate_number_detective(
    difficulty: int = 1,
    seed: int | None = None,
    rng: random.Random | None = None,
    max_attempts: int = MAX_GENERATION_ATTEMPTS,
    attempt_builder=None,
) -> NumberDetectivePuzzle:
    if difficulty not in (1, 2, 3):
        raise PrimarySchoolGenerationError(
            f"Unsupported Number Detective difficulty {difficulty}."
        )
    if max_attempts < 1:
        raise PrimarySchoolGenerationError(
            "Number Detective generation needs a positive attempt budget."
        )

    chooser = rng or random.Random(seed)
    builder = attempt_builder or _attempt_number_detective
    last_error = "Could not generate a valid Number Detective puzzle."

    for attempt in range(1, max_attempts + 1):
        try:
            puzzle = builder(difficulty, chooser)
            _validate_generated(puzzle, difficulty)
            return replace(puzzle, attempts_used=attempt)
        except LogicalReasoningVerificationError as error:
            last_error = f"{error.code}: {error}"

    raise PrimarySchoolGenerationError(last_error)


def _attempt_number_detective(
    difficulty: int,
    rng: random.Random,
) -> NumberDetectivePuzzle:
    value = rng.randint(NUMBER_MIN, NUMBER_MAX)
    return _build_from_intended(difficulty, NumberCandidate(value), rng)


def _build_from_intended(
    difficulty: int,
    intended: NumberCandidate,
    rng: random.Random,
) -> NumberDetectivePuzzle:
    if difficulty == 1:
        constraints = _clues_difficulty_one(intended)
    elif difficulty == 2:
        constraints = _clues_with_interval(intended, rng, _D2_PREFIXES)
    else:
        constraints = _clues_difficulty_three(intended, rng)
    spec = LogicalPuzzleSpec(
        family=FAMILY_NUMBER_DETECTIVE,
        domain=NumberDomain(),
        constraints=constraints,
    )
    verify_unique_solution(spec, intended)
    counts = _elimination_counts(constraints)
    _check_quality(spec, intended, counts)
    _check_difficulty(difficulty, constraints, counts)
    return NumberDetectivePuzzle(
        spec=spec,
        intended=intended,
        difficulty=difficulty,
        elimination=counts,
    )


def _validate_generated(
    puzzle: NumberDetectivePuzzle,
    difficulty: int,
) -> None:
    if puzzle.family != FAMILY_NUMBER_DETECTIVE:
        raise LogicalReasoningVerificationError(
            "invalid_family",
            "Generated puzzle is not Number Detective.",
        )
    if puzzle.difficulty != difficulty:
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Generated difficulty does not match the request.",
        )
    if (
        puzzle.intended.value < NUMBER_MIN
        or puzzle.intended.value > NUMBER_MAX
    ):
        raise LogicalReasoningVerificationError(
            "invalid_candidate",
            "Intended Number Detective answer is not a two-digit number.",
        )
    verify_unique_solution(puzzle.spec, puzzle.intended)
    counts = _elimination_counts(puzzle.spec.constraints)
    _check_quality(puzzle.spec, puzzle.intended, counts)
    _check_difficulty(difficulty, puzzle.spec.constraints, counts)
    puzzle.public_view()


def _clues_difficulty_one(
    intended: NumberCandidate,
) -> tuple:
    digit_sum = DigitSum(intended.tens + intended.units)
    digit_diff = DigitDifference(intended.tens - intended.units)
    if _remaining_count((digit_sum,)) > 1:
        constraints = (digit_sum, digit_diff)
    else:
        constraints = (digit_diff, digit_sum)
    return constraints


def _clues_difficulty_three(
    intended: NumberCandidate,
    rng: random.Random,
) -> tuple:
    for prefixes in (_D3_PREFIXES_FOUR, _D3_PREFIXES_THREE):
        try:
            return _clues_with_interval(intended, rng, prefixes)
        except LogicalReasoningVerificationError as error:
            if error.code != "no_template":
                raise
    raise LogicalReasoningVerificationError(
        "no_template",
        "No Number Detective clue template met the difficulty contract.",
    )


def _clues_with_interval(
    intended: NumberCandidate,
    rng: random.Random,
    prefixes: tuple[tuple[str, ...], ...],
) -> tuple:
    divisor = _choose_divisor(intended.value, rng)
    options = list(prefixes)
    rng.shuffle(options)
    for kinds in options:
        prefix = _instantiate_prefix(kinds, intended, divisor)
        if prefix is None:
            continue
        remaining = _remaining_values(prefix)
        if intended.value not in remaining or len(remaining) < 2:
            continue
        prefix_counts = _elimination_counts(prefix)
        if not _is_strictly_decreasing(prefix_counts):
            continue
        if prefix_counts[-1] <= 1:
            continue
        interval = _isolating_interval(intended.value, remaining, rng)
        if interval is None:
            continue
        return prefix + (interval,)
    raise LogicalReasoningVerificationError(
        "no_template",
        "No Number Detective clue template met the difficulty contract.",
    )


def _instantiate_prefix(
    kinds: tuple[str, ...],
    intended: NumberCandidate,
    divisor: int | None,
) -> tuple | None:
    clues = []
    for kind in kinds:
        if kind == "divisible_by":
            if divisor is None:
                return None
            clues.append(DivisibleBy(divisor))
            continue
        clues.append(_constraint_for_kind(kind, intended))
    return tuple(clues)


def _constraint_for_kind(kind: str, intended: NumberCandidate):
    if kind == "digit_sum":
        return DigitSum(intended.tens + intended.units)
    if kind == "digit_diff":
        return DigitDifference(intended.tens - intended.units)
    if kind == "digit_order":
        if intended.tens > intended.units:
            relation = ORDER_TENS_GT
        elif intended.tens < intended.units:
            relation = ORDER_TENS_LT
        else:
            relation = ORDER_TENS_EQ
        return DigitOrder(relation)
    if kind == "parity":
        return NumberParity(intended.value % 2 == 0)
    raise LogicalReasoningVerificationError(
        "invalid_constraint",
        f"Unsupported Number Detective clue kind: {kind}",
    )


def _choose_divisor(value: int, rng: random.Random) -> int | None:
    choices = [divisor for divisor in GRADE_DIVISORS if value % divisor == 0]
    if not choices:
        return None
    return rng.choice(choices)


def _isolating_interval(
    value: int,
    remaining: tuple[int, ...],
    rng: random.Random,
) -> InInterval | None:
    others = tuple(item for item in remaining if item != value)
    low_limit = NUMBER_MIN
    high_limit = NUMBER_MAX
    below = tuple(item for item in others if item < value)
    above = tuple(item for item in others if item > value)
    if below:
        low_limit = max(low_limit, max(below) + 1)
    if above:
        high_limit = min(high_limit, min(above) - 1)
    if not (low_limit <= value <= high_limit):
        return None
    window = high_limit - low_limit + 1
    if window < MIN_INTERVAL_SPAN:
        return None
    for _ in range(12):
        interval = _sample_interval(
            value,
            low_limit,
            high_limit,
            rng,
        )
        if interval is not None and _interval_is_usable(
            interval,
            value,
            others,
        ):
            return interval
    fallback = _centered_interval(value, low_limit, high_limit)
    if fallback is not None and _interval_is_usable(fallback, value, others):
        return fallback
    return None


def _sample_interval(
    value: int,
    low_limit: int,
    high_limit: int,
    rng: random.Random,
) -> InInterval | None:
    window = high_limit - low_limit + 1
    span = rng.randint(MIN_INTERVAL_SPAN, min(MAX_INTERVAL_SPAN, window))
    min_low = max(low_limit, value - span + 1)
    max_low = min(value, high_limit - span + 1)
    if min_low > max_low:
        return None
    low = rng.randint(min_low, max_low)
    high = low + span - 1
    if high > high_limit:
        high = high_limit
        low = high - span + 1
    if low < low_limit:
        low = low_limit
        high = min(high_limit, low + span - 1)
    return InInterval(low, high)


def _centered_interval(
    value: int,
    low_limit: int,
    high_limit: int,
) -> InInterval | None:
    window = high_limit - low_limit + 1
    span = min(max(MIN_INTERVAL_SPAN, min(30, window)), window)
    low = value - span // 2
    high = low + span - 1
    if low < low_limit:
        low = low_limit
        high = low + span - 1
    if high > high_limit:
        high = high_limit
        low = high - span + 1
    if high - low + 1 < MIN_INTERVAL_SPAN:
        return None
    return InInterval(low, high)


def _interval_is_usable(
    interval: InInterval,
    value: int,
    others: tuple[int, ...],
) -> bool:
    span = interval.high - interval.low + 1
    if span < MIN_INTERVAL_SPAN:
        return False
    if not (interval.low <= value <= interval.high):
        return False
    if any(interval.low <= item <= interval.high for item in others):
        return False
    if interval.low == interval.high:
        return False
    if interval.low == value and value != NUMBER_MIN:
        return False
    if interval.high == value and value != NUMBER_MAX:
        return False
    if interval.low == value and interval.high == value:
        return False
    return True


def _elimination_counts(constraints: tuple) -> tuple[int, ...]:
    counts = [NUMBER_MAX - NUMBER_MIN + 1]
    for index in range(len(constraints)):
        counts.append(_remaining_count(constraints[: index + 1]))
    return tuple(counts)


def _remaining_count(constraints: tuple) -> int:
    return len(satisfying_candidates(_spec_from(constraints)))


def _remaining_values(constraints: tuple) -> tuple[int, ...]:
    return tuple(
        candidate.value
        for candidate in satisfying_candidates(_spec_from(constraints))
    )


def _spec_from(constraints: tuple) -> LogicalPuzzleSpec:
    return LogicalPuzzleSpec(
        family=FAMILY_NUMBER_DETECTIVE,
        domain=NumberDomain(),
        constraints=constraints,
    )


def _is_strictly_decreasing(counts: tuple[int, ...]) -> bool:
    if len(counts) < 2:
        return False
    return all(
        counts[index] > counts[index + 1]
        for index in range(len(counts) - 1)
    )


def _check_quality(
    spec: LogicalPuzzleSpec,
    intended: NumberCandidate,
    counts: tuple[int, ...],
) -> None:
    constraints = spec.constraints
    kinds = tuple(constraint.kind for constraint in constraints)
    if len(set(kinds)) != len(kinds):
        raise LogicalReasoningVerificationError(
            "poor_clues",
            "Number Detective clues must not be duplicated.",
        )
    for constraint in constraints:
        if not candidate_satisfies(constraint, intended, spec):
            raise LogicalReasoningVerificationError(
                "poor_clues",
                "A Number Detective clue is false for the intended answer.",
            )
        if isinstance(constraint, DivisibleBy):
            if constraint.divisor < 2 or constraint.divisor == intended.value:
                raise LogicalReasoningVerificationError(
                    "poor_clues",
                    "Divisibility clue is educationally invalid.",
                )
            if constraint.divisor not in GRADE_DIVISORS:
                raise LogicalReasoningVerificationError(
                    "poor_clues",
                    "Divisor is not age-appropriate.",
                )
        if isinstance(constraint, InInterval):
            others = tuple(
                value
                for value in _remaining_values(
                    tuple(
                        item
                        for item in constraints
                        if item is not constraint
                    )
                )
                if value != intended.value
            )
            if not _interval_is_usable(constraint, intended.value, others):
                raise LogicalReasoningVerificationError(
                    "poor_clues",
                    "Interval clue is too narrow or revealing.",
                )
        if isinstance(constraint, NumberParity) and any(
            isinstance(item, DivisibleBy) and item.divisor == 2
            for item in constraints
        ):
            raise LogicalReasoningVerificationError(
                "poor_clues",
                "Parity and divisibility by 2 duplicate the same fact.",
            )
    if not _is_strictly_decreasing(counts) or counts[-1] != 1:
        raise LogicalReasoningVerificationError(
            "poor_clues",
            "Clues must strictly narrow the domain to one answer.",
        )
    if counts[0] != NUMBER_MAX - NUMBER_MIN + 1 or counts[1] <= 1:
        raise LogicalReasoningVerificationError(
            "poor_clues",
            "The first clue must not uniquely determine the answer.",
        )


def _check_difficulty(
    difficulty: int,
    constraints: tuple,
    counts: tuple[int, ...],
) -> None:
    kinds = frozenset(constraint.kind for constraint in constraints)
    has_sum_and_diff = "digit_sum" in kinds and "digit_diff" in kinds
    if difficulty == 1:
        if len(constraints) != 2 or kinds != {"digit_sum", "digit_diff"}:
            raise LogicalReasoningVerificationError(
                "difficulty_not_met",
                "Difficulty 1 needs digit sum and digit difference.",
            )
        return
    if has_sum_and_diff:
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Higher-difficulty puzzles cannot use sum and difference together.",
        )
    first_kind = constraints[0].kind
    last_kind = constraints[-1].kind
    if difficulty == 2:
        if (
            len(constraints) != 3
            or last_kind != "in_interval"
            or first_kind not in {"digit_sum", "digit_diff"}
            or counts[2] <= 1
        ):
            raise LogicalReasoningVerificationError(
                "difficulty_not_met",
                "Difficulty 2 needs three contributing clues "
                "starting from a digit sum or difference.",
            )
        return
    if (
        last_kind != "in_interval"
        or first_kind not in {"digit_order", "parity"}
        or len(constraints) not in (3, 4)
        or counts[2] <= 1
        or (len(constraints) == 4 and counts[3] <= 1)
        or (len(constraints) == 3 and counts[1] < 9)
    ):
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Difficulty 3 needs a broad first clue and an isolating interval.",
        )


def _public_clue(constraint) -> dict:
    if isinstance(constraint, DigitDifference):
        amount = constraint.amount
        if amount > 0:
            comparison = "tens_greater"
        elif amount < 0:
            comparison = "units_greater"
        else:
            comparison = "equal"
        return {
            "kind": constraint.kind,
            "amount": amount,
            "absolute_amount": abs(amount),
            "comparison": comparison,
        }
    payload = {"kind": constraint.kind}
    for name, value in vars(constraint).items():
        if name == "kind":
            continue
        payload[name] = value
    allowed = PUBLIC_CLUE_KEYS.get(constraint.kind)
    if allowed is not None and set(payload) - allowed:
        raise LogicalReasoningVerificationError(
            "private_leak",
            f"Public clue {constraint.kind} has extra fields.",
        )
    return payload
