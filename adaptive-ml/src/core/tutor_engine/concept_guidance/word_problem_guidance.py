import re
from typing import TYPE_CHECKING

from src.core.i18n.locale import normalize_locale
from src.core.i18n.primary_school import pst

if TYPE_CHECKING:
    from src.core.question_engine.contracts import TutorQuestionContext


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

_PHRASES = (
    (
        "twice_as_many",
        (
            "twice as many",
            "two times as many",
            "twice",
            "два пъти толкова",
            "два пъти",
        ),
    ),
    (
        "times_as_many",
        (
            "times as many",
            "пъти толкова",
        ),
    ),
    (
        "doubled",
        (
            "was doubled",
            "doubled",
            "doubling",
            "удвоен",
            "удвоени",
            "удвои",
        ),
    ),
    (
        "remaining",
        (
            "remaining",
            "останали",
            "останало",
            "останалите",
        ),
    ),
    (
        "fewer",
        (
            "fewer than",
            "less than",
            "fewer",
            "по-малко",
        ),
    ),
    (
        "more_than",
        (
            "more than",
            "повече",
        ),
    ),
    (
        "in_all",
        (
            "in all",
            "together",
            "общо",
            "заедно",
        ),
    ),
)

_EXAMPLES = {
    "twice_as_many": {"ex_left": 5, "ex_result": 10},
    "more_than": {"ex_left": 6, "ex_extra": 3, "ex_result": 9},
    "fewer": {"ex_left": 9, "ex_extra": 4, "ex_result": 5},
    "times_as_many": {
        "ex_left": 4,
        "ex_times": 3,
        "ex_result": 12,
    },
}

_METHOD_CUES = (
    "how do i",
    "how can i",
    "how to",
    "how do we",
    "how should",
    "what action",
    "what operation",
    "which operation",
    "what do i use",
    "find the answer",
    "solve this",
    "solve the problem",
    "solve the step",
    "this step",
    "current step",
    "how do i solve",
    "как да",
    "как се",
    "какво действие",
    "коя операция",
    "каква операция",
    "на тази стъпка",
    "тази стъпка",
    "тази задача",
    "да намеря отговора",
    "да реша",
)


def match_word_problem_explanation(
    question: str,
    context: "TutorQuestionContext",
) -> str | None:
    if context.topic != "story_problems":
        return None

    folded = _fold_message(question)
    phrase = match_story_phrase(folded)
    if phrase:
        return build_story_phrase_explanation(
            phrase,
            context,
        )
    if not match_story_method_intent(folded):
        return None
    from src.core.tutor_engine.concept_guidance.story_step_guidance import (
        build_story_guidance_from_question_context,
        explain_story_method,
        story_method_fallback,
    )

    story = build_story_guidance_from_question_context(context)
    if story is None:
        return story_method_fallback(context.language)
    return explain_story_method(story)


def match_story_method_intent(question: str) -> bool:
    message = _fold_message(question)
    return any(cue in message for cue in _METHOD_CUES)


def match_story_phrase(question: str) -> str | None:
    message = _fold_message(question)
    if not any(cue in message for cue in _DEFINITION_CUES):
        return None
    found: list[tuple[int, str]] = []
    for term, aliases in _PHRASES:
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


def build_story_phrase_explanation(
    phrase: str,
    context: "TutorQuestionContext",
) -> str:
    locale = normalize_locale(context.language)
    params = dict(_EXAMPLES.get(phrase) or {})
    forbidden = _visible_numbers(context)
    if forbidden.intersection(params.values()):
        params = _shifted_example(phrase, forbidden)
    return pst(
        locale,
        f"gen.story.vocab.{phrase}",
        **params,
    )


def _visible_numbers(
    context: "TutorQuestionContext",
) -> set[int]:
    found: set[int] = set()
    statement = context.problem_statement or ""
    for match in re.findall(r"\d+", statement):
        found.add(int(match))
    return found


def _shifted_example(
    phrase: str,
    forbidden: set[int],
) -> dict[str, int]:
    base = dict(_EXAMPLES.get(phrase) or {})
    if not base:
        return {}
    for shift in range(1, 8):
        candidate = {
            key: value + shift
            for key, value in base.items()
        }
        if phrase == "twice_as_many":
            candidate["ex_result"] = candidate["ex_left"] * 2
        elif phrase == "more_than":
            candidate["ex_result"] = (
                candidate["ex_left"] + candidate["ex_extra"]
            )
        elif phrase == "fewer":
            if candidate["ex_left"] <= candidate["ex_extra"]:
                continue
            candidate["ex_result"] = (
                candidate["ex_left"] - candidate["ex_extra"]
            )
        elif phrase == "times_as_many":
            candidate["ex_result"] = (
                candidate["ex_left"] * candidate["ex_times"]
            )
        if set(candidate.values()).isdisjoint(forbidden):
            return candidate
    return base


def _fold_message(question: str) -> str:
    text = question.strip().lower()
    for mark in (",", ".", "!", "?", ";", ":", "„", "“", "”", '"', "'"):
        text = text.replace(mark, " ")
    return " ".join(text.split())
