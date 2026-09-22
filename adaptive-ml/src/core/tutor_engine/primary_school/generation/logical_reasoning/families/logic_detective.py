"""Logic Detective generator.

Difficulty contract
-------------------
The domain is 3 objects × 3 positions. After AllDifferent there are
exactly 6 complete assignments. Difficulty is deduction structure,
not clue count padding and not AllDifferent itself.

AllDifferent is a domain rule. Display clues are only PlacedAt and
NotPlacedAt. The target object is never given by a PlacedAt clue.

Level 1 — direct elimination
    Two display clues: one PlacedAt of a helper object and one
    NotPlacedAt. Remaining complete assignments go 6 → n → 1 with
    n > 1. The target is the last deduced object.

Level 2 — connected elimination
    Three display clues including exactly one PlacedAt. Counts are
    strictly decreasing and unique only after the third clue. At
    least one deduction uses an already established placement
    (occupied-position elimination).

Level 3 — multi-stage elimination
    Three display clues, all NotPlacedAt. No positive placement is
    given. Counts are strictly decreasing and unique only after the
    third clue. Every object's position is deduced. This is feasible
    in 3×3: two exclusions can pin a helper object, and a third
    exclusion finishes the bijection.

The 3×3 domain cannot support a substantially longer forced chain
than three contributing exclusions. Level 3 is that exclusion-only
chain, not a larger grid.
"""

from dataclasses import dataclass, replace
from itertools import combinations, permutations
import random

from src.core.tutor_engine.primary_school.generation.errors import (
    PrimarySchoolGenerationError,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.constraints import (
    candidate_satisfies,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.enumerate import (
    enumerate_candidates,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    AllDifferent,
    FAMILY_LOGIC_DETECTIVE,
    LogicCandidate,
    LogicDomain,
    LogicalPuzzleSpec,
    LogicalReasoningVerificationError,
    NotPlacedAt,
    PlacedAt,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.verify import (
    assert_public_view_is_safe,
    verify_unique_solution,
)


MAX_GENERATION_ATTEMPTS = 32
OBJECTS = ("red", "blue", "green")
POSITIONS = (1, 2, 3)
PUBLIC_LOGIC_KEYS = frozenset(
    {"family", "difficulty", "domain", "clues", "target_object"}
)
PUBLIC_CLUE_KEYS = {
    "placed_at": frozenset({"kind", "item", "position"}),
    "not_placed_at": frozenset({"kind", "item", "position"}),
}
DEDUCTION_KINDS = (
    "direct_placement",
    "exclude_position",
    "occupied_elimination",
    "only_remaining_position",
    "only_remaining_object",
)


@dataclass(frozen=True)
class DeductionStep:
    step_number: int
    kind: str
    item: str
    position: int
    before_positions: tuple[int, ...]
    after_positions: tuple[int, ...]
    uses_clues: tuple[int, ...]
    uses_steps: tuple[int, ...]


@dataclass(frozen=True)
class DeductionBlueprint:
    template_id: str
    steps: tuple[DeductionStep, ...]


@dataclass(frozen=True)
class LogicDetectivePuzzle:
    spec: LogicalPuzzleSpec
    intended: LogicCandidate
    difficulty: int
    target_object: str
    target_position: int
    blueprint: DeductionBlueprint
    elimination: tuple[int, ...]
    attempts_used: int = 1

    @property
    def family(self) -> str:
        return self.spec.family

    def public_view(self) -> dict:
        domain = self.spec.domain
        view = {
            "family": FAMILY_LOGIC_DETECTIVE,
            "difficulty": self.difficulty,
            "domain": {
                "type": "logic",
                "objects": domain.objects,
                "positions": domain.positions,
                "all_different": True,
            },
            "clues": tuple(
                _public_clue(constraint)
                for constraint in _display_clues(self.spec)
            ),
            "target_object": self.target_object,
        }
        extra = set(view) - PUBLIC_LOGIC_KEYS
        if extra:
            raise LogicalReasoningVerificationError(
                "private_leak",
                "Public Logic Detective view has extra fields: "
                + ", ".join(sorted(extra)),
            )
        assert_public_view_is_safe(view)
        return view


def generate_logic_detective(
    difficulty: int = 1,
    seed: int | None = None,
    rng: random.Random | None = None,
    max_attempts: int = MAX_GENERATION_ATTEMPTS,
    attempt_builder=None,
) -> LogicDetectivePuzzle:
    if difficulty not in (1, 2, 3):
        raise PrimarySchoolGenerationError(
            f"Unsupported Logic Detective difficulty {difficulty}."
        )
    if max_attempts < 1:
        raise PrimarySchoolGenerationError(
            "Logic Detective generation needs a positive attempt budget."
        )

    chooser = rng or random.Random(seed)
    builder = attempt_builder or _attempt_logic_detective
    last_error = "Could not generate a valid Logic Detective puzzle."

    for attempt in range(1, max_attempts + 1):
        try:
            puzzle = builder(difficulty, chooser)
            _validate_generated(puzzle, difficulty)
            return replace(puzzle, attempts_used=attempt)
        except LogicalReasoningVerificationError as error:
            last_error = f"{error.code}: {error}"

    raise PrimarySchoolGenerationError(last_error)


def verify_blueprint(
    blueprint: DeductionBlueprint,
    spec: LogicalPuzzleSpec,
    intended: LogicCandidate,
) -> dict[str, int]:
    if blueprint.template_id not in (
        "direct_elimination",
        "connected_elimination",
        "exclusion_chain",
    ):
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            f"Unknown Logic Detective template: {blueprint.template_id}",
        )
    if not blueprint.steps:
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            "Blueprint has no deduction steps.",
        )
    display = _display_clues(spec)
    possible = list(_bijections(spec))
    established = {}
    for index, step in enumerate(blueprint.steps, start=1):
        if step.step_number != index:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Blueprint step numbers must be sequential.",
            )
        if step.kind not in DEDUCTION_KINDS:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                f"Unsupported deduction kind: {step.kind}",
            )
        if any(clue_index >= len(display) for clue_index in step.uses_clues):
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                f"Blueprint step {index} references a missing clue.",
            )
        if any(prior >= index or prior < 1 for prior in step.uses_steps):
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                f"Blueprint step {index} has an invalid dependency.",
            )
        before = _positions_of(possible, step.item)
        if before != step.before_positions:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                f"Blueprint step {index} has the wrong candidate positions.",
            )
        possible, established = _apply_verified_step(
            step,
            display,
            possible,
            established,
            intended,
            spec,
        )
        after = _positions_of(possible, step.item)
        if after != step.after_positions:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                f"Blueprint step {index} does not match remaining positions.",
            )
    if len(possible) != 1 or possible[0] != intended:
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            "Blueprint does not end on the verified unique assignment.",
        )
    reconstructed = {
        name: established[name]
        for name in spec.domain.objects
    }
    if reconstructed != dict(intended.assignment):
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            "Blueprint reconstructed assignment is incomplete or wrong.",
        )
    return reconstructed


def _attempt_logic_detective(
    difficulty: int,
    rng: random.Random,
) -> LogicDetectivePuzzle:
    intended = _sample_assignment(rng)
    options = _candidate_puzzles(intended, difficulty)
    if not options:
        raise LogicalReasoningVerificationError(
            "no_template",
            "No Logic Detective clue set met the difficulty contract.",
        )
    chosen = rng.choice(options)
    return _finish_puzzle(intended, chosen, difficulty)


def _sample_assignment(rng: random.Random) -> LogicCandidate:
    perm = list(POSITIONS)
    rng.shuffle(perm)
    return LogicCandidate(tuple(zip(OBJECTS, tuple(perm))))


def _candidate_puzzles(intended: LogicCandidate, difficulty: int) -> list[dict]:
    domain = LogicDomain(objects=OBJECTS, positions=POSITIONS)
    true_clues = _true_display_clues(intended)
    size = 2 if difficulty == 1 else 3
    options = []
    for combo in combinations(true_clues, size):
        for ordered in permutations(combo):
            display = tuple(ordered)
            if not _clues_are_quality(display, intended, difficulty):
                continue
            spec = _spec_from(display, domain)
            bijections = _bijections(spec)
            counts = _elimination_counts(display, bijections, spec)
            remaining = _apply_clues(bijections, display, spec)
            if remaining != (intended,):
                continue
            if not _counts_match_difficulty(counts, difficulty):
                continue
            try:
                blueprint = _build_blueprint(display, spec, intended)
                verify_blueprint(blueprint, spec, intended)
            except LogicalReasoningVerificationError:
                continue
            target = _target_from_blueprint(blueprint, display)
            if target is None:
                continue
            if not _blueprint_matches_difficulty(blueprint, difficulty):
                continue
            options.append(
                {
                    "display": display,
                    "spec": spec,
                    "blueprint": blueprint,
                    "target": target,
                    "counts": counts,
                }
            )
    options.sort(key=_option_sort_key)
    return options


def _finish_puzzle(
    intended: LogicCandidate,
    chosen: dict,
    difficulty: int,
) -> LogicDetectivePuzzle:
    spec = chosen["spec"]
    verify_unique_solution(spec, intended)
    verify_blueprint(chosen["blueprint"], spec, intended)
    target = chosen["target"]
    puzzle = LogicDetectivePuzzle(
        spec=spec,
        intended=intended,
        difficulty=difficulty,
        target_object=target,
        target_position=intended.position_of(target),
        blueprint=chosen["blueprint"],
        elimination=chosen["counts"],
    )
    _check_quality(puzzle)
    _check_difficulty(puzzle, difficulty)
    return puzzle


def _validate_generated(puzzle: LogicDetectivePuzzle, difficulty: int) -> None:
    if puzzle.family != FAMILY_LOGIC_DETECTIVE:
        raise LogicalReasoningVerificationError(
            "invalid_family",
            "Generated puzzle is not Logic Detective.",
        )
    if puzzle.difficulty != difficulty:
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Generated difficulty does not match the request.",
        )
    verify_unique_solution(puzzle.spec, puzzle.intended)
    verify_blueprint(puzzle.blueprint, puzzle.spec, puzzle.intended)
    _check_quality(puzzle)
    _check_difficulty(puzzle, difficulty)
    puzzle.public_view()


def _true_display_clues(intended: LogicCandidate) -> tuple:
    clues = []
    for item in OBJECTS:
        position = intended.position_of(item)
        clues.append(PlacedAt(item, position))
        for other in POSITIONS:
            if other != position:
                clues.append(NotPlacedAt(item, other))
    return tuple(sorted(clues, key=_clue_key))


def _clues_are_quality(
    display: tuple,
    intended: LogicCandidate,
    difficulty: int,
) -> bool:
    if len(set(display)) != len(display):
        return False
    placed = tuple(c for c in display if isinstance(c, PlacedAt))
    excluded = tuple(c for c in display if isinstance(c, NotPlacedAt))
    if difficulty == 1:
        if len(placed) != 1 or len(excluded) != 1:
            return False
    elif difficulty == 2:
        if len(placed) != 1 or len(excluded) != 2:
            return False
    elif len(placed) != 0 or len(excluded) != 3:
        return False
    for clue in display:
        if isinstance(clue, PlacedAt):
            if intended.position_of(clue.item) != clue.position:
                return False
            continue
        if isinstance(clue, NotPlacedAt):
            if intended.position_of(clue.item) == clue.position:
                return False
            continue
        return False
    return True


def _counts_match_difficulty(counts: tuple[int, ...], difficulty: int) -> bool:
    if counts[0] != 6 or counts[-1] != 1:
        return False
    if not _strictly_decreasing(counts):
        return False
    if difficulty == 1:
        return len(counts) == 3 and counts[1] > 1
    return len(counts) == 4 and counts[1] > 1 and counts[2] > 1


def _blueprint_matches_difficulty(
    blueprint: DeductionBlueprint,
    difficulty: int,
) -> bool:
    kinds = tuple(step.kind for step in blueprint.steps)
    if difficulty == 1:
        return (
            blueprint.template_id == "direct_elimination"
            and kinds.count("direct_placement") == 1
        )
    if difficulty == 2:
        return (
            blueprint.template_id == "connected_elimination"
            and kinds.count("direct_placement") == 1
            and "occupied_elimination" in kinds
        )
    return (
        blueprint.template_id == "exclusion_chain"
        and "direct_placement" not in kinds
        and kinds.count("only_remaining_position")
        + kinds.count("only_remaining_object")
        >= 3
    )


def _check_quality(puzzle: LogicDetectivePuzzle) -> None:
    display = _display_clues(puzzle.spec)
    if len(set(display)) != len(display):
        raise LogicalReasoningVerificationError(
            "poor_clues",
            "Logic Detective clues must not be duplicated.",
        )
    for clue in display:
        if not candidate_satisfies(clue, puzzle.intended, puzzle.spec):
            raise LogicalReasoningVerificationError(
                "poor_clues",
                "A Logic Detective clue is false for the intended assignment.",
            )
        if isinstance(clue, PlacedAt) and clue.item == puzzle.target_object:
            raise LogicalReasoningVerificationError(
                "poor_clues",
                "A visible placement clue reveals the target object.",
            )
    target_exclusions = sum(
        1
        for clue in display
        if isinstance(clue, NotPlacedAt)
        and clue.item == puzzle.target_object
    )
    if target_exclusions > 1:
        raise LogicalReasoningVerificationError(
            "poor_clues",
            "The target is placed by exclusions about that object alone.",
        )
    if puzzle.elimination[-1] != 1:
        raise LogicalReasoningVerificationError(
            "poor_clues",
            "Display clues must leave one complete assignment.",
        )


def _check_difficulty(puzzle: LogicDetectivePuzzle, difficulty: int) -> None:
    display = _display_clues(puzzle.spec)
    placed = tuple(c for c in display if isinstance(c, PlacedAt))
    excluded = tuple(c for c in display if isinstance(c, NotPlacedAt))
    if puzzle.spec.domain.objects != OBJECTS:
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Logic Detective objects must be red, blue and green.",
        )
    if puzzle.spec.domain.positions != POSITIONS:
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Logic Detective positions must be 1, 2 and 3.",
        )
    if not _counts_match_difficulty(puzzle.elimination, difficulty):
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Elimination counts do not match the difficulty contract.",
        )
    if not _blueprint_matches_difficulty(puzzle.blueprint, difficulty):
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Deduction structure does not match the difficulty contract.",
        )
    if difficulty == 1 and (len(placed) != 1 or len(excluded) != 1):
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Difficulty 1 needs one placement and one exclusion.",
        )
    if difficulty == 2 and (len(placed) != 1 or len(excluded) != 2):
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Difficulty 2 needs one placement and two exclusions.",
        )
    if difficulty == 3 and (placed or len(excluded) != 3):
        raise LogicalReasoningVerificationError(
            "difficulty_not_met",
            "Difficulty 3 needs three exclusions and no placements.",
        )


def _build_blueprint(
    display: tuple,
    spec: LogicalPuzzleSpec,
    intended: LogicCandidate,
) -> DeductionBlueprint:
    possible = list(_bijections(spec))
    established = {}
    steps = []

    def emit(kind, item, position, before, after, uses_clues, uses_steps):
        step = DeductionStep(
            step_number=len(steps) + 1,
            kind=kind,
            item=item,
            position=position,
            before_positions=before,
            after_positions=after,
            uses_clues=uses_clues,
            uses_steps=uses_steps,
        )
        steps.append(step)
        return step.step_number

    for clue_index, clue in enumerate(display):
        item = clue.item
        before = _positions_of(possible, item)
        if isinstance(clue, PlacedAt):
            possible = [
                candidate
                for candidate in possible
                if candidate.position_of(item) == clue.position
            ]
            after = _positions_of(possible, item)
            placed_step = emit(
                "direct_placement",
                item,
                clue.position,
                before,
                after,
                (clue_index,),
                (),
            )
            established[item] = clue.position
            _emit_occupied(
                emit,
                possible,
                established,
                item,
                clue.position,
                placed_step,
            )
        else:
            possible = [
                candidate
                for candidate in possible
                if candidate.position_of(item) != clue.position
            ]
            after = _positions_of(possible, item)
            emit(
                "exclude_position",
                item,
                clue.position,
                before,
                after,
                (clue_index,),
                (),
            )
        _flush_forced(emit, possible, established, steps)

    if len(possible) != 1:
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            "Clues do not force a unique complete assignment.",
        )
    if len(display) == 2:
        template = "direct_elimination"
    elif any(isinstance(clue, PlacedAt) for clue in display):
        template = "connected_elimination"
    else:
        template = "exclusion_chain"
    return DeductionBlueprint(template, tuple(steps))


def _emit_occupied(
    emit,
    possible,
    established,
    occupier,
    position,
    uses_step,
):
    for item in OBJECTS:
        if item == occupier or item in established:
            continue
        before = _positions_of(possible, item)
        after = tuple(pos for pos in before if pos != position)
        emit(
            "occupied_elimination",
            item,
            position,
            before,
            after,
            (),
            (uses_step,),
        )


def _flush_forced(emit, possible, established, steps):
    changed = True
    while changed:
        changed = False
        placement_steps = tuple(
            step.step_number
            for step in steps
            if step.kind in (
                "direct_placement",
                "only_remaining_position",
                "only_remaining_object",
            )
        )
        for item in OBJECTS:
            if item in established:
                continue
            remaining = _positions_of(possible, item)
            if len(remaining) != 1:
                continue
            position = remaining[0]
            step_number = emit(
                "only_remaining_position",
                item,
                position,
                remaining,
                remaining,
                (),
                placement_steps,
            )
            established[item] = position
            _emit_occupied(
                emit,
                possible,
                established,
                item,
                position,
                step_number,
            )
            changed = True
        for position in POSITIONS:
            holders = [
                item
                for item in OBJECTS
                if item not in established
                and position in _positions_of(possible, item)
            ]
            if len(holders) != 1:
                continue
            item = holders[0]
            before = _positions_of(possible, item)
            step_number = emit(
                "only_remaining_object",
                item,
                position,
                before,
                (position,),
                (),
                placement_steps,
            )
            established[item] = position
            possible[:] = [
                candidate
                for candidate in possible
                if candidate.position_of(item) == position
            ]
            _emit_occupied(
                emit,
                possible,
                established,
                item,
                position,
                step_number,
            )
            changed = True


def _apply_verified_step(
    step: DeductionStep,
    display: tuple,
    possible: list,
    established: dict,
    intended: LogicCandidate,
    spec: LogicalPuzzleSpec,
) -> tuple[list, dict]:
    item = step.item
    position = step.position
    if step.kind == "direct_placement":
        clue = display[step.uses_clues[0]]
        if not isinstance(clue, PlacedAt) or clue.item != item:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Direct placement does not match a placement clue.",
            )
        if clue.position != position:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Direct placement position does not match its clue.",
            )
        updated = [
            candidate
            for candidate in possible
            if candidate_satisfies(clue, candidate, spec)
        ]
        if intended not in updated:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Direct placement eliminated the true assignment.",
            )
        established = dict(established)
        established[item] = position
        return updated, established
    if step.kind == "exclude_position":
        clue = display[step.uses_clues[0]]
        if not isinstance(clue, NotPlacedAt) or clue.item != item:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Exclusion does not match an exclusion clue.",
            )
        if clue.position != position:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Exclusion position does not match its clue.",
            )
        updated = [
            candidate
            for candidate in possible
            if candidate_satisfies(clue, candidate, spec)
        ]
        if intended not in updated:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Exclusion eliminated the true assignment.",
            )
        return updated, established
    if step.kind == "occupied_elimination":
        occupiers = tuple(
            name
            for name, placed in established.items()
            if placed == position and name != item
        )
        if not occupiers:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Occupied elimination has no established occupier.",
            )
        if any(
            candidate.position_of(occupiers[0]) != position
            for candidate in possible
        ):
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Occupied elimination is not forced by current assignments.",
            )
        updated = [
            candidate
            for candidate in possible
            if candidate.position_of(item) != position
        ]
        if intended not in updated:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "Occupied elimination removed the true assignment.",
            )
        return updated, established
    if step.kind == "only_remaining_position":
        remaining = _positions_of(possible, item)
        if remaining != (position,):
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                "The object still has more than one possible position.",
            )
        established = dict(established)
        established[item] = position
        return possible, established
    remaining_holders = tuple(
        name
        for name in OBJECTS
        if name not in established
        and position in _positions_of(possible, name)
    )
    if remaining_holders != (item,):
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            "The position is not forced to a single remaining object.",
        )
    updated = [
        candidate
        for candidate in possible
        if candidate.position_of(item) == position
    ]
    if intended not in updated:
        raise LogicalReasoningVerificationError(
            "invalid_blueprint",
            "Only-remaining-object removed the true assignment.",
        )
    established = dict(established)
    established[item] = position
    return updated, established


def _target_from_blueprint(
    blueprint: DeductionBlueprint,
    display: tuple,
) -> str | None:
    placed = {clue.item for clue in display if isinstance(clue, PlacedAt)}
    deduced = []
    for step in blueprint.steps:
        if step.kind in {
            "direct_placement",
            "only_remaining_position",
            "only_remaining_object",
        } and step.item not in deduced:
            deduced.append(step.item)
    targets = tuple(item for item in deduced if item not in placed)
    if not targets:
        return None
    target = targets[-1]
    exclusions = sum(
        1
        for clue in display
        if isinstance(clue, NotPlacedAt) and clue.item == target
    )
    if exclusions > 1:
        return None
    return target


def _bijections(spec: LogicalPuzzleSpec) -> tuple[LogicCandidate, ...]:
    domain_spec = LogicalPuzzleSpec(
        family=FAMILY_LOGIC_DETECTIVE,
        domain=spec.domain,
        constraints=(AllDifferent(),),
    )
    return tuple(
        candidate
        for candidate in enumerate_candidates(domain_spec)
        if candidate_satisfies(AllDifferent(), candidate, domain_spec)
    )


def _elimination_counts(
    display: tuple,
    bijections: tuple[LogicCandidate, ...],
    spec: LogicalPuzzleSpec,
) -> tuple[int, ...]:
    remaining = bijections
    counts = [len(remaining)]
    for clue in display:
        remaining = _apply_clues(remaining, (clue,), spec)
        counts.append(len(remaining))
    return tuple(counts)


def _apply_clues(
    candidates: tuple[LogicCandidate, ...],
    clues: tuple,
    spec: LogicalPuzzleSpec,
) -> tuple[LogicCandidate, ...]:
    remaining = candidates
    for clue in clues:
        remaining = tuple(
            candidate
            for candidate in remaining
            if candidate_satisfies(clue, candidate, spec)
        )
    return remaining


def _positions_of(possible: list, item: str) -> tuple[int, ...]:
    found = []
    for candidate in possible:
        position = candidate.position_of(item)
        if position not in found:
            found.append(position)
    return tuple(sorted(found))


def _spec_from(display: tuple, domain: LogicDomain) -> LogicalPuzzleSpec:
    return LogicalPuzzleSpec(
        family=FAMILY_LOGIC_DETECTIVE,
        domain=domain,
        constraints=(AllDifferent(),) + display,
    )


def _display_clues(spec: LogicalPuzzleSpec) -> tuple:
    return tuple(
        constraint
        for constraint in spec.constraints
        if not isinstance(constraint, AllDifferent)
    )


def _strictly_decreasing(counts: tuple[int, ...]) -> bool:
    return all(
        counts[index] > counts[index + 1]
        for index in range(len(counts) - 1)
    )


def _clue_key(clue) -> tuple:
    if isinstance(clue, PlacedAt):
        return ("placed_at", clue.item, clue.position)
    return ("not_placed_at", clue.item, clue.position)


def _option_sort_key(option: dict) -> tuple:
    return tuple(_clue_key(clue) for clue in option["display"]) + (
        option["target"],
    )


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
