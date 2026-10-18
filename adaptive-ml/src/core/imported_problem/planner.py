from src.core.imported_problem.contracts import (
    ConfirmedProblem,
    PlannedStep,
    StructuredSolutionPlan,
    UNSUPPORTED_REASON,
)
from src.core.imported_problem.errors import (
    ImportedPlannerUnavailableError,
)
from src.core.imported_problem.parse import parse_solution_plan


class NullImportedProblemPlanner:
    def is_available(self) -> bool:
        return False

    def plan(
        self,
        confirmed: ConfirmedProblem,
    ) -> StructuredSolutionPlan:
        raise ImportedPlannerUnavailableError(
            "Imported problem planner unavailable."
        )


class FakeImportedProblemPlanner:
    def __init__(
        self,
        plan: StructuredSolutionPlan | None = None,
        *,
        available: bool = True,
        error: Exception | None = None,
        raw: str | None = None,
    ):
        self.fixed_plan = plan
        self.available = available
        self.error = error
        self.raw = raw
        self.calls: list[ConfirmedProblem] = []

    def is_available(self) -> bool:
        return self.available

    def plan(
        self,
        confirmed: ConfirmedProblem,
    ) -> StructuredSolutionPlan:
        self.calls.append(confirmed)
        if not self.available:
            raise ImportedPlannerUnavailableError(
                "Imported problem planner unavailable."
            )
        if self.error is not None:
            raise self.error
        if self.raw is not None:
            return parse_solution_plan(self.raw)
        if self.fixed_plan is not None:
            return self.fixed_plan
        return default_plan_for_confirmed(confirmed)


def default_plan_for_confirmed(
    confirmed: ConfirmedProblem,
) -> StructuredSolutionPlan:
    text = " ".join(confirmed.transcription.split())
    language = (
        confirmed.language
        if confirmed.language in {"en", "bg"}
        else "en"
    )
    if text in {"12 + 7", "Compute 12 + 7."}:
        return arithmetic_plan(language)
    if text == "2x + 5 = 17":
        return unknown_number_plan(language)
    if _is_en_story(text):
        return story_plan_en()
    if _is_bg_story(text):
        return story_plan_bg()
    return unsupported_plan()


def arithmetic_plan(language: str) -> StructuredSolutionPlan:
    if language == "bg":
        title = "Аритметична задача"
        instruction = "Колко е 12 + 7?"
        hints = ("Събери 12 и 7.",)
    else:
        title = "Arithmetic problem"
        instruction = "What is 12 + 7?"
        hints = ("Add 12 and 7.",)
    return StructuredSolutionPlan(
        supported=True,
        normalized_topic="arithmetic",
        title=title,
        statement="12 + 7",
        final_answer=19,
        steps=(
            PlannedStep(instruction, 19, hints),
        ),
    )


def unknown_number_plan(language: str) -> StructuredSolutionPlan:
    if language == "bg":
        steps = (
            PlannedStep(
                "Извади 5 от двете страни. Колко е стойността на 2x?",
                12,
                ("Извади 5 от 17.",),
                "2x = 12",
            ),
            PlannedStep(
                "Раздели двете страни на 2. Колко е x?",
                6,
                ("Раздели 12 на 2.",),
                "x = 6",
            ),
        )
        title = "Неизвестно число"
    else:
        steps = (
            PlannedStep(
                "Subtract 5 from both sides. What is the value of 2x?",
                12,
                ("Subtract 5 from 17.",),
                "2x = 12",
            ),
            PlannedStep(
                "Divide both sides by 2. What is x?",
                6,
                ("Divide 12 by 2.",),
                "x = 6",
            ),
        )
        title = "Unknown number"
    return StructuredSolutionPlan(
        supported=True,
        normalized_topic="unknown_numbers",
        title=title,
        statement="2x + 5 = 17",
        final_answer=6,
        steps=steps,
    )


def story_plan_en() -> StructuredSolutionPlan:
    return StructuredSolutionPlan(
        supported=True,
        normalized_topic="story_problems",
        title="Story problem",
        statement=(
            "Maria has 3 times as many apples as Ivan. "
            "Together they have 48. How many does Ivan have?"
        ),
        final_answer=12,
        steps=(
            PlannedStep(
                "How many times as many apples does Maria have as Ivan?",
                3,
                ("Read the comparison in the problem.",),
            ),
            PlannedStep(
                "If Ivan has x apples, how many apples are there together?",
                4,
                ("Maria has 3x, so together they have 4x.",),
            ),
            PlannedStep(
                "How many apples does Ivan have?",
                12,
                ("Divide 48 by 4.",),
            ),
        ),
    )


def story_plan_bg() -> StructuredSolutionPlan:
    return StructuredSolutionPlan(
        supported=True,
        normalized_topic="story_problems",
        title="Текстова задача",
        statement=(
            "Иван има 4 ябълки. Мария има 3 пъти повече ябълки от Иван. "
            "Колко ябълки има Мария?"
        ),
        final_answer=12,
        steps=(
            PlannedStep(
                "Колко ябълки има Иван?",
                4,
                ("Прочети даденото число в условието.",),
            ),
            PlannedStep(
                "Колко ябълки има Мария?",
                12,
                ("Умножи ябълките на Иван по 3.",),
            ),
        ),
    )


def unsupported_plan() -> StructuredSolutionPlan:
    return StructuredSolutionPlan(
        supported=False,
        normalized_topic="unsupported",
        title="",
        statement="",
        final_answer=None,
        steps=(),
        unsupported_reason=UNSUPPORTED_REASON,
    )


def _is_en_story(text: str) -> bool:
    return (
        "Maria has 3 times as many apples as Ivan." in text
        and "Together they have 48." in text
    )


def _is_bg_story(text: str) -> bool:
    return (
        "Иван има 4 ябълки." in text
        and "Мария има 3 пъти повече" in text
    )


_imported_planner = None


def get_imported_planner():
    global _imported_planner
    if _imported_planner is None:
        from src.core.imported_problem.config import (
            build_imported_planner_from_env,
        )

        _imported_planner = build_imported_planner_from_env()
    return _imported_planner


def set_imported_planner(planner) -> None:
    global _imported_planner
    _imported_planner = planner
