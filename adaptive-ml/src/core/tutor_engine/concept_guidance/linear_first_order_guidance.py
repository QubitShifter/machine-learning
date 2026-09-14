import re

import sympy as sp

from src.core.i18n.locale import normalize_locale
from src.core.i18n.ode import ot
from src.core.tutor_engine.linear_first_order_session import (
    LinearODEStage,
)


_QUESTION_PHRASES = (
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
    "защо",
    "какво е",
    "каква е",
    "какъв е",
    "какво представлява",
    "обясни",
    "не разбирам",
    "как се",
    "как да",
    "за какво",
    "дали",
    "трябва ли",
)

_DIVIDE_MARKERS = (
    "why divide",
    "why do we divide",
    "divide by mu",
    "divide by the integrating factor",
    "divide both sides",
    "раздел",
    "делим",
    "деля",
    "дели на",
)

_BOTH_SIDES_MARKERS = (
    "both sides",
    "двете страни",
)

_DIVIDE_MU_MARKERS = (
    "integrating factor",
    "интегриращ",
    "mu",
)


def _fold_message(student_message: str) -> str:
    text = student_message.strip().lower()
    for mark in (",", ".", "!", "?", ";", ":", "„", "“", "”"):
        text = text.replace(mark, " ")
    return " ".join(text.split())


def _mentions(message: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in message for phrase in phrases)


def _asks_about_dividing(message: str) -> bool:
    if _mentions(message, _DIVIDE_MARKERS):
        return True

    return _mentions(message, _BOTH_SIDES_MARKERS) and _mentions(
        message,
        _DIVIDE_MU_MARKERS,
    )


def looks_like_linear_concept_question(
    student_message: str,
) -> bool:
    """
    Detect whether the student is asking for conceptual help
    rather than submitting a mathematical answer.
    """

    message = _fold_message(student_message)

    if any(phrase in message for phrase in _QUESTION_PHRASES):
        return True

    if re.search(r"\bли\b", message):
        return True

    return _asks_about_dividing(message)


def explain_integrating_factor(
    p_expression,
    language: str | None = None,
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

    return ot(
        language,
        "linear.concept.mu",
        P=P,
        integrated_p=sp.sstr(integrated_p),
        mu=sp.sstr(mu),
    )


def explain_product_derivative(
    language: str | None = None,
) -> str:
    return ot(language, "linear.concept.product")


def explain_integration_constant(
    language: str | None = None,
) -> str:
    return ot(language, "linear.concept.constant")


def explain_dividing_by_integrating_factor(
    language: str | None = None,
) -> str:
    return ot(language, "linear.concept.divide")


def explain_p_q_identification(
    language: str | None = None,
) -> str:
    return ot(language, "linear.concept.pq")


def respond_to_linear_concept_question(
    student_message: str,
    stage: LinearODEStage,
    p_expression=None,
    language: str | None = None,
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

    locale = normalize_locale(language)
    message = _fold_message(student_message)

    asks_about_integrating_factor = _mentions(
        message,
        (
            "integrating factor",
            "integration factor",
            "why do we need mu",
            "why do we use mu",
            "what is mu",
            "интегриращ",
            "какво е mu",
            "защо mu",
        ),
    )

    asks_about_product_derivative = _mentions(
        message,
        (
            "product derivative",
            "product rule",
            "why does this become a derivative",
            "why is this a derivative",
            "why does the left side",
            "производна на произведение",
            "правилото за произведение",
            "правило за произведение",
            "защо лявата страна",
        ),
    )

    asks_about_constant = _mentions(
        message,
        (
            "why do we add c",
            "why add c",
            "why + c",
            "constant c",
            "integration constant",
            "arbitrary constant",
            "защо добавяме c",
            "защо + c",
            "константа c",
            "произволна константа",
        ),
    )

    asks_about_dividing = _asks_about_dividing(message)

    asks_about_p_q = _mentions(
        message,
        (
            "what is p",
            "what is q",
            "how do i find p",
            "how do i find q",
            "identify p",
            "identify q",
            "какво е p",
            "какво е q",
            "как да намеря p",
            "как да намеря q",
            "определете p",
            "определете q",
        ),
    )

    if asks_about_dividing:
        return explain_dividing_by_integrating_factor(
            locale,
        )

    if asks_about_product_derivative:
        return explain_product_derivative(locale)

    if asks_about_constant:
        return explain_integration_constant(locale)

    if asks_about_p_q:
        return explain_p_q_identification(locale)

    if asks_about_integrating_factor:
        return explain_integrating_factor(
            p_expression,
            locale,
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
        return explain_p_q_identification(locale)

    if (
        stage
        == LinearODEStage.FIND_INTEGRATING_FACTOR
    ):
        return explain_integrating_factor(
            p_expression,
            locale,
        )

    if (
        stage
        == LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE
    ):
        return explain_product_derivative(locale)

    if (
        stage
        == LinearODEStage.INTEGRATE_BOTH_SIDES
    ):
        return explain_integration_constant(locale)

    if (
        stage
        == LinearODEStage.SOLVE_FOR_Y
    ):
        return explain_dividing_by_integrating_factor(
            locale,
        )

    return ot(locale, "linear.concept.fallback")
