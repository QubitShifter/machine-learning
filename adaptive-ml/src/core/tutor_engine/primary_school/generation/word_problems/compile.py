from src.core.tutor_engine.primary_school.generation.builder import (
    build_problem_from_specs,
    integer_step,
)
from src.core.tutor_engine.primary_school.generation.word_problems.model import (
    FAMILY_REVERSE,
    OP_ADD,
    OP_DOUBLE,
    OP_MUL,
    OP_SUB,
    StoryTemplate,
)
from src.core.tutor_engine.primary_school.generation.word_problems.relations import (
    evaluate_quantities,
    render_forward_operation,
    render_undo_operation,
    undo_relation,
)
from src.core.tutor_engine.primary_school.problem_types import (
    ProblemType,
    SolutionStepType,
)


_SKILL_FORWARD = "grade4_word_problems"
_SKILL_IDENTIFY = "grade4_word_problem_identify_known"
_UNDO_SKILLS = {
    OP_ADD: "grade4_reverse_addition",
    OP_SUB: "grade4_reverse_subtraction",
    OP_MUL: "grade4_reverse_multiplication",
    OP_DOUBLE: "grade4_reverse_multiplication",
}

_BOUNDS = {
    1: 40,
    2: 80,
    3: 200,
}


def compile_story_problem(
    template: StoryTemplate,
    slots: dict[str, int],
    difficulty: int,
):
    quantities = evaluate_quantities(template.relations, slots)
    _require_bounds(quantities, difficulty)
    statement_params = {
        name: quantities[name]
        for name in template.statement_ids
    }
    if template.family == FAMILY_REVERSE:
        step_specs = _reverse_steps(template, quantities)
        strategy = "work_backwards"
    else:
        step_specs = _forward_steps(template, quantities)
        strategy = "dependent_calculations"

    known = {
        "template_id": template.template_id,
        "family": template.family,
        "difficulty": difficulty,
        "slots": dict(slots),
        "quantities": dict(quantities),
        "relations": [
            {
                "op": relation.op,
                "inputs": list(relation.inputs),
                "output": relation.output,
            }
            for relation in template.relations
        ],
        "ask": template.ask,
        "hidden": list(template.hidden),
        "statement_key": template.statement_key,
        "statement_ids": list(template.statement_ids),
        "statement_params": statement_params,
        "relation_count": template.relation_count,
        "identify_known": template.identify_known,
        "meaning": template.semantics.meaning,
    }
    return build_problem_from_specs(
        problem_id="grade4_word_problems",
        grade=4,
        topic="story_problems",
        problem_type=ProblemType.WORD_PROBLEM,
        language="en",
        skills=["grade4_word_problems"],
        known=known,
        unknown={
            "name": template.ask,
            "quantity_id": template.ask,
        },
        strategy=strategy,
        final_answer=quantities[template.ask],
        step_specs=step_specs,
        metadata={
            "family": template.family,
            "template_id": template.template_id,
            "difficulty": difficulty,
            "relation_count": template.relation_count,
        },
    )


def _forward_steps(template: StoryTemplate, quantities: dict[str, int]):
    specs = [
        integer_step(
            step_number=1,
            skill_id=_SKILL_IDENTIFY,
            expected_answer=quantities[template.identify_known],
            prompt_key=_prompt_key(
                template.template_id,
                template.identify_known,
            ),
            hint_key=_hint_key(
                template.template_id,
                template.identify_known,
            ),
            params=_visible_params(template, quantities),
            step_type=SolutionStepType.IDENTIFY_KNOWN,
        )
    ]
    for index, relation in enumerate(template.relations, start=2):
        specs.append(
            integer_step(
                step_number=index,
                skill_id=_SKILL_FORWARD,
                expected_answer=quantities[relation.output],
                prompt_key=_prompt_key(
                    template.template_id,
                    relation.output,
                ),
                hint_key=_hint_key(
                    template.template_id,
                    relation.output,
                ),
                params=_visible_params(template, quantities),
                operation=render_forward_operation(
                    relation,
                    quantities,
                ),
                step_type=SolutionStepType.CALCULATION,
            )
        )
    return specs


def _reverse_steps(template: StoryTemplate, quantities: dict[str, int]):
    specs = [
        integer_step(
            step_number=1,
            skill_id=_SKILL_IDENTIFY,
            expected_answer=quantities[template.identify_known],
            prompt_key=_prompt_key(
                template.template_id,
                template.identify_known,
            ),
            hint_key=_hint_key(
                template.template_id,
                template.identify_known,
            ),
            params=_visible_params(template, quantities),
            step_type=SolutionStepType.IDENTIFY_KNOWN,
        )
    ]
    known_now = {
        name: quantities[name]
        for name in template.statement_ids
    }
    step_number = 2
    for relation in reversed(template.relations):
        unknown, recovered = undo_relation(relation, known_now)
        known_now[unknown] = recovered
        if recovered != quantities[unknown]:
            raise ValueError("Reverse recovery mismatch.")
        specs.append(
            integer_step(
                step_number=step_number,
                skill_id=_UNDO_SKILLS[relation.op],
                expected_answer=recovered,
                prompt_key=_prompt_key(
                    template.template_id,
                    unknown,
                ),
                hint_key=_hint_key(
                    template.template_id,
                    unknown,
                ),
                params=_visible_params(template, quantities),
                operation=render_undo_operation(
                    relation,
                    unknown,
                    quantities,
                ),
                step_type=SolutionStepType.CALCULATION,
            )
        )
        step_number += 1
    return specs


def _visible_params(
    template: StoryTemplate,
    quantities: dict[str, int],
) -> dict[str, int]:
    return {
        name: quantities[name]
        for name in template.statement_ids
    }


def _prompt_key(template_id: str, quantity_id: str) -> str:
    return f"gen.story.{template_id}.prompt.{quantity_id}"


def _hint_key(template_id: str, quantity_id: str) -> str:
    return f"gen.story.{template_id}.hint.{quantity_id}"


def _require_bounds(quantities: dict[str, int], difficulty: int) -> None:
    maximum = _BOUNDS[difficulty]
    for name, value in quantities.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} is not an integer.")
        if value <= 0:
            raise ValueError(f"{name} is not positive.")
        if value > maximum:
            raise ValueError(f"{name} exceeds difficulty bounds.")
