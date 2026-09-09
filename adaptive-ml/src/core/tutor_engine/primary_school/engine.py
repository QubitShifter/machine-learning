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
                feedback=(
                    "Excellent. You solved the problem."
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
            hint_available=(
                step.hint is not None
            ),
            expected_input_type="text",
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
        )

        if evaluation["correct"]:
            completed_step_number = (
                step.step_number
            )

            self.session.advance()

            if self.session.is_complete():
                return TutorResponse(
                    status="complete",
                    feedback=(
                        "Excellent. You solved the problem."
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
                suggestion=(
                    "Good. Let's continue."
                ),
                current_step=(
                    next_step.step_number
                ),
                total_steps=(
                    self.problem.get_number_of_steps()
                ),
                completed=False,
                hint_available=(
                    next_step.hint is not None
                ),
                expected_input_type="text",
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

        return TutorResponse(
            status="incorrect",
            feedback=(
                evaluation["feedback"]
            ),
            suggestion=(
                step.hint
                if attempts >= 2
                else None
            ),
            current_step=(
                step.step_number
            ),
            total_steps=(
                self.problem.get_number_of_steps()
            ),
            completed=False,
            hint_available=(
                step.hint is not None
            ),
            expected_input_type="text",
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

        self.session.record_hint()

        hint = (
            step.hint
            or "No additional hint is available."
        )

        return TutorResponse(
            status="hint",
            feedback=hint,
            current_step=step.step_number,
            total_steps=(
                self.problem.get_number_of_steps()
            ),
            completed=False,
            hint_available=(
                step.hint is not None
            ),
            expected_input_type="text",
            metadata={
                "hints_used_on_step": (
                    self.session
                    .get_hints_for_current_step()
                ),
            },
        )