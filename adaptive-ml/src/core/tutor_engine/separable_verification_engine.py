from enum import Enum

import sympy as sp

from src.core.i18n.ode import ot
from src.core.i18n.locale import normalize_locale
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
        language: str | None = None,
    ):
        self.rhs_expression = rhs_expression
        self.solution_expression = solution_expression
        self.language = normalize_locale(language)

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
                "separable.verify.title.diff",

            VerificationStage.SUBSTITUTE_RHS:
                "separable.verify.title.substitute",

            VerificationStage.COMPARE:
                "separable.verify.title.compare",

            VerificationStage.COMPLETE:
                "separable.verify.title.complete",
        }

        return ot(self.language, titles[self.stage])

    def get_prompt(self) -> str:
        solution_text = sp.sstr(
            self.solution_expression
        )

        rhs_text = sp.sstr(
            self.rhs_expression
        )

        if self.stage == VerificationStage.DIFFERENTIATE:
            return ot(
                self.language,
                "separable.verify.prompt.diff",
                solution=solution_text,
            )

        if self.stage == VerificationStage.SUBSTITUTE_RHS:
            return ot(
                self.language,
                "separable.verify.prompt.substitute",
                rhs=rhs_text,
            )

        if self.stage == VerificationStage.COMPARE:
            substituted = sp.sstr(
                self.rhs_expression.subs(
                    sp.symbols("y"),
                    self.solution_expression,
                )
            )
            return ot(
                self.language,
                "separable.verify.prompt.compare",
                derivative=sp.sstr(
                    self.derivative_expression
                ),
                rhs=substituted,
            )

        return ot(
            self.language,
            "separable.verify.prompt.complete",
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