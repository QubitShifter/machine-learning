from dataclasses import dataclass, replace
from typing import Any

import sympy as sp

from src.core.question_engine.contracts import (
    TutorQuestionContext,
)


_LINEAR_TOPICS = frozenset(
    {
        "first_order_linear",
    }
)
_MU_ESTABLISHED_STAGES = frozenset(
    {
        "multiply_by_integrating_factor",
        "recognize_product_derivative",
        "integrate_both_sides",
        "solve_for_y",
        "verify_solution",
        "complete",
    }
)
METHOD_INTEGRATING_FACTOR = (
    "first-order linear integrating-factor method"
)
METHOD_SEPARABLE = "separable"
METHOD_SEPARABLE_LABEL = "separable variables"


@dataclass(frozen=True)
class VerifiedTransformation:
    method: str
    original_equation: str
    rearranged_equation: str
    separated_equation: str | None = None
    integration_step: str | None = None
    conditions: tuple[str, ...] = ()
    constant_solutions: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "method": self.method,
            "verified": True,
            "original_equation": self.original_equation,
            "rearranged_equation": self.rearranged_equation,
        }
        if self.separated_equation is not None:
            data["separated_equation"] = (
                self.separated_equation
            )
        if self.integration_step is not None:
            data["integration_step"] = (
                self.integration_step
            )
        if self.conditions:
            data["conditions"] = list(self.conditions)
        if self.constant_solutions:
            data["constant_solutions"] = list(
                self.constant_solutions
            )
        return data


@dataclass(frozen=True)
class InternalSolutionCheck:
    method: str
    candidate: str
    residual: str
    verified: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "candidate": self.candidate,
            "residual": self.residual,
            "verified": self.verified,
        }


def enrich_question_context(
    context: TutorQuestionContext,
) -> TutorQuestionContext:
    raw_metadata = context.tutor_metadata
    metadata = (
        dict(raw_metadata)
        if isinstance(raw_metadata, dict)
        else {}
    )
    if context.topic in _LINEAR_TOPICS:
        metadata.update(
            linear_ode_verified_facts(metadata)
        )

    return replace(context, tutor_metadata=metadata)


def linear_ode_residual(P, Q, y_expr, x=None):
    independent = x if x is not None else sp.symbols("x")
    residual = (
        sp.diff(y_expr, independent)
        + P * y_expr
        - Q
    )
    return sp.simplify(residual)


def linear_ode_verified_facts(
    metadata: dict[str, Any],
) -> dict[str, Any]:
    p_raw = metadata.get("p_expression")
    q_raw = metadata.get("q_expression")
    if not isinstance(p_raw, str) or not isinstance(
        q_raw,
        str,
    ):
        return {}

    try:
        P = sp.sympify(p_raw)
        Q = sp.sympify(q_raw)
    except (sp.SympifyError, TypeError, ValueError):
        return {}

    x = sp.symbols("x")
    equation = (
        "dy/dx + "
        f"({sp.sstr(P)})*y = {sp.sstr(Q)}"
    )
    facts: dict[str, Any] = {
        "equation": equation,
        "p_expression": sp.sstr(P),
        "q_expression": sp.sstr(Q),
        "integrating_factor_method_applies": True,
        "also_separable": False,
        "also_direct_integration": bool(
            sp.simplify(P) == 0
        ),
        "verified_alternative_methods": [
            METHOD_INTEGRATING_FACTOR,
        ],
        "verified_method_evidence": [],
        "classified_separable": False,
        "separable_transformation_verified": False,
    }

    stage = metadata.get("stage")
    if (
        isinstance(stage, str)
        and stage in _MU_ESTABLISHED_STAGES
    ):
        try:
            mu = sp.exp(sp.integrate(P, x))
            facts["integrating_factor"] = sp.sstr(mu)
        except (ValueError, TypeError, AttributeError):
            pass

    classified = _classify_linear_ode(P, Q, x)
    facts["classified_separable"] = (
        "separable" in classified
    )

    transformation = _verified_separable_transformation(
        P,
        Q,
        x,
        equation,
    )
    if transformation is not None:
        facts["also_separable"] = True
        facts["separable_transformation_verified"] = True
        facts["verified_alternative_methods"] = [
            METHOD_INTEGRATING_FACTOR,
            METHOD_SEPARABLE_LABEL,
        ]
        facts["verified_method_evidence"] = [
            transformation.to_public_dict(),
        ]
        facts["alternative_method_notes"] = (
            "The integrating-factor method applies because "
            "the ODE is first-order linear. A verified "
            "separable-variables transformation is included "
            "below. Explain those verified steps. Do not "
            "invent extra algebra. Do not claim that the "
            "integrating-factor method is the only possible "
            "method. Do not reveal a complete explicit "
            "solution for y unless the learner asked for a "
            "fully worked solution."
        )
        internal = _internal_dsolve_check(P, Q, x)
        if internal is not None:
            facts["internal_solution_checks"] = [
                internal.to_dict(),
            ]
    else:
        facts["alternative_method_notes"] = (
            "The integrating-factor method applies because "
            "the ODE is first-order linear. Other methods "
            "can work for particular equations, but no "
            "verified alternative transformation is "
            "available for this P(x) and Q(x). Do not "
            "assume every first-order linear ODE is "
            "separable. Do not invent a separated equation. "
            "Do not claim that the integrating-factor "
            "method is the only possible method, and do "
            "not invent other method names."
        )

    return facts


def _classify_linear_ode(P, Q, x) -> set[str]:
    try:
        y = sp.Function("y")
        ode = y(x).diff(x) + P * y(x) - Q
        return set(sp.classify_ode(ode))
    except (
        TypeError,
        ValueError,
        NotImplementedError,
        AttributeError,
    ):
        return set()


def _verified_separable_transformation(
    P,
    Q,
    x,
    original_equation: str,
) -> VerifiedTransformation | None:
    y = sp.symbols("y")
    try:
        rhs = sp.simplify(Q - P * y)
        if sp.simplify(rhs + P * y - Q) != 0:
            return None
        if rhs == 0:
            return None

        factored = sp.factor(rhs)
        f_part, g_part = factored.as_independent(
            y,
            as_Add=False,
        )
        if f_part.has(y) or g_part.has(x):
            return None
        if sp.simplify(f_part * g_part - rhs) != 0:
            return None
        if g_part != 0 and sp.simplify(
            rhs / g_part - f_part
        ) != 0:
            return None

        rearranged = f"dy/dx = {sp.sstr(factored)}"
        if g_part == 0:
            return None

        if not g_part.has(y):
            separated = _separated_latex(f_part * g_part, None)
            conditions: tuple[str, ...] = ()
            constants: tuple[str, ...] = ()
            integrand_y = 1
            integrand_x = f_part * g_part
        else:
            separated = _separated_latex(f_part, g_part)
            conditions = (_restriction_latex(g_part),)
            constants = _verified_constant_solutions(
                P,
                Q,
                g_part,
                y,
            )
            integrand_y = 1 / g_part
            integrand_x = f_part

        integration_step = _verified_integration_step(
            integrand_y,
            integrand_x,
            y,
            x,
        )
        return VerifiedTransformation(
            method=METHOD_SEPARABLE,
            original_equation=original_equation,
            rearranged_equation=rearranged,
            separated_equation=separated,
            integration_step=integration_step,
            conditions=conditions,
            constant_solutions=constants,
        )
    except (
        TypeError,
        ValueError,
        NotImplementedError,
        AttributeError,
        sp.SympifyError,
    ):
        return None


def _verified_constant_solutions(
    P,
    Q,
    g_part,
    y,
) -> tuple[str, ...]:
    try:
        roots = sp.solve(g_part, y)
    except (
        TypeError,
        ValueError,
        NotImplementedError,
    ):
        return ()

    verified: list[str] = []
    x = sp.symbols("x")
    for root in roots:
        if getattr(root, "has", lambda *_: True)(x):
            continue
        residual = sp.simplify(P * root - Q)
        if residual == 0:
            verified.append(
                sp.latex(sp.Eq(y, root))
            )

    return tuple(verified)


def _factor_latex(expr) -> str:
    if getattr(expr, "is_Add", False):
        return r"\left(" + sp.latex(expr) + r"\right)"
    return sp.latex(expr)


def _separated_latex(f_part, g_part) -> str:
    if g_part is None:
        return rf"dy = {_factor_latex(f_part)}\, dx"
    denom = sp.latex(g_part)
    return (
        rf"\frac{{dy}}{{{denom}}} = "
        rf"{_factor_latex(f_part)}\, dx"
    )


def _restriction_latex(g_part) -> str:
    return sp.latex(sp.Ne(g_part, 0))


def _verified_integration_step(
    integrand_y,
    integrand_x,
    y,
    x,
) -> str | None:
    try:
        left = sp.simplify(sp.integrate(integrand_y, y))
        right = sp.simplify(sp.integrate(integrand_x, x))
    except (
        TypeError,
        ValueError,
        NotImplementedError,
        AttributeError,
    ):
        return None

    if left.has(sp.Integral) or right.has(sp.Integral):
        return None

    return f"{sp.sstr(left)} = {sp.sstr(right)} + C"


def _internal_dsolve_check(
    P,
    Q,
    x,
) -> InternalSolutionCheck | None:
    try:
        y = sp.Function("y")
        ode = sp.Eq(y(x).diff(x) + P * y(x), Q)
        solution = sp.dsolve(ode, y(x))
        candidate = solution.rhs
        residual = linear_ode_residual(
            P,
            Q,
            candidate,
            x,
        )
        return InternalSolutionCheck(
            method=METHOD_SEPARABLE,
            candidate=sp.sstr(candidate),
            residual=sp.sstr(residual),
            verified=residual == 0,
        )
    except (
        TypeError,
        ValueError,
        NotImplementedError,
        AttributeError,
    ):
        return None
