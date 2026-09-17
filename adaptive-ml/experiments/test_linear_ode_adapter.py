import sympy as sp

from src.core.tutor_engine.adapters.linear_ode_adapter import (
    STAGE_INPUT_TYPES,
    VERIFICATION_INPUT_TYPES,
    LinearODETutorAdapter,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
)
from src.core.tutor_engine.linear_first_order_session import (
    LinearODEStage,
)
from src.core.tutor_engine.linear_first_order_verification import (
    LinearVerificationStage,
)


x = sp.symbols("x")


def make_adapter():
    return LinearODETutorAdapter(
        p_expression=2 * x,
        q_expression=x,
    )


def submit(
    adapter,
    answer,
    input_type="text",
):
    return adapter.submit(
        StudentSubmission(
            answer=answer,
            input_type=input_type,
        )
    )


def assert_stage_input_mapping():
    assert (
        STAGE_INPUT_TYPES[
            LinearODEStage.IDENTIFY_STANDARD_FORM
        ]
        == "text"
    )
    assert (
        STAGE_INPUT_TYPES[
            LinearODEStage.IDENTIFY_P_Q
        ]
        == "text"
    )

    math_stages = [
        LinearODEStage.FIND_INTEGRATING_FACTOR,
        LinearODEStage.MULTIPLY_BY_INTEGRATING_FACTOR,
        LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE,
        LinearODEStage.INTEGRATE_BOTH_SIDES,
        LinearODEStage.SOLVE_FOR_Y,
    ]

    for stage in math_stages:
        assert STAGE_INPUT_TYPES[stage] == "math"

    assert (
        VERIFICATION_INPUT_TYPES[
            LinearVerificationStage.DIFFERENTIATE
        ]
        == "math"
    )
    assert (
        VERIFICATION_INPUT_TYPES[
            LinearVerificationStage.SUBSTITUTE
        ]
        == "math"
    )
    assert (
        VERIFICATION_INPUT_TYPES[
            LinearVerificationStage.COMPARE
        ]
        == "text"
    )


def assert_initial_response_uses_shared_contract():
    adapter = make_adapter()

    response = adapter.get_current_response()

    assert response.status == "waiting_for_answer"
    assert response.current_step == 1
    assert response.total_steps == 8
    assert response.expected_input_type == "text"
    assert response.metadata["stage"] == (
        "identify_standard_form"
    )
    assert "standard form" in response.feedback


def assert_concept_question_does_not_advance():
    adapter = make_adapter()

    before = adapter.get_current_response()

    response = submit(
        adapter,
        "why do we use this form?",
    )

    after = adapter.get_current_response()

    assert response.status == "concept"
    assert response.metadata["concept_question"] is True
    assert response.current_step == before.current_step
    assert after.current_step == before.current_step
    assert adapter.solution_session.get_attempts_for_current_stage() == 0


def assert_bulgarian_yes_is_accepted():
    adapter = LinearODETutorAdapter(
        p_expression=2 * x,
        q_expression=x,
        language="bg",
    )

    response = submit(adapter, "да")
    assert response.status == "correct"
    assert response.current_step == 2
    assert (
        "След това определете P(x) и Q(x)."
        == response.suggestion
    )
    assert "The equation is already" not in (
        response.feedback
    )
    assert "Next, identify" not in (
        response.suggestion or ""
    )


def assert_progression_into_mathlive_stage():
    adapter = make_adapter()

    stage_1 = submit(
        adapter,
        "yes",
    )
    assert stage_1.status == "correct"
    assert stage_1.current_step == 2
    assert stage_1.expected_input_type == "text"

    stage_2 = submit(
        adapter,
        "P = 2*x, Q = x",
    )
    assert stage_2.status == "correct"
    assert stage_2.current_step == 3
    assert stage_2.expected_input_type == "math"


def assert_mathlive_latex_reaches_existing_checker():
    adapter = make_adapter()

    submit(adapter, "yes")
    submit(adapter, "P = 2*x, Q = x")

    response = submit(
        adapter,
        r"e^{x^2}",
        input_type="math",
    )

    assert response.status == "correct"
    assert response.current_step == 4
    assert response.expected_input_type == "math"


def assert_malformed_math_input_is_safe():
    adapter = make_adapter()

    submit(adapter, "yes")
    submit(adapter, "P = 2*x, Q = x")

    response = submit(
        adapter,
        r"e^{x^2",
        input_type="math",
    )

    assert response.status == "incorrect"
    assert response.current_step == 3
    assert response.expected_input_type == "math"
    assert response.metadata["error_type"] == "parse_error"
    assert response.completed is False


def assert_full_solution_stage_flow_reaches_verification():
    adapter = make_adapter()

    submit(adapter, "yes")
    submit(adapter, "P = 2*x, Q = x")
    submit(adapter, r"e^{x^2}", input_type="math")
    submit(
        adapter,
        (
            r"e^{x^2}*y' + 2*x*e^{x^2}*y "
            r"= x*e^{x^2}"
        ),
        input_type="math",
    )
    submit(
        adapter,
        r"d/dx(e^{x^2}*y) = x*e^{x^2}",
        input_type="math",
    )
    submit(
        adapter,
        r"e^{x^2}*y = e^{x^2}/2 + C",
        input_type="math",
    )
    response = submit(
        adapter,
        r"y = 1/2 + C*e^{-x^2}",
        input_type="math",
    )

    assert response.status == "correct"
    assert response.current_step == 8
    assert response.expected_input_type == "math"
    assert response.metadata["stage"] == "verify_solution"
    assert (
        response.metadata["verification_stage"]
        == "differentiate"
    )


def assert_bulgarian_concept_question_keeps_spaces():
    adapter = LinearODETutorAdapter(
        p_expression=2 * x,
        q_expression=x,
        language="bg",
    )

    submit(adapter, "да")
    submit(adapter, "P = 2*x, Q = x")

    question = "Защо ми е нужен интегриращ фактор?"
    response = submit(adapter, question)

    assert response.status == "concept"
    assert response.current_step == 3
    assert "Интегриращият фактор" in response.feedback
    assert "mu' = P(x)*mu" in response.feedback
    assert "The integrating factor" not in response.feedback
    assert "We start with" not in response.feedback
    assert "By the product rule" not in response.feedback

    variant = submit(
        adapter,
        "Защо използваме интегриращ фактор?",
    )
    assert variant.status == "concept"
    assert "Интегриращият фактор" in variant.feedback
    assert "The integrating factor" not in variant.feedback


def reach_solve_for_y(adapter):
    submit(adapter, "да" if adapter.language == "bg" else "yes")
    submit(adapter, "P = 2*x, Q = x")
    submit(adapter, r"e^{x^2}", input_type="math")
    submit(
        adapter,
        (
            r"e^{x^2}*y' + 2*x*e^{x^2}*y "
            r"= x*e^{x^2}"
        ),
        input_type="math",
    )
    submit(
        adapter,
        r"d/dx(e^{x^2}*y) = x*e^{x^2}",
        input_type="math",
    )
    submit(
        adapter,
        r"e^{x^2}*y = e^{x^2}/2 + C",
        input_type="math",
    )


def reach_compare(adapter):
    reach_solve_for_y(adapter)
    submit(
        adapter,
        r"y = 1/2 + C*e^{-x^2}",
        input_type="math",
    )
    submit(
        adapter,
        r"\frac{dy}{dx}=-2xCe^{-x^2}",
        input_type="math",
    )
    return submit(adapter, "x", input_type="math")


def assert_bulgarian_divide_question_is_concept_not_incorrect():
    adapter = LinearODETutorAdapter(
        p_expression=2 * x,
        q_expression=x,
        language="bg",
    )
    reach_solve_for_y(adapter)
    attempts_before = (
        adapter.solution_session
        .get_attempts_for_current_stage()
    )
    step_before = adapter.get_current_response().current_step

    question = (
        "И двете страни на уравнението ли да се разделят "
        "на интегриращия фактор?"
    )
    response = submit(adapter, question)

    assert response.status == "concept"
    assert response.metadata["concept_question"] is True
    assert "разделяме двете страни" in response.feedback
    assert "mu(x)" in response.feedback
    assert "Задайте концептуален въпрос" not in response.feedback
    assert "Интегриращият фактор се избира" not in response.feedback
    assert "The integrating factor" not in response.feedback
    assert response.current_step == step_before
    assert (
        adapter.solution_session.get_attempts_for_current_stage()
        == attempts_before
    )

    second = submit(
        adapter,
        "Трябва ли да разделя двете страни на интегриращия фактор?",
    )
    assert second.status == "concept"
    assert "разделяме двете страни" in second.feedback
    assert (
        adapter.solution_session.get_attempts_for_current_stage()
        == attempts_before
    )


def assert_comparison_payload(response, left="x", right="x"):
    comparison = response.metadata.get("comparison")
    assert comparison is not None
    assert comparison["kind"] == "expression_comparison"
    assert comparison["left"] == left
    assert comparison["right"] == right
    assert comparison["title"]
    assert comparison["left_label"]
    assert comparison["right_label"]
    assert comparison["question"]


def assert_bulgarian_compare_keeps_lhs_rhs_and_accepts_match():
    adapter = LinearODETutorAdapter(
        p_expression=2 * x,
        q_expression=x,
        language="bg",
    )
    initial = reach_compare(adapter)
    assert_comparison_payload(initial)
    assert initial.metadata["verification_stage"] == "compare"

    wrong = submit(adapter, "не")
    assert wrong.status == "incorrect"
    assert wrong.completed is False
    assert_comparison_payload(wrong)
    assert wrong.metadata["comparison"]["left"] == (
        initial.metadata["comparison"]["left"]
    )
    assert wrong.metadata["comparison"]["right"] == (
        initial.metadata["comparison"]["right"]
    )
    assert "Съвпадат ли" in (
        wrong.metadata["comparison"]["question"]
    ) or "съвпадат" in wrong.metadata["comparison"]["question"].lower()

    hint = adapter.request_hint()
    assert hint.status == "hint"
    assert_comparison_payload(hint)

    concept = submit(
        adapter,
        "Защо ни е нужен интегриращ фактор?",
    )
    assert concept.status == "concept"
    assert_comparison_payload(concept)

    correct = submit(adapter, "да, съвпадат")
    assert correct.status == "complete"
    assert correct.completed is True
    assert "comparison" not in correct.metadata


def assert_generated_problem_title_is_distinct():
    x = sp.symbols("x")
    fixed = LinearODETutorAdapter(
        p_expression=2 * x,
        q_expression=x,
        problem_id="linear_first_order_fixed_001",
        language="bg",
    )
    generated = LinearODETutorAdapter(
        p_expression=2 * x,
        q_expression=x,
        problem_id=(
            "linear_first_order_generated_a1b2c3d4e5f6"
        ),
        language="bg",
    )

    assert fixed.problem_id == (
        "linear_first_order_fixed_001"
    )
    assert generated.problem_id == (
        "linear_first_order_generated_a1b2c3d4e5f6"
    )
    assert fixed.problem_title == (
        "Линейно диференциално уравнение от първи ред"
    )
    assert generated.problem_title == (
        "Генерирана задача — линейно ДУ от първи ред"
    )
    assert fixed.problem_title != generated.problem_title

    english_generated = LinearODETutorAdapter(
        p_expression=2 * x,
        q_expression=x,
        problem_id=(
            "linear_first_order_generated_a1b2c3d4e5f6"
        ),
        language="en",
    )
    assert english_generated.problem_title == (
        "Generated problem — first-order linear ODE"
    )


def main():
    assert_generated_problem_title_is_distinct()
    assert_stage_input_mapping()
    assert_initial_response_uses_shared_contract()
    assert_concept_question_does_not_advance()
    assert_bulgarian_yes_is_accepted()
    assert_bulgarian_concept_question_keeps_spaces()
    assert_bulgarian_divide_question_is_concept_not_incorrect()
    assert_progression_into_mathlive_stage()
    assert_mathlive_latex_reaches_existing_checker()
    assert_malformed_math_input_is_safe()
    assert_full_solution_stage_flow_reaches_verification()
    assert_bulgarian_compare_keeps_lhs_rhs_and_accepts_match()

    print("linear_ode_adapter tests passed")


if __name__ == "__main__":
    main()
