import sympy as sp

from src.core.math_input import normalize_math_text
from src.core.tutor_engine.adapters.separable_ode_adapter import (
    STAGE_INPUT_TYPES,
    VERIFICATION_INPUT_TYPES,
    SeparableODETutorAdapter,
)
from src.core.tutor_engine.concept_guidance.log_solve_stage_checker import (
    evaluate_apply_exp_step,
)
from src.core.tutor_engine.concept_guidance.separable_session import (
    SeparableStage,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
)
from src.core.tutor_engine.separable_verification_engine import (
    VerificationStage,
)


x, y = sp.symbols("x y")


def make_adapter():
    return SeparableODETutorAdapter(
        rhs_expression=2 * x * y,
    )


def submit(
    adapter,
    answer,
    input_type="math",
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
            SeparableStage.SEPARATE_VARIABLES
        ]
        == "math"
    )
    assert (
        STAGE_INPUT_TYPES[
            SeparableStage.INTEGRATE_BOTH_SIDES
        ]
        == "math"
    )
    assert (
        STAGE_INPUT_TYPES[
            SeparableStage.SOLVE_LOG_EQUATION
        ]
        == "math"
    )

    assert (
        VERIFICATION_INPUT_TYPES[
            VerificationStage.DIFFERENTIATE
        ]
        == "math"
    )
    assert (
        VERIFICATION_INPUT_TYPES[
            VerificationStage.SUBSTITUTE_RHS
        ]
        == "math"
    )
    assert (
        VERIFICATION_INPUT_TYPES[
            VerificationStage.COMPARE
        ]
        == "text"
    )


def assert_initial_response():
    adapter = make_adapter()
    response = adapter.get_current_response()

    assert response.status == "waiting_for_answer"
    assert response.current_step == 1
    assert response.total_steps == 4
    assert response.expected_input_type == "math"
    assert response.metadata["stage"] == (
        "separate_variables"
    )
    assert response.metadata["rhs_expression"] == "2*x*y"
    assert "separate" in response.feedback.lower()


def assert_hint_uses_shared_response():
    adapter = make_adapter()
    response = adapter.request_hint()

    assert response.status == "hint"
    assert response.current_step == 1
    assert response.expected_input_type == "math"
    assert response.completed is False
    assert "divide" in response.feedback.lower()


def assert_incorrect_answer_stays_on_stage():
    adapter = make_adapter()
    response = submit(adapter, "1/y = 3*x")

    assert response.status == "incorrect"
    assert response.current_step == 1
    assert response.expected_input_type == "math"
    assert response.metadata["error_type"] == (
        "incorrect_separation"
    )


def assert_malformed_math_input_is_safe():
    adapter = make_adapter()
    response = submit(
        adapter,
        r"\frac{1}{y",
    )

    assert response.status == "incorrect"
    assert response.current_step == 1
    assert response.expected_input_type == "math"
    assert response.metadata["error_type"] == "parse_error"
    assert response.completed is False


def advance_to_log_stage(adapter):
    response = submit(adapter, "1/y = 2*x")
    assert response.status == "correct"
    assert response.current_step == 2

    response = submit(
        adapter,
        (
            r"\ln\left|y\right|"
            r"=2\cdot x^{^2}/2+C"
        ),
    )
    assert response.status == "correct"
    assert response.current_step == 3
    assert response.metadata["log_stage"] == "apply_exp"
    assert response.metadata["integrated_fx"] == "x**2"
    assert "x**2" in response.metadata["next_prompt"]
    assert "5*x^2/2" not in response.metadata["next_prompt"]
    assert "2*x^3" not in response.metadata["next_prompt"]
    assert "2*x**3" not in response.metadata["next_prompt"]
    assert response.suggestion is not None
    assert "simplify" in response.suggestion


def advance_through_log_answers(
    adapter,
    answers,
):
    for answer in answers:
        response = submit(adapter, answer)
        assert response.status == "correct"
        current = response

    return current


def assert_log_stage_hints_are_specific():
    adapter = make_adapter()
    advance_to_log_stage(adapter)

    submit(adapter, "exp(ln(y)) = exp(x^2 + C)")
    cancel_prompt = adapter.get_current_response()
    assert cancel_prompt.metadata["log_stage"] == (
        "cancel_log"
    )
    assert "Simplify the expression" in (
        cancel_prompt.feedback
    )
    assert "exp(ln|y|)" in cancel_prompt.feedback

    advance_through_log_answers(
        adapter,
        [
            "|y| = exp(x^2 + C)",
            "|y| = exp(x^2)*exp(C)",
        ],
    )

    rename_prompt = adapter.get_current_response()
    assert rename_prompt.metadata["log_stage"] == (
        "rename_exp_constant"
    )

    rename_hint = adapter.request_hint()
    rename_text = rename_hint.feedback.lower()

    assert rename_hint.status == "hint"
    assert "positive constant" in rename_text
    assert "rename" in rename_text
    assert "k" in rename_text
    assert "absolute value" not in rename_text

    submit(adapter, "|y| = K*exp(x^2)")
    remove_prompt = adapter.get_current_response()
    assert remove_prompt.metadata["log_stage"] == (
        "remove_absolute_value"
    )

    remove_hint = adapter.request_hint()
    remove_text = remove_hint.feedback.lower()

    assert remove_hint.status == "hint"
    assert remove_hint.feedback != rename_hint.feedback
    assert "sign" in remove_text
    assert "+/-" in remove_hint.feedback
    assert "absorb" not in remove_text
    assert "arbitrary constant c" not in remove_text
    assert "use exp to undo ln" not in remove_text

    submit(adapter, "y = +/- K*exp(x^2)")
    absorb_prompt = adapter.get_current_response()
    assert absorb_prompt.metadata["log_stage"] == (
        "absorb_constant"
    )
    assert "Combine +/- K" in absorb_prompt.feedback
    assert "into one new arbitrary constant C." in (
        absorb_prompt.feedback
    )


def assert_concept_question_does_not_advance():
    adapter = make_adapter()
    advance_to_log_stage(adapter)

    response = submit(
        adapter,
        "what is the inverse of ln?",
        input_type="text",
    )

    assert response.status == "concept"
    assert response.current_step == 3
    assert response.expected_input_type == "math"
    assert response.metadata["concept_question"] is True
    assert response.metadata["attempts"] == 0


def assert_full_completion():
    adapter = make_adapter()
    advance_to_log_stage(adapter)

    answers = [
        "exp(ln(y)) = exp(x^2 + C)",
        "|y| = exp(x^2 + C)",
        "|y| = exp(x^2)*exp(C)",
        "|y| = K*exp(x^2)",
        "y = +/- K*exp(x^2)",
        "y = C*exp(x^2)",
        "dy/dx = 2*x*C*exp(x^2)",
        "2*x*C*exp(x^2)",
        "yes",
    ]

    response = None

    for answer in answers:
        input_type = (
            "text"
            if answer == "yes"
            else "math"
        )
        response = submit(
            adapter,
            answer,
            input_type=input_type,
        )

        assert response.status in {
            "correct",
            "complete",
        }

    assert response is not None
    assert response.status == "complete"
    assert response.completed is True
    assert response.current_step == 4
    assert response.total_steps == 4


def assert_latex_derivative_reaches_checker():
    adapter = make_adapter()
    advance_to_log_stage(adapter)

    for answer in [
        "exp(ln(y)) = exp(x^2 + C)",
        "|y| = exp(x^2 + C)",
        "|y| = exp(x^2)*exp(C)",
        "|y| = K*exp(x^2)",
        "y = +/- K*exp(x^2)",
        "y = C*exp(x^2)",
    ]:
        submit(adapter, answer)

    response = submit(
        adapter,
        r"\frac{dy}{dx}=2xCe^{x^2}",
    )

    assert response.status == "correct"
    assert response.current_step == 4
    assert response.expected_input_type == "math"


def assert_browser_absolute_value_latex_is_accepted():
    step_3_1_payloads = [
        r"\exp(\ln(|y|))=\exp(x^2+C)",
        (
            r"\exp\left(\ln\left("
            r"\left|y\right|\right)\right)"
            r"=\exp\left(x^2+C\right)"
        ),
        (
            r"\operatorname{exp}\left("
            r"\operatorname{ln}\left("
            r"\left|y\right|\right)\right)"
            r"=\operatorname{exp}\left(x^2+C\right)"
        ),
    ]

    for raw_payload in step_3_1_payloads:
        adapter = make_adapter()
        advance_to_log_stage(adapter)
        normalized = normalize_math_text(
            raw_payload,
            input_type="math",
        )
        checker_result = evaluate_apply_exp_step(
            normalized,
            x**2,
        )

        response = submit(
            adapter,
            raw_payload,
        )
        assert response.status == "correct"
        assert response.metadata["log_stage"] == "cancel_log"

    adapter = make_adapter()
    advance_to_log_stage(adapter)

    response = submit(
        adapter,
        "exp(ln(|y|)) = exp(x^2 + C + )",
    )
    assert response.status == "incorrect"
    assert response.current_step == 3
    assert response.metadata["error_type"] == "parse_error"
    assert "x**2" in response.suggestion
    assert "5*x^2/2" not in response.suggestion
    assert "2*x^3" not in response.suggestion
    assert "2*x**3" not in response.suggestion
    assert "ln|y|" in response.suggestion

    response = submit(
        adapter,
        (
            r"\operatorname{exp}\left("
            r"\operatorname{ln}\left("
            r"\left|y\right|\right)\right)"
            r"=\operatorname{exp}\left(x^2+C\right)"
        ),
    )
    assert response.status == "correct"
    assert response.metadata["log_stage"] == "cancel_log"

    malformed = submit(
        adapter,
        r"\lvert y=e^{x^2+C}",
    )
    assert malformed.status == "incorrect"
    assert malformed.current_step == 3
    assert malformed.metadata["error_type"] == "parse_error"

    response = submit(
        adapter,
        r"\lvert y \rvert=e^{x^2+C}",
    )

    assert response.status == "correct"
    assert response.current_step == 3
    assert response.metadata["log_stage"] == (
        "split_exponential"
    )


def assert_browser_rename_constant_latex_advances():
    adapter = make_adapter()
    advance_to_log_stage(adapter)

    for answer in [
        (
            r"\operatorname{exp}\left("
            r"\operatorname{ln}\left("
            r"\left|y\right|\right)\right)"
            r"=\operatorname{exp}\left(x^2+C\right)"
        ),
        r"|y|=\exp \left(x^{2}+C\right)",
        (
            r"|y|=\exp \left(x^{2}\right)"
            r"\cdot \exp \left(C\right)"
        ),
    ]:
        response = submit(adapter, answer)
        assert response.status == "correct"

    response = submit(
        adapter,
        r"|y|=Ke^{x^{2}}",
    )

    assert response.status == "correct"
    assert response.current_step == 3
    assert response.metadata["log_stage"] == (
        "remove_absolute_value"
    )


def main():
    assert_stage_input_mapping()
    assert_initial_response()
    assert_hint_uses_shared_response()
    assert_incorrect_answer_stays_on_stage()
    assert_malformed_math_input_is_safe()
    assert_concept_question_does_not_advance()
    assert_full_completion()
    assert_latex_derivative_reaches_checker()
    assert_browser_absolute_value_latex_is_accepted()
    assert_browser_rename_constant_latex_advances()
    assert_log_stage_hints_are_specific()

    print("separable_ode_adapter tests passed")


if __name__ == "__main__":
    main()
