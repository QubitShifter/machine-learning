import random

from src.core.tutor_engine.primary_school.generation.errors import (
    PrimarySchoolGenerationError,
)
from src.core.tutor_engine.primary_school.generation.word_problems.compile import (
    compile_story_problem,
)
from src.core.tutor_engine.primary_school.generation.word_problems.templates import (
    templates_for_difficulty,
)
from src.core.tutor_engine.primary_school.generation.word_problems.verify import (
    verify_word_problem,
)
from src.core.tutor_engine.primary_school.problem_types import (
    PrimarySchoolProblem,
)


MAX_GENERATION_ATTEMPTS = 24


def generate_word_problem(
    difficulty: int = 1,
    seed: int | None = None,
    rng: random.Random | None = None,
    language: str = "en",
    max_attempts: int = MAX_GENERATION_ATTEMPTS,
    attempt_builder=None,
) -> PrimarySchoolProblem:
    if difficulty not in (1, 2, 3):
        raise PrimarySchoolGenerationError(
            f"Unsupported story-problem difficulty {difficulty}."
        )

    chooser = rng or random.Random(seed)
    builder = attempt_builder or _attempt_word_problem
    last_error = "Could not generate a valid story problem."

    for _ in range(max_attempts):
        try:
            problem = builder(difficulty, chooser)
            verify_word_problem(problem)
            from src.core.tutor_engine.primary_school.generation.localize import (
                localize_generated_primary_school,
            )

            localized = localize_generated_primary_school(
                problem,
                language,
            )
            verify_word_problem(localized)
            return localized
        except ValueError as error:
            last_error = str(error)

    raise PrimarySchoolGenerationError(last_error)


def _attempt_word_problem(
    difficulty: int,
    rng: random.Random,
) -> PrimarySchoolProblem:
    templates = templates_for_difficulty(difficulty)
    template = rng.choice(templates)
    slots = template.sampler(rng)
    return compile_story_problem(template, slots, difficulty)
