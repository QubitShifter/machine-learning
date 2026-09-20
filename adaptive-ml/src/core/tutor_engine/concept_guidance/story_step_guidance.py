from dataclasses import dataclass

from src.core.i18n.locale import normalize_locale
from src.core.i18n.story_guidance import has_story_guidance_key, sgt
from src.core.tutor_engine.concept_guidance.word_problem_guidance import (
    _EXAMPLES,
    _shifted_example,
)
from src.core.tutor_engine.primary_school.generation.word_problems.model import (
    FAMILY_REVERSE,
    OP_ADD,
    OP_DOUBLE,
    OP_MUL,
    OP_SUB,
    Relation,
)
from src.core.tutor_engine.primary_school.generation.word_problems.templates import (
    TEMPLATES_BY_ID,
)
PURPOSE_IDENTIFY = "identify_visible"
PURPOSE_FORWARD = "apply_forward"
PURPOSE_UNDO = "undo"


@dataclass(frozen=True)
class StoryGuidanceContext:
    template_id: str
    family: str
    language: str
    ask: str
    identify_known: str
    statement_ids: tuple[str, ...]
    visible_values: dict[str, int]
    hidden_ids: tuple[str, ...]
    hidden_values: frozenset[int]
    current_quantity_id: str
    current_purpose: str
    current_op: str | None
    current_relation: Relation | None
    visible_operand_ids: tuple[str, ...]
    disclosed_values: dict[str, int]


def build_story_guidance_context(
    problem,
    live_response,
    language: str | None,
) -> StoryGuidanceContext | None:
    known = getattr(problem, "known", None) or {}
    template_id = known.get("template_id")
    template = TEMPLATES_BY_ID.get(template_id)
    if template is None:
        return None
    statement_ids = tuple(template.statement_ids)
    statement_params = known.get("statement_params") or {}
    visible_values = {
        name: int(statement_params[name])
        for name in statement_ids
        if name in statement_params
        and _is_positive_int(statement_params[name])
    }
    quantities = known.get("quantities") or {}
    hidden_ids = tuple(template.hidden)
    hidden_values = frozenset(
        int(value)
        for name, value in quantities.items()
        if name not in statement_ids and _is_positive_int(value)
    )
    quantity_id = _current_quantity_id(problem, live_response)
    if not quantity_id:
        return None
    purpose, relation, operand_ids = _resolve_step_action(
        template,
        quantity_id,
    )
    return StoryGuidanceContext(
        template_id=template.template_id,
        family=template.family,
        language=normalize_locale(language),
        ask=template.ask,
        identify_known=template.identify_known,
        statement_ids=statement_ids,
        visible_values=visible_values,
        hidden_ids=hidden_ids,
        hidden_values=hidden_values,
        current_quantity_id=quantity_id,
        current_purpose=purpose,
        current_op=relation.op if relation is not None else None,
        current_relation=relation,
        visible_operand_ids=operand_ids,
        disclosed_values=_disclosed_values(
            problem,
            live_response,
            visible_values,
        ),
    )


def explain_story_given(ctx: StoryGuidanceContext) -> str | None:
    return _render(
        ctx,
        f"story.guide.given.{ctx.template_id}",
    )


def explain_story_asked(ctx: StoryGuidanceContext) -> str | None:
    return _render(
        ctx,
        f"story.guide.ask.{ctx.template_id}",
    )


def explain_story_step(ctx: StoryGuidanceContext) -> str | None:
    purpose_key = {
        PURPOSE_IDENTIFY: "identify",
        PURPOSE_FORWARD: "forward",
        PURPOSE_UNDO: "undo",
    }.get(ctx.current_purpose)
    if purpose_key is None:
        return None
    return _render(
        ctx,
        "story.guide.step."
        f"{purpose_key}.{ctx.template_id}."
        f"{ctx.current_quantity_id}",
    )


def explain_story_phrase(
    phrase: str,
    ctx: StoryGuidanceContext,
) -> str | None:
    define_key = f"story.guide.phrase.{phrase}.define"
    if not has_story_guidance_key(ctx.language, define_key):
        return None
    params = _safe_example_params(phrase, ctx)
    definition = sgt(ctx.language, define_key, **params)
    here_key = (
        f"story.guide.phrase.here.{ctx.template_id}.{phrase}"
    )
    if has_story_guidance_key(ctx.language, here_key):
        here = _render(ctx, here_key)
        if here:
            return f"{definition} {here}"
    return definition


def _render(ctx: StoryGuidanceContext, key: str) -> str | None:
    if not has_story_guidance_key(ctx.language, key):
        return None
    text = sgt(ctx.language, key, **ctx.visible_values)
    if "{" in text and "}" in text:
        return None
    return text


def _resolve_step_action(
    template,
    quantity_id: str,
) -> tuple[str, Relation | None, tuple[str, ...]]:
    if quantity_id == template.identify_known:
        operands = (
            (quantity_id,)
            if quantity_id in template.statement_ids
            else ()
        )
        return PURPOSE_IDENTIFY, None, operands
    if template.family == FAMILY_REVERSE:
        known = set(template.statement_ids)
        for relation in reversed(template.relations):
            unknown_inputs = [
                name
                for name in relation.inputs
                if name not in known
            ]
            if (
                len(unknown_inputs) == 1
                and unknown_inputs[0] == quantity_id
            ):
                operands = tuple(
                    name
                    for name in relation.inputs
                    if name in template.statement_ids
                )
                return PURPOSE_UNDO, relation, operands
            if len(unknown_inputs) == 1:
                known.add(unknown_inputs[0])
        return PURPOSE_UNDO, None, ()
    for relation in template.relations:
        if relation.output == quantity_id:
            operands = tuple(
                name
                for name in relation.inputs
                if name in template.statement_ids
            )
            return PURPOSE_FORWARD, relation, operands
    return PURPOSE_FORWARD, None, ()


def _current_quantity_id(problem, live_response) -> str:
    if problem is None:
        return ""
    getter = getattr(problem, "get_step", None)
    if getter is None:
        return ""
    step = getter(live_response.current_step)
    if step is None:
        return ""
    key = (step.metadata or {}).get("prompt_key") or ""
    if "." not in str(key):
        return ""
    return str(key).rsplit(".", 1)[-1]


def _safe_example_params(
    phrase: str,
    ctx: StoryGuidanceContext,
) -> dict[str, int]:
    forbidden = set(ctx.visible_values.values()) | set(
        ctx.hidden_values
    )
    params = dict(_EXAMPLES.get(phrase) or {})
    if phrase == "doubled" and not params:
        params = {"ex_left": 3, "ex_result": 6}
    if not params:
        return {}
    if set(params.values()) & forbidden:
        params = _shifted_example(phrase, forbidden)
        if phrase == "doubled":
            for left in range(3, 12):
                result = left * 2
                if {left, result}.isdisjoint(forbidden):
                    return {"ex_left": left, "ex_result": result}
    if phrase == "doubled" and "ex_left" not in params:
        params = {"ex_left": 3, "ex_result": 6}
    return params


def _is_positive_int(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return value > 0


def build_story_guidance_from_question_context(
    context,
) -> StoryGuidanceContext | None:
    metadata = context.tutor_metadata or {}
    template_id = metadata.get("template_id")
    template = TEMPLATES_BY_ID.get(template_id)
    if template is None:
        return None
    prompt_key = str(metadata.get("prompt_key") or "")
    quantity_id = (
        prompt_key.rsplit(".", 1)[-1] if "." in prompt_key else ""
    )
    if not quantity_id:
        return None
    visible_values = _int_map(metadata.get("story_visible"))
    disclosed = _int_map(metadata.get("disclosed_values")) or dict(
        visible_values
    )
    purpose, relation, operand_ids = _resolve_step_action(
        template,
        quantity_id,
    )
    hidden_values = frozenset(
        int(value)
        for value in (metadata.get("hidden_values") or ())
        if _is_positive_int(value)
    )
    return StoryGuidanceContext(
        template_id=template.template_id,
        family=template.family,
        language=normalize_locale(context.language),
        ask=template.ask,
        identify_known=template.identify_known,
        statement_ids=tuple(template.statement_ids),
        visible_values=visible_values,
        hidden_ids=tuple(template.hidden),
        hidden_values=hidden_values,
        current_quantity_id=quantity_id,
        current_purpose=purpose,
        current_op=relation.op if relation is not None else None,
        current_relation=relation,
        visible_operand_ids=operand_ids,
        disclosed_values=disclosed,
    )


def explain_story_method(ctx: StoryGuidanceContext) -> str:
    parts = []
    step = explain_story_step(ctx)
    if step:
        parts.append(step)
    setup = unevaluated_setup(ctx)
    if setup:
        parts.append(
            sgt(
                ctx.language,
                "story.method.setup",
                setup=setup,
            )
        )
    if parts:
        return " ".join(parts)
    return sgt(ctx.language, "story.method.fallback")


def story_method_fallback(language: str | None) -> str:
    return sgt(language, "story.method.fallback")


def progressive_hint(
    ctx: StoryGuidanceContext,
    level: int,
) -> tuple[str, bool]:
    """Return (text, exhausted). level is 1-based after recording."""
    level = _as_hint_level(level)
    exhausted = level >= 3
    if level > 3:
        last = _hint_text(ctx, 3)
        extra = sgt(ctx.language, "story.hint.exhausted")
        return f"{last} {extra}", True
    text = _hint_text(ctx, level)
    if exhausted:
        text = f"{text} {sgt(ctx.language, 'story.hint.last')}"
    return text, exhausted


def incorrect_story_nudge(ctx: StoryGuidanceContext) -> str:
    if ctx.current_purpose == PURPOSE_IDENTIFY:
        key = "story.incorrect.identify"
    elif ctx.current_purpose == PURPOSE_UNDO:
        key = "story.incorrect.undo"
    else:
        key = "story.incorrect.forward"
    return sgt(ctx.language, key)


def unevaluated_setup(ctx: StoryGuidanceContext) -> str | None:
    params = _hint_params(ctx)
    relation = ctx.current_relation
    if ctx.current_purpose == PURPOSE_IDENTIFY:
        return None
    if relation is None:
        return None
    if ctx.current_purpose == PURPOSE_UNDO:
        output = params.get("output")
        if output is None:
            return None
        if relation.op == OP_ADD:
            other = params.get("other")
            if other is None:
                return None
            return f"{output} - {other} = ?"
        if relation.op == OP_SUB:
            other = params.get("other")
            if other is None:
                return None
            return f"{output} + {other} = ?"
        if relation.op == OP_MUL:
            other = params.get("other")
            if other is None:
                return None
            return f"{output} ÷ {other} = ?"
        if relation.op == OP_DOUBLE:
            return f"{output} ÷ 2 = ?"
        return None
    if ctx.current_purpose == PURPOSE_FORWARD:
        if relation.op == OP_ADD:
            left = params.get("left")
            right = params.get("right")
            if left is None or right is None:
                return None
            return f"{left} + {right} = ?"
        if relation.op == OP_SUB:
            left = params.get("left")
            right = params.get("right")
            if left is None or right is None:
                return None
            return f"{left} - {right} = ?"
        if relation.op == OP_MUL:
            left = params.get("left")
            right = params.get("right")
            if left is None or right is None:
                return None
            return f"{left} × {right} = ?"
        if relation.op == OP_DOUBLE:
            left = params.get("left")
            if left is None:
                return None
            return f"{left} × 2 = ?"
    return None


def _as_hint_level(level) -> int:
    try:
        value = int(level)
    except (TypeError, ValueError):
        return 1
    if value < 1:
        return 1
    return value


def _hint_stage(level: int) -> str:
    value = _as_hint_level(level)
    if value <= 1:
        return "understand"
    if value == 2:
        return "operation"
    return "setup"


def _hint_text(ctx: StoryGuidanceContext, level: int) -> str:
    kind = {
        PURPOSE_IDENTIFY: "identify",
        PURPOSE_FORWARD: "forward",
        PURPOSE_UNDO: "undo",
    }.get(ctx.current_purpose)
    stage = _hint_stage(level)
    op = ctx.current_op or "none"
    if ctx.current_purpose == PURPOSE_IDENTIFY:
        key = f"story.hint.{stage}.identify"
    else:
        key = f"story.hint.{stage}.{kind}.{op}"
    params = _hint_params(ctx)
    if stage == "setup":
        setup = unevaluated_setup(ctx)
        if setup:
            params = {**params, "setup": setup}
            key = "story.hint.setup.expression"
        elif not has_story_guidance_key(ctx.language, key):
            key = "story.hint.setup.generic"
    if not has_story_guidance_key(ctx.language, key):
        if stage == "setup":
            key = "story.hint.setup.generic"
        elif kind == "identify":
            key = f"story.hint.{stage}.identify"
        else:
            key = f"story.hint.{stage}.generic"
    text = sgt(ctx.language, key, **params)
    if "{" in text and "}" in text:
        return sgt(ctx.language, "story.hint.setup.generic")
    return text


def _hint_params(ctx: StoryGuidanceContext) -> dict[str, int | str]:
    disclosed = dict(ctx.disclosed_values or ctx.visible_values)
    params: dict[str, int | str] = dict(ctx.visible_values)
    relation = ctx.current_relation
    if relation is None:
        return params
    if ctx.current_purpose == PURPOSE_UNDO:
        output = disclosed.get(relation.output)
        if output is not None:
            params["output"] = output
        if relation.op != OP_DOUBLE:
            others = [
                name
                for name in relation.inputs
                if name != ctx.current_quantity_id
            ]
            if len(others) == 1:
                other = disclosed.get(others[0])
                if other is None:
                    other = ctx.visible_values.get(others[0])
                if other is not None:
                    params["other"] = other
        return params
    if ctx.current_purpose == PURPOSE_FORWARD:
        values = [disclosed.get(name) for name in relation.inputs]
        if relation.op == OP_DOUBLE and values and values[0] is not None:
            params["left"] = values[0]
        elif len(values) == 2 and None not in values:
            params["left"] = values[0]
            params["right"] = values[1]
    return params


def _disclosed_values(problem, live_response, visible_values) -> dict[str, int]:
    disclosed = dict(visible_values)
    current_step = getattr(live_response, "current_step", 0) or 0
    steps = getattr(problem, "solution_steps", ()) or ()
    for step in steps:
        if step.step_number >= current_step:
            continue
        key = (step.metadata or {}).get("prompt_key") or ""
        if "." not in str(key):
            continue
        quantity_id = str(key).rsplit(".", 1)[-1]
        value = step.expected_answer
        if quantity_id and _is_positive_int(value):
            disclosed[quantity_id] = int(value)
    return disclosed


def _int_map(raw) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    values: dict[str, int] = {}
    for key, value in raw.items():
        if _is_positive_int(value):
            values[str(key)] = int(value)
    return values
