import sympy as sp

from src.core.tutor_engine.concept_guidance.linear_first_order_guidance import (
    respond_to_linear_concept_question,
)
from src.core.tutor_engine.linear_first_order_engine import (
    LinearFirstOrderEngine,
)
from src.core.tutor_engine.linear_first_order_session import (
    LinearODEStage,
)


x = sp.symbols("x")


engine = LinearFirstOrderEngine(
    p_expression=2 * x,
    q_expression=x,
)
bg_engine = LinearFirstOrderEngine(
    p_expression=2 * x,
    q_expression=x,
    language="bg",
)


tests = [
    (
        LinearODEStage.FIND_INTEGRATING_FACTOR,
        "why do we need an integrating factor?",
        "The integrating factor",
    ),
    (
        LinearODEStage.FIND_INTEGRATING_FACTOR,
        "what is mu?",
        "The integrating factor",
    ),
    (
        LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE,
        "why does this become a product derivative?",
        "product rule",
    ),
    (
        LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE,
        "how does the product rule work here?",
        "product rule",
    ),
    (
        LinearODEStage.INTEGRATE_BOTH_SIDES,
        "why do we add C?",
        "indefinite integral",
    ),
    (
        LinearODEStage.SOLVE_FOR_Y,
        "why do we divide by the integrating factor?",
        "divide both sides",
    ),
]


for stage, question, expected in tests:
    print()
    print(
        "Stage:",
        stage.value,
    )

    print(
        "Question:",
        question,
    )

    result = engine.evaluate(
        stage=stage,
        student_answer=question,
    )

    print(
        "Kind:",
        result.get("kind"),
    )

    print(
        "Correct:",
        result["correct"],
    )

    print(
        "Advance:",
        result.get("advance"),
    )

    print(
        "Feedback:"
    )

    print(
        result["feedback"]
    )

    assert result.get("kind") == "concept"
    assert result["correct"] is False
    assert result.get("advance") is False
    assert expected in result["feedback"]
    assert "Интегриращият фактор" not in result["feedback"]


ENGLISH_FRAGMENTS = (
    "The integrating factor",
    "We start with",
    "and multiply everything",
    "We want the two terms",
    "By the product rule",
    "So we need",
    "The function that has this property",
    "For this problem",
    "and therefore",
)

bg_mu_questions = (
    "Защо ни е нужен интегриращ фактор?",
    "Защо използваме интегриращ фактор?",
    "Защо ни трябва интегриращ фактор?",
    "Каква е целта на интегриращия фактор?",
)

for question in bg_mu_questions:
    result = bg_engine.evaluate(
        stage=LinearODEStage.FIND_INTEGRATING_FACTOR,
        student_answer=question,
    )
    feedback = result["feedback"]
    assert result.get("kind") == "concept", question
    assert "Интегриращият фактор" in feedback, question
    assert "mu' = P(x)*mu" in feedback, question
    assert "y' + P(x)y = Q(x)" in feedback, question
    for fragment in ENGLISH_FRAGMENTS:
        assert fragment not in feedback, (question, fragment)

direct = respond_to_linear_concept_question(
    student_message="Защо ни е нужен интегриращ фактор?",
    stage=LinearODEStage.IDENTIFY_STANDARD_FORM,
    p_expression=2 * x,
    language="bg",
)
assert direct is not None
assert "Интегриращият фактор се избира с конкретна цел." in direct
assert "Това е концептуален въпрос" not in direct

bg_product = bg_engine.evaluate(
    stage=LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE,
    student_answer="Защо лявата страна става производна на произведение?",
)
assert bg_product.get("kind") == "concept"
assert "правилото за произведение" in bg_product["feedback"]
assert "This comes directly from the product rule." not in (
    bg_product["feedback"]
)

bg_constant = bg_engine.evaluate(
    stage=LinearODEStage.INTEGRATE_BOTH_SIDES,
    student_answer="Защо добавяме C?",
)
assert bg_constant.get("kind") == "concept"
assert "Добавяме C" in bg_constant["feedback"]
assert "We add C because" not in bg_constant["feedback"]

bg_divide = bg_engine.evaluate(
    stage=LinearODEStage.SOLVE_FOR_Y,
    student_answer="Защо делим на интегриращия фактор?",
)
assert bg_divide.get("kind") == "concept"
assert "разделяме двете страни" in bg_divide["feedback"]
assert "At this stage we have an equation" not in (
    bg_divide["feedback"]
)

bg_pq = bg_engine.evaluate(
    stage=LinearODEStage.IDENTIFY_P_Q,
    student_answer="Какво е P?",
)
assert bg_pq.get("kind") == "concept"
assert "P(x) е коефициентът" in bg_pq["feedback"]
assert "A first-order linear differential equation" not in (
    bg_pq["feedback"]
)

DIVIDE_FALLBACK_PHRASES = (
    "Задайте концептуален въпрос",
    "Това е концептуален въпрос",
)
DIVIDE_ENGLISH_FRAGMENTS = (
    "The integrating factor",
    "We start with",
    "At this stage we have an equation",
    "We want y by itself",
)
BG_DIVIDE_QUESTIONS = (
    "И двете страни на уравнението ли да се разделят "
    "на интегриращия фактор?",
    "Трябва ли да разделя двете страни на интегриращия фактор?",
    "Защо делим на интегриращия фактор?",
    "И двете страни ли делим на интегриращия фактор?",
    "Защо разделяме на интегриращия фактор?",
    "На интегриращия фактор ли трябва да разделим?",
    "И ДВЕТЕ СТРАНИ НА УРАВНЕНИЕТО ЛИ ДА СЕ РАЗДЕЛЯТ "
    "НА ИНТЕГРИРАЩИЯ ФАКТОР?",
    "И двете страни на уравнението ли да се разделят "
    "на интегриращия фактор",
    "и давете страни ли да се разделят на интегриращия фактор?",
)

for question in BG_DIVIDE_QUESTIONS:
    feedback = respond_to_linear_concept_question(
        student_message=question,
        stage=LinearODEStage.IDENTIFY_STANDARD_FORM,
        p_expression=2 * x,
        language="bg",
    )
    assert feedback is not None, question
    assert "разделяме двете страни" in feedback, question
    assert "mu(x)" in feedback, question
    assert "Интегриращият фактор се избира" not in feedback, question
    for phrase in DIVIDE_FALLBACK_PHRASES:
        assert phrase not in feedback, (question, phrase)
    for fragment in DIVIDE_ENGLISH_FRAGMENTS:
        assert fragment not in feedback, (question, fragment)

    engine_result = bg_engine.evaluate(
        stage=LinearODEStage.SOLVE_FOR_Y,
        student_answer=question,
    )
    assert engine_result.get("kind") == "concept", question
    assert engine_result["correct"] is False, question
    assert engine_result.get("advance") is False, question
    assert "разделяме двете страни" in engine_result["feedback"], (
        question
    )

mu_not_divide = respond_to_linear_concept_question(
    student_message="Защо ни е нужен интегриращ фактор?",
    stage=LinearODEStage.SOLVE_FOR_Y,
    p_expression=2 * x,
    language="bg",
)
assert mu_not_divide is not None
assert "Интегриращият фактор се избира" in mu_not_divide
assert "разделяме двете страни" not in mu_not_divide

english_divide = respond_to_linear_concept_question(
    student_message="Why do we divide by the integrating factor?",
    stage=LinearODEStage.IDENTIFY_STANDARD_FORM,
    p_expression=2 * x,
    language="en",
)
assert english_divide is not None
assert "divide both sides" in english_divide
assert "разделяме двете страни" not in english_divide

print("linear_concept tests passed")
