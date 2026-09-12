from dataclasses import dataclass
from tokenize import TokenError

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from src.core.math_input.latex_parser import (
    MathInputError,
    latex_to_sympy_text,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
)


x, y, yp, C, K, mu = sp.symbols(
    "x y yp C K mu"
)

TRANSFORMATIONS = (
    standard_transformations
    + (
        implicit_multiplication_application,
        convert_xor,
    )
)

LOCAL_DICT = {
    "x": x,
    "y": y,
    "yp": yp,
    "C": C,
    "K": K,
    "mu": mu,
    "e": sp.E,
    "E": sp.E,
    "exp": sp.exp,
    "sqrt": sp.sqrt,
    "log": sp.log,
    "ln": sp.log,
    "abs": sp.Abs,
    "Abs": sp.Abs,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "pi": sp.pi,
}


@dataclass
class NormalizedMathInput:
    original: str
    input_type: str
    normalized: str
    expression: sp.Expr | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


def normalize_math_text(
    answer: str,
    input_type: str = "text",
) -> str:
    """
    Normalize answer text according to its declared input type.
    Text/number inputs remain backward-compatible plain strings.
    Math/LaTeX inputs are converted to SymPy-readable text.
    """

    clean_answer = answer.strip()
    normalized_input_type = input_type.strip().lower()

    if normalized_input_type in {
        "math",
        "latex",
    }:
        return latex_to_sympy_text(
            clean_answer
        )

    return (
        clean_answer
        .replace("×", "*")
        .replace("÷", "/")
    )


def parse_normalized_math(
    normalized: str,
) -> sp.Expr:
    try:
        return parse_expr(
            normalized,
            transformations=TRANSFORMATIONS,
            local_dict=LOCAL_DICT,
            evaluate=True,
        )

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        TokenError,
        sp.SympifyError,
    ) as exc:
        raise MathInputError(
            "Malformed mathematical input."
        ) from exc


def normalize_student_submission(
    submission: StudentSubmission,
) -> NormalizedMathInput:
    input_type = (
        submission.input_type
        .strip()
        .lower()
    )

    try:
        normalized = normalize_math_text(
            answer=submission.answer,
            input_type=input_type,
        )

        if input_type in {
            "math",
            "latex",
        }:
            expression = parse_normalized_math(
                normalized
            )
        else:
            expression = None

        return NormalizedMathInput(
            original=submission.answer,
            input_type=input_type,
            normalized=normalized,
            expression=expression,
        )

    except MathInputError as exc:
        return NormalizedMathInput(
            original=submission.answer,
            input_type=input_type,
            normalized="",
            expression=None,
            error=str(exc),
        )
