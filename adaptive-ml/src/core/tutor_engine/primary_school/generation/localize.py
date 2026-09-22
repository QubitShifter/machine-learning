from src.core.i18n.locale import normalize_locale
from src.core.i18n.primary_school import pst
from src.core.tutor_engine.primary_school.problem_types import (
    PrimarySchoolProblem,
    SolutionStep,
)


_FAMILY_TITLE_KEYS = {
    "arithmetic": "gen.arithmetic.title",
    "unknown_number": "gen.unknown.title",
    "number_patterns": "gen.patterns.title",
    "several_operations": "gen.story.title",
    "comparison": "gen.story.title",
    "reverse": "gen.story.title",
    "number_detective": "gen.logic.number.title",
    "distribution_puzzles": "gen.logic.distribution.title",
    "logic_detective": "gen.logic.logic.title",
}
_LOGICAL_FAMILIES = {
    "number_detective",
    "distribution_puzzles",
    "logic_detective",
}
_STORY_FAMILIES = {
    "several_operations",
    "comparison",
    "reverse",
}


def localize_generated_primary_school(
    problem: PrimarySchoolProblem,
    language: str | None,
) -> PrimarySchoolProblem:
    locale = normalize_locale(language)
    family = (problem.metadata or {}).get("family")
    params = _statement_params(problem)
    title_key = _FAMILY_TITLE_KEYS.get(
        family,
        "gen.arithmetic.title",
    )
    statement_key = _statement_key(problem)
    steps = [
        _render_step(step, locale)
        for step in problem.solution_steps
    ]
    if problem.topic == "logical_reasoning" or family in _LOGICAL_FAMILIES:
        problem_text = _render_logical_statement(problem, locale)
    else:
        problem_text = pst(
            locale,
            statement_key,
            **params,
        )
    return PrimarySchoolProblem(
        problem_id=problem.problem_id,
        grade=problem.grade,
        topic=problem.topic,
        problem_type=problem.problem_type,
        title=pst(locale, title_key),
        language=locale,
        problem_text=problem_text,
        skills=list(problem.skills),
        known=dict(problem.known),
        unknown=dict(problem.unknown),
        strategy=problem.strategy,
        solution_steps=steps,
        final_answer=problem.final_answer,
        metadata=dict(problem.metadata or {}),
    )


def _statement_key(problem: PrimarySchoolProblem) -> str:
    family = (problem.metadata or {}).get("family")
    stored = problem.known.get("statement_key")
    if family in _STORY_FAMILIES and stored:
        return stored
    if family == "arithmetic":
        return "gen.arithmetic.statement"
    if family == "unknown_number":
        return "gen.unknown.statement"
    if problem.known.get("variant") == "chain":
        if problem.known.get("direction") == "reverse":
            return "gen.chain.statement.reverse"
        return "gen.chain.statement.forward"
    return "gen.sequence.statement"


def _statement_params(problem: PrimarySchoolProblem) -> dict:
    known = problem.known
    if known.get("statement_params") is not None:
        return dict(known["statement_params"])
    if "expression" in known:
        return {"expression": known["expression"]}
    if "equation" in known:
        return {"equation": known["equation"]}
    if known.get("variant") == "chain":
        return {"chain": known["chain_text"]}
    return {"sequence": known.get("sequence_text", "")}


def _render_logical_statement(problem: PrimarySchoolProblem, locale: str) -> str:
    parts = (problem.known or {}).get("statement_parts") or ()
    sentences = []
    for part in parts:
        params = _logical_params(part.get("params") or {}, locale)
        text = pst(locale, part["key"], **params)
        sentences.append(_capitalize_sentence(text))
    return " ".join(sentences)


def _capitalize_sentence(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]


def _logical_params(params: dict, locale: str) -> dict:
    values = dict(params)
    item = values.get("item")
    if item:
        values["item_name"] = pst(locale, f"gen.logic.object.{item}")
    box = values.get("box")
    if box:
        values["box_name"] = pst(locale, f"gen.logic.box.{box}")
    left = values.get("left")
    if left:
        values["left_name"] = pst(locale, f"gen.logic.box.{left}")
    right = values.get("right")
    if right:
        values["right_name"] = pst(locale, f"gen.logic.box.{right}")
    extra_left = values.get("extra_left")
    if extra_left:
        values["extra_left_name"] = pst(
            locale,
            f"gen.logic.box.{extra_left}",
        )
    extra_right = values.get("extra_right")
    if extra_right:
        values["extra_right_name"] = pst(
            locale,
            f"gen.logic.box.{extra_right}",
        )
    factor = values.get("factor")
    if isinstance(factor, int) and not isinstance(factor, bool):
        key = f"gen.logic.factor_word.{factor}"
        word = pst(locale, key)
        values["factor_word"] = str(factor) if word == key else word
    return values


def _render_step(
    step: SolutionStep,
    locale: str,
) -> SolutionStep:
    meta = dict(step.metadata or {})
    params = _logical_params(dict(meta.get("params") or {}), locale)
    prompt_key = meta.get("prompt_key")
    hint_key = meta.get("hint_key")
    prompt = (
        pst(locale, prompt_key, **params)
        if prompt_key
        else step.prompt
    )
    hint = (
        pst(locale, hint_key, **params)
        if hint_key
        else step.hint
    )
    return SolutionStep(
        step_number=step.step_number,
        skill_id=step.skill_id,
        prompt=prompt,
        expected_answer=step.expected_answer,
        hint=hint,
        operation=step.operation,
        step_type=step.step_type,
        input_type=step.input_type,
        answer_format=step.answer_format,
        metadata=meta,
    )
