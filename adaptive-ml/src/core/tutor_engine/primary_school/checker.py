def normalize_student_answer(
    student_answer: str,
) -> str:
    """
    Normalize simple primary-school answers.

    This first version focuses on numeric answers.
    """

    return (
        student_answer
        .strip()
        .replace(",", ".")
    )


def evaluate_step_answer(
    student_answer: str,
    expected_answer,
) -> dict:
    """
    Check a student's answer for one solution step.

    For the first prototype, expected answers are
    simple integers or numeric values.
    """

    answer_text = normalize_student_answer(
        student_answer
    )

    if not answer_text:
        return {
            "correct": False,
            "error_type": "empty_answer",
            "feedback": (
                "Please enter an answer."
            ),
        }

    try:
        student_value = float(
            answer_text
        )

    except ValueError:
        return {
            "correct": False,
            "error_type": "not_numeric",
            "feedback": (
                "I could not understand that as a number."
            ),
        }

    try:
        expected_value = float(
            expected_answer
        )

    except (
        TypeError,
        ValueError,
    ):
        return {
            "correct": False,
            "error_type": "invalid_expected_answer",
            "feedback": (
                "The tutor could not validate this step."
            ),
        }

    if student_value == expected_value:
        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct."
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_answer",
        "feedback": (
            "That is not the correct answer yet."
        ),
    }