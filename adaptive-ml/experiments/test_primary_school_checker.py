from src.core.tutor_engine.primary_school.checker import (
    evaluate_step_answer,
)


tests = [
    ("7", 7),
    ("7.0", 7),
    (" 7 ", 7),
    ("12", 12),
    ("11", 12),
    ("hello", 12),
    ("", 12),
]


for student_answer, expected_answer in tests:
    result = evaluate_step_answer(
        student_answer=student_answer,
        expected_answer=expected_answer,
    )

    print()
    print(
        "Student:",
        repr(student_answer),
    )

    print(
        "Expected:",
        expected_answer,
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