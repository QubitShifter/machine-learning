import sympy as sp

from src.core.tutor_engine.linear_first_order_session import (
    LinearODEStage,
)


def looks_like_linear_concept_question(
    student_message: str,
) -> bool:
    """
    Detect whether the student is asking for conceptual help
    rather than submitting a mathematical answer.
    """

    message = (
        student_message
        .strip()
        .lower()
    )

    question_phrases = [
        "why",
        "what is",
        "what does",
        "what are",
        "how does",
        "how do",
        "how can",
        "why do",
        "why does",
        "why is",
        "explain",
        "i don't understand",
        "i dont understand",
        "i do not understand",
        "what's",
        "whats",
        "where does",
        "where do",
    ]

    return any(
        phrase in message
        for phrase in question_phrases
    )


def explain_integrating_factor(
    p_expression,
) -> str:
    P = sp.sstr(
        p_expression
    )

    integrated_p = sp.integrate(
        p_expression,
        sp.symbols("x"),
    )

    mu = sp.exp(
        integrated_p
    )

    return (
        "The integrating factor is chosen for a very specific reason.\n\n"
        "We start with:\n\n"
        "    y' + P(x)y = Q(x)\n\n"
        "and multiply everything by a function mu(x):\n\n"
        "    mu*y' + mu*P(x)*y = mu*Q(x)\n\n"
        "We want the two terms on the left to become the derivative "
        "of the product mu(x)*y.\n\n"
        "By the product rule:\n\n"
        "    d/dx(mu*y) = mu*y' + mu'*y\n\n"
        "So we need:\n\n"
        "    mu' = P(x)*mu\n\n"
        "The function that has this property is:\n\n"
        "    mu(x) = exp(integral(P(x)) dx)\n\n"
        f"For this problem P(x) = {P}, so:\n\n"
        f"    integral(P(x)) dx = {sp.sstr(integrated_p)}\n\n"
        f"and therefore:\n\n"
        f"    mu(x) = {sp.sstr(mu)}\n\n"
        "So the integrating factor is not an arbitrary trick. "
        "It is deliberately constructed so that the left side "
        "turns into one product derivative."
    )


def explain_product_derivative() -> str:
    return (
        "This comes directly from the product rule.\n\n"
        "For two functions mu(x) and y(x):\n\n"
        "    d/dx(mu*y) = mu*y' + mu'*y\n\n"
        "After multiplying the linear ODE by the integrating factor, "
        "the left side is:\n\n"
        "    mu*y' + mu*P(x)*y\n\n"
        "But the integrating factor was chosen so that:\n\n"
        "    mu' = P(x)*mu\n\n"
        "Therefore:\n\n"
        "    mu*P(x)*y = mu'*y\n\n"
        "and the left side becomes:\n\n"
        "    mu*y' + mu'*y\n\n"
        "which is exactly:\n\n"
        "    d/dx(mu*y)\n\n"
        "We are using the product rule backward."
    )


def explain_integration_constant() -> str:
    return (
        "We add C because we are taking an indefinite integral.\n\n"
        "When we differentiate a constant, its derivative is zero.\n"
        "For example:\n\n"
        "    d/dx(x^2 + 5) = 2*x\n"
        "    d/dx(x^2 - 8) = 2*x\n\n"
        "So when we reverse differentiation, there are infinitely "
        "many antiderivatives that differ only by a constant.\n\n"
        "That is why we write:\n\n"
        "    integral(f(x)) dx = F(x) + C\n\n"
        "For a differential equation, C is especially important "
        "because it represents the whole family of solutions."
    )


def explain_dividing_by_integrating_factor() -> str:
    return (
        "At this stage we have an equation of the form:\n\n"
        "    mu(x)*y = F(x) + C\n\n"
        "We want y by itself, so we divide both sides by mu(x):\n\n"
        "    y = (F(x) + C) / mu(x)\n\n"
        "This is safe because an integrating factor has the form:\n\n"
        "    mu(x) = exp(...)\n\n"
        "and an exponential is always positive, so mu(x) is never zero."
    )


def explain_p_q_identification() -> str:
    return (
        "A first-order linear differential equation is written as:\n\n"
        "    y' + P(x)y = Q(x)\n\n"
        "P(x) is the coefficient multiplying y.\n\n"
        "Q(x) is the expression by itself on the right-hand side.\n\n"
        "So the goal is simply to compare the current equation "
        "term by term with this standard form."
    )


def respond_to_linear_concept_question(
    student_message: str,
    stage: LinearODEStage,
    p_expression=None,
) -> str | None:
    """
    Return a conceptual explanation appropriate to the current
    stage. Return None when the message does not appear to be
    a concept question.
    """

    if not looks_like_linear_concept_question(
        student_message
    ):
        return None

    message = (
        student_message
        .strip()
        .lower()
    )

    asks_about_integrating_factor = (
        "integrating factor" in message
        or "integration factor" in message
        or "why do we need mu" in message
        or "why do we use mu" in message
        or "what is mu" in message
    )

    asks_about_product_derivative = (
        "product derivative" in message
        or "product rule" in message
        or "why does this become a derivative" in message
        or "why is this a derivative" in message
        or "why does the left side" in message
    )

    asks_about_constant = (
        "why do we add c" in message
        or "why add c" in message
        or "why + c" in message
        or "constant c" in message
        or "integration constant" in message
        or "arbitrary constant" in message
    )

    asks_about_dividing = (
        "why divide" in message
        or "why do we divide" in message
        or "divide by mu" in message
        or "divide by the integrating factor" in message
    )

    asks_about_p_q = (
        "what is p" in message
        or "what is q" in message
        or "how do i find p" in message
        or "how do i find q" in message
        or "identify p" in message
        or "identify q" in message
    )

    if asks_about_dividing:
        return explain_dividing_by_integrating_factor()

    if asks_about_product_derivative:
        return explain_product_derivative()

    if asks_about_constant:
        return explain_integration_constant()

    if asks_about_p_q:
        return explain_p_q_identification()

    if asks_about_integrating_factor:
        return explain_integrating_factor(
            p_expression
        )

    #
    # Stage-aware fallback.
    #
    # This means a genuine conceptual question such as
    # "I don't understand this step" still receives useful help.
    #
    if (
        stage
        == LinearODEStage.IDENTIFY_P_Q
    ):
        return explain_p_q_identification()

    if (
        stage
        == LinearODEStage.FIND_INTEGRATING_FACTOR
    ):
        return explain_integrating_factor(
            p_expression
        )

    if (
        stage
        == LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE
    ):
        return explain_product_derivative()

    if (
        stage
        == LinearODEStage.INTEGRATE_BOTH_SIDES
    ):
        return explain_integration_constant()

    if (
        stage
        == LinearODEStage.SOLVE_FOR_Y
    ):
        return explain_dividing_by_integrating_factor()

    return (
        "This is a conceptual question about the current step. "
        "Try asking what part of the step is unclear, and I will "
        "explain the mathematical idea without advancing the problem."
    )