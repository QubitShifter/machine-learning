from dataclasses import dataclass

from src.core.i18n.guided_questions import gst
from src.core.i18n.locale import normalize_locale
from src.core.tutor_engine.concept_guidance.logical_reasoning_guidance import (
    build_logical_guidance_context,
    explain_logical_check,
    explain_logical_eliminate,
    explain_logical_first_clue,
    explain_logical_known,
    explain_logical_unknown,
)
from src.core.tutor_engine.concept_guidance.unknown_number_guidance import (
    build_unknown_number_explanation,
    build_vocabulary_explanation,
    extract_unknown_number_facts,
)
from src.core.tutor_engine.concept_guidance.story_step_guidance import (
    explain_story_asked,
    explain_story_given,
    explain_story_phrase,
    explain_story_step,
    build_story_guidance_context,
)
from src.core.tutor_engine.primary_school.generation.word_problems.templates import (
    TEMPLATES_BY_ID,
)
class GuidedQuestionError(ValueError):
    """Raised when a guided question_id is invalid for this step."""


CATEGORY_DEFINITION = "definition"
CATEGORY_UNDERSTAND = "understand_step"
CATEGORY_METHOD = "explain_method"

DISCLOSURE_DEFINITION = "definition"
DISCLOSURE_UNDERSTAND = "understand_step"
DISCLOSURE_METHOD = "explain_method"

_STORY_PHRASES = {
    "story.phrase.more_than": "more_than",
    "story.phrase.fewer": "fewer",
    "story.phrase.twice_as_many": "twice_as_many",
    "story.phrase.times_as_many": "times_as_many",
    "story.phrase.doubled": "doubled",
    "story.phrase.remaining": "remaining",
    "story.phrase.in_all": "in_all",
}

_TEMPLATE_PHRASES = {
    "cards_total": ("story.phrase.in_all",),
    "stamps_then_stickers": ("story.phrase.times_as_many",),
    "boxes_then_stickers": ("story.phrase.times_as_many",),
    "more_than": ("story.phrase.more_than",),
    "fewer_than": ("story.phrase.fewer",),
    "twice_as_many": ("story.phrase.twice_as_many",),
    "more_then_together": (
        "story.phrase.more_than",
        "story.phrase.in_all",
    ),
    "books_from_class": (
        "story.phrase.more_than",
        "story.phrase.twice_as_many",
    ),
    "remaining_after_taken": ("story.phrase.remaining",),
    "removed_then_doubled": (
        "story.phrase.remaining",
        "story.phrase.doubled",
    ),
    "removed_doubled_then_added": (
        "story.phrase.remaining",
        "story.phrase.doubled",
    ),
}

_MAX_SUGGESTIONS = 4


@dataclass(frozen=True)
class SuggestedQuestion:
    question_id: str
    label: str
    category: str


def list_suggested_questions(
    *,
    topic: str,
    problem,
    live_response,
    language: str,
    completed: bool,
) -> list[SuggestedQuestion]:
    if completed:
        return []
    locale = normalize_locale(language)
    ids = _select_ids(topic, problem, live_response)
    items = []
    for question_id in ids[:_MAX_SUGGESTIONS]:
        items.append(
            SuggestedQuestion(
                question_id=question_id,
                label=gst(locale, _label_key(question_id, problem)),
                category=_category(question_id),
            )
        )
    return items


def resolve_guided_question(
    question_id: str,
    *,
    allowed_ids: set[str],
    topic: str,
    problem,
    live_response,
    context,
    language: str,
) -> tuple[str, str]:
    if not question_id or question_id not in allowed_ids:
        raise GuidedQuestionError(
            "This suggested question is not available "
            "for the current step."
        )
    if _disclosure(question_id) == "complete":
        raise GuidedQuestionError(
            "Complete solutions are not available as "
            "suggested questions."
        )
    locale = normalize_locale(language)
    label = gst(locale, _label_key(question_id, problem))
    answer = _explain(
        question_id,
        topic=topic,
        problem=problem,
        live_response=live_response,
        context=context,
        language=locale,
    )
    if not answer:
        raise GuidedQuestionError(
            "This suggested question is not available "
            "for the current step."
        )
    return label, answer


def suggested_as_dicts(
    items: list[SuggestedQuestion],
) -> list[dict[str, str]]:
    return [
        {
            "question_id": item.question_id,
            "label": item.label,
            "category": item.category,
        }
        for item in items
    ]


def _select_ids(topic: str, problem, live_response) -> list[str]:
    if topic == "unknown_numbers":
        return _unknown_ids(problem)
    if topic == "story_problems":
        return _story_ids(problem, live_response)
    if topic == "arithmetic":
        return _arithmetic_ids(problem)
    if topic == "number_patterns":
        return _pattern_ids(problem)
    if topic == "logical_reasoning":
        return _logical_ids(problem)
    return []


def _unknown_ids(problem) -> list[str]:
    known = getattr(problem, "known", None) or {}
    form = known.get("form")
    if form == "x+a=b":
        return [
            "unknown.addend.identify_known",
            "unknown.addend.definition",
            "unknown.addend.unknown",
            "unknown.addend.find_unknown",
        ]
    if form == "x-a=b":
        return [
            "unknown.subtrahend.identify_known",
            "unknown.subtrahend.definition",
            "unknown.minuend.definition",
            "unknown.minuend.find_unknown",
        ]
    if form == "a*x=b":
        return [
            "unknown.factor.identify_known",
            "unknown.factor.definition",
            "unknown.product.definition",
            "unknown.factor.find_unknown",
        ]
    return []


def _story_ids(problem, live_response) -> list[str]:
    known = getattr(problem, "known", None) or {}
    template_id = known.get("template_id")
    template = TEMPLATES_BY_ID.get(template_id)
    if template is None:
        return []
    quantity = _current_quantity(problem, live_response)
    phrase = _story_phrase_for_step(template_id, quantity)
    ids = ["story.step.how_to_start"]
    if phrase:
        ids.append(phrase)
    ids.extend(
        (
            "story.known.what_is_given",
            "story.unknown.what_to_find",
        )
    )
    return ids


def _story_phrase_for_step(
    template_id: str,
    quantity: str,
) -> str | None:
    phrases = _TEMPLATE_PHRASES.get(template_id, ())
    if not phrases:
        return None
    if quantity in {"nina", "boys", "extra"}:
        for phrase in phrases:
            if phrase.endswith("more_than"):
                return phrase
    if quantity in {"leo"} and template_id == "fewer_than":
        return "story.phrase.fewer"
    if quantity in {"nina", "books"}:
        for phrase in phrases:
            if phrase.endswith("twice_as_many"):
                return phrase
    if quantity in {"stickers", "stamps_now", "boxed"}:
        for phrase in phrases:
            if phrase.endswith("times_as_many"):
                return phrase
    if quantity in {"total"}:
        for phrase in phrases:
            if phrase.endswith("in_all"):
                return phrase
    if quantity in {"remaining", "start", "final", "doubled"}:
        if quantity == "doubled" or quantity == "final":
            for phrase in phrases:
                if phrase.endswith("doubled"):
                    return phrase
        for phrase in phrases:
            if phrase.endswith("remaining"):
                return phrase
    return phrases[0]


def _arithmetic_ids(problem) -> list[str]:
    known = getattr(problem, "known", None) or {}
    shape = known.get("shape")
    if shape == "simple_binary":
        return ["arith.left_to_right"]
    if shape == "order_of_operations":
        return ["arith.order.first"]
    if shape == "parentheses":
        return [
            "arith.parentheses.definition",
            "arith.order.first",
            "arith.parentheses.why",
        ]
    return []


def _pattern_ids(problem) -> list[str]:
    known = getattr(problem, "known", None) or {}
    if known.get("variant") == "sequence":
        return [
            "pattern.sequence.what",
            "pattern.sequence.rule",
        ]
    if known.get("variant") == "chain":
        ids = ["pattern.chain.what"]
        if known.get("direction") == "reverse":
            ids.append("pattern.chain.undo")
        else:
            ids.append("pattern.chain.follow")
        return ids
    return []


def _logical_ids(problem) -> list[str]:
    known = getattr(problem, "known", None) or {}
    family = known.get("family")
    ids = ["logic.known", "logic.unknown"]
    if family == "distribution_puzzles":
        ids.extend(["logic.first_clue", "logic.check"])
        return ids
    if family == "number_detective":
        ids.extend(["logic.first_clue", "logic.eliminate"])
        return ids
    if family == "logic_detective":
        ids.extend(["logic.eliminate", "logic.check"])
        return ids
    ids.append("logic.check")
    return ids


def _explain(
    question_id: str,
    *,
    topic: str,
    problem,
    live_response,
    context,
    language: str,
) -> str | None:
    if question_id.startswith("unknown."):
        return _explain_unknown(question_id, context, language)
    if question_id.startswith("story."):
        return _explain_story(
            question_id,
            problem,
            live_response,
            context,
            language,
        )
    if question_id.startswith("arith."):
        return _explain_arithmetic(question_id, problem, language)
    if question_id.startswith("pattern."):
        return gst(language, _explain_key(question_id))
    if question_id.startswith("logic."):
        return _explain_logical(
            question_id,
            problem,
            live_response,
            language,
        )
    return None


def _explain_arithmetic(
    question_id: str,
    problem,
    language: str,
) -> str:
    known = getattr(problem, "known", None) or {}
    if question_id == "arith.order.first":
        if known.get("shape") == "parentheses":
            return gst(
                language,
                "guided.arith.explain.parentheses_first",
            )
        return gst(
            language,
            "guided.arith.explain.multiply_first",
        )
    return gst(language, _explain_key(question_id))


def _explain_unknown(question_id: str, context, language: str) -> str | None:
    facts = extract_unknown_number_facts(context)
    if facts is None:
        return None
    if question_id.endswith(".definition"):
        term = question_id.split(".")[1]
        if term == "subtrahend":
            term = "subtrahend"
        return build_vocabulary_explanation(
            term,
            facts,
            language,
        )
    if question_id.endswith(".identify_known"):
        kind = facts["kind"]
        return gst(
            language,
            f"guided.unknown.explain.identify.{kind}",
            equation=facts["equation"],
        )
    if question_id == "unknown.addend.unknown":
        return gst(language, "guided.unknown.explain.unknown_addend")
    if question_id.endswith(".find_unknown"):
        return build_unknown_number_explanation(
            facts,
            language,
            complete=False,
        )
    return None


def _explain_story(
    question_id: str,
    problem,
    live_response,
    context,
    language: str,
) -> str | None:
    story = build_story_guidance_context(
        problem,
        live_response,
        language,
    )
    if story is None:
        return None
    if question_id in _STORY_PHRASES:
        return explain_story_phrase(
            _STORY_PHRASES[question_id],
            story,
        )
    if question_id == "story.known.what_is_given":
        return explain_story_given(story)
    if question_id == "story.unknown.what_to_find":
        return explain_story_asked(story)
    if question_id == "story.step.how_to_start":
        return explain_story_step(story)
    return None


def _explain_logical(
    question_id: str,
    problem,
    live_response,
    language: str,
) -> str | None:
    ctx = build_logical_guidance_context(
        problem,
        live_response,
        language,
    )
    if ctx is None:
        return None
    if question_id == "logic.known":
        return explain_logical_known(ctx)
    if question_id == "logic.unknown":
        return explain_logical_unknown(ctx)
    if question_id == "logic.first_clue":
        return explain_logical_first_clue(ctx)
    if question_id == "logic.eliminate":
        if ctx.family == "distribution_puzzles":
            return None
        return explain_logical_eliminate(ctx)
    if question_id == "logic.check":
        return explain_logical_check(ctx)
    return None


def _current_step(problem, live_response):
    if problem is None:
        return None
    getter = getattr(problem, "get_step", None)
    if getter is None:
        return None
    return getter(live_response.current_step)


def _current_quantity(problem, live_response) -> str:
    step = _current_step(problem, live_response)
    if step is None:
        return ""
    key = (step.metadata or {}).get("prompt_key") or ""
    if "." not in key:
        return ""
    return str(key).rsplit(".", 1)[-1]


def _label_key(question_id: str, problem=None) -> str:
    base = {
        "unknown.addend.definition": (
            "guided.unknown.addend.definition"
        ),
        "unknown.addend.identify_known": (
            "guided.unknown.addend.identify_known"
        ),
        "unknown.addend.unknown": "guided.unknown.addend.unknown",
        "unknown.addend.find_unknown": (
            "guided.unknown.addend.find_unknown"
        ),
        "unknown.minuend.definition": (
            "guided.unknown.minuend.definition"
        ),
        "unknown.subtrahend.definition": (
            "guided.unknown.subtrahend.definition"
        ),
        "unknown.subtrahend.identify_known": (
            "guided.unknown.subtrahend.identify_known"
        ),
        "unknown.minuend.find_unknown": (
            "guided.unknown.minuend.find_unknown"
        ),
        "unknown.factor.definition": (
            "guided.unknown.factor.definition"
        ),
        "unknown.product.definition": (
            "guided.unknown.product.definition"
        ),
        "unknown.factor.identify_known": (
            "guided.unknown.factor.identify_known"
        ),
        "unknown.factor.find_unknown": (
            "guided.unknown.factor.find_unknown"
        ),
        "arith.parentheses.definition": (
            "guided.arith.parentheses.definition"
        ),
        "arith.order.first": "guided.arith.order.first",
        "arith.parentheses.why": "guided.arith.parentheses.why",
        "arith.left_to_right": "guided.arith.left_to_right",
        "arith.multiply_first": "guided.arith.order.first",
        "pattern.sequence.what": "guided.pattern.sequence.what",
        "pattern.sequence.rule": "guided.pattern.sequence.rule",
        "pattern.chain.what": "guided.pattern.chain.what",
        "pattern.chain.follow": "guided.pattern.chain.follow",
        "pattern.chain.undo": "guided.pattern.chain.undo",
        "story.known.what_is_given": "guided.story.known",
        "story.unknown.what_to_find": "guided.story.unknown",
        "story.step.how_to_start": "guided.story.how_to_start",
        "story.phrase.more_than": "guided.story.phrase.more_than",
        "story.phrase.fewer": "guided.story.phrase.fewer",
        "story.phrase.twice_as_many": (
            "guided.story.phrase.twice_as_many"
        ),
        "story.phrase.times_as_many": (
            "guided.story.phrase.times_as_many"
        ),
        "story.phrase.doubled": "guided.story.phrase.doubled",
        "story.phrase.remaining": "guided.story.phrase.remaining",
        "story.phrase.in_all": "guided.story.phrase.in_all",
        "logic.known": "guided.logic.known",
        "logic.unknown": "guided.logic.unknown",
        "logic.first_clue": "guided.logic.first_clue",
        "logic.eliminate": "guided.logic.eliminate",
        "logic.check": "guided.logic.check",
    }.get(question_id, question_id)
    if question_id != "logic.first_clue":
        return base
    known = getattr(problem, "known", None) or {}
    if known.get("family") == "distribution_puzzles":
        return "guided.logic.first_clue.distribution"
    return base


def _explain_key(question_id: str) -> str:
    return {
        "arith.parentheses.definition": (
            "guided.arith.explain.parentheses"
        ),
        "arith.order.first": "guided.arith.explain.multiply_first",
        "arith.multiply_first": "guided.arith.explain.multiply_first",
        "arith.parentheses.why": "guided.arith.explain.why_parentheses",
        "arith.left_to_right": "guided.arith.explain.left_to_right",
        "pattern.sequence.what": "guided.pattern.explain.sequence",
        "pattern.sequence.rule": "guided.pattern.explain.rule",
        "pattern.chain.what": "guided.pattern.explain.chain",
        "pattern.chain.follow": "guided.pattern.explain.follow",
        "pattern.chain.undo": "guided.pattern.explain.undo",
    }.get(question_id, question_id)


def _category(question_id: str) -> str:
    if question_id.endswith(".definition") or question_id.startswith(
        "story.phrase."
    ):
        return CATEGORY_DEFINITION
    if question_id.endswith(".find_unknown") or question_id in {
        "arith.order.first",
        "arith.multiply_first",
        "pattern.sequence.rule",
        "pattern.chain.follow",
        "pattern.chain.undo",
    }:
        return CATEGORY_METHOD
    if question_id.endswith(".identify_known") or question_id in {
        "story.step.how_to_start",
        "unknown.addend.unknown",
        "story.known.what_is_given",
        "story.unknown.what_to_find",
        "arith.left_to_right",
        "arith.parentheses.why",
        "pattern.sequence.what",
        "pattern.chain.what",
        "logic.known",
        "logic.unknown",
        "logic.first_clue",
        "logic.eliminate",
        "logic.check",
    }:
        return CATEGORY_UNDERSTAND
    return CATEGORY_DEFINITION


def _disclosure(question_id: str) -> str:
    if "complete" in question_id.split("."):
        return "complete"
    if question_id.endswith(".find_unknown"):
        return DISCLOSURE_METHOD
    if question_id.endswith(".definition") or question_id.startswith(
        "story.phrase."
    ):
        return DISCLOSURE_DEFINITION
    return DISCLOSURE_UNDERSTAND
