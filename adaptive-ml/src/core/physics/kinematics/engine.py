from src.core.i18n.kinematics import kt
from src.core.i18n.locale import normalize_locale
from src.core.physics.kinematics.checker import (
    evaluate_step,
)
from src.core.physics.kinematics.models import (
    KinematicsProblem,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
    TutorResponse,
)


class KinematicsTutorEngine:
    def __init__(
        self,
        problem: KinematicsProblem,
    ):
        self.problem = problem
        self.index = 0
        self.attempts = [0] * problem.total_steps()
        self.hints = [0] * problem.total_steps()

    def get_current_response(self) -> TutorResponse:
        if self._is_complete():
            return self._complete_response()

        step = self.problem.steps[self.index]
        return TutorResponse(
            status="waiting_for_answer",
            feedback=step.prompt,
            current_step=self.index + 1,
            total_steps=self.problem.total_steps(),
            completed=False,
            hint_available=True,
            expected_input_type=step.input_type,
            metadata=self._metadata(
                {
                    "step_kind": step.kind,
                    "quantity": step.quantity,
                    "formula_id": step.formula_id,
                }
            ),
        )

    def submit(
        self,
        submission: StudentSubmission,
    ) -> TutorResponse:
        if self._is_complete():
            return self.get_current_response()

        step = self.problem.steps[self.index]
        self.attempts[self.index] += 1
        evaluation = evaluate_step(
            self.problem,
            step,
            submission.answer,
        )

        if evaluation["correct"]:
            completed_step = self.index + 1
            self.index += 1
            if self._is_complete():
                response = self._complete_response()
                response.metadata["completed_step"] = (
                    completed_step
                )
                return response

            next_step = self.problem.steps[self.index]
            return TutorResponse(
                status="correct",
                feedback=evaluation["feedback"],
                suggestion=kt(
                    self._language(),
                    "continue",
                ),
                current_step=self.index + 1,
                total_steps=self.problem.total_steps(),
                completed=False,
                hint_available=True,
                expected_input_type=next_step.input_type,
                metadata=self._metadata(
                    {
                        "completed_step": completed_step,
                        "next_prompt": next_step.prompt,
                        "step_kind": next_step.kind,
                    }
                ),
            )

        return TutorResponse(
            status="incorrect",
            feedback=evaluation["feedback"],
            suggestion=(
                step.hint
                if self.attempts[self.index] >= 2
                else None
            ),
            current_step=self.index + 1,
            total_steps=self.problem.total_steps(),
            completed=False,
            hint_available=True,
            expected_input_type=step.input_type,
            metadata=self._metadata(
                {
                    "error_type": evaluation["error_type"],
                    "attempts_on_step": (
                        self.attempts[self.index]
                    ),
                }
            ),
        )

    def request_hint(self) -> TutorResponse:
        if self._is_complete():
            return self.get_current_response()

        step = self.problem.steps[self.index]
        self.hints[self.index] += 1
        return TutorResponse(
            status="hint",
            feedback=step.hint,
            current_step=self.index + 1,
            total_steps=self.problem.total_steps(),
            completed=False,
            hint_available=True,
            expected_input_type=step.input_type,
            metadata=self._metadata(
                {
                    "hints_used_on_step": (
                        self.hints[self.index]
                    ),
                }
            ),
        )

    def _is_complete(self) -> bool:
        return self.index >= self.problem.total_steps()

    def _complete_response(self) -> TutorResponse:
        last = self.problem.steps[-1]
        return TutorResponse(
            status="complete",
            feedback=kt(
                self._language(),
                "complete",
            ),
            current_step=self.problem.total_steps(),
            total_steps=self.problem.total_steps(),
            completed=True,
            hint_available=False,
            expected_input_type=last.input_type,
            metadata=self._metadata(
                {
                    "final_velocity": (
                        self.problem.quantities.v
                    ),
                    "displacement": (
                        self.problem.quantities.dx
                    ),
                }
            ),
        )

    def _language(self) -> str:
        return normalize_locale(
            self.problem.metadata.get("language")
        )

    def _metadata(
        self,
        extra: dict,
    ) -> dict:
        return {
            "subject": "physics",
            "domain": "classical_mechanics",
            "topic": "kinematics",
            "problem_id": self.problem.problem_id,
            **self.problem.metadata,
            **extra,
        }
