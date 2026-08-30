from enum import Enum

import sympy as sp

from src.core.tutor_engine.concept_guidance.separable_verification_checker import (
    evaluate_derivative_step,
    evaluate_rhs_substitution_step,
    evaluate_verification_confirmation,
)


class VerificationStage(Enum):
    DIFFERENTIATE = "differentiate"
    SUBSTITUTE_RHS = "substitute_rhs"
    COMPARE = "compare"
    COMPLETE = "complete"


class SeparableVerificationEngine:
    def __init__(
        self,
        rhs_expression,
        solution_expression,
    ):
        self.rhs_expression = rhs_expression
        self.solution_expression = solution_expression

        self.stage = (
            VerificationStage.DIFFERENTIATE
        )

        self.derivative_expression = sp.diff(
            solution_expression,
            sp.symbols("x"),
        )

    def get_stage(self):
        return self.stage

    def get_title(self) -> str:
        titles = {
            VerificationStage.DIFFERENTIATE:
                "Step 4.1 — Differentiate the proposed solution",

            VerificationStage.SUBSTITUTE_RHS:
                "Step 4.2 — Substitute y into the original ODE",

            VerificationStage.COMPARE:
                "Step 4.3 — Compare both sides",

            VerificationStage.COMPLETE:
                "Verification complete",
        }

        return titles[self.stage]

    def get_prompt(self) -> str:
        solution_text = sp.sstr(
            self.solution_expression
        )

        rhs_text = sp.sstr(
            self.rhs_expression
        )

        if self.stage == VerificationStage.DIFFERENTIATE:
            return (
                "Your proposed solution is:\n"
                f"    y = {solution_text}\n\n"
                "Differentiate it with respect to x.\n"
                "You may write:\n"
                "    dy/dx = ..."
            )

        if self.stage == VerificationStage.SUBSTITUTE_RHS:
            return (
                "The original differential equation has "
                "right-hand side:\n"
                f"    {rhs_text}\n\n"
                "Substitute your proposed y into this "
                "right-hand side."
            )

        if self.stage == VerificationStage.COMPARE:
            return (
                "Compare the two expressions:\n\n"
                f"    dy/dx = {sp.sstr(self.derivative_expression)}\n"
                f"    RHS   = {sp.sstr(self.rhs_expression.subs(sp.symbols('y'), self.solution_expression))}\n\n"
                "Do they match?"
            )

        return (
            "The proposed solution has been verified."
        )

    def evaluate(
        self,
        student_answer: str,
    ) -> dict:
        if self.stage == VerificationStage.DIFFERENTIATE:
            result = evaluate_derivative_step(
                student_answer=student_answer,
                solution_expression=self.solution_expression,
            )

            if result["correct"]:
                self.stage = (
                    VerificationStage.SUBSTITUTE_RHS
                )

            return result

        if self.stage == VerificationStage.SUBSTITUTE_RHS:
            result = evaluate_rhs_substitution_step(
                student_answer=student_answer,
                rhs_expression=self.rhs_expression,
                solution_expression=self.solution_expression,
            )

            if result["correct"]:
                self.stage = (
                    VerificationStage.COMPARE
                )

            return result

        if self.stage == VerificationStage.COMPARE:
            result = evaluate_verification_confirmation(
                derivative_expression=self.derivative_expression,
                rhs_expression=self.rhs_expression,
                solution_expression=self.solution_expression,
            )

            if result["correct"]:
                self.stage = (
                    VerificationStage.COMPLETE
                )

            return {
                "correct": result["correct"],
                "error_type": None,
                "feedback": result["feedback"],
                "suggestion": None,
            }

        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "The solution has already been verified."
            ),
            "suggestion": None,
        }

    def is_complete(self):
        return (
            self.stage
            == VerificationStage.COMPLETE
        )