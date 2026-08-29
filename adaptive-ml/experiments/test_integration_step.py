from src.core.tutor_engine.concept_guidance.separable_stage_checker import (
    evaluate_integration_step,
)


rhs = "5*x*y"

answers = [
    "ln(y) = 5*x^2/2 + C",
    "log(y) = 5*x**2/2 + C",
    "ln(y) = 5*x^2/2",
    "y = 5*x^2/2 + C",
    "ln(y) = 5*x + C",
]


for answer in answers:
    result = evaluate_integration_step(
        student_answer=answer,
        rhs_expression=rhs,
    )

    print(f"\nAnswer: {answer}")
    print("Correct:", result["correct"])
    print("Error type:", result["error_type"])
    print("Feedback:", result["feedback"])