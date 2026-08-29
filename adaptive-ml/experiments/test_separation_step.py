from src.core.tutor_engine.concept_guidance.separable_stage_checker import (
    evaluate_separation_step,
)


rhs = "5*x*y"

answers = [
    "1/y = 5*x",
    "5x = 1/y",
    "1/y = 5x",
    "y = 5*x",
    "1/x = 5*y",
    "dx/5x = y",
]


for answer in answers:
    result = evaluate_separation_step(
        student_answer=answer,
        rhs_expression=rhs,
    )

    print(f"\nAnswer: {answer}")
    print("Correct:", result["correct"])
    print("Feedback:", result["feedback"])