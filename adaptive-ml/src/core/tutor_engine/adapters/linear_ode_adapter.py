import json
import re

import sympy as sp

from src.core.math_input import (
    MathInputError,
    normalize_math_text,
)
from src.core.tutor_engine.concept_guidance.linear_first_order_guidance import (
    respond_to_linear_concept_question,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
    TutorResponse,
)
from src.core.tutor_engine.linear_first_order_engine import (
    LinearFirstOrderEngine,
)
from src.core.tutor_engine.linear_first_order_session import (
    LinearODEStage,
    LinearODESolutionSession,
)
from src.core.tutor_engine.linear_first_order_verification import (
    LinearFirstOrderVerificationEngine,
    LinearVerificationStage,
)


TOTAL_LINEAR_ODE_STEPS = 8

STAGE_ORDER = [
    LinearODEStage.IDENTIFY_STANDARD_FORM,
    LinearODEStage.IDENTIFY_P_Q,
    LinearODEStage.FIND_INTEGRATING_FACTOR,
    LinearODEStage.MULTIPLY_BY_INTEGRATING_FACTOR,
    LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE,
    LinearODEStage.INTEGRATE_BOTH_SIDES,
    LinearODEStage.SOLVE_FOR_Y,
    LinearODEStage.VERIFY_SOLUTION,
]

STAGE_INPUT_TYPES = {
    LinearODEStage.IDENTIFY_STANDARD_FORM: "text",
    LinearODEStage.IDENTIFY_P_Q: "text",
    LinearODEStage.FIND_INTEGRATING_FACTOR: "math",
    LinearODEStage.MULTIPLY_BY_INTEGRATING_FACTOR: "math",
    LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE: "math",
    LinearODEStage.INTEGRATE_BOTH_SIDES: "math",
    LinearODEStage.SOLVE_FOR_Y: "math",
}

VERIFICATION_INPUT_TYPES = {
    LinearVerificationStage.DIFFERENTIATE: "math",
    LinearVerificationStage.SUBSTITUTE: "math",
    LinearVerificationStage.COMPARE: "text",
}


class LinearODETutorAdapter:
    """
    Shared MAT-PAL adapter for the existing first-order
    linear ODE tutor.

    The adapter composes the existing ODE engine/session
    instead of changing their mathematical logic.
    """

    def __init__(
        self,
        p_expression,
        q_expression,
        problem_id: str = "linear_first_order_fixed_001",
    ):
        self.problem_id = problem_id
        self.engine = LinearFirstOrderEngine(
            p_expression=p_expression,
            q_expression=q_expression,
        )
        self.solution_session = (
            LinearODESolutionSession()
        )
        self.verification_engine = None

    @property
    def problem_title(self) -> str:
        return "First-Order Linear ODE"

    @property
    def problem_statement(self) -> str:
        return (
            "Solve "
            f"dy/dx + ({sp.sstr(self.engine.p_expression)})*y "
            f"= {sp.sstr(self.engine.q_expression)}"
        )

    def get_current_response(self) -> TutorResponse:
        if self.solution_session.is_complete():
            return TutorResponse(
                status="complete",
                feedback=(
                    "Excellent. The linear ODE has been solved."
                ),
                current_step=TOTAL_LINEAR_ODE_STEPS,
                total_steps=TOTAL_LINEAR_ODE_STEPS,
                completed=True,
                hint_available=False,
                expected_input_type="text",
                metadata=self._metadata(),
            )

        stage = self.solution_session.get_stage()

        if stage == LinearODEStage.VERIFY_SOLUTION:
            return self._verification_response()

        return TutorResponse(
            status="waiting_for_answer",
            feedback=self.engine.get_stage_prompt(
                stage
            ),
            current_step=self._current_step_number(),
            total_steps=TOTAL_LINEAR_ODE_STEPS,
            completed=False,
            hint_available=True,
            expected_input_type=STAGE_INPUT_TYPES[
                stage
            ],
            metadata=self._metadata(),
        )

    def submit(
        self,
        submission: StudentSubmission,
    ) -> TutorResponse:
        if self.solution_session.is_complete():
            return self.get_current_response()

        stage = self.solution_session.get_stage()

        concept_response = (
            respond_to_linear_concept_question(
                student_message=submission.answer,
                stage=stage,
                p_expression=self.engine.p_expression,
            )
        )

        if concept_response is not None:
            return TutorResponse(
                status="concept",
                feedback=concept_response,
                suggestion=(
                    "When you're ready, continue with "
                    "the mathematical step."
                ),
                current_step=self._current_step_number(),
                total_steps=TOTAL_LINEAR_ODE_STEPS,
                completed=False,
                hint_available=True,
                expected_input_type=(
                    self._expected_input_type()
                ),
                metadata=self._metadata(
                    extra={
                        "concept_question": True,
                    }
                ),
            )

        if stage == LinearODEStage.VERIFY_SOLUTION:
            return self._submit_verification(
                submission
            )

        answer = self._prepare_answer_for_stage(
            submission,
            stage,
        )

        if isinstance(answer, TutorResponse):
            return answer

        self.solution_session.record_attempt()

        if stage == LinearODEStage.IDENTIFY_P_Q:
            student_p, student_q = (
                self._parse_p_q_answer(answer)
            )

            if not student_p or not student_q:
                return TutorResponse(
                    status="incorrect",
                    feedback=(
                        "Please identify both P(x) and Q(x)."
                    ),
                    suggestion=(
                        "You can write: P = ..., Q = ..."
                    ),
                    current_step=self._current_step_number(),
                    total_steps=TOTAL_LINEAR_ODE_STEPS,
                    completed=False,
                    hint_available=True,
                    expected_input_type=(
                        self._expected_input_type()
                    ),
                    metadata=self._metadata(
                        extra={
                            "error_type": (
                                "missing_p_or_q"
                            ),
                        }
                    ),
                )

            result = self.engine.evaluate(
                stage=stage,
                student_p=student_p,
                student_q=student_q,
            )

        else:
            result = self.engine.evaluate(
                stage=stage,
                student_answer=answer,
            )

        return self._response_from_result(
            result
        )

    def request_hint(self) -> TutorResponse:
        if self.solution_session.is_complete():
            return self.get_current_response()

        return TutorResponse(
            status="hint",
            feedback=(
                "Ask a conceptual question such as "
                "'why do we use an integrating factor?' "
                "or use the current prompt as your guide."
            ),
            current_step=self._current_step_number(),
            total_steps=TOTAL_LINEAR_ODE_STEPS,
            completed=False,
            hint_available=True,
            expected_input_type=self._expected_input_type(),
            metadata=self._metadata(),
        )

    def _ensure_verification_engine(
        self,
    ) -> LinearFirstOrderVerificationEngine:
        if self.verification_engine is None:
            self.verification_engine = (
                LinearFirstOrderVerificationEngine(
                    p_expression=(
                        self.engine.p_expression
                    ),
                    q_expression=(
                        self.engine.q_expression
                    ),
                    solution_expression=(
                        self.engine
                        .get_general_solution()
                    ),
                )
            )

        return self.verification_engine

    def _verification_response(self) -> TutorResponse:
        verification_engine = (
            self._ensure_verification_engine()
        )
        verification_stage = (
            verification_engine.get_stage()
        )
        metadata = self._metadata(
            extra={
                "verification_stage": (
                    verification_stage.value
                ),
            }
        )
        comparison = self._comparison_metadata(
            verification_engine=verification_engine,
            verification_stage=verification_stage,
        )

        if comparison is not None:
            metadata["comparison"] = comparison

        return TutorResponse(
            status="waiting_for_answer",
            feedback=self._verification_prompt(
                verification_stage
            ),
            current_step=TOTAL_LINEAR_ODE_STEPS,
            total_steps=TOTAL_LINEAR_ODE_STEPS,
            completed=False,
            hint_available=True,
            expected_input_type=VERIFICATION_INPUT_TYPES[
                verification_stage
            ],
            metadata=metadata,
        )

    def _submit_verification(
        self,
        submission: StudentSubmission,
    ) -> TutorResponse:
        verification_engine = (
            self._ensure_verification_engine()
        )
        verification_stage = (
            verification_engine.get_stage()
        )

        prepared_answer = (
            self._prepare_verification_answer(
                submission,
                verification_stage,
            )
        )

        if isinstance(prepared_answer, TutorResponse):
            return prepared_answer

        self.solution_session.record_attempt()
        result = verification_engine.evaluate(
            prepared_answer
        )

        if result["correct"]:
            verification_engine.advance()

            if verification_engine.is_complete():
                self.solution_session.advance()

        return self._response_from_result(
            result,
            verification_stage=verification_stage,
        )

    def _prepare_answer_for_stage(
        self,
        submission: StudentSubmission,
        stage: LinearODEStage,
    ) -> str | TutorResponse:
        if STAGE_INPUT_TYPES[stage] != "math":
            return submission.answer

        return self._normalize_math_submission(
            submission
        )

    def _prepare_verification_answer(
        self,
        submission: StudentSubmission,
        verification_stage: LinearVerificationStage,
    ) -> str | TutorResponse:
        if (
            VERIFICATION_INPUT_TYPES[
                verification_stage
            ]
            != "math"
        ):
            return submission.answer

        return self._normalize_math_submission(
            submission
        )

    def _normalize_math_submission(
        self,
        submission: StudentSubmission,
    ) -> str | TutorResponse:
        try:
            return normalize_math_text(
                answer=submission.answer,
                input_type=submission.input_type,
            )

        except MathInputError as error:
            return TutorResponse(
                status="incorrect",
                feedback=(
                    "I could not understand the mathematical input."
                ),
                suggestion=str(error),
                current_step=self._current_step_number(),
                total_steps=TOTAL_LINEAR_ODE_STEPS,
                completed=False,
                hint_available=True,
                expected_input_type=self._expected_input_type(),
                metadata=self._metadata(
                    extra={
                        "error_type": "parse_error",
                        "normalization_error": str(error),
                    }
                ),
            )

    def _response_from_result(
        self,
        result: dict,
        verification_stage:
            LinearVerificationStage | None = None,
    ) -> TutorResponse:
        correct = bool(result.get("correct"))

        completed_stage = (
            self.solution_session.get_stage()
        )

        if correct and not self.solution_session.is_complete():
            if (
                completed_stage
                != LinearODEStage.VERIFY_SOLUTION
            ):
                self.solution_session.advance()

        if self.solution_session.is_complete():
            return self.get_current_response()

        metadata = self._metadata(
            extra={
                "error_type": result.get(
                    "error_type"
                ),
            }
        )

        if verification_stage is not None:
            metadata[
                "completed_verification_stage"
            ] = verification_stage.value

        if correct:
            next_response = self.get_current_response()
            metadata["next_prompt"] = (
                next_response.feedback
            )

            for key in (
                "verification_stage",
                "comparison",
            ):
                if key in next_response.metadata:
                    metadata[key] = (
                        next_response.metadata[
                            key
                        ]
                    )

        return TutorResponse(
            status=(
                "correct"
                if correct
                else "incorrect"
            ),
            feedback=result["feedback"],
            suggestion=result.get("suggestion"),
            current_step=self._current_step_number(),
            total_steps=TOTAL_LINEAR_ODE_STEPS,
            completed=False,
            hint_available=True,
            expected_input_type=self._expected_input_type(),
            metadata=metadata,
        )

    def _parse_p_q_answer(
        self,
        answer: str,
    ) -> tuple[str | None, str | None]:
        answer = answer.strip()

        if answer.startswith("{"):
            try:
                data = json.loads(answer)

            except json.JSONDecodeError:
                return None, None

            return (
                data.get("P")
                or data.get("p")
                or data.get("p_expression"),
                data.get("Q")
                or data.get("q")
                or data.get("q_expression"),
            )

        p_match = re.search(
            r"\bP(?:\(x\))?\s*=\s*([^,;\n]+)",
            answer,
            flags=re.IGNORECASE,
        )
        q_match = re.search(
            r"\bQ(?:\(x\))?\s*=\s*([^,;\n]+)",
            answer,
            flags=re.IGNORECASE,
        )

        return (
            p_match.group(1).strip()
            if p_match
            else None,
            q_match.group(1).strip()
            if q_match
            else None,
        )

    def _verification_prompt(
        self,
        verification_stage: LinearVerificationStage,
    ) -> str:
        solution = sp.sstr(
            self.engine.get_general_solution()
        )
        p_expression = sp.sstr(
            self.engine.p_expression
        )
        q_expression = sp.sstr(
            self.engine.q_expression
        )

        if (
            verification_stage
            == LinearVerificationStage.DIFFERENTIATE
        ):
            return (
                "Differentiate the proposed solution "
                f"y = {solution} with respect to x."
            )

        if (
            verification_stage
            == LinearVerificationStage.SUBSTITUTE
        ):
            return (
                "Substitute y and y' into the left-hand "
                f"side y' + ({p_expression})*y."
            )

        return (
            "After substitution, compare the simplified "
            f"left-hand side with Q(x) = {q_expression}. "
            "Do they match?"
        )

    def _comparison_metadata(
        self,
        verification_engine:
            LinearFirstOrderVerificationEngine,
        verification_stage: LinearVerificationStage,
    ) -> dict | None:
        if (
            verification_stage
            != LinearVerificationStage.COMPARE
        ):
            return None

        return {
            "kind": "expression_comparison",
            "title": "Verification comparison",
            "left_label": (
                "Simplified left-hand side"
            ),
            "left": sp.sstr(
                verification_engine
                .get_expected_lhs()
            ),
            "right_label": "Right-hand side Q(x)",
            "right": sp.sstr(
                verification_engine.q_expression
            ),
            "question": "Do they match?",
        }

    def _expected_input_type(self) -> str:
        if self.solution_session.is_complete():
            return "text"

        stage = self.solution_session.get_stage()

        if stage == LinearODEStage.VERIFY_SOLUTION:
            verification_stage = (
                self
                ._ensure_verification_engine()
                .get_stage()
            )

            return VERIFICATION_INPUT_TYPES[
                verification_stage
            ]

        return STAGE_INPUT_TYPES[stage]

    def _current_step_number(self) -> int:
        stage = self.solution_session.get_stage()

        if stage == LinearODEStage.COMPLETE:
            return TOTAL_LINEAR_ODE_STEPS

        return STAGE_ORDER.index(stage) + 1

    def _metadata(
        self,
        extra: dict | None = None,
    ) -> dict:
        metadata = {
            "adapter": "linear_first_order_ode",
            "stage": (
                self.solution_session
                .get_stage()
                .value
            ),
            "attempts": (
                self.solution_session
                .get_attempts_for_current_stage()
            ),
            "p_expression": sp.sstr(
                self.engine.p_expression
            ),
            "q_expression": sp.sstr(
                self.engine.q_expression
            ),
        }

        if extra:
            metadata.update(extra)

        return metadata
