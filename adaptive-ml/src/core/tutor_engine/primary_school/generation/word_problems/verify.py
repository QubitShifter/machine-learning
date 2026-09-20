import re

from src.core.tutor_engine.primary_school.generation.word_problems.model import (
    FAMILY_REVERSE,
    SUPPORTED_FAMILIES,
    StoryTemplate,
)
from src.core.tutor_engine.primary_school.generation.word_problems.relations import (
    apply_relation,
    evaluate_quantities,
    recover_hidden,
)
from src.core.tutor_engine.primary_school.generation.word_problems.templates import (
    TEMPLATES_BY_ID,
)
from src.core.tutor_engine.primary_school.problem_types import (
    PrimarySchoolProblem,
    SolutionStepType,
)


def verify_word_problem(problem: PrimarySchoolProblem) -> None:
    template = _template_of(problem)
    _verify_structure(problem, template)
    quantities = _verify_quantities(problem, template)
    _verify_steps(problem, template, quantities)
    _verify_semantics(problem, template, quantities)


def _template_of(problem: PrimarySchoolProblem) -> StoryTemplate:
    template_id = problem.known.get("template_id")
    template = TEMPLATES_BY_ID.get(template_id)
    if template is None:
        raise ValueError(f"Unknown story template: {template_id}")
    return template


def _verify_structure(
    problem: PrimarySchoolProblem,
    template: StoryTemplate,
) -> None:
    family = problem.known.get("family")
    if family not in SUPPORTED_FAMILIES:
        raise ValueError(f"Unsupported story family: {family}")
    if family != template.family:
        raise ValueError("Family does not match the template.")
    difficulty = problem.metadata.get("difficulty")
    if difficulty not in (1, 2, 3):
        raise ValueError("Difficulty must be 1, 2, or 3.")
    if template.difficulty != difficulty:
        raise ValueError("Template does not match difficulty.")
    relation_count = problem.known.get("relation_count")
    if relation_count != template.relation_count:
        raise ValueError("Relation count does not match the template.")
    if relation_count != difficulty:
        raise ValueError(
            "Relation count must match reasoning difficulty."
        )
    if problem.unknown.get("quantity_id") != template.ask:
        raise ValueError("Unknown quantity is not the asked quantity.")
    if problem.topic != "story_problems":
        raise ValueError("Story problems must use topic story_problems.")


def _verify_quantities(
    problem: PrimarySchoolProblem,
    template: StoryTemplate,
) -> dict[str, int]:
    slots = dict(problem.known["slots"])
    stored = dict(problem.known["quantities"])
    recomputed = evaluate_quantities(template.relations, slots)
    if recomputed != stored:
        raise ValueError("Stored quantities do not match the relations.")
    statement_params = dict(problem.known["statement_params"])
    expected_params = {
        name: recomputed[name]
        for name in template.statement_ids
    }
    if statement_params != expected_params:
        raise ValueError("Statement parameters are inconsistent.")
    if set(statement_params.values()) != set(expected_params.values()):
        raise ValueError("Visible numbers are inconsistent.")
    if len(set(statement_params.values())) != len(statement_params):
        raise ValueError("Visible story numbers are not unique.")
    asked = recomputed[template.ask]
    if asked in statement_params.values():
        raise ValueError("Asked quantity equals a visible story number.")
    if problem.final_answer != asked:
        raise ValueError("Final answer is not the asked quantity.")
    if template.family == FAMILY_REVERSE:
        visible = {
            name: recomputed[name]
            for name in template.statement_ids
        }
        recovered = recover_hidden(template.relations, visible)
        if recovered[template.ask] != slots[template.ask]:
            raise ValueError("Reverse recovery does not restore start.")
        for name in template.hidden:
            if name in statement_params:
                raise ValueError("Hidden quantity appears in the story.")
    semantics = template.semantics
    if semantics.larger_id and semantics.smaller_id:
        if recomputed[semantics.larger_id] <= recomputed[
            semantics.smaller_id
        ]:
            raise ValueError("Comparison direction is reversed.")
    if semantics.double_input and semantics.double_output:
        doubled = recomputed[semantics.double_input] * 2
        if recomputed[semantics.double_output] != doubled:
            raise ValueError("Doubling is not times two.")
        if recomputed[semantics.double_output] == (
            recomputed[semantics.double_input] * 3
        ):
            raise ValueError("Doubling was modeled as adding twice.")
    for relation in template.relations:
        if apply_relation(relation, recomputed) != recomputed[
            relation.output
        ]:
            raise ValueError("Relation evaluation mismatch.")
    return recomputed


def _verify_steps(
    problem: PrimarySchoolProblem,
    template: StoryTemplate,
    quantities: dict[str, int],
) -> None:
    specs = list(problem.metadata["step_specs"])
    calc_count = sum(
        1
        for spec in specs
        if spec.get("step_type")
        == SolutionStepType.CALCULATION.value
    )
    if calc_count != template.relation_count:
        raise ValueError(
            "Calculation steps do not match relation count."
        )
    if specs[0]["step_type"] != SolutionStepType.IDENTIFY_KNOWN.value:
        raise ValueError("First step must identify a known quantity.")
    if specs[0]["expected_answer"] != quantities[template.identify_known]:
        raise ValueError("Identify-known step is incorrect.")
    identify = quantities[template.identify_known]
    if identify not in problem.known["statement_params"].values():
        raise ValueError("Identify-known is not a visible number.")
    last = specs[-1]["expected_answer"]
    if last != quantities[template.ask]:
        raise ValueError("Last step is not the asked quantity.")
    if last != problem.final_answer:
        raise ValueError("Last step does not match the final answer.")
    answers = [spec["expected_answer"] for spec in specs]
    if any(
        not isinstance(value, int) or isinstance(value, bool)
        for value in answers
    ):
        raise ValueError("Step answers must be integers.")
    if len(answers) != len(set(answers)):
        raise ValueError("Step answers must be unique.")
    if template.family == FAMILY_REVERSE:
        expected = [quantities[template.identify_known]]
        known_now = {
            name: quantities[name]
            for name in template.statement_ids
        }
        for relation in reversed(template.relations):
            unknown, recovered = _undo(relation, known_now)
            known_now[unknown] = recovered
            expected.append(recovered)
        if answers != expected:
            raise ValueError("Reverse steps are not the undo order.")
        if expected[-1] != quantities[template.ask]:
            raise ValueError("Reverse plan does not answer the story.")
    else:
        expected = [quantities[template.identify_known]]
        expected.extend(
            quantities[relation.output]
            for relation in template.relations
        )
        if answers != expected:
            raise ValueError("Forward steps are not dependency order.")
    _verify_hint_params(specs, quantities[template.ask], answers)


def _verify_hint_params(
    specs: list[dict],
    final_answer: int,
    answers: list[int],
) -> None:
    for index, spec in enumerate(specs):
        params = spec.get("params") or {}
        if final_answer in params.values():
            raise ValueError("Hint params include the final answer.")
        future = set(answers[index + 1 :])
        if future.intersection(params.values()):
            raise ValueError("Hint params include a future answer.")


def _verify_semantics(
    problem: PrimarySchoolProblem,
    template: StoryTemplate,
    quantities: dict[str, int],
) -> None:
    statement = problem.problem_text or ""
    if statement:
        visible = [
            quantities[name]
            for name in template.statement_ids
        ]
        found = {
            int(match)
            for match in re.findall(r"\d+", statement)
        }
        if found != set(visible):
            raise ValueError(
                "Statement numbers do not match the model."
            )
        lowered = statement.lower()
        if "twice as many as remained were put in" in lowered:
            raise ValueError("Ambiguous doubling wording is forbidden.")


def _undo(relation, known_now: dict[str, int]):
    from src.core.tutor_engine.primary_school.generation.word_problems.relations import (
        undo_relation,
    )

    return undo_relation(relation, known_now)
