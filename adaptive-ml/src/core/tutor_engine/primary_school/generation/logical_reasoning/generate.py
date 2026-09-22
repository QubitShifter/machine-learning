"""Registered Grade 4 logical-reasoning generator.

Family selection
----------------
The public topic is ``logical_reasoning``. Internal families are
``number_detective``, ``distribution_puzzles``, and
``logic_detective``.

Callers may pass an optional ``family``. Existing clients that send
only topic and difficulty keep working.

When ``family`` is omitted:

- If ``seed`` is provided, the family is
  ``LOGICAL_REASONING_FAMILIES[seed % 3]``. Consecutive seeds cycle
  through all three families, so none is unreachable.
- If ``seed`` is omitted, one of the three families is chosen with
  ``random.choice``. That draw is uniform among the three families
  for an unseeded call.

An unsupported family raises ``PrimarySchoolGenerationError``.
"""

from __future__ import annotations

import random

from src.core.tutor_engine.primary_school.generation.errors import (
    PrimarySchoolGenerationError,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.compile import (
    compile_logical_reasoning_puzzle,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.distribution_puzzles import (
    generate_distribution_puzzle,
    verify_blueprint as verify_distribution_blueprint,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.logic_detective import (
    generate_logic_detective,
    verify_blueprint as verify_logic_blueprint,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.number_detective import (
    generate_number_detective,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    FAMILY_DISTRIBUTION,
    FAMILY_LOGIC_DETECTIVE,
    FAMILY_NUMBER_DETECTIVE,
    LogicalReasoningVerificationError,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.verify import (
    verify_unique_solution,
)
from src.core.tutor_engine.primary_school.problem_types import (
    PrimarySchoolProblem,
)


LOGICAL_REASONING_FAMILIES = (
    FAMILY_NUMBER_DETECTIVE,
    FAMILY_DISTRIBUTION,
    FAMILY_LOGIC_DETECTIVE,
)
_FAMILY_GENERATORS = {
    FAMILY_NUMBER_DETECTIVE: generate_number_detective,
    FAMILY_DISTRIBUTION: generate_distribution_puzzle,
    FAMILY_LOGIC_DETECTIVE: generate_logic_detective,
}


def select_logical_reasoning_family(
    family: str | None = None,
    seed: int | None = None,
    rng: random.Random | None = None,
) -> str:
    if family is not None:
        if family not in _FAMILY_GENERATORS:
            raise PrimarySchoolGenerationError(
                "Unsupported logical-reasoning family "
                f"{family}."
            )
        return family
    if seed is not None:
        return LOGICAL_REASONING_FAMILIES[
            seed % len(LOGICAL_REASONING_FAMILIES)
        ]
    chooser = rng or random.Random()
    return chooser.choice(LOGICAL_REASONING_FAMILIES)


def generate_logical_reasoning_problem(
    difficulty: int = 1,
    seed: int | None = None,
    rng: random.Random | None = None,
    language: str = "en",
    family: str | None = None,
) -> PrimarySchoolProblem:
    if difficulty not in (1, 2, 3):
        raise PrimarySchoolGenerationError(
            "Unsupported logical-reasoning difficulty "
            f"{difficulty}."
        )
    selected = select_logical_reasoning_family(
        family,
        seed,
        rng,
    )
    generator = _FAMILY_GENERATORS[selected]
    try:
        puzzle = generator(
            difficulty=difficulty,
            seed=seed,
            rng=rng,
        )
        verify_unique_solution(puzzle.spec, puzzle.intended)
        if selected == FAMILY_DISTRIBUTION:
            verify_distribution_blueprint(
                puzzle.blueprint,
                puzzle.spec,
                puzzle.intended,
            )
        elif selected == FAMILY_LOGIC_DETECTIVE:
            verify_logic_blueprint(
                puzzle.blueprint,
                puzzle.spec,
                puzzle.intended,
            )
        return compile_logical_reasoning_puzzle(
            puzzle,
            language,
        )
    except LogicalReasoningVerificationError as error:
        raise PrimarySchoolGenerationError(
            f"{error.code}: {error}"
        ) from error
