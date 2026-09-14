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


from src.core.i18n.locale import normalize_locale
from src.core.i18n.primary_school import pst


def evaluate_step_answer(
    student_answer: str,
    expected_answer,
    language: str | None = None,
) -> dict:
    """
    Check a student's answer for one solution step.

    For the first prototype, expected answers are
    simple integers or numeric values.
    """

    locale = normalize_locale(language)
    answer_text = normalize_student_answer(
        student_answer
    )

    if not answer_text:
        return {
            "correct": False,
            "error_type": "empty_answer",
            "feedback": pst(locale, "empty_answer"),
        }

    try:
        student_value = float(
            answer_text
        )

    except ValueError:
        return {
            "correct": False,
            "error_type": "not_numeric",
            "feedback": pst(locale, "not_numeric"),
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
            "feedback": pst(locale, "invalid_expected"),
        }

    if student_value == expected_value:
        return {
            "correct": True,
            "error_type": None,
            "feedback": pst(locale, "correct"),
        }

    return {
        "correct": False,
        "error_type": "incorrect_answer",
            "feedback": pst(locale, "incorrect"),
    }