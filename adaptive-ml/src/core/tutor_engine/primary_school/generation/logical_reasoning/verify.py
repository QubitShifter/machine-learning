"""Independent uniqueness verification for logical puzzles.

Invariant: a puzzle is accepted only when
``len(satisfying_candidates) == 1`` and that candidate equals the
intended solution. For Logic Detective the candidate is a complete
assignment of every object to a position. Matching one asked
position while other objects still permute is not unique.

Verification enumerates the declared finite domain and evaluates
typed constraints. It does not reconstruct a generator's intended
answer.
"""

from dataclasses import dataclass

from src.core.tutor_engine.primary_school.generation.logical_reasoning.constraints import (
    holds_all,
    validate_candidate,
    validate_spec,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.enumerate import (
    enumerate_candidates,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    Candidate,
    LogicalPuzzleSpec,
    LogicalReasoningVerificationError,
    PRIVATE_PUZZLE_FIELDS,
)


@dataclass(frozen=True)
class VerificationResult:
    unique: Candidate
    satisfying: tuple[Candidate, ...]


def satisfying_candidates(
    spec: LogicalPuzzleSpec,
) -> tuple[Candidate, ...]:
    validate_spec(spec)
    return tuple(
        candidate
        for candidate in enumerate_candidates(spec)
        if holds_all(candidate, spec)
    )


def verify_unique_solution(
    spec: LogicalPuzzleSpec,
    intended: Candidate,
) -> VerificationResult:
    """Accept only when exactly one candidate matches the intended solution."""
    satisfying = satisfying_candidates(spec)
    if not satisfying:
        raise LogicalReasoningVerificationError(
            "zero_solutions",
            "No candidate satisfies every constraint.",
        )
    if len(satisfying) != 1:
        raise LogicalReasoningVerificationError(
            "multiple_solutions",
            "More than one candidate satisfies every constraint.",
        )
    unique = satisfying[0]
    validate_candidate(intended, spec)
    if unique != intended:
        raise LogicalReasoningVerificationError(
            "intended_mismatch",
            "The unique solution is not the intended solution.",
        )
    return VerificationResult(
        unique=unique,
        satisfying=satisfying,
    )


def assert_public_view_is_safe(view: dict) -> None:
    leaked = PRIVATE_PUZZLE_FIELDS.intersection(view)
    if leaked:
        raise LogicalReasoningVerificationError(
            "private_leak",
            "Public puzzle view contains private solver fields: "
            + ", ".join(sorted(leaked)),
        )
    for item in view.values():
        _assert_nested_view_is_safe(item)


def _assert_nested_view_is_safe(item) -> None:
    if isinstance(item, dict):
        assert_public_view_is_safe(item)
        return
    if isinstance(item, (tuple, list)):
        for nested in item:
            _assert_nested_view_is_safe(nested)
