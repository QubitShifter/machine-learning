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


def main():
    assert_stage_input_mapping()
    assert_initial_response_uses_shared_contract()
    assert_concept_question_does_not_advance()
    assert_progression_into_mathlive_stage()
    assert_mathlive_latex_reaches_existing_checker()
    assert_malformed_math_input_is_safe()
    assert_full_solution_stage_flow_reaches_verification()

    print("linear_ode_adapter tests passed")


if __name__ == "__main__":
    main()
