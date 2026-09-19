import re
from typing import TYPE_CHECKING, Any

from src.core.i18n.locale import normalize_locale
from src.core.i18n.primary_school import pst

if TYPE_CHECKING:
    from src.core.question_engine.contracts import TutorQuestionContext


_METHOD_PHRASES = (
    "how do i",
    "how can i",
    "how to",
    "how does",
    "how do we",
    "why do",
    "why does",
    "why is",
    "why subtract",
    "why add",
    "why divide",
    "explain",
    "inverse",
    "both sides",
    "unknown addend",
    "unknown factor",
    "unknown minuend",
    "known addend",
    "known subtrahend",
    "known factor",
    "find x",
    "solve this",
    "solve the equation",
    "как да",
    "как се",
    "защо",
    "обясни",
    "обратн",
    "двете страни",
    "неизвестн",
    "намери x",
    "да намеря x",
    "реши уравнен",
    "да реша",
)

_FULL_SOLUTION_PHRASES = (
    "full solution",
    "complete solution",
    "worked solution",
    "show all steps",
    "show the answer",
    "what is the answer",
    "what is x",
    "what's x",
    "solve it completely",
    "solve completely",
    "final answer",
    "цялото решение",
    "пълното решение",
    "покажи отговора",
    "покажи решението",
    "какъв е отговорът",
    "колко е x",
    "колко е неизвестн",
    "реши докрай",
    "пълна проверка",
)

_ADD_EQUATION = re.compile(
    r"x\s*\+\s*(\d+)\s*=\s*(\d+)",
)
_SUB_EQUATION = re.compile(
    r"x\s*-\s*(\d+)\s*=\s*(\d+)",
)
_MUL_EQUATION = re.compile(
    r"(\d+)\s*[×*]\s*x\s*=\s*(\d+)",
)

_FORM_KIND = {
    "x+a=b": "add",
    "x-a=b": "sub",
    "a*x=b": "mul",
}

_DEFINITION_CUES = (
    "what is a ",
    "what is an ",
    "what is the ",
    "what is ",
    "what's a ",
    "what's an ",
    "what's the ",
    "what's ",
    "what does ",
    "what do we call",
    "what do we mean",
    "meaning of ",
    "define ",
    "definition of ",
    "какво е ",
    "какво означава ",
    "какво значи ",
    "какво представлява ",
    "какво наричаме ",
    "що е ",
)

_VOCAB_TERMS = {
    "factor": (
        "factor",
        "factors",
        "множител",
        "множителя",
        "множителят",
        "множители",
    ),
    "product": (
        "product",
        "products",
        "произведение",
        "произведението",
        "произведения",
    ),
    "addend": (
        "addend",
        "addends",
        "събираемо",
        "събираемото",
        "събираеми",
    ),
    "subtrahend": (
        "subtrahend",
        "subtrahends",
        "умалител",
        "умалителя",
        "умалителят",
        "умалители",
    ),
    "minuend": (
        "minuend",
        "minuends",
        "умаляемо",
        "умаляемото",
        "умаляеми",
    ),
}

_TERM_FORMS = {
    "factor": {"mul"},
    "product": {"mul"},
    "addend": {"add"},
    "subtrahend": {"sub"},
    "minuend": {"sub"},
}

_MUL_EXAMPLES = (
    (3, 4, 12),
    (2, 6, 12),
    (5, 4, 20),
    (2, 8, 16),
)
_ADD_EXAMPLES = (
    (2, 5, 7),
    (3, 6, 9),
    (4, 8, 12),
    (1, 9, 10),
)
_SUB_EXAMPLES = (
    (9, 4, 5),
    (8, 3, 5),
    (10, 6, 4),
    (11, 2, 9),
)


def match_unknown_number_explanation(
    question: str,
    context: "TutorQuestionContext",
) -> str | None:
    if context.topic != "unknown_numbers":
        return None

    facts = extract_unknown_number_facts(context)
    if facts is None:
        return None

    folded = _fold_message(question)
    vocab_term = match_vocabulary_term(folded)
    if vocab_term:
        return build_vocabulary_explanation(
            vocab_term,
            facts,
            context.language,
        )

    completed = bool(
        (context.tutor_metadata or {}).get(
            "exercise_completed"
        )
    )
    if _asks_for_worked_solution(folded) or (
        completed and _asks_about_method(folded)
    ):
        return build_unknown_number_explanation(
            facts,
            context.language,
            complete=True,
        )

    if _asks_about_method(folded):
        return build_unknown_number_explanation(
            facts,
            context.language,
            complete=False,
        )
    return None


def extract_unknown_number_facts(
    context: "TutorQuestionContext",
) -> dict[str, Any] | None:
    metadata = context.tutor_metadata or {}
    equation = metadata.get("equation")
    form = metadata.get("form")
    a = metadata.get("a")
    b = metadata.get("b")
    if not isinstance(equation, str) or not equation:
        equation = _equation_from_statement(
            context.problem_statement
        )
    parsed = _parse_equation(equation) if equation else None
    if parsed is not None:
        form = form or parsed["form"]
        a = parsed["a"] if a is None else a
        b = parsed["b"] if b is None else b
        equation = parsed["equation"]
    if form not in _FORM_KIND:
        return None
    if isinstance(a, bool) or isinstance(b, bool):
        return None
    try:
        a_value = int(a)
        b_value = int(b)
    except (TypeError, ValueError):
        return None
    x_value = _solve(form, a_value, b_value)
    if x_value is None:
        return None
    transforms = _verified_transforms(form, a_value, b_value)
    if not _transforms_match(form, a_value, b_value, x_value):
        return None
    return {
        "form": form,
        "kind": _FORM_KIND[form],
        "a": a_value,
        "b": b_value,
        "x": x_value,
        "equation": equation or transforms["equation"],
        **transforms,
    }


def build_unknown_number_explanation(
    facts: dict[str, Any],
    language: str | None,
    *,
    complete: bool,
) -> str:
    locale = normalize_locale(language)
    kind = facts["kind"]
    method = pst(
        locale,
        f"gen.unknown.method.{kind}",
        equation=facts["equation"],
        a=facts["a"],
        b=facts["b"],
        left_undo=facts["left_undo"],
        right_undo=facts["right_undo"],
    )
    if not complete:
        return method
    return pst(
        locale,
        f"gen.unknown.complete.{kind}",
        method=method,
        equation=facts["equation"],
        a=facts["a"],
        b=facts["b"],
        x=facts["x"],
    )


def match_vocabulary_term(question: str) -> str | None:
    message = _fold_message(question)
    if not any(cue in message for cue in _DEFINITION_CUES):
        return None
    found: list[tuple[int, str]] = []
    for term, aliases in _VOCAB_TERMS.items():
        for alias in aliases:
            match = re.search(
                r"(?<!\w)" + re.escape(alias) + r"(?!\w)",
                message,
            )
            if match:
                found.append((match.start(), term))
                break
    if not found:
        return None
    found.sort()
    return found[0][1]


def build_vocabulary_explanation(
    term: str,
    facts: dict[str, Any],
    language: str | None,
) -> str:
    locale = normalize_locale(language)
    example = _example_for_term(term, facts)
    parts = [
        pst(
            locale,
            f"gen.unknown.vocab.{term}.define",
            **example,
        )
    ]
    if facts["kind"] in _TERM_FORMS.get(term, set()):
        parts.append(
            pst(
                locale,
                f"gen.unknown.vocab.{term}.here",
                equation=facts["equation"],
                a=facts["a"],
                b=facts["b"],
            )
        )
    else:
        parts.append(
            pst(
                locale,
                f"gen.unknown.vocab.{term}.other",
                equation=facts["equation"],
            )
        )
    return "\n\n".join(parts)


def _example_for_term(
    term: str,
    facts: dict[str, Any],
) -> dict[str, int]:
    forbidden = {facts["a"], facts["b"], facts["x"]}
    if term in {"factor", "product"}:
        candidates = _MUL_EXAMPLES
    elif term == "addend":
        candidates = _ADD_EXAMPLES
    else:
        candidates = _SUB_EXAMPLES
    for left, right, result in candidates:
        if {left, right, result}.isdisjoint(forbidden):
            return {
                "ex_left": left,
                "ex_right": right,
                "ex_result": result,
            }
    left, right, result = candidates[0]
    return {
        "ex_left": left,
        "ex_right": right,
        "ex_result": result,
    }


def _fold_message(question: str) -> str:
    text = question.strip().lower()
    for mark in (",", ".", "!", "?", ";", ":", "„", "“", "”"):
        text = text.replace(mark, " ")
    return " ".join(text.split())


def _asks_about_method(message: str) -> bool:
    return any(phrase in message for phrase in _METHOD_PHRASES)


def _asks_for_worked_solution(message: str) -> bool:
    return any(
        phrase in message for phrase in _FULL_SOLUTION_PHRASES
    )


def _equation_from_statement(statement: str) -> str:
    for pattern in (_ADD_EQUATION, _SUB_EQUATION, _MUL_EQUATION):
        match = pattern.search(statement or "")
        if match:
            return match.group(0)
    return ""


def _parse_equation(equation: str) -> dict | None:
    text = " ".join((equation or "").split())
    add = _ADD_EQUATION.search(text)
    if add:
        return {
            "form": "x+a=b",
            "a": int(add.group(1)),
            "b": int(add.group(2)),
            "equation": f"x + {add.group(1)} = {add.group(2)}",
        }
    sub = _SUB_EQUATION.search(text)
    if sub:
        return {
            "form": "x-a=b",
            "a": int(sub.group(1)),
            "b": int(sub.group(2)),
            "equation": f"x - {sub.group(1)} = {sub.group(2)}",
        }
    mul = _MUL_EQUATION.search(text)
    if mul:
        return {
            "form": "a*x=b",
            "a": int(mul.group(1)),
            "b": int(mul.group(2)),
            "equation": f"{mul.group(1)} × x = {mul.group(2)}",
        }
    return None


def _solve(form: str, a: int, b: int) -> int | None:
    if a == 0:
        return None
    if form == "x+a=b":
        return b - a
    if form == "x-a=b":
        return b + a
    if form == "a*x=b":
        if b % a != 0:
            return None
        return b // a
    return None


def _verified_transforms(form: str, a: int, b: int) -> dict:
    if form == "x+a=b":
        return {
            "equation": f"x + {a} = {b}",
            "left_undo": f"x + {a} - {a}",
            "right_undo": f"{b} - {a}",
        }
    if form == "x-a=b":
        return {
            "equation": f"x - {a} = {b}",
            "left_undo": f"x - {a} + {a}",
            "right_undo": f"{b} + {a}",
        }
    return {
        "equation": f"{a} × x = {b}",
        "left_undo": f"({a} × x) ÷ {a}",
        "right_undo": f"{b} ÷ {a}",
    }


def _transforms_match(
    form: str,
    a: int,
    b: int,
    x: int,
) -> bool:
    if form == "x+a=b":
        return x + a == b and (b - a) == x
    if form == "x-a=b":
        return x - a == b and (b + a) == x
    if form == "a*x=b":
        return a * x == b and b % a == 0 and (b // a) == x
    return False
