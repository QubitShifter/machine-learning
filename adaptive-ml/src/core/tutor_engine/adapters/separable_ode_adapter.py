from tokenize import TokenError

import sympy as sp

from src.core.i18n.locale import normalize_locale
from src.core.i18n.ode import ot
from src.core.math_input import (
    MathInputError,
    normalize_math_text,
)
from src.core.tutor_engine.concept_guidance.separable_session import (
    LogSolveStage,
    SeparableSolutionSession,
    SeparableStage,
)
from src.core.tutor_engine.concept_guidance.separable_stage_checker import (
    evaluate_integration_step,
    evaluate_separation_step,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
    TutorResponse,
)
from src.core.tutor_engine.separable_log_engine import (
    SeparableLogEngine,
    looks_like_concept_question,
)
from src.core.tutor_engine.separable_verification_engine import (
    SeparableVerificationEngine,
    VerificationStage,
)


TOTAL_SEPARABLE_ODE_STEPS = 4

STAGE_ORDER = [
    SeparableStage.SEPARATE_VARIABLES,
    SeparableStage.INTEGRATE_BOTH_SIDES,
    SeparableStage.SOLVE_LOG_EQUATION,
    SeparableStage.FINAL_SOLUTION,
]

STAGE_INPUT_TYPES = {
    SeparableStage.SEPARATE_VARIABLES: "math",
    SeparableStage.INTEGRATE_BOTH_SIDES: "math",
    SeparableStage.SOLVE_LOG_EQUATION: "math",
    SeparableStage.FINAL_SOLUTION: "math",
}

VERIFICATION_INPUT_TYPES = {
    VerificationStage.DIFFERENTIATE: "math",
    VerificationStage.SUBSTITUTE_RHS: "math",
    VerificationStage.COMPARE: "text",
}


class SeparableODETutorAdapter:
    """
    Shared MAT-PAL adapter for the existing separable
    variables ODE tutor.

    The adapter composes the older separable session,
    stage validators, log sub-engine, and verification engine
    instead of rewriting their mathematical checks.
    """

    def __init__(
        self,
        rhs_expression,
        problem_id: str = "separable_ode_fixed_001",
        language: str | None = None,
    ):
        self.problem_id = problem_id
        self.language = normalize_locale(language)
        self.rhs_expression = sp.sympify(
            rhs_expression
        )
        self.solution_session = (
            SeparableSolutionSession()
        )
        self.verification_engine = None

    @property
    def problem_title(self) -> str:
        return ot(self.language, "separable.title")

    @property
    def problem_statement(self) -> str:
        equation = (
            "dy/dx = "
            f"{sp.sstr(self.rhs_expression)}"
        )
        return ot(
            self.language,
            "separable.statement",
            equation=equation,
        )

    def get_current_response(self) -> TutorResponse:
        if self.solution_session.is_complete():
            return TutorResponse(
                status="complete",
                feedback=ot(
                    self.language,
                    "separable.complete",
                ),
                current_step=TOTAL_SEPARABLE_ODE_STEPS,
                total_steps=TOTAL_SEPARABLE_ODE_STEPS,
                completed=True,
                hint_available=False,
                expected_input_type="text",
                metadata=self._metadata(),
            )

        stage = self.solution_session.get_stage()

        if stage == SeparableStage.FINAL_SOLUTION:
            return self._verification_response()

        return TutorResponse(
            status="waiting_for_answer",
            feedback=self._stage_prompt(stage),
            current_step=self._current_step_number(),
            total_steps=TOTAL_SEPARABLE_ODE_STEPS,
            completed=False,
            hint_available=True,
            expected_input_type=self._expected_input_type(),
            metadata=self._metadata(),
        )

    def submit(
        self,
        submission: StudentSubmission,
    ) -> TutorResponse:
        if self.solution_session.is_complete():
            return self.get_current_response()

        stage = self.solution_session.get_stage()

        concept_response = self._concept_response(
            submission,
            stage,
        )

        if concept_response is not None:
            return concept_response

        if stage == SeparableStage.FINAL_SOLUTION:
            return self._submit_verification(
                submission
            )

        prepared_answer = self._prepare_math_answer(
            submission
        )

        if isinstance(prepared_answer, TutorResponse):
            return prepared_answer

        if stage == SeparableStage.SEPARATE_VARIABLES:
            self.solution_session.record_attempt()
            result = self._safe_evaluate(
                evaluate_separation_step,
                student_answer=prepared_answer,
                rhs_expression=sp.sstr(
                    self.rhs_expression
                ),
            )
            return self._response_from_result(result)

        if (
            stage
            == SeparableStage.INTEGRATE_BOTH_SIDES
        ):
            self.solution_session.record_attempt()
            result = self._safe_evaluate(
                evaluate_integration_step,
                student_answer=prepared_answer,
                rhs_expression=sp.sstr(
                    self.rhs_expression
                ),
            )
            return self._response_from_result(result)

        if (
            stage
            == SeparableStage.SOLVE_LOG_EQUATION
        ):
            return self._submit_log_stage(
                prepared_answer
            )

        return self.get_current_response()

    def request_hint(self) -> TutorResponse:
        return TutorResponse(
            status="hint",
            feedback=self._hint_text(),
            current_step=self._current_step_number(),
            total_steps=TOTAL_SEPARABLE_ODE_STEPS,
            completed=False,
            hint_available=True,
            expected_input_type=self._expected_input_type(),
            metadata=self._metadata(),
        )

    def _submit_log_stage(
        self,
        prepared_answer: str,
    ) -> TutorResponse:
        log_stage = (
            self.solution_session.get_log_stage()
        )
        log_engine = self._log_engine()
        result = self._safe_evaluate(
            log_engine.evaluate,
            stage=log_stage,
            student_answer=prepared_answer,
        )

        if result.get("kind") == "concept":
            return TutorResponse(
                status="concept",
                feedback=result["feedback"],
                suggestion=result.get("suggestion"),
                current_step=self._current_step_number(),
                total_steps=TOTAL_SEPARABLE_ODE_STEPS,
                completed=False,
                hint_available=True,
                expected_input_type=self._expected_input_type(),
                metadata=self._metadata(
                    extra={
                        "concept_question": True,
                    }
                ),
            )

        if result.get("kind") == "math":
            self.solution_session.record_attempt()

        if result.get("advance"):
            self.solution_session.advance_log_stage_by(
                result.get("steps_completed", 1)
            )

            if (
                self.solution_session
                .is_log_stage_complete()
            ):
                self.solution_session.advance()

        return self._response_from_result(result)

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

        if (
            VERIFICATION_INPUT_TYPES[
                verification_stage
            ]
            == "math"
        ):
            prepared_answer = (
                self._prepare_math_answer(
                    submission,
                    restore_derivative_left=True,
                )
            )

            if isinstance(
                prepared_answer,
                TutorResponse,
            ):
                return prepared_answer

        else:
            prepared_answer = submission.answer

        self.solution_session.record_attempt()
        result = self._safe_evaluate(
            verification_engine.evaluate,
            prepared_answer
        )

        if verification_engine.is_complete():
            self.solution_session.advance()

        return self._response_from_result(
            result,
            verification_stage=verification_stage,
        )

    def _safe_evaluate(
        self,
        evaluator,
        *args,
        **kwargs,
    ) -> dict:
        try:
            return evaluator(
                *args,
                **kwargs,
            )

        except (
            SyntaxError,
            TypeError,
            ValueError,
            NameError,
            TokenError,
            sp.SympifyError,
        ) as error:
            return {
                "correct": False,
                "advance": False,
                "error_type": "parse_error",
                "feedback": ot(
                    self.language,
                    "linear.parse_error",
                ),
                "suggestion": str(error),
            }

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
            feedback=verification_engine.get_prompt(),
            current_step=self._current_step_number(),
            total_steps=TOTAL_SEPARABLE_ODE_STEPS,
            completed=False,
            hint_available=True,
            expected_input_type=self._expected_input_type(),
            metadata=metadata,
        )

    def _response_from_result(
        self,
        result: dict,
        verification_stage: VerificationStage | None = None,
    ) -> TutorResponse:
        correct = bool(result.get("correct"))

        if (
            correct
            and not self.solution_session.is_complete()
            and self.solution_session.get_stage()
            in {
                SeparableStage.SEPARATE_VARIABLES,
                SeparableStage.INTEGRATE_BOTH_SIDES,
            }
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
            total_steps=TOTAL_SEPARABLE_ODE_STEPS,
            completed=False,
            hint_available=True,
            expected_input_type=self._expected_input_type(),
            metadata=metadata,
        )

    def _prepare_math_answer(
        self,
        submission: StudentSubmission,
        restore_derivative_left: bool = False,
    ) -> str | TutorResponse:
        try:
            answer = normalize_math_text(
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
                total_steps=TOTAL_SEPARABLE_ODE_STEPS,
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

        if (
            restore_derivative_left
            and answer.startswith("yp")
            and "=" in answer
        ):
            answer = answer.replace(
                "yp",
                "dy/dx",
                1,
            )

        return answer

    def _concept_response(
        self,
        submission: StudentSubmission,
        stage: SeparableStage,
    ) -> TutorResponse | None:
        if (
            submission.input_type != "text"
            or not looks_like_concept_question(
                submission.answer
            )
            or stage == SeparableStage.SOLVE_LOG_EQUATION
        ):
            return None

        return TutorResponse(
            status="concept",
            feedback=self._generic_concept_feedback(stage),
            suggestion=(
                ot(self.language, "separable.continue")
            ),
            current_step=self._current_step_number(),
            total_steps=TOTAL_SEPARABLE_ODE_STEPS,
            completed=False,
            hint_available=True,
            expected_input_type=self._expected_input_type(),
            metadata=self._metadata(
                extra={
                    "concept_question": True,
                }
            ),
        )

    def _stage_prompt(
        self,
        stage: SeparableStage,
    ) -> str:
        if stage == SeparableStage.SEPARATE_VARIABLES:
            return ot(
                self.language,
                "separable.stage.separate_wrap",
                base=ot(
                    self.language,
                    "separable.stage.separate",
                ),
                equation=self.problem_statement,
            )

        if (
            stage
            == SeparableStage.INTEGRATE_BOTH_SIDES
        ):
            return ot(
                self.language,
                "separable.stage.integrate",
                fx=sp.sstr(self._fx_expression()),
            )

        if (
            stage
            == SeparableStage.SOLVE_LOG_EQUATION
        ):
            log_engine = self._log_engine()
            log_stage = (
                self.solution_session.get_log_stage()
            )

            return (
                f"{log_engine.get_step_title(log_stage)}\n\n"
                f"{log_engine.get_prompt(log_stage)}"
            )

        return self.solution_session.get_prompt()

    def _log_stage_hint_text(
        self,
        log_stage: LogSolveStage,
    ) -> str:
        if log_stage == LogSolveStage.APPLY_EXP:
            return ot(self.language, "separable.hint.exp")

        if log_stage == LogSolveStage.CANCEL_LOG:
            return ot(self.language, "separable.hint.cancel")

        if (
            log_stage
            == LogSolveStage.SPLIT_EXPONENTIAL
        ):
            return ot(self.language, "separable.hint.split")

        if (
            log_stage
            == LogSolveStage.RENAME_EXP_CONSTANT
        ):
            return ot(self.language, "separable.hint.rename")

        if (
            log_stage
            == LogSolveStage.REMOVE_ABSOLUTE_VALUE
        ):
            return ot(self.language, "separable.hint.abs")

        if log_stage == LogSolveStage.ABSORB_CONSTANT:
            return ot(self.language, "separable.hint.absorb")

        return ot(
            self.language,
            "separable.hint.log_default",
        )

    def _hint_text(self) -> str:
        stage = self.solution_session.get_stage()

        if stage == SeparableStage.SEPARATE_VARIABLES:
            return ot(
                self.language,
                "separable.hint.separate",
            )

        if (
            stage
            == SeparableStage.INTEGRATE_BOTH_SIDES
        ):
            return ot(
                self.language,
                "separable.hint.integrate",
                fx=sp.sstr(self._fx_expression()),
            )

        if (
            stage
            == SeparableStage.SOLVE_LOG_EQUATION
        ):
            return self._log_stage_hint_text(
                self.solution_session.get_log_stage()
            )

        return ot(
            self.language,
            "separable.hint.verify",
        )

    def _generic_concept_feedback(
        self,
        stage: SeparableStage,
    ) -> str:
        if stage == SeparableStage.SEPARATE_VARIABLES:
            return ot(
                self.language,
                "separable.concept.separate",
            )

        if (
            stage
            == SeparableStage.INTEGRATE_BOTH_SIDES
        ):
            return ot(
                self.language,
                "separable.concept.integrate",
            )

        return ot(
            self.language,
            "separable.concept.verify",
        )

    def _comparison_metadata(
        self,
        verification_engine: SeparableVerificationEngine,
        verification_stage: VerificationStage,
    ) -> dict | None:
        if verification_stage != VerificationStage.COMPARE:
            return None

        rhs = sp.simplify(
            verification_engine.rhs_expression.subs(
                sp.symbols("y"),
                verification_engine.solution_expression,
            )
        )

        return {
            "kind": "expression_comparison",
            "title": ot(
                self.language,
                "separable.compare.title",
            ),
            "left_label": ot(
                self.language,
                "separable.compare.left",
            ),
            "left": sp.sstr(
                verification_engine.derivative_expression
            ),
            "right_label": ot(
                self.language,
                "separable.compare.right",
            ),
            "right": sp.sstr(rhs),
            "question": ot(
                self.language,
                "separable.compare.question",
            ),
        }

    def _ensure_verification_engine(
        self,
    ) -> SeparableVerificationEngine:
        if self.verification_engine is None:
            self.verification_engine = (
                SeparableVerificationEngine(
                    rhs_expression=self.rhs_expression,
                    solution_expression=(
                        self._solution_expression()
                    ),
                    language=self.language,
                )
            )

        return self.verification_engine

    def _expected_input_type(self) -> str:
        if self.solution_session.is_complete():
            return "text"

        stage = self.solution_session.get_stage()

        if stage == SeparableStage.FINAL_SOLUTION:
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

        if stage == SeparableStage.COMPLETE:
            return TOTAL_SEPARABLE_ODE_STEPS

        return STAGE_ORDER.index(stage) + 1

    def _metadata(
        self,
        extra: dict | None = None,
    ) -> dict:
        metadata = {
            "adapter": "separable_ode",
            "stage": (
                self.solution_session
                .get_stage()
                .value
            ),
            "attempts": (
                self.solution_session
                .get_attempts_for_current_stage()
            ),
            "rhs_expression": sp.sstr(
                self.rhs_expression
            ),
            "fx_expression": sp.sstr(
                self._fx_expression()
            ),
            "integrated_fx": sp.sstr(
                self._integrated_fx()
            ),
        }

        if (
            self.solution_session.get_stage()
            == SeparableStage.SOLVE_LOG_EQUATION
        ):
            metadata["log_stage"] = (
                self.solution_session
                .get_log_stage()
                .value
            )

        if extra:
            metadata.update(extra)

        return metadata

    def _fx_expression(self):
        y = sp.symbols("y")

        return sp.simplify(
            self.rhs_expression / y
        )

    def _integrated_fx(self):
        x = sp.symbols("x")

        return sp.integrate(
            self._fx_expression(),
            x,
        )

    def _solution_expression(self):
        C = sp.symbols("C")

        return C * sp.exp(
            self._integrated_fx()
        )

    def _log_engine(self) -> SeparableLogEngine:
        return SeparableLogEngine(
            integrated_fx=self._integrated_fx(),
            language=self.language,
        )
