import random

import sympy as sp


x = sp.symbols("x")
C = sp.symbols("C")


def generate_linear_first_order_question(
    difficulty: int = 1,
) -> dict:
    """
    Generate first-order linear ODEs of the form:

        y' + P(x)y = Q(x)

    The generator is constructed so that the integrating-factor
    step produces a clean elementary integral.

    Instead of choosing arbitrary P(x) and Q(x), we choose:

        P(x)

    and a simple function R(x), then define:

        Q(x) = R'(x) + P(x)*R(x)

    This guarantees that R(x) is a particular solution.

    The general solution is then:

        y = R(x) + C*exp(-integral(P(x), x))

    This makes the resulting exercises clean and suitable
    for step-by-step tutoring.
    """

    if difficulty == 1:
        p_choices = [
            1,
            2,
            -1,
            -2,
        ]

        particular_choices = [
            1,
            -1,
            2,
            x,
            -x,
        ]

    elif difficulty == 2:
        p_choices = [
            x,
            2 * x,
            -x,
            -2 * x,
        ]

        particular_choices = [
            1,
            -1,
            x,
            -x,
            2 * x,
        ]

    else:
        p_choices = [
            x,
            2 * x,
            -x,
            -2 * x,
            x**2,
            -x**2,
        ]

        particular_choices = [
            1,
            -1,
            x,
            -x,
            x**2,
            -x**2,
        ]

    P = random.choice(
        p_choices
    )

    particular_solution = random.choice(
        particular_choices
    )

    #
    # Construct Q so that:
    #
    # particular_solution' + P*particular_solution = Q
    #
    Q = sp.simplify(
        sp.diff(
            particular_solution,
            x,
        )
        + P * particular_solution
    )

    integrated_p = sp.integrate(
        P,
        x,
    )

    integrating_factor = sp.exp(
        integrated_p
    )

    #
    # mu*Q is guaranteed to integrate cleanly because:
    #
    # d/dx(mu*R) = mu*(R' + P*R)
    #             = mu*Q
    #
    integrand = sp.simplify(
        integrating_factor * Q
    )

    antiderivative = sp.simplify(
        integrating_factor
        * particular_solution
    )

    general_solution = sp.simplify(
        particular_solution
        + C * sp.exp(
            -integrated_p
        )
    )

    question_text = (
        "Solve "
        f"dy/dx + ({sp.sstr(P)})*y "
        f"= {sp.sstr(Q)}"
    )

    return {
        "type": "linear_first_order",
        "difficulty": difficulty,
        "question": question_text,

        "P": sp.sstr(P),
        "Q": sp.sstr(Q),

        "p_expression": P,
        "q_expression": Q,

        "integrated_p": integrated_p,
        "integrating_factor": integrating_factor,

        "particular_solution": particular_solution,

        "integrand": integrand,
        "antiderivative": antiderivative,

        "general_solution": general_solution,
    }