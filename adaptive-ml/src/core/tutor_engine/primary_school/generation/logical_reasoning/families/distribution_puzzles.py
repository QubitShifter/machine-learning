"""Distribution Puzzles generator.

Difficulty contract
-------------------
Difficulty is the dependency structure of the arithmetic, not the
size of the quantities.

Level 1
    Two named quantities, a total, and one relationship.
    Either a multiplicative clue (times 2 or 3) or an additive clue.
    The blueprint reconstructs the reference quantity in one short
    share calculation, then the related quantity.

Level 2
    Three named quantities, a total, one multiplicative clue and one
    additive clue that share the same reference quantity:
    box_a = factor * box_b and box_c = box_b + extra.
    Both derived quantities fan out from the same reconstructed
    reference.

Level 3
    Three named quantities, a total, and a chain:
    box_a = factor * box_b and box_b = box_c + extra.
    The additive clue's left operand is the multiplicative clue's
    right operand. Reconstruction is sequential: base, then middle,
    then the scaled quantity. The extra must be compensated on more
    than one term, which is a different path from level 2.

Identifiers box_a, box_b and box_c are language-neutral. Operand
roles in DistTimes and DistMoreThan are preserved exactly.
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
    DEFAULT_DISTRIBUTION_MAX,
    DistMoreThan,
    DistTimes,
    DistTotal,
    DistributionCandidate,
    DistributionDomain,
    FAMILY_DISTRIBUTION,
    LogicalPuzzleSpec,
    LogicalReasoningVerificationError,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.verify import (
    assert_public_view_is_safe,
    verify_unique_solution,
)


MAX_GENERATION_ATTEMPTS = 32
TWO_NAMES = ("box_a", "box_b")
THREE_NAMES = ("box_a", "box_b", "box_c")
FACTORS = (2, 3)
EXTRAS = (2, 3, 4, 5, 6)
MIN_QUANTITY = 2
UNIT_NAME = "coeff.unit"
PUBLIC_DISTRIBUTION_KEYS = frozenset(
    {"family", "difficulty", "domain", "clues"}
)
PUBLIC_CLUE_KEYS = {
    "total": frozenset({"kind", "total"}),
    "more_than": frozenset({"kind", "left", "right", "extra"}),
    "times_as_many": frozenset({"kind", "left", "right", "factor"}),
}
SUPPORTED_OPERATIONS = (
    "addition",
    "subtraction",
    "multiplication",
    "exact_division",
)


@dataclass(frozen=True)
class ArithmeticStep:
    step_number: int
    operation: str
    uses: tuple[str, ...]
    produces: str
    purpose: str
    result: int


@dataclass(frozen=True)
class ArithmeticBlueprint:
    template_id: str
    steps: tuple[ArithmeticStep, ...]


@dataclass(frozen=True)
class DistributionPuzzle:
    spec: LogicalPuzzleSpec
    intended: DistributionCandidate
    difficulty: int
    blueprint: ArithmeticBlueprint
    attempts_used: int = 1

    @property
    def family(self) -> str:
        return self.spec.family

    def public_view(self) -> dict:
        domain = self.spec.domain
        view = {
            "family": FAMILY_DISTRIBUTION,
            "difficulty": self.difficulty,
            "domain": {
                "type": "distribution",
                "names": domain.names,
                "minimum": domain.minimum,
                "maximum": domain.maximum,
            },
            "clues": tuple(
                _public_clue(constraint)
                for constraint in self.spec.constraints
            ),
        }
        extra = set(view) - PUBLIC_DISTRIBUTION_KEYS
        if extra:
            raise LogicalReasoningVerificationError(
                "private_leak",
                "Public Distribution Puzzle view has extra fields: "
                + ", ".join(sorted(extra)),
            )
        assert_public_view_is_safe(view)
        return view


def generate_distribution_puzzle(
    difficulty: int = 1,
    seed: int | None = None,
    rng: random.Random | None = None,
    max_attempts: int = MAX_GENERATION_ATTEMPTS,
    attempt_builder=None,
) -> DistributionPuzzle:
    if difficulty not in (1, 2, 3):
        raise PrimarySchoolGenerationError(
            f"Unsupported Distribution Puzzle difficulty {difficulty}."
        )
    if max_attempts < 1:
        raise PrimarySchoolGenerationError(
            "Distribution Puzzle generation needs a positive attempt budget."
        )

    chooser = rng or random.Random(seed)
    builder = attempt_builder or _attempt_distribution_puzzle
    last_error = "Could not generate a valid Distribution Puzzle."

    for attempt in range(1, max_attempts + 1):
        try:
            puzzle = builder(difficulty, chooser)
            _validate_generated(puzzle, difficulty)
            return replace(puzzle, attempts_used=attempt)
        except LogicalReasoningVerificationError as error:
            last_error = f"{error.code}: {error}"

    raise PrimarySchoolGenerationError(last_error)


def verify_blueprint(
    blueprint: ArithmeticBlueprint,
    spec: LogicalPuzzleSpec,
    intended: DistributionCandidate,
) -> dict[str, int]:
    if blueprint.template_id not in (
        "two_multiplicative",
        "two_additive",
        "three_shared_reference",
        "three_chain",
    ):
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            f"Unknown blueprint template: {blueprint.template_id}",
        )
    if not blueprint.steps:
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            "Blueprint has no arithmetic steps.",
        )
    known = _initial_known(spec)
    produced = []
    for index, step in enumerate(blueprint.steps, start=1):
        if step.step_number != index:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Blueprint step numbers must be sequential.",
            )
        if step.operation not in SUPPORTED_OPERATIONS:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                f"Unsupported blueprint operation: {step.operation}",
            )
        if step.produces in known:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                f"Blueprint redefines {step.produces}.",
            )
        try:
            operands = tuple(known[name] for name in step.uses)
        except KeyError as error:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                f"Blueprint step {index} uses an unknown value: {error}.",
            ) from error
        recomputed = _apply_operation(step.operation, operands)
        if recomputed != step.result:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                f"Blueprint step {index} does not recalculate to "
                f"{step.result}.",
            )
        known[step.produces] = recomputed
        produced.append(step.produces)

    reconstructed = {}
    for name, value in intended.quantities:
        key = f"qty.{name}"
        if key not in known:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                f"Blueprint never reconstructs {name}.",
            )
        if known[key] != value:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                f"Blueprint reconstructs {name} incorrectly.",
            )
        reconstructed[name] = known[key]
    if len(reconstructed) != len(intended.quantities):
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            "Blueprint quantity count does not match the assignment.",
        )
    return reconstructed


def _attempt_distribution_puzzle(
    difficulty: int,
    rng: random.Random,
) -> DistributionPuzzle:
    if difficulty == 1:
        if rng.choice((0, 1)) == 0:
            return _build_two_multiplicative(rng)
        return _build_two_additive(rng)
    if difficulty == 2:
        return _build_three_shared_reference(rng)
    return _build_three_chain(rng)


def _build_two_multiplicative(rng: random.Random) -> DistributionPuzzle:
    factor = rng.choice(FACTORS)
    max_b = DEFAULT_DISTRIBUTION_MAX // factor
    if max_b < MIN_QUANTITY:
        raise LogicalReasoningVerificationError(
            "no_template",
            "Multiplicative two-box template is out of bounds.",
        )
    box_b = rng.randint(MIN_QUANTITY, max_b)
    box_a = factor * box_b
    values = {"box_a": box_a, "box_b": box_b}
    constraints = (
        DistTotal(box_a + box_b),
        DistTimes("box_a", "box_b", factor),
    )
    steps = (
        ArithmeticStep(
            1,
            "addition",
            ("clue.factor", UNIT_NAME),
            "share_count",
            "count_shares",
            factor + 1,
        ),
        ArithmeticStep(
            2,
            "exact_division",
            ("clue.total", "share_count"),
            "qty.box_b",
            "reference_quantity",
            box_b,
        ),
        ArithmeticStep(
            3,
            "multiplication",
            ("clue.factor", "qty.box_b"),
            "qty.box_a",
            "scaled_quantity",
            box_a,
        ),
    )
    return _finish_puzzle(
        TWO_NAMES,
        values,
        constraints,
        ArithmeticBlueprint("two_multiplicative", steps),
        1,
    )


def _build_two_additive(rng: random.Random) -> DistributionPuzzle:
    extra = rng.choice(EXTRAS)
    max_b = DEFAULT_DISTRIBUTION_MAX - extra
    if max_b < MIN_QUANTITY:
        raise LogicalReasoningVerificationError(
            "no_template",
            "Additive two-box template is out of bounds.",
        )
    box_b = rng.randint(MIN_QUANTITY, max_b)
    box_a = box_b + extra
    values = {"box_a": box_a, "box_b": box_b}
    constraints = (
        DistTotal(box_a + box_b),
        DistMoreThan("box_a", "box_b", extra),
    )
    remaining = box_a + box_b - extra
    steps = (
        ArithmeticStep(
            1,
            "subtraction",
            ("clue.total", "clue.extra"),
            "remaining_total",
            "remove_extra",
            remaining,
        ),
        ArithmeticStep(
            2,
            "addition",
            (UNIT_NAME, UNIT_NAME),
            "share_count",
            "count_shares",
            2,
        ),
        ArithmeticStep(
            3,
            "exact_division",
            ("remaining_total", "share_count"),
            "qty.box_b",
            "reference_quantity",
            box_b,
        ),
        ArithmeticStep(
            4,
            "addition",
            ("qty.box_b", "clue.extra"),
            "qty.box_a",
            "apply_extra",
            box_a,
        ),
    )
    return _finish_puzzle(
        TWO_NAMES,
        values,
        constraints,
        ArithmeticBlueprint("two_additive", steps),
        1,
    )


def _build_three_shared_reference(rng: random.Random) -> DistributionPuzzle:
    factor = rng.choice(FACTORS)
    extra = rng.choice(EXTRAS)
    max_b = min(
        DEFAULT_DISTRIBUTION_MAX // factor,
        DEFAULT_DISTRIBUTION_MAX - extra,
    )
    if max_b < MIN_QUANTITY:
        raise LogicalReasoningVerificationError(
            "no_template",
            "Shared-reference template is out of bounds.",
        )
    box_b = rng.randint(MIN_QUANTITY, max_b)
    box_a = factor * box_b
    box_c = box_b + extra
    values = {"box_a": box_a, "box_b": box_b, "box_c": box_c}
    total = box_a + box_b + box_c
    remaining = total - extra
    shares = factor + 1 + 1
    constraints = (
        DistTotal(total),
        DistTimes("box_a", "box_b", factor),
        DistMoreThan("box_c", "box_b", extra),
    )
    steps = (
        ArithmeticStep(
            1,
            "subtraction",
            ("clue.total", "clue.extra"),
            "remaining_total",
            "remove_extra",
            remaining,
        ),
        ArithmeticStep(
            2,
            "addition",
            ("clue.factor", UNIT_NAME, UNIT_NAME),
            "share_count",
            "count_shares",
            shares,
        ),
        ArithmeticStep(
            3,
            "exact_division",
            ("remaining_total", "share_count"),
            "qty.box_b",
            "shared_reference",
            box_b,
        ),
        ArithmeticStep(
            4,
            "multiplication",
            ("clue.factor", "qty.box_b"),
            "qty.box_a",
            "scaled_quantity",
            box_a,
        ),
        ArithmeticStep(
            5,
            "addition",
            ("qty.box_b", "clue.extra"),
            "qty.box_c",
            "apply_extra",
            box_c,
        ),
    )
    return _finish_puzzle(
        THREE_NAMES,
        values,
        constraints,
        ArithmeticBlueprint("three_shared_reference", steps),
        2,
    )


def _build_three_chain(rng: random.Random) -> DistributionPuzzle:
    factor = rng.choice(FACTORS)
    extra = rng.choice(EXTRAS)
    max_b = DEFAULT_DISTRIBUTION_MAX // factor
    min_b = extra + MIN_QUANTITY
    if min_b > max_b:
        raise LogicalReasoningVerificationError(
            "no_template",
            "Chain template is out of bounds.",
        )
    box_b = rng.randint(min_b, max_b)
    box_c = box_b - extra
    box_a = factor * box_b
    values = {"box_a": box_a, "box_b": box_b, "box_c": box_c}
    total = box_a + box_b + box_c
    extra_from_a = factor * extra
    extra_total = extra_from_a + extra
    remaining = total - extra_total
    shares = factor + 1 + 1
    constraints = (
        DistTotal(total),
        DistTimes("box_a", "box_b", factor),
        DistMoreThan("box_b", "box_c", extra),
    )
    steps = (
        ArithmeticStep(
            1,
            "multiplication",
            ("clue.factor", "clue.extra"),
            "extra_from_scaled",
            "propagate_extra",
            extra_from_a,
        ),
        ArithmeticStep(
            2,
            "addition",
            ("extra_from_scaled", "clue.extra"),
            "extra_total",
            "combine_extras",
            extra_total,
        ),
        ArithmeticStep(
            3,
            "subtraction",
            ("clue.total", "extra_total"),
            "remaining_total",
            "remove_chain_extras",
            remaining,
        ),
        ArithmeticStep(
            4,
            "addition",
            ("clue.factor", UNIT_NAME, UNIT_NAME),
            "share_count",
            "count_shares",
            shares,
        ),
        ArithmeticStep(
            5,
            "exact_division",
            ("remaining_total", "share_count"),
            "qty.box_c",
            "chain_base",
            box_c,
        ),
        ArithmeticStep(
            6,
            "addition",
            ("qty.box_c", "clue.extra"),
            "qty.box_b",
            "chain_middle",
            box_b,
        ),
        ArithmeticStep(
            7,
            "multiplication",
            ("clue.factor", "qty.box_b"),
            "qty.box_a",
            "scaled_quantity",
            box_a,
        ),
    )
    return _finish_puzzle(
        THREE_NAMES,
        values,
        constraints,
        ArithmeticBlueprint("three_chain", steps),
        3,
    )


def _finish_puzzle(
    names: tuple[str, ...],
    values: dict[str, int],
    constraints: tuple,
    blueprint: ArithmeticBlueprint,
    difficulty: int,
) -> DistributionPuzzle:
    _check_assignment_bounds(values)
    intended = DistributionCandidate(
        quantities=tuple((name, values[name]) for name in names),
    )
    spec = LogicalPuzzleSpec(
        family=FAMILY_DISTRIBUTION,
        domain=DistributionDomain(
            names=names,
            minimum=1,
            maximum=DEFAULT_DISTRIBUTION_MAX,
        ),
        constraints=constraints,
    )
    verify_unique_solution(spec, intended)
    verify_blueprint(blueprint, spec, intended)
    _check_quality(spec, intended)
    _check_difficulty(difficulty, spec, blueprint)
    return DistributionPuzzle(
        spec=spec,
        intended=intended,
        difficulty=difficulty,
        blueprint=blueprint,
    )


def _validate_generated(puzzle: DistributionPuzzle, difficulty: int) -> None:
    if puzzle.family != FAMILY_DISTRIBUTION:
        raise LogicalReasoningVerificationError(
            "invalid_family",
            "Generated puzzle is not a Distribution Puzzle.",
        )
    if puzzle.difficulty != difficulty:
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Generated difficulty does not match the request.",
        )
    verify_unique_solution(puzzle.spec, puzzle.intended)
    verify_blueprint(puzzle.blueprint, puzzle.spec, puzzle.intended)
    _check_quality(puzzle.spec, puzzle.intended)
    _check_difficulty(difficulty, puzzle.spec, puzzle.blueprint)
    puzzle.public_view()


def _check_assignment_bounds(values: dict[str, int]) -> None:
    for name, value in values.items():
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < MIN_QUANTITY
            or value > DEFAULT_DISTRIBUTION_MAX
        ):
            raise LogicalReasoningVerificationError(
                "invalid_candidate",
                f"{name} is outside the Distribution Puzzle bounds.",
            )


def _check_quality(
    spec: LogicalPuzzleSpec,
    intended: DistributionCandidate,
) -> None:
    kinds = tuple(constraint.kind for constraint in spec.constraints)
    if len(set(kinds)) != len(kinds):
        raise LogicalReasoningVerificationError(
            "poor_clues",
            "Distribution clues must not be duplicated.",
        )
    if "total" not in kinds:
        raise LogicalReasoningVerificationError(
            "poor_clues",
            "A Distribution Puzzle needs a total.",
        )
    for constraint in spec.constraints:
        if not candidate_satisfies(constraint, intended, spec):
            raise LogicalReasoningVerificationError(
                "poor_clues",
                "A Distribution clue is false for the intended assignment.",
            )
        if isinstance(constraint, DistTimes) and constraint.factor not in FACTORS:
            raise LogicalReasoningVerificationError(
                "poor_clues",
                "Multiplicative factor is not Grade 4 appropriate.",
            )
        if isinstance(constraint, DistMoreThan) and constraint.extra not in EXTRAS:
            raise LogicalReasoningVerificationError(
                "poor_clues",
                "Additive extra is not Grade 4 appropriate.",
            )
        if isinstance(constraint, DistTimes):
            left = intended.get(constraint.left)
            right = intended.get(constraint.right)
            if left != right * constraint.factor:
                raise LogicalReasoningVerificationError(
                    "poor_clues",
                    "Times clue does not preserve operand direction.",
                )
        if isinstance(constraint, DistMoreThan):
            left = intended.get(constraint.left)
            right = intended.get(constraint.right)
            if left != right + constraint.extra or left <= right:
                raise LogicalReasoningVerificationError(
                    "poor_clues",
                    "More-than clue does not preserve operand direction.",
                )


def _check_difficulty(
    difficulty: int,
    spec: LogicalPuzzleSpec,
    blueprint: ArithmeticBlueprint,
) -> None:
    names = spec.domain.names
    times = tuple(
        item for item in spec.constraints if isinstance(item, DistTimes)
    )
    more = tuple(
        item for item in spec.constraints if isinstance(item, DistMoreThan)
    )
    totals = tuple(
        item for item in spec.constraints if isinstance(item, DistTotal)
    )
    if len(totals) != 1:
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "A Distribution Puzzle needs exactly one total.",
        )
    if difficulty == 1:
        if (
            names != TWO_NAMES
            or len(spec.constraints) != 2
            or len(times) + len(more) != 1
            or blueprint.template_id not in (
                "two_multiplicative",
                "two_additive",
            )
            or len(blueprint.steps) > 4
        ):
            raise LogicalReasoningVerificationError(
                "difficulty_not_met",
                "Difficulty 1 needs two quantities and one relationship.",
            )
        return
    if names != THREE_NAMES or len(times) != 1 or len(more) != 1:
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Higher-difficulty puzzles need three quantities and two relations.",
        )
    if difficulty == 2:
        if (
            blueprint.template_id != "three_shared_reference"
            or more[0].right != times[0].right
            or more[0].left == times[0].right
            or "shared_reference" not in tuple(
                step.purpose for step in blueprint.steps
            )
            or len(blueprint.steps) != 5
        ):
            raise LogicalReasoningVerificationError(
                "difficulty_not_met",
                "Difficulty 2 needs a shared-reference reconstruction.",
            )
        return
    if (
        blueprint.template_id != "three_chain"
        or more[0].left != times[0].right
        or more[0].right == times[0].right
        or "chain_base" not in tuple(step.purpose for step in blueprint.steps)
        or "chain_middle" not in tuple(step.purpose for step in blueprint.steps)
        or len(blueprint.steps) < 7
    ):
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Difficulty 3 needs a chained reconstruction.",
        )


def _initial_known(spec: LogicalPuzzleSpec) -> dict[str, int]:
    known = {UNIT_NAME: 1}
    for constraint in spec.constraints:
        if isinstance(constraint, DistTotal):
            known["clue.total"] = constraint.total
        elif isinstance(constraint, DistTimes):
            known["clue.factor"] = constraint.factor
        elif isinstance(constraint, DistMoreThan):
            known["clue.extra"] = constraint.extra
        else:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Blueprint cannot use an unsupported clue type.",
            )
    return known


def _apply_operation(operation: str, operands: tuple[int, ...]) -> int:
    if any(
        not isinstance(value, int) or isinstance(value, bool)
        for value in operands
    ):
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            "Blueprint operands must be integers.",
        )
    if operation == "addition":
        if len(operands) < 2:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Addition needs at least two operands.",
            )
        return sum(operands)
    if len(operands) != 2:
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            f"{operation} needs exactly two operands.",
        )
    left, right = operands
    if operation == "subtraction":
        result = left - right
        if result <= 0:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Subtraction must produce a positive integer.",
            )
        return result
    if operation == "multiplication":
        if left < 1 or right < 1:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Multiplication operands must be positive.",
            )
        return left * right
    if right <= 0 or left % right != 0:
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            "Division must be exact and by a positive integer.",
        )
    result = left // right
    if result < 1:
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            "Division must produce a positive integer.",
        )
    return result


def _public_clue(constraint) -> dict:
    payload = {"kind": constraint.kind}
    for name, value in vars(constraint).items():
        if name == "kind":
            continue
        payload[name] = value
    allowed = PUBLIC_CLUE_KEYS.get(constraint.kind)
    if allowed is not None and set(payload) != allowed:
        raise LogicalReasoningVerificationError(
            "private_leak",
            f"Public clue {constraint.kind} has unexpected fields.",
        )
    return payload
