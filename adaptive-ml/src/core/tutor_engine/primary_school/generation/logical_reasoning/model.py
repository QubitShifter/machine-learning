from dataclasses import dataclass


FAMILY_NUMBER_DETECTIVE = "number_detective"
FAMILY_DISTRIBUTION = "distribution_puzzles"
FAMILY_LOGIC_DETECTIVE = "logic_detective"

SUPPORTED_FAMILIES = (
    FAMILY_NUMBER_DETECTIVE,
    FAMILY_DISTRIBUTION,
    FAMILY_LOGIC_DETECTIVE,
)

NUMBER_MIN = 10
NUMBER_MAX = 99
DIGIT_TENS = "tens"
DIGIT_UNITS = "units"
SUPPORTED_DIGITS = (DIGIT_TENS, DIGIT_UNITS)

ORDER_TENS_GT = "tens_gt_units"
ORDER_TENS_LT = "tens_lt_units"
ORDER_TENS_EQ = "tens_eq_units"
SUPPORTED_DIGIT_ORDERS = (
    ORDER_TENS_GT,
    ORDER_TENS_LT,
    ORDER_TENS_EQ,
)

DEFAULT_DISTRIBUTION_MAX = 20
HARD_MAX_DISTRIBUTION_QUANTITY = 30
MIN_DISTRIBUTION_BOXES = 2
MAX_DISTRIBUTION_BOXES = 3
MAX_ENUMERATED_CANDIDATES = 8000
LOGIC_SLOT_COUNT = 3

PRIVATE_PUZZLE_FIELDS = frozenset(
    {
        "intended",
        "satisfying",
        "candidates",
        "enumeration",
        "expected_answer",
        "hidden_steps",
        "future_steps",
        "solution",
    }
)


class LogicalReasoningVerificationError(ValueError):
    """Raised when a logical puzzle is malformed or not unique."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class NumberCandidate:
    value: int

    @property
    def tens(self) -> int:
        return self.value // 10

    @property
    def units(self) -> int:
        return self.value % 10


@dataclass(frozen=True)
class DistributionCandidate:
    quantities: tuple[tuple[str, int], ...]

    def get(self, name: str) -> int:
        for slot, value in self.quantities:
            if slot == name:
                return value
        raise LogicalReasoningVerificationError(
            "unknown_quantity",
            f"Unknown quantity: {name}",
        )


@dataclass(frozen=True)
class LogicCandidate:
    assignment: tuple[tuple[str, int], ...]

    def position_of(self, name: str) -> int:
        for obj, position in self.assignment:
            if obj == name:
                return position
        raise LogicalReasoningVerificationError(
            "unknown_object",
            f"Unknown object: {name}",
        )

    def positions(self) -> tuple[int, ...]:
        return tuple(position for _, position in self.assignment)


Candidate = NumberCandidate | DistributionCandidate | LogicCandidate


@dataclass(frozen=True)
class NumberDomain:
    minimum: int = NUMBER_MIN
    maximum: int = NUMBER_MAX


@dataclass(frozen=True)
class DistributionDomain:
    names: tuple[str, ...]
    minimum: int = 1
    maximum: int = DEFAULT_DISTRIBUTION_MAX


@dataclass(frozen=True)
class LogicDomain:
    objects: tuple[str, ...]
    positions: tuple[int, ...]


Domain = NumberDomain | DistributionDomain | LogicDomain


@dataclass(frozen=True)
class DigitSum:
    total: int
    kind: str = "digit_sum"


@dataclass(frozen=True)
class DigitDifference:
    amount: int
    kind: str = "digit_diff"


@dataclass(frozen=True)
class DigitOrder:
    relation: str
    kind: str = "digit_order"


@dataclass(frozen=True)
class NumberParity:
    even: bool
    kind: str = "parity"


@dataclass(frozen=True)
class DivisibleBy:
    divisor: int
    kind: str = "divisible_by"


@dataclass(frozen=True)
class InInterval:
    low: int
    high: int
    kind: str = "in_interval"


@dataclass(frozen=True)
class DistTotal:
    total: int
    kind: str = "total"


@dataclass(frozen=True)
class DistMoreThan:
    left: str
    right: str
    extra: int
    kind: str = "more_than"


@dataclass(frozen=True)
class DistTimes:
    left: str
    right: str
    factor: int
    kind: str = "times_as_many"


@dataclass(frozen=True)
class PlacedAt:
    item: str
    position: int
    kind: str = "placed_at"


@dataclass(frozen=True)
class NotPlacedAt:
    item: str
    position: int
    kind: str = "not_placed_at"


@dataclass(frozen=True)
class AllDifferent:
    kind: str = "all_different"


Constraint = (
    DigitSum
    | DigitDifference
    | DigitOrder
    | NumberParity
    | DivisibleBy
    | InInterval
    | DistTotal
    | DistMoreThan
    | DistTimes
    | PlacedAt
    | NotPlacedAt
    | AllDifferent
)


@dataclass(frozen=True)
class LogicalPuzzleSpec:
    """Public puzzle body. The intended solution is passed separately."""

    family: str
    domain: Domain
    constraints: tuple[Constraint, ...]

    def public_view(self) -> dict:
        return {
            "family": self.family,
            "domain": _public_domain(self.domain),
            "clues": tuple(
                _public_constraint(item)
                for item in self.constraints
            ),
        }


def _public_domain(domain: Domain) -> dict:
    if isinstance(domain, NumberDomain):
        return {
            "type": "number",
            "minimum": domain.minimum,
            "maximum": domain.maximum,
        }
    if isinstance(domain, DistributionDomain):
        return {
            "type": "distribution",
            "names": domain.names,
            "minimum": domain.minimum,
            "maximum": domain.maximum,
        }
    return {
        "type": "logic",
        "objects": domain.objects,
        "positions": domain.positions,
    }


def _public_constraint(constraint: Constraint) -> dict:
    payload = {"kind": constraint.kind}
    for name, value in vars(constraint).items():
        if name == "kind":
            continue
        payload[name] = value
    return payload
