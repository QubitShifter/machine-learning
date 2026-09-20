from src.core.i18n.primary_school import pst
from src.core.tutor_engine.concept_guidance.story_step_guidance import (
    build_story_guidance_context,
    incorrect_story_nudge,
    progressive_hint,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
    TutorResponse,
)

from src.core.tutor_engine.primary_school.checker import (
    evaluate_step_answer,
)

from src.core.tutor_engine.primary_school.problem_types import (
    PrimarySchoolProblem,
)

from src.core.tutor_engine.primary_school.session import (
    PrimarySchoolSession,
)


class PrimarySchoolTutorEngine:
    """
    Frontend/API-friendly tutor engine for one
    primary-school mathematics problem.

    This class contains no input() or print() calls.
    """

    def __init__(
        self,
        problem: PrimarySchoolProblem,
    ):
        self.session = PrimarySchoolSession(
            problem=problem
        )


    @property
    def problem(
        self,
    ) -> PrimarySchoolProblem:
        return self.session.problem


    @property
    def problem_title(self) -> str:
        return self.problem.title

    @property
    def problem_statement(self) -> str:
        return self.problem.problem_text

    @property
    def language(self) -> str:
        return self.problem.language

    def get_current_response(
        self,
    ) -> TutorResponse:
        """
        Return the current tutor state without
        evaluating a student answer.
        """

        step = self.session.get_current_step()

        if step is None:
            return TutorResponse(
                status="complete",
                feedback=pst(
                    self.problem.language,
                    "complete",
                ),
                current_step=(
                    self.problem.get_number_of_steps()
                ),
                total_steps=(
                    self.problem.get_number_of_steps()
                ),
                completed=True,
                hint_available=False,
                metadata={
                    "final_answer": (
                        self.problem.final_answer
                    ),
                },
            )

        return TutorResponse(
            status="waiting_for_answer",
            feedback=step.prompt,
            current_step=step.step_number,
            total_steps=(
                self.problem.get_number_of_steps()
            ),
            completed=False,
            hint_available=self._hint_available(step),
            expected_input_type=_input_type_for_step(step),
            metadata={
                "skill_id": step.skill_id,
                "step_type": (
                    step.step_type.value
                ),
            },
        )


    def submit(
        self,
        submission: StudentSubmission,
    ) -> TutorResponse:
        """
        Evaluate one student submission.
        """

        if self.session.is_complete():
            return self.get_current_response()

        step = self.session.get_current_step()

        self.session.record_attempt()

        evaluation = evaluate_step_answer(
            student_answer=submission.answer,
            expected_answer=(
                step.expected_answer
            ),
            language=self.problem.language,
            answer_format=step.answer_format,
        )

        if evaluation["correct"]:
            completed_step_number = (
                step.step_number
            )

            self.session.advance()

            if self.session.is_complete():
                return TutorResponse(
                    status="complete",
                    feedback=pst(
                        self.problem.language,
                        "complete",
                    ),
                    current_step=(
                        self.problem
                        .get_number_of_steps()
                    ),
                    total_steps=(
                        self.problem
                        .get_number_of_steps()
                    ),
                    completed=True,
                    hint_available=False,
                    metadata={
                        "final_answer": (
                            self.problem.final_answer
                        ),
                        "completed_step": (
                            completed_step_number
                        ),
                    },
                )

            next_step = (
                self.session.get_current_step()
            )

            return TutorResponse(
                status="correct",
                feedback=(
                    evaluation["feedback"]
                ),
                suggestion=pst(
                    self.problem.language,
                    "continue",
                ),
                current_step=(
                    next_step.step_number
                ),
                total_steps=(
                    self.problem.get_number_of_steps()
                ),
                completed=False,
                hint_available=self._hint_available(next_step),
                expected_input_type=_input_type_for_step(
                    next_step
                ),
                metadata={
                    "completed_step": (
                        completed_step_number
                    ),
                    "next_prompt": (
                        next_step.prompt
                    ),
                },
            )

        attempts = (
            self.session
            .get_attempts_for_current_step()
        )
        feedback = evaluation["feedback"]
        if self.problem.topic == "story_problems":
            live = type(
                "Live",
                (),
                {"current_step": step.step_number},
            )()
            story = build_story_guidance_context(
                self.problem,
                live,
                self.problem.language,
            )
            if story is not None:
                feedback = incorrect_story_nudge(story)

        return TutorResponse(
            status="incorrect",
            feedback=feedback,
            suggestion=(
                None
                if self.problem.topic == "story_problems"
                else (
                    step.hint
                    if attempts >= 2
                    else None
                )
            ),
            current_step=(
                step.step_number
            ),
            total_steps=(
                self.problem.get_number_of_steps()
            ),
            completed=False,
            hint_available=self._hint_available(step),
            expected_input_type=_input_type_for_step(step),
            metadata={
                "error_type": (
                    evaluation["error_type"]
                ),
                "attempts_on_step": attempts,
            },
        )


    def request_hint(
        self,
    ) -> TutorResponse:
        """
        Return a hint for the current step without
        counting it as a mathematical attempt.
        """

        step = self.session.get_current_step()

        if step is None:
            return self.get_current_response()

        used_before = self.session.get_hints_for_current_step()
        story_exhausted = (
            self.problem.topic == "story_problems"
            and used_before >= 3
        )
        if not story_exhausted:
            self.session.record_hint()
        used = self.session.get_hints_for_current_step()
        if story_exhausted:
            used = used_before + 1
        hint, exhausted, level = _story_or_static_hint(
            self.problem,
            step,
            used,
        )

        return TutorResponse(
            status="hint",
            feedback=hint,
            current_step=step.step_number,
            total_steps=(
                self.problem.get_number_of_steps()
            ),
            completed=False,
            hint_available=not exhausted,
            expected_input_type=_input_type_for_step(step),
            metadata={
                "hints_used_on_step": (
                    self.session.get_hints_for_current_step()
                ),
                "hint_level": level,
                "hint_exhausted": exhausted,
                "hint_counted": not story_exhausted,
            },
        )


    def _hint_available(self, step) -> bool:
        if step is None:
            return False
        if self.problem.topic == "story_problems":
            return self.session.get_hints_for_current_step() < 3
        return step.hint is not None


def _story_or_static_hint(problem, step, used: int):
    if problem.topic == "story_problems":
        live = type("Live", (), {"current_step": step.step_number})()
        story = build_story_guidance_context(
            problem,
            live,
            problem.language,
        )
        if story is not None:
            text, exhausted = progressive_hint(story, used)
            level = 3 if used >= 3 else used
            return text, exhausted, level
    hint = step.hint or pst(problem.language, "no_hint")
    return hint, False, 1


def _input_type_for_step(step) -> str:
    value = getattr(step, "input_type", None)
    if value:
        return value
    return "text"