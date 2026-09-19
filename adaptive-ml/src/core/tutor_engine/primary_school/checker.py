from src.core.i18n.locale import normalize_locale
from src.core.i18n.primary_school import pst
from src.core.tutor_engine.primary_school.problem_types import (
    AnswerFormat,
)


MAX_INTEGER_ANSWER_LENGTH = 24
_NON_FINITE = {
    "nan",
    "inf",
    "+inf",
    "-inf",
    "infinity",
    "+infinity",
    "-infinity",
}


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


def parse_exact_integer(student_answer: str):
    """
    Parse a whole-number answer without rounding.

    Returns (value, error_type). error_type is None
    when parsing succeeds.
    """

    if not isinstance(student_answer, str):
        return None, "not_numeric"

    text = student_answer.strip()
    if not text:
        return None, "empty_answer"
    if len(text) > MAX_INTEGER_ANSWER_LENGTH:
        return None, "not_numeric"

    lowered = text.lower()
    if lowered in _NON_FINITE:
        return None, "not_numeric"

    sign = 1
    if text[0] in "+-":
        if text[0] == "-":
            sign = -1
        text = text[1:]
        if not text:
            return None, "not_numeric"

    text = text.replace(",", ".")
    if "e" in text.lower() or " " in text:
        return None, "not_numeric"
    if text.count(".") > 1:
        return None, "not_numeric"

    if "." in text:
        whole, frac = text.split(".", 1)
        if not whole.isdigit() or not frac.isdigit():
            return None, "not_numeric"
        if any(digit != "0" for digit in frac):
            return None, "not_integer"
        return sign * int(whole), None

    if not text.isdigit():
        return None, "not_numeric"
    return sign * int(text), None


def evaluate_integer_answer(
    student_answer: str,
    expected_answer,
    language: str | None = None,
) -> dict:
    locale = normalize_locale(language)
    value, error_type = parse_exact_integer(
        student_answer
    )
    if error_type is not None:
        return {
            "correct": False,
            "error_type": error_type,
            "feedback": pst(locale, error_type),
        }

    try:
        expected_value = int(expected_answer)
    except (TypeError, ValueError):
        return {
            "correct": False,
            "error_type": "invalid_expected_answer",
            "feedback": pst(locale, "invalid_expected"),
        }

    if isinstance(expected_answer, bool):
        return {
            "correct": False,
            "error_type": "invalid_expected_answer",
            "feedback": pst(locale, "invalid_expected"),
        }

    if isinstance(expected_answer, float):
        if expected_answer != expected_value:
            return {
                "correct": False,
                "error_type": "invalid_expected_answer",
                "feedback": pst(locale, "invalid_expected"),
            }

    if value == expected_value:
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


def evaluate_step_answer(
    student_answer: str,
    expected_answer,
    language: str | None = None,
    answer_format: str | None = None,
) -> dict:
    """
    Check a student's answer for one solution step.
    """

    format_value = _format_name(answer_format)
    if format_value == AnswerFormat.INTEGER.value:
        return evaluate_integer_answer(
            student_answer,
            expected_answer,
            language=language,
        )

    return _evaluate_legacy_numeric(
        student_answer,
        expected_answer,
        language=language,
    )


def _format_name(answer_format) -> str | None:
    if answer_format is None:
        return None
    if isinstance(answer_format, AnswerFormat):
        return answer_format.value
    return str(answer_format)


def _evaluate_legacy_numeric(
    student_answer: str,
    expected_answer,
    language: str | None = None,
) -> dict:
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
