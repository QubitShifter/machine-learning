import sympy as sp

from enum import Enum

from src.core.tutor_engine.linear_first_order_checker import (
    normalize_expression,
    parse_math,
)


x = sp.symbols("x")
y = sp.symbols("y")
C = sp.symbols("C")


class LinearVerificationStage(Enum):
    DIFFERENTIATE = "differentiate"
    SUBSTITUTE = "substitute"
    COMPARE = "compare"
    COMPLETE = "complete"


def _normalize(
    text: str,
) -> str:
    text = normalize_expression(text)

    if "=" in text:
        left, right = text.split(
            "=",
            maxsplit=1,
        )

        if left.strip().lower() in {
            "dy/dx",
            "y'",
            "yp",
        }:
            text = right.strip()

    return text


def _parse(
    text: str,
):
    return parse_math(text)


class LinearFirstOrderVerificationEngine:
    def __init__(
        self,
        p_expression,
        q_expression,
        solution_expression,
    ):
        self.p_expression = sp.sympify(
            p_expression
        )

        self.q_expression = sp.sympify(
            q_expression
        )

        self.solution_expression = sp.sympify(
            solution_expression
        )

        self.stage = (
            LinearVerificationStage.DIFFERENTIATE
        )

        self.student_derivative = None
        self.student_substitution = None

    def get_stage(self):
        return self.stage

    def is_complete(self):
        return (
            self.stage
            == LinearVerificationStage.COMPLETE
        )

    def advance(self):
        order = [
            LinearVerificationStage.DIFFERENTIATE,
            LinearVerificationStage.SUBSTITUTE,
            LinearVerificationStage.COMPARE,
            LinearVerificationStage.COMPLETE,
        ]

        index = order.index(
            self.stage
        )

        if index < len(order) - 1:
            self.stage = order[
                index + 1
            ]

    def get_expected_derivative(self):
        return sp.simplify(
            sp.diff(
                self.solution_expression,
                x,
            )
        )

    def get_expected_lhs(self):
        derivative = (
            self.get_expected_derivative()
        )

        return sp.simplify(
            derivative
            + self.p_expression
            * self.solution_expression
        )

    def evaluate(
        self,
        student_answer: str,
    ) -> dict:

        if (
            self.stage
            == LinearVerificationStage.DIFFERENTIATE
        ):
            return self._evaluate_derivative(
                student_answer
            )

        if (
            self.stage
            == LinearVerificationStage.SUBSTITUTE
        ):
            return self._evaluate_substitution(
                student_answer
            )

        if (
            self.stage
            == LinearVerificationStage.COMPARE
        ):
            return self._evaluate_compare(
                student_answer
            )

        return {
            "correct": False,
            "error_type": "verification_complete",
            "feedback": (
                "Verification is already complete."
            ),
            "suggestion": None,
        }

    def _evaluate_derivative(
        self,
        student_answer: str,
    ) -> dict:

        answer = _normalize(
            student_answer
        )

        try:
            parsed = _parse(
                answer
            )

        except Exception:
            return {
                "correct": False,
                "error_type": "parse_error",
                "feedback": (
                    "I could not understand the derivative."
                ),
                "suggestion": (
                    "Differentiate the proposed solution "
                    "with respect to x."
                ),
            }

        expected = (
            self.get_expected_derivative()
        )

        correct = (
            sp.simplify(
                parsed - expected
            ) == 0
        )

        if not correct:
            return {
                "correct": False,
                "error_type": "incorrect_derivative",
                "feedback": (
                    "That derivative does not match the "
                    "derivative of the proposed solution."
                ),
                "suggestion": (
                    f"Differentiate y = "
                    f"{sp.sstr(self.solution_expression)}."
                ),
            }

        self.student_derivative = parsed

        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. That is the derivative of "
                "the proposed solution."
            ),
            "suggestion": (
                "Next, substitute y and y' into "
                "y' + P(x)y."
            ),
        }

    def _evaluate_substitution(
        self,
        student_answer: str,
    ) -> dict:

        answer = _normalize(
            student_answer
        )

        try:
            parsed = _parse(
                answer
            )

        except Exception:
            return {
                "correct": False,
                "error_type": "parse_error",
                "feedback": (
                    "I could not understand the substituted "
                    "left-hand side."
                ),
                "suggestion": (
                    "Calculate y' + P(x)y using the "
                    "proposed solution."
                ),
            }

        expected = (
            self.get_expected_lhs()
        )

        correct = (
            sp.simplify(
                parsed - expected
            ) == 0
        )

        if not correct:
            return {
                "correct": False,
                "error_type": "incorrect_substitution",
                "feedback": (
                    "That does not match y' + P(x)y "
                    "after substitution."
                ),
                "suggestion": (
                    "Use the derivative from the previous "
                    "step and add P(x) times the proposed y."
                ),
            }

        self.student_substitution = parsed

        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. You substituted the proposed "
                "solution into the left-hand side."
            ),
            "suggestion": (
                "Now compare the result with Q(x)."
            ),
        }

    def _evaluate_compare(
        self,
        student_answer: str,
    ) -> dict:

        answer = (
            student_answer
            .strip()
            .lower()
        )

        normalized_answer = (
            answer
            .replace(",", "")
            .replace(".", "")
            .replace("!", "")
            .replace("?", "")
        )

        positive_phrases = [
            "yes",
            "they match",
            "match",
            "they are equal",
            "are equal",
            "equal",
            "same",
            "correct",
            "true",
        ]

        negative_phrases = [
            "no",
            "do not match",
            "don't match",
            "not equal",
            "not the same",
            "false",
        ]

        student_says_no = any(
            phrase in normalized_answer
            for phrase in negative_phrases
        )

        student_says_yes = (
            not student_says_no
            and any(
                phrase in normalized_answer
                for phrase in positive_phrases
            )
        )

        expected_lhs = (
            self.get_expected_lhs()
        )

        actually_matches = (
            sp.simplify(
                expected_lhs
                - self.q_expression
            ) == 0
        )

        if actually_matches:
            if student_says_yes:
                return {
                    "correct": True,
                    "error_type": None,
                    "feedback": (
                        "Verified. The proposed solution "
                        "satisfies the original linear ODE."
                    ),
                    "suggestion": None,
                }

            return {
                "correct": False,
                "error_type": "comparison_error",
                "feedback": (
                    "The two expressions are mathematically equal."
                ),
                "suggestion": (
                    "Compare the simplified left-hand side "
                    "with Q(x)."
                ),
            }

        if student_says_no:
            return {
                "correct": True,
                "error_type": None,
                "feedback": (
                    "Correct. The proposed solution does not "
                    "satisfy the original ODE."
                ),
                "suggestion": None,
            }

        return {
            "correct": False,
            "error_type": "comparison_error",
            "feedback": (
                "The two expressions do not match."
            ),
            "suggestion": (
                "Compare the simplified expressions again."
            ),
        }
