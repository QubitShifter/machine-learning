import sympy as sp

from src.core.i18n.concept import (
    CANONICAL_YES,
    normalize_concept_answer,
)
from src.core.i18n.locale import normalize_locale
from src.core.i18n.ode import ot
from src.core.tutor_engine.linear_first_order_session import (
    LinearODEStage,
)

from src.core.tutor_engine.linear_first_order_checker import (
    evaluate_p_q_identification,
    evaluate_integrating_factor,
    evaluate_multiply_by_integrating_factor,
    evaluate_product_derivative,
    evaluate_linear_integration_step,
    evaluate_linear_solve_for_y,
)

from src.core.tutor_engine.concept_guidance.linear_first_order_guidance import (
    respond_to_linear_concept_question,
)


x = sp.symbols("x")


class LinearFirstOrderEngine:
    """
    Controls the mathematical tutoring flow for first-order
    linear differential equations:

        y' + P(x)y = Q(x)

    This engine does not own mastery or question selection.
    Its responsibility is the step-by-step mathematical flow.
    """

    def __init__(
        self,
        p_expression,
        q_expression,
        language: str | None = None,
    ):
        self.language = normalize_locale(language)
        self.p_expression = sp.sympify(
            p_expression
        )

        self.q_expression = sp.sympify(
            q_expression
        )

    # --------------------------------------------------
    # Useful derived expressions
    # --------------------------------------------------

    def get_integrated_p(self):
        return sp.integrate(
            self.p_expression,
            x,
        )

    def get_integrating_factor(self):
        return sp.exp(
            self.get_integrated_p()
        )

    def get_integrand(self):
        mu = self.get_integrating_factor()

        return sp.simplify(
            mu * self.q_expression
        )

    def get_antiderivative(self):
        return sp.integrate(
            self.get_integrand(),
            x,
        )

    def get_general_solution(self):
        C = sp.symbols("C")

        mu = self.get_integrating_factor()

        antiderivative = (
            self.get_antiderivative()
        )

        return sp.simplify(
            (
                antiderivative + C
            )
            / mu
        )

    # --------------------------------------------------
    # Stage presentation
    # --------------------------------------------------

    def get_stage_title(
        self,
        stage: LinearODEStage,
    ) -> str:

        titles = {
            LinearODEStage.IDENTIFY_STANDARD_FORM:
                "linear.title.stage.identify_form",

            LinearODEStage.IDENTIFY_P_Q:
                "linear.title.stage.identify_pq",

            LinearODEStage.FIND_INTEGRATING_FACTOR:
                "linear.title.stage.mu",

            LinearODEStage.MULTIPLY_BY_INTEGRATING_FACTOR:
                "linear.title.stage.multiply",

            LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE:
                "linear.title.stage.product",

            LinearODEStage.INTEGRATE_BOTH_SIDES:
                "linear.title.stage.integrate",

            LinearODEStage.SOLVE_FOR_Y:
                "linear.title.stage.solve_y",

            LinearODEStage.VERIFY_SOLUTION:
                "linear.title.stage.verify",

            LinearODEStage.COMPLETE:
                "linear.title.stage.complete",
        }

        return ot(
            self.language,
            titles[stage],
        )

    def get_stage_prompt(
        self,
        stage: LinearODEStage,
    ) -> str:

        P = sp.sstr(
            self.p_expression
        )

        Q = sp.sstr(
            self.q_expression
        )

        mu = sp.sstr(
            self.get_integrating_factor()
        )

        integrated_p = sp.sstr(
            self.get_integrated_p()
        )

        integrand = sp.sstr(
            self.get_integrand()
        )

        antiderivative = sp.sstr(
            self.get_antiderivative()
        )

        prompts = {
            LinearODEStage.IDENTIFY_STANDARD_FORM: ot(
                self.language,
                "linear.stage.identify_form",
            ),

            LinearODEStage.IDENTIFY_P_Q: ot(
                self.language,
                "linear.stage.identify_pq",
            ),

            LinearODEStage.FIND_INTEGRATING_FACTOR: ot(
                self.language,
                "linear.stage.mu",
                P=P,
                integrated_p=integrated_p,
            ),

            LinearODEStage.MULTIPLY_BY_INTEGRATING_FACTOR: ot(
                self.language,
                "linear.stage.multiply",
                mu=mu,
                P=P,
                Q=Q,
            ),

            LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE: ot(
                self.language,
                "linear.stage.product",
            ),

            LinearODEStage.INTEGRATE_BOTH_SIDES: ot(
                self.language,
                "linear.stage.integrate",
                integrand=integrand,
            ),

            LinearODEStage.SOLVE_FOR_Y: ot(
                self.language,
                "linear.stage.solve_y",
                mu=mu,
                antiderivative=antiderivative,
            ),

            LinearODEStage.VERIFY_SOLUTION: ot(
                self.language,
                "linear.stage.verify",
            ),

            LinearODEStage.COMPLETE: ot(
                self.language,
                "linear.stage.complete",
            ),
        }

        return prompts[
            stage
        ]

    # --------------------------------------------------
    # Mathematical evaluation
    # --------------------------------------------------

    def evaluate(
        self,
        stage: LinearODEStage,
        student_answer=None,
        student_p=None,
        student_q=None,
    ) -> dict:

        if student_answer is not None:
            concept_response = (
                respond_to_linear_concept_question(
                    student_message=student_answer,
                    stage=stage,
                    p_expression=self.p_expression,
                    language=self.language,
                )
            )

            if concept_response is not None:
                return {
                    "kind": "concept",
                    "correct": False,
                    "advance": False,
                    "error_type": None,
                    "feedback": concept_response,
                    "suggestion": ot(
                        self.language,
                        "linear.continue",
                    ),
                }

        if stage == LinearODEStage.IDENTIFY_STANDARD_FORM:
            return self._evaluate_standard_form(
                student_answer
            )

        if stage == LinearODEStage.IDENTIFY_P_Q:
            return evaluate_p_q_identification(
                student_p=student_p,
                student_q=student_q,
                expected_p=self.p_expression,
                expected_q=self.q_expression,
                language=self.language,
            )

        if stage == LinearODEStage.FIND_INTEGRATING_FACTOR:
            return evaluate_integrating_factor(
                student_answer=student_answer,
                expected_p=self.p_expression,
                language=self.language,
            )

        if stage == LinearODEStage.MULTIPLY_BY_INTEGRATING_FACTOR:
            return evaluate_multiply_by_integrating_factor(
                student_answer=student_answer,
                expected_p=self.p_expression,
                expected_q=self.q_expression,
                language=self.language,
            )

        if stage == LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE:
            return evaluate_product_derivative(
                student_answer=student_answer,
                expected_p=self.p_expression,
                expected_q=self.q_expression,
                language=self.language,
            )

        if stage == LinearODEStage.INTEGRATE_BOTH_SIDES:
            return evaluate_linear_integration_step(
                student_answer=student_answer,
                expected_p=self.p_expression,
                expected_q=self.q_expression,
                language=self.language,
            )

        if stage == LinearODEStage.SOLVE_FOR_Y:
            return evaluate_linear_solve_for_y(
                student_answer=student_answer,
                expected_p=self.p_expression,
                expected_q=self.q_expression,
                language=self.language,
            )

        if stage == LinearODEStage.VERIFY_SOLUTION:
            return {
                "correct": False,
                "error_type": "verification_not_implemented",
                "feedback": (
                    "Verification will be handled by the "
                    "verification engine."
                ),
                "suggestion": None,
            }

        return {
            "correct": False,
            "error_type": "invalid_stage",
            "feedback": (
                "Unknown linear ODE stage."
            ),
            "suggestion": None,
        }

    # --------------------------------------------------
    # Stage 1
    # --------------------------------------------------

    def _evaluate_standard_form(
        self,
        student_answer: str,
    ) -> dict:

        if student_answer is None:
            return {
                "correct": False,
                "error_type": "missing_answer",
                "feedback": ot(
                    self.language,
                    "linear.feedback.standard_form.missing",
                ),
                "suggestion": ot(
                    self.language,
                    "linear.suggestion.standard_form.compare",
                ),
            }

        if (
            normalize_concept_answer(
                student_answer,
                self.language,
            )
            == CANONICAL_YES
        ):
            return {
                "correct": True,
                "error_type": None,
                "feedback": ot(
                    self.language,
                    "linear.feedback.standard_form.correct",
                ),
                "suggestion": ot(
                    self.language,
                    "linear.suggestion.identify_pq",
                ),
            }

        return {
            "correct": False,
            "error_type": "standard_form_not_recognized",
            "feedback": ot(
                self.language,
                "linear.feedback.standard_form.incorrect",
            ),
            "suggestion": ot(
                self.language,
                "linear.suggestion.standard_form.compare_direct",
            ),
        }