import sympy as sp

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
    ):
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
                "Stage 1 — Recognize the linear form",

            LinearODEStage.IDENTIFY_P_Q:
                "Stage 2 — Identify P(x) and Q(x)",

            LinearODEStage.FIND_INTEGRATING_FACTOR:
                "Stage 3 — Find the integrating factor",

            LinearODEStage.MULTIPLY_BY_INTEGRATING_FACTOR:
                "Stage 4 — Multiply by the integrating factor",

            LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE:
                "Stage 5 — Recognize the product derivative",

            LinearODEStage.INTEGRATE_BOTH_SIDES:
                "Stage 6 — Integrate both sides",

            LinearODEStage.SOLVE_FOR_Y:
                "Stage 7 — Solve for y",

            LinearODEStage.VERIFY_SOLUTION:
                "Stage 8 — Verify the solution",

            LinearODEStage.COMPLETE:
                "Complete",
        }

        return titles[
            stage
        ]

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
            LinearODEStage.IDENTIFY_STANDARD_FORM: (
                "A first-order linear ODE has the standard form:\n\n"
                "    y' + P(x)y = Q(x)\n\n"
                "Is the current equation already in this form?"
            ),

            LinearODEStage.IDENTIFY_P_Q: (
                "Compare the equation with:\n\n"
                "    y' + P(x)y = Q(x)\n\n"
                "Identify P(x) and Q(x)."
            ),

            LinearODEStage.FIND_INTEGRATING_FACTOR: (
                f"We have:\n\n"
                f"    P(x) = {P}\n\n"
                "Use:\n\n"
                "    mu(x) = exp(integral(P(x)) dx)\n\n"
                f"Here integral(P(x)) dx = {integrated_p}\n\n"
                "Find mu(x)."
            ),

            LinearODEStage.MULTIPLY_BY_INTEGRATING_FACTOR: (
                f"The integrating factor is:\n\n"
                f"    mu(x) = {mu}\n\n"
                "Multiply EVERY term of\n\n"
                f"    y' + ({P})*y = {Q}\n\n"
                "by the integrating factor."
            ),

            LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE: (
                "The left-hand side now has the form:\n\n"
                "    mu*y' + mu*P(x)*y\n\n"
                "Use the product rule backward and rewrite "
                "the complete equation using:\n\n"
                "    d/dx(mu*y)"
            ),

            LinearODEStage.INTEGRATE_BOTH_SIDES: (
                "We now have the derivative of a product.\n\n"
                "Integrate both sides with respect to x.\n\n"
                f"The right-hand integrand is:\n"
                f"    {integrand}\n\n"
                "Remember the arbitrary constant C."
            ),

            LinearODEStage.SOLVE_FOR_Y: (
                "After integration we have:\n\n"
                f"    ({mu})*y = "
                f"{antiderivative} + C\n\n"
                "Divide by the integrating factor "
                "and solve explicitly for y."
            ),

            LinearODEStage.VERIFY_SOLUTION: (
                "Verify that the proposed solution satisfies "
                "the original differential equation."
            ),

            LinearODEStage.COMPLETE: (
                "The linear ODE has been solved."
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
            )

        if stage == LinearODEStage.FIND_INTEGRATING_FACTOR:
            return evaluate_integrating_factor(
                student_answer=student_answer,
                expected_p=self.p_expression,
            )

        if stage == LinearODEStage.MULTIPLY_BY_INTEGRATING_FACTOR:
            return evaluate_multiply_by_integrating_factor(
                student_answer=student_answer,
                expected_p=self.p_expression,
                expected_q=self.q_expression,
            )

        if stage == LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE:
            return evaluate_product_derivative(
                student_answer=student_answer,
                expected_p=self.p_expression,
                expected_q=self.q_expression,
            )

        if stage == LinearODEStage.INTEGRATE_BOTH_SIDES:
            return evaluate_linear_integration_step(
                student_answer=student_answer,
                expected_p=self.p_expression,
                expected_q=self.q_expression,
            )

        if stage == LinearODEStage.SOLVE_FOR_Y:
            return evaluate_linear_solve_for_y(
                student_answer=student_answer,
                expected_p=self.p_expression,
                expected_q=self.q_expression,
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
                "feedback": (
                    "Please answer whether the equation is "
                    "already in standard linear form."
                ),
                "suggestion": (
                    "Compare it with y' + P(x)y = Q(x)."
                ),
            }

        answer = (
            student_answer
            .strip()
            .lower()
        )

        positive_answers = {
            "yes",
            "y",
            "true",
            "correct",
            "it is",
            "yes it is",
        }

        if answer in positive_answers:
            return {
                "correct": True,
                "error_type": None,
                "feedback": (
                    "Correct. The equation is already written "
                    "in first-order linear standard form."
                ),
                "suggestion": (
                    "Next, identify P(x) and Q(x)."
                ),
            }

        return {
            "correct": False,
            "error_type": "standard_form_not_recognized",
            "feedback": (
                "This equation is already in first-order "
                "linear standard form."
            ),
            "suggestion": (
                "Compare it directly with "
                "y' + P(x)y = Q(x)."
            ),
        }