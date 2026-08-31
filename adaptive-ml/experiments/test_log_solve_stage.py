import sympy as sp

from src.core.tutor_engine.concept_guidance.log_solve_stage_checker import (
    evaluate_apply_exp_step,
)

from src.core.tutor_engine.concept_guidance.log_solve_stage_checker import (
    evaluate_apply_exp_step,
    evaluate_cancel_log_step,
    evaluate_split_exponential_step,
    evaluate_rename_exp_constant_step,
    evaluate_remove_absolute_value_step,
    evaluate_absorb_constant_step,
)

x = sp.symbols("x")

integrated_fx = 2 * x**3


answers = [
    "exp(ln(y)) = exp(2*x**3 + C)",
    "exp(log(y)) = exp(2x^3 + C)",
    "ln(y) = exp(2*x**3 + C)",
    "exp(ln(y)) = 2*x**3 + C",
]


for answer in answers:
    result = evaluate_apply_exp_step(
        student_answer=answer,
        integrated_fx=integrated_fx,
    )

    print(
        f"\nAnswer: {answer}"
    )

    print(
        "Correct:",
        result["correct"],
    )

    print(
        "Error type:",
        result["error_type"],
    )

    print(
        "Feedback:",
        result["feedback"],
    )

    print(
        "Suggestion:",
        result["suggestion"],
    )

print("\n--- Cancel ln/exp step ---")

cancel_answers = [
    "|y| = exp(2*x**3 + C)",
    "Abs(y) = exp(2*x**3 + C)",
    "y = exp(2*x**3 + C)",
    "ln(y) = exp(2*x**3 + C)",
    "|y| = 2*x**3 + C",
]

for answer in cancel_answers:
    result = evaluate_cancel_log_step(
        student_answer=answer,
        integrated_fx=integrated_fx,
    )

    print(f"\nAnswer: {answer}")
    print("Correct:", result["correct"])
    print("Error type:", result["error_type"])
    print("Feedback:", result["feedback"])
    print("Suggestion:", result["suggestion"])

print("\n--- Split exponential step ---")

split_answers = [
    "|y| = exp(2*x**3) * exp(C)",
    "|y| = exp(C) * exp(2*x**3)",
    "Abs(y) = exp(2x^3)exp(C)",
    "|y| = exp(2*x**3 + C)",
    "|y| = exp(2*x**3) + exp(C)",
]

for answer in split_answers:
    result = evaluate_split_exponential_step(
        student_answer=answer,
        integrated_fx=integrated_fx,
    )

    print(f"\nAnswer: {answer}")
    print("Correct:", result["correct"])
    print("Error type:", result["error_type"])
    print("Feedback:", result["feedback"])
    print("Suggestion:", result["suggestion"])

print("\n--- Rename exp(C) step ---")

constant_answers = [
    "|y| = K*exp(2*x**3)",
    "|y| = exp(2*x**3)*K",
    "Abs(y) = K exp(2x^3)",
    "|y| = exp(2*x**3)*exp(C)",
    "y = K*exp(2*x**3)",
]

for answer in constant_answers:
    result = evaluate_rename_exp_constant_step(
        student_answer=answer,
        integrated_fx=integrated_fx,
    )

    print(f"\nAnswer: {answer}")
    print("Correct:", result["correct"])
    print("Error type:", result["error_type"])
    print("Feedback:", result["feedback"])
    print("Suggestion:", result["suggestion"])

print("\n--- Remove absolute value step ---")

absolute_answers = [
    "y = +/- K*exp(2*x**3)",
    "y = ±K*exp(2*x**3)",
    "y = +/-K exp(2x^3)",
    "+/- y = K*exp(2*x**3)",
    "±y = K*exp(2*x**3)",
    "y = K*exp(2*x**3)",
    "y = -K*exp(2*x**3)",
    "|y| = K*exp(2*x**3)",
    "y = K*ecp(2*x**3)",
]

for answer in absolute_answers:
    result = evaluate_remove_absolute_value_step(
        student_answer=answer,
        integrated_fx=integrated_fx,
    )

    print(f"\nAnswer: {answer}")
    print("Correct:", result["correct"])
    print("Error type:", result["error_type"])
    print("Feedback:", result["feedback"])
    print("Suggestion:", result["suggestion"])

print("\n--- Absorb constant step ---")

absorb_answers = [
    "y = C*exp(2*x**3)",
    "y = exp(2*x**3)*C",
    "y = C exp(2x^3)",
    "y = exp(2*x**3)",
    "y = C*exp(3*x**3)",
    "y = C*ecp(2*x**3)",
]

for answer in absorb_answers:
    result = evaluate_absorb_constant_step(
        student_answer=answer,
        integrated_fx=integrated_fx,
    )

    print(f"\nAnswer: {answer}")
    print("Correct:", result["correct"])
    print("Error type:", result["error_type"])
    print("Feedback:", result["feedback"])
    print("Suggestion:", result["suggestion"])