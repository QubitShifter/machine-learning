from __future__ import annotations

import re

import sympy as sp
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

PARSE_TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
)

from src.core.physics.kinematics.models import (
    KinematicsProblem,
    KinematicsStep,
)
from src.core.physics.kinematics.units import (
    QUANTITY_UNITS,
    match_leading_unit,
    normalize_unit,
    parse_quantity_answer,
    unit_dimension,
)


FORMULA_CANONICAL = {
    "velocity": "v = v0 + a*t",
    "displacement": "dx = v0*t + (1/2)*a*t**2",
    "displacement_avg": "dx = ((v0 + v)/2)*t",
    "velocity_sq": "v**2 = v0**2 + 2*a*dx",
    "time": "t = (v - v0)/a",
    "acceleration": "a = (v - v0)/t",
    "constant_velocity": "dx = v*t",
}

FORMULA_SYMBOLS = {
    "v": sp.symbols("v"),
    "v0": sp.symbols("v0"),
    "a": sp.symbols("a"),
    "t": sp.symbols("t"),
    "dx": sp.symbols("dx"),
    "x": sp.symbols("x"),
    "x0": sp.symbols("x0"),
}

ABS_TOLERANCE = 1e-6
REL_TOLERANCE = 1e-4


def format_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.4g}"


def quantity_value(
    problem: KinematicsProblem,
    quantity: str,
) -> float | None:
    return getattr(problem.quantities, quantity)


def evaluate_step(
    problem: KinematicsProblem,
    step: KinematicsStep,
    answer: str,
) -> dict:
    if step.kind == "formula":
        return evaluate_formula(step, answer)

    if step.kind == "summary":
        return evaluate_summary(problem, answer)

    return evaluate_quantity(problem, step, answer)


def evaluate_quantity(
    problem: KinematicsProblem,
    step: KinematicsStep,
    answer: str,
) -> dict:
    expected = quantity_value(problem, step.quantity or "")
    required_unit = step.unit or QUANTITY_UNITS.get(
        step.quantity or "",
    )
    value, unit_text, raw = parse_quantity_answer(answer)

    if value is None:
        return {
            "correct": False,
            "error_type": "not_numeric",
            "feedback": (
                "I could not read a numeric value. "
                "Include the number and its SI unit."
            ),
        }

    if expected is None:
        return {
            "correct": False,
            "error_type": "invalid_expected_answer",
            "feedback": (
                "The tutor could not validate this step."
            ),
        }

    if required_unit and unit_text is None:
        return {
            "correct": False,
            "error_type": "missing_unit",
            "feedback": (
                "Include the SI unit for "
                f"{_quantity_label(step.quantity)}."
            ),
        }

    if required_unit and unit_text is not None:
        canonical = normalize_unit(unit_text)
        if canonical is None:
            return {
                "correct": False,
                "error_type": "unknown_unit",
                "feedback": (
                    "I could not recognize that unit. "
                    f"Use {required_unit}."
                ),
            }

        expected_dimension = unit_dimension(required_unit)
        given_dimension = unit_dimension(canonical)
        if given_dimension != expected_dimension:
            return {
                "correct": False,
                "error_type": "wrong_unit",
                "feedback": (
                    "The numeric value may be close, "
                    "but the unit should represent "
                    f"{expected_dimension}."
                ),
            }

        if canonical != required_unit:
            return {
                "correct": False,
                "error_type": "wrong_unit",
                "feedback": (
                    "Use the SI unit "
                    f"{required_unit}."
                ),
            }

    if _values_match(value, expected):
        return {
            "correct": True,
            "error_type": None,
            "feedback": "Correct.",
        }

    if value * expected < 0:
        return {
            "correct": False,
            "error_type": "wrong_sign",
            "feedback": (
                "Check the chosen positive direction "
                "and the sign of acceleration."
            ),
        }

    return {
        "correct": False,
        "error_type": "wrong_value",
        "feedback": (
            "Check the substitution and arithmetic. "
            f"Raw input was {raw}."
        ),
    }


def evaluate_formula(
    step: KinematicsStep,
    answer: str,
) -> dict:
    expected = FORMULA_CANONICAL.get(
        step.formula_id or "",
        step.expected_text or "",
    )
    student = _equation_residual(answer)
    target = _equation_residual(expected)

    if student is None:
        return {
            "correct": False,
            "error_type": "missing_equals",
            "feedback": (
                "Write a complete equation using =."
            ),
        }

    if target is None:
        return {
            "correct": False,
            "error_type": "invalid_expected_answer",
            "feedback": (
                "The tutor could not validate this formula."
            ),
        }

    if _residuals_equivalent(student, target):
        return {
            "correct": True,
            "error_type": None,
            "feedback": "Correct.",
        }

    return {
        "correct": False,
        "error_type": "wrong_formula",
        "feedback": (
            "That equation does not relate the "
            "known quantities for this step."
        ),
    }


def evaluate_summary(
    problem: KinematicsProblem,
    answer: str,
) -> dict:
    found = _extract_quantities(answer)
    required = _required_summary_quantities(problem)

    if not required:
        return {
            "correct": False,
            "error_type": "invalid_expected_answer",
            "feedback": (
                "The tutor could not validate this step."
            ),
        }

    missing = [
        quantity
        for quantity, expected in required.items()
        if quantity not in found
        or not _values_match(found[quantity], expected)
    ]
    if missing:
        return {
            "correct": False,
            "error_type": "wrong_value",
            "feedback": (
                "State each requested result with "
                "its SI unit."
            ),
        }

    return {
        "correct": True,
        "error_type": None,
        "feedback": (
            "Correct. Those are the final results."
        ),
    }


def _required_summary_quantities(
    problem: KinematicsProblem,
) -> dict[str, float]:
    required: dict[str, float] = {}
    unknown = problem.unknown
    if unknown in {"v", "v_and_dx", "all"}:
        if problem.quantities.v is not None:
            required["v"] = problem.quantities.v
    if unknown in {"dx", "v_and_dx", "all"}:
        if problem.quantities.dx is not None:
            required["dx"] = problem.quantities.dx
    if unknown == "t" and problem.quantities.t is not None:
        required["t"] = problem.quantities.t
    if unknown == "a" and problem.quantities.a is not None:
        required["a"] = problem.quantities.a
    return required


def _extract_quantities(answer: str) -> dict[str, float]:
    found: dict[str, float] = {}

    for match in re.finditer(
        r"([+-]?(?:\d+(?:\.\d+)?|\.\d+))",
        answer,
    ):
        unit_alias = match_leading_unit(
            answer[match.end():]
        )
        if unit_alias is None:
            continue

        number = float(match.group(1))
        dimension = unit_dimension(unit_alias)
        if dimension == "velocity":
            found["v"] = number
        elif dimension == "length":
            found["dx"] = number
        elif dimension == "time":
            found["t"] = number
        elif dimension == "acceleration":
            found["a"] = number

    return found


def _values_match(value: float, expected: float) -> bool:
    difference = abs(value - expected)
    scale = max(1.0, abs(expected))
    return (
        difference <= ABS_TOLERANCE
        or difference / scale <= REL_TOLERANCE
    )


def _quantity_label(quantity: str | None) -> str:
    return {
        "v0": "initial velocity",
        "v": "velocity",
        "a": "acceleration",
        "t": "time",
        "dx": "displacement",
    }.get(quantity or "", "this quantity")


def normalize_formula_text(answer: str) -> str:
    text = answer.strip()
    replacements = (
        ("\\Delta_{x}", "dx"),
        ("\\delta_{x}", "dx"),
        ("\\Delta_x", "dx"),
        ("\\delta_x", "dx"),
        ("\\Delta{x}", "dx"),
        ("\\delta{x}", "dx"),
        ("\\Delta x", "dx"),
        ("\\delta x", "dx"),
        ("Δ_{x}", "dx"),
        ("δ_{x}", "dx"),
        ("Δ_x", "dx"),
        ("δ_x", "dx"),
        ("Δx", "dx"),
        ("δx", "dx"),
        ("delta_{x}", "dx"),
        ("Delta_{x}", "dx"),
        ("delta_x", "dx"),
        ("Delta_x", "dx"),
        ("delta x", "dx"),
        ("Delta x", "dx"),
        ("x_{0}", "x0"),
        ("x_0", "x0"),
        ("x - x0", "dx"),
        ("x-x0", "dx"),
        ("v_{\\mathrm{f}}", "v"),
        ("v_\\mathrm{f}", "v"),
        ("v_{f}", "v"),
        ("v_f", "v"),
        ("v_{0}", "v0"),
        ("v_0", "v0"),
        ("\\cdot{}", "*"),
        ("\\times{}", "*"),
        ("\\cdot", "*"),
        ("\\times", "*"),
        ("·", "*"),
        ("×", "*"),
        ("\\frac{1}{2}", "(1/2)"),
        ("1/2", "(1/2)"),
        ("^2", "**2"),
        ("²", "**2"),
    )
    for source, target in replacements:
        text = text.replace(source, target)
    text = re.sub(r"x\s*-\s*x0\b", "dx", text)
    text = re.sub(
        r"(?<![A-Za-z_\\])at(?![A-Za-z_])",
        "a*t",
        text,
    )
    return text


def _equation_residual(answer: str):
    normalized = normalize_formula_text(answer)
    if "=" not in normalized:
        return None

    left, right = normalized.split("=", 1)
    try:
        left_expr = parse_expr(
            left,
            local_dict=FORMULA_SYMBOLS,
            transformations=PARSE_TRANSFORMATIONS,
            evaluate=True,
        )
        right_expr = parse_expr(
            right,
            local_dict=FORMULA_SYMBOLS,
            transformations=PARSE_TRANSFORMATIONS,
            evaluate=True,
        )
    except (sp.SympifyError, SyntaxError, TypeError):
        return None

    residual = sp.expand(left_expr - right_expr)
    residual = residual.subs(
        {
            FORMULA_SYMBOLS["x"] - FORMULA_SYMBOLS["x0"]: (
                FORMULA_SYMBOLS["dx"]
            )
        }
    )
    return sp.simplify(residual)


def _residuals_equivalent(student, expected) -> bool:
    student = sp.simplify(student)
    expected = sp.simplify(expected)

    if student == 0 and expected == 0:
        return True

    if (
        sp.simplify(student - expected) == 0
        or sp.simplify(student + expected) == 0
    ):
        return True

    if expected == 0:
        return student == 0

    ratio = sp.simplify(sp.together(student / expected))
    if ratio == 0:
        return False

    if ratio.free_symbols:
        return False

    return ratio != 0
