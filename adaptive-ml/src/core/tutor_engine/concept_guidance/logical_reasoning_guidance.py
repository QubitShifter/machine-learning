from dataclasses import dataclass
import re

from src.core.i18n.locale import normalize_locale
from src.core.i18n.logical_reasoning import lrt
from src.core.tutor_engine.primary_school.generation.logical_reasoning.compile import (
    discloses_protected,
    protected_answers_from,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    FAMILY_DISTRIBUTION,
)


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
    "which clue",
    "what clue",
    "eliminate",
    "wrong options",
    "impossible",
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
    "коя улика",
    "коя улика да използвам",
    "кое условие",
    "как да изключа",
    "грешните възможности",
    "невъзможните",
)

_HOW_METHOD_RE = re.compile(
    r"(?:how(?:\s+\w{1,16}){0,2}\s+(?:do i|do we|can i|to|should))"
    r"|(?:\bкак(?:\s+\w{1,16}){0,2}\s+(?:да|се)\b)"
)


_FORMAT_ACTION_CUES = (
    "enter",
    "type",
    "input",
    "write",
    "въвед",
    "напиша",
    "напишеш",
    "напишете",
)

_FORMAT_SHAPE_CUES = (
    "comma",
    "запетая",
    "separated",
    "разделени",
    "two boxes",
    "two box",
    "две кутии",
    "two numbers",
    "две числа",
    "two answers",
    "двата отговора",
    "два отговора",
    "both answers",
    "both numbers",
    "both values",
    "both quantities",
    "both boxes",
    "together",
    "заедно",
    "one number",
    "едно число",
    "how many numbers",
    "колко числа",
    "one value",
    "two values",
)


_TERM_WORDS = (
    "scaled",
    "multiplied",
    "multiply",
    "умножен",
    "умножение",
)

_TERM_ASK = (
    "what does",
    "what is",
    "what's",
    "which box",
    "meaning of",
    "define ",
    "какво означава",
    "какво значи",
    "коя кутия",
)


@dataclass(frozen=True)
class LogicalGuidanceContext:
    family: str
    language: str
    milestone: str
    purpose: str
    params: dict
    clue_kinds: tuple[str, ...]
    visible_numbers: frozenset[int]
    protected: frozenset[int]
    current_step: int
    public_clues: tuple = ()
    current_prompt: str = ""


def build_logical_guidance_context(
    problem,
    live_response,
    language: str | None = None,
) -> LogicalGuidanceContext | None:
    if getattr(problem, "topic", "") != "logical_reasoning":
        return None
    known = getattr(problem, "known", None) or {}
    step_number = getattr(live_response, "current_step", None)
    step = None
    getter = getattr(problem, "get_step", None)
    if getter is not None and step_number is not None:
        step = getter(step_number)
    if step is None:
        return None
    meta = step.metadata or {}
    params = dict(meta.get("params") or {})
    locale = normalize_locale(language or getattr(problem, "language", "en"))
    public_clues = tuple(known.get("public_clues") or ())
    _merge_public_relations(params, public_clues, locale)
    _fill_names(params, locale)
    visible = frozenset(
        int(value)
        for value in (known.get("visible_numbers") or ())
        if isinstance(value, int) and not isinstance(value, bool)
    )
    protected = frozenset(
        protected_answers_from(problem, step.step_number)
    )
    return LogicalGuidanceContext(
        family=str(known.get("family") or meta.get("family") or ""),
        language=locale,
        milestone=str(meta.get("milestone") or ""),
        purpose=str(meta.get("purpose") or ""),
        params=params,
        clue_kinds=tuple(known.get("clue_kinds") or ()),
        visible_numbers=visible,
        protected=protected,
        current_step=step.step_number,
        public_clues=public_clues,
        current_prompt=str(step.prompt or ""),
    )


def build_logical_guidance_from_question_context(context):
    metadata = context.tutor_metadata or {}
    family = str(metadata.get("family") or "")
    milestone = str(metadata.get("milestone") or "")
    if not family or not milestone:
        return None
    params = dict(metadata.get("logic_params") or metadata.get("params") or {})
    locale = normalize_locale(context.language)
    public_clues = tuple(metadata.get("public_clues") or ())
    _merge_public_relations(params, public_clues, locale)
    _fill_names(params, locale)
    visible = frozenset(
        int(value)
        for value in (metadata.get("visible_numbers") or ())
        if isinstance(value, int) and not isinstance(value, bool)
    )
    return LogicalGuidanceContext(
        family=family,
        language=locale,
        milestone=milestone,
        purpose=str(metadata.get("purpose") or milestone),
        params=params,
        clue_kinds=tuple(metadata.get("clue_kinds") or ()),
        visible_numbers=visible,
        protected=frozenset(),
        current_step=int(context.current_step or 1),
        public_clues=public_clues,
        current_prompt=str(context.current_prompt or ""),
    )


def match_logical_method_intent(question: str) -> bool:
    message = " ".join((question or "").strip().lower().split())
    if any(cue in message for cue in _METHOD_CUES):
        return True
    return _HOW_METHOD_RE.search(message) is not None


def match_logical_answer_format_intent(question: str) -> bool:
    message = " ".join((question or "").strip().lower().split())
    has_action = any(
        _contains_format_cue(message, cue)
        for cue in _FORMAT_ACTION_CUES
    )
    has_shape = any(
        _contains_format_cue(message, cue)
        for cue in _FORMAT_SHAPE_CUES
    )
    return has_action and has_shape


def match_logical_terminology_intent(question: str) -> bool:
    message = " ".join((question or "").strip().lower().split())
    has_term = any(word in message for word in _TERM_WORDS)
    has_ask = any(cue in message for cue in _TERM_ASK)
    return has_term and has_ask


def match_logical_reasoning_explanation(question: str, context) -> str | None:
    if context.topic != "logical_reasoning":
        return None
    if match_logical_answer_format_intent(question):
        formatted = explain_logical_answer_format(context)
        if formatted:
            return formatted
    if match_logical_terminology_intent(question):
        guidance = build_logical_guidance_from_question_context(context)
        if guidance is None or guidance.family != FAMILY_DISTRIBUTION:
            return None
        return explain_logical_terminology(guidance)
    if not match_logical_method_intent(question):
        return None
    guidance = build_logical_guidance_from_question_context(context)
    if guidance is None:
        return logical_method_fallback(context.language)
    return explain_logical_method(guidance)


def explain_logical_answer_format(context) -> str | None:
    if not _expects_single_number(context):
        return None
    locale = normalize_locale(context.language)
    metadata = context.tutor_metadata or {}
    if not isinstance(metadata, dict):
        metadata = {}
    family = str(metadata.get("family") or "")
    if family == FAMILY_DISTRIBUTION:
        key = "gen.logic.input.one_number.distribution"
    else:
        key = "gen.logic.input.one_number"
    return lrt(locale, key)


def explain_logical_method(ctx: LogicalGuidanceContext) -> str:
    key = f"gen.logic.method.{ctx.milestone}"
    text = lrt(ctx.language, key, **ctx.params)
    if text == key:
        text = lrt(ctx.language, "gen.logic.method.fallback", **ctx.params)
    return _safe_text(text, ctx)


def logical_method_fallback(language: str | None) -> str:
    return lrt(language, "gen.logic.method.fallback")


def progressive_logical_hint(
    ctx: LogicalGuidanceContext,
    used: int,
) -> tuple[str, bool]:
    level = used if used >= 1 else 1
    exhausted = level >= 3
    if level > 3:
        last = _hint_text(ctx, 3)
        extra = lrt(ctx.language, "gen.logic.hint.exhausted")
        return f"{last} {extra}", True
    text = _hint_text(ctx, min(level, 3))
    if exhausted:
        text = f"{text} {lrt(ctx.language, 'gen.logic.hint.last')}"
    return text, exhausted


def incorrect_logical_nudge(ctx: LogicalGuidanceContext) -> str:
    key = f"gen.logic.incorrect.{ctx.milestone}"
    text = lrt(ctx.language, key, **ctx.params)
    if text == key:
        text = lrt(ctx.language, "gen.logic.method.fallback", **ctx.params)
    return _safe_text(text, ctx)


def correct_logical_nudge(ctx: LogicalGuidanceContext) -> str:
    key = f"gen.logic.correct.{ctx.milestone}"
    text = lrt(ctx.language, key, **ctx.params)
    if text == key:
        text = lrt(ctx.language, "gen.logic.correct.box_quantity", **ctx.params)
    return _safe_text(text, ctx)


def explain_logical_known(ctx: LogicalGuidanceContext) -> str:
    if ctx.family == FAMILY_DISTRIBUTION:
        params = dict(ctx.params)
        params["clue_list"] = _distribution_clue_list(ctx)
        return _safe_text(
            lrt(ctx.language, "gen.logic.guide.known.distribution", **params),
            ctx,
        )
    return _safe_text(
        lrt(ctx.language, "gen.logic.guide.known", **ctx.params),
        ctx,
    )


def explain_logical_unknown(ctx: LogicalGuidanceContext) -> str:
    if ctx.family == FAMILY_DISTRIBUTION:
        params = dict(ctx.params)
        params["current_prompt"] = ctx.current_prompt
        return _safe_text(
            lrt(
                ctx.language,
                "gen.logic.guide.unknown.distribution",
                **params,
            ),
            ctx,
        )
    return _safe_text(
        lrt(ctx.language, "gen.logic.guide.unknown", **ctx.params),
        ctx,
    )


def explain_logical_first_clue(ctx: LogicalGuidanceContext) -> str:
    if ctx.family == FAMILY_DISTRIBUTION:
        specific = (
            f"gen.logic.guide.first_clue.distribution.{ctx.milestone}"
        )
        text = lrt(ctx.language, specific, **ctx.params)
        if text == specific:
            text = lrt(
                ctx.language,
                "gen.logic.guide.first_clue.distribution",
                **ctx.params,
            )
        return _safe_text(text, ctx)
    return _safe_text(
        lrt(ctx.language, "gen.logic.guide.first_clue", **ctx.params),
        ctx,
    )


def explain_logical_eliminate(ctx: LogicalGuidanceContext) -> str:
    if ctx.family == FAMILY_DISTRIBUTION:
        return _safe_text(
            lrt(ctx.language, "gen.logic.guide.no_eliminate", **ctx.params),
            ctx,
        )
    return _safe_text(
        lrt(ctx.language, "gen.logic.guide.eliminate", **ctx.params),
        ctx,
    )


def explain_logical_check(ctx: LogicalGuidanceContext) -> str:
    if ctx.family == FAMILY_DISTRIBUTION:
        specific = f"gen.logic.guide.check.distribution.{ctx.milestone}"
        text = lrt(ctx.language, specific, **ctx.params)
        if text == specific:
            text = lrt(
                ctx.language,
                "gen.logic.guide.check.distribution",
                **ctx.params,
            )
        return _safe_text(text, ctx)
    return _safe_text(
        lrt(ctx.language, "gen.logic.guide.check", **ctx.params),
        ctx,
    )


def explain_logical_terminology(ctx: LogicalGuidanceContext) -> str:
    if ctx.params.get("left") and ctx.params.get("right"):
        return _safe_text(
            lrt(ctx.language, "gen.logic.term.scaled", **ctx.params),
            ctx,
        )
    return _safe_text(
        lrt(ctx.language, "gen.logic.term.scaled.none", **ctx.params),
        ctx,
    )


def _hint_text(ctx: LogicalGuidanceContext, level: int) -> str:
    key = f"gen.logic.hint.{ctx.milestone}.{level}"
    params = dict(ctx.params)
    setup = _localized_setup(ctx)
    if setup:
        params["setup"] = setup
    text = lrt(ctx.language, key, **params)
    if text == key:
        text = lrt(ctx.language, "gen.logic.method.fallback", **params)
    return _safe_text(text, ctx)


def _localized_setup(ctx: LogicalGuidanceContext) -> str | None:
    parts = ctx.params.get("setup_parts")
    operation = ctx.params.get("setup_op")
    if not parts or not operation:
        setup = ctx.params.get("setup")
        return str(setup) if setup else None
    from src.core.tutor_engine.primary_school.generation.logical_reasoning.compile import (
        format_setup_expression,
    )

    return format_setup_expression(operation, parts, ctx.language)


def _safe_text(text: str, ctx: LogicalGuidanceContext) -> str:
    if "{" in text and "}" in text:
        return lrt(ctx.language, "gen.logic.method.fallback")
    if discloses_protected(text, ctx.protected, ctx.visible_numbers):
        return lrt(ctx.language, "gen.logic.method.fallback")
    return text


def _expects_single_number(context) -> bool:
    input_type = str(
        getattr(context, "expected_input_type", "") or ""
    ).strip().lower()
    if input_type == "number":
        return True
    metadata = getattr(context, "tutor_metadata", None) or {}
    if not isinstance(metadata, dict):
        return False
    answer_format = str(
        metadata.get("answer_format") or ""
    ).strip().lower()
    return answer_format == "integer"


def _contains_format_cue(message: str, cue: str) -> bool:
    if any(ord(character) > 127 for character in cue):
        return cue in message
    pattern = r"(?<![a-z0-9])" + re.escape(cue) + r"(?![a-z0-9])"
    return re.search(pattern, message) is not None


def _fill_names(params: dict, locale: str) -> None:
    item = params.get("item")
    if item and "item_name" not in params:
        params["item_name"] = lrt(locale, f"gen.logic.object.{item}")
    box = params.get("box")
    if box and "box_name" not in params:
        params["box_name"] = lrt(locale, f"gen.logic.box.{box}")
    left = params.get("left")
    if left and "left_name" not in params:
        params["left_name"] = lrt(locale, f"gen.logic.box.{left}")
    right = params.get("right")
    if right and "right_name" not in params:
        params["right_name"] = lrt(locale, f"gen.logic.box.{right}")
    extra_left = params.get("extra_left")
    if extra_left and "extra_left_name" not in params:
        params["extra_left_name"] = lrt(
            locale,
            f"gen.logic.box.{extra_left}",
        )
    extra_right = params.get("extra_right")
    if extra_right and "extra_right_name" not in params:
        params["extra_right_name"] = lrt(
            locale,
            f"gen.logic.box.{extra_right}",
        )
    factor = params.get("factor")
    if (
        isinstance(factor, int)
        and not isinstance(factor, bool)
        and "factor_word" not in params
    ):
        key = f"gen.logic.factor_word.{factor}"
        word = lrt(locale, key)
        params["factor_word"] = str(factor) if word == key else word
    left_name = params.get("left_name")
    if (
        isinstance(left_name, str)
        and left_name
        and "left_name_cap" not in params
    ):
        params["left_name_cap"] = left_name[:1].upper() + left_name[1:]
    extra_left_name = params.get("extra_left_name")
    if (
        isinstance(extra_left_name, str)
        and extra_left_name
        and "extra_left_name_cap" not in params
    ):
        params["extra_left_name_cap"] = (
            extra_left_name[:1].upper() + extra_left_name[1:]
        )


def _merge_public_relations(params: dict, public_clues, locale: str) -> None:
    for clue in public_clues or ():
        if not isinstance(clue, dict):
            continue
        kind = clue.get("kind")
        if kind == "times_as_many":
            params.setdefault("left", clue.get("left"))
            params.setdefault("right", clue.get("right"))
            params.setdefault("factor", clue.get("factor"))
        elif kind == "more_than":
            params.setdefault("extra_left", clue.get("left"))
            params.setdefault("extra_right", clue.get("right"))
            params.setdefault("extra", clue.get("extra"))
        elif kind == "total":
            params.setdefault("total", clue.get("total"))
    _fill_names(params, locale)


def _distribution_clue_list(ctx: LogicalGuidanceContext) -> str:
    box_names = set()
    for clue in ctx.public_clues:
        if not isinstance(clue, dict):
            continue
        for key in ("left", "right"):
            value = clue.get(key)
            if value:
                box_names.add(value)
    count = "three" if len(box_names) >= 3 else "two"
    sentences = []
    for clue in ctx.public_clues:
        if not isinstance(clue, dict):
            continue
        kind = clue.get("kind")
        params = dict(clue)
        _fill_names(params, ctx.language)
        if kind == "total":
            key = f"gen.logic.clue.total.{count}"
        elif kind == "times_as_many":
            key = "gen.logic.clue.times_as_many"
        elif kind == "more_than":
            key = "gen.logic.clue.more_than"
        else:
            continue
        text = lrt(ctx.language, key, **params)
        if text != key:
            sentences.append(text[:1].upper() + text[1:] if text else text)
    return " ".join(sentences)
