from src.core.math_input import (
    normalize_student_submission,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
    TutorResponse,
)


class MathInputProbeEngine:
    """
    Minimal shared-session activity for proving the
    MathLive -> LaTeX -> FastAPI -> normalization path.
    """

    problem_title = "Math Input API Probe"
    problem_statement = (
        "Enter a mathematical expression so MAT-PAL can "
        "verify that LaTeX reaches the backend safely."
    )

    def __init__(self):
        self.completed = False
        self.last_submission = None

    def get_current_response(self) -> TutorResponse:
        if self.completed:
            return TutorResponse(
                status="complete",
                feedback=(
                    "MAT-PAL received your mathematical input."
                ),
                current_step=1,
                total_steps=1,
                completed=True,
                hint_available=False,
                expected_input_type="math",
                metadata=self.last_submission or {},
            )

        return TutorResponse(
            status="waiting_for_answer",
            feedback=(
                "Enter a mathematical expression such as "
                "e^{-x^2}."
            ),
            current_step=1,
            total_steps=1,
            completed=False,
            hint_available=True,
            expected_input_type="math",
            metadata={
                "activity_type": "math_input_probe",
            },
        )

    def submit(
        self,
        submission: StudentSubmission,
    ) -> TutorResponse:
        normalized = normalize_student_submission(
            submission
        )

        self.last_submission = {
            "received_answer": submission.answer,
            "received_input_type": submission.input_type,
            "normalized_input": normalized.normalized,
            "normalization_ok": normalized.ok,
            "normalization_error": normalized.error,
            "parsed_expression": (
                str(normalized.expression)
                if normalized.expression is not None
                else None
            ),
        }

        if not normalized.ok:
            return TutorResponse(
                status="incorrect",
                feedback=(
                    "MAT-PAL received the submission, but "
                    "could not normalize it as mathematical input."
                ),
                current_step=1,
                total_steps=1,
                completed=False,
                hint_available=True,
                expected_input_type="math",
                suggestion=normalized.error,
                metadata=self.last_submission,
            )

        self.completed = True

        return TutorResponse(
            status="complete",
            feedback=(
                "MAT-PAL received and normalized your "
                "mathematical input."
            ),
            current_step=1,
            total_steps=1,
            completed=True,
            hint_available=False,
            expected_input_type="math",
            metadata=self.last_submission,
        )

    def request_hint(self) -> TutorResponse:
        return TutorResponse(
            status="hint",
            feedback=(
                "Try entering e^(-x^2). The frontend should "
                "send the LaTeX string to FastAPI."
            ),
            current_step=1,
            total_steps=1,
            completed=self.completed,
            hint_available=not self.completed,
            expected_input_type="math",
            metadata={
                "activity_type": "math_input_probe",
            },
        )
