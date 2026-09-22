"""Compile verified logical-reasoning puzzles into tutoring steps.

Step-selection rules
--------------------
A verified blueprint is not copied 1:1 into student questions.
Internal calculations may stay in the blueprint.

Shared rules:
- Ask only uniquely determined integers.
- Uniqueness is tested from public clues, domain rules, and
  previously asked student answers — never by copying a private
  intended value onto an ambiguous question.
- Do not ask students to repeat a number stated as a clue.
- Do not ask for a coefficient of 1.
- Do not reveal a later expected answer in an earlier prompt.
- Skip a candidate question when its answer is not unique, or
  when it duplicates an earlier student question.

Number Detective:
- Difficulty 1 (digit sum and digit difference): ask units, then
  tens, then the two-digit number. Those digits are uniquely
  determined by the two public clues together.
- Difficulty 2 and 3: ask an intermediate digit only when a
  proper prefix of the clues already forces that digit. Otherwise
  ask the secret number directly.
- Never ask for the digit-sum or digit-difference values.

Distribution puzzles:
- Walk the verified arithmetic blueprint in dependency order.
- Skip counting two shares from 1+1 (coefficient 1).
- Keep remaining-total, combined-extra, scaled-extra, share
  counts of 3 or more, exact division, and reconstructed boxes.
- Every student-visible operation is recomputed from the
  blueprint operands; a competing algebraic solution is not built.

Logic Detective:
- Skip copying a given PlacedAt clue.
- Ask inferred placements (only remaining position/object).
- Preserve deduction order, then place the target object last.
- Student questions are box numbers, not object names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Iterable

from src.core.i18n.locale import normalize_locale
from src.core.tutor_engine.primary_school.generation.builder import (
    build_problem_from_specs,
    integer_step,
)
from src.core.tutor_engine.primary_school.generation.localize import (
    localize_generated_primary_school,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.distribution_puzzles import (
    UNIT_NAME,
    DistributionPuzzle,
    _apply_operation,
    verify_blueprint as verify_distribution_blueprint,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.logic_detective import (
    LogicDetectivePuzzle,
    verify_blueprint as verify_logic_blueprint,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.number_detective import (
    NumberDetectivePuzzle,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    DistMoreThan,
    DistTimes,
    DistTotal,
    FAMILY_DISTRIBUTION,
    FAMILY_LOGIC_DETECTIVE,
    FAMILY_NUMBER_DETECTIVE,
    LogicalPuzzleSpec,
    LogicalReasoningVerificationError,
    NumberDomain,
    PlacedAt,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.verify import (
    satisfying_candidates,
    verify_unique_solution,
)
from src.core.tutor_engine.primary_school.problem_types import (
    PrimarySchoolProblem,
    ProblemType,
    SolutionStepType,
)


TOPIC_LOGICAL_REASONING = "logical_reasoning"
SKILL_LOGICAL_REASONING = "grade4_logical_reasoning"
PUBLIC_KNOWN_KEYS = frozenset(
    {
        "family",
        "difficulty",
        "statement_parts",
        "public_clues",
        "clue_kinds",
        "visible_numbers",
        "domain",
        "target_object",
        "template_id",
        "ask_key",
    }
)
PUBLIC_METADATA_KEYS = frozenset(
    {
        "family",
        "difficulty",
        "generated",
        "answer_format",
    }
)
PUBLIC_STEP_METADATA_KEYS = frozenset(
    {
        "prompt_key",
        "hint_key",
        "params",
        "milestone",
        "purpose",
        "family",
    }
)
_INFER_KINDS = frozenset(
    {
        "only_remaining_position",
        "only_remaining_object",
    }
)
_PURPOSE_MILESTONE = {
    "remove_extra": "remaining_total",
    "remove_chain_extras": "remaining_total",
    "count_shares": "share_count",
    "reference_quantity": "box_quantity",
    "shared_reference": "box_quantity",
    "chain_base": "box_quantity",
    "scaled_quantity": "box_quantity",
    "apply_extra": "box_quantity",
    "chain_middle": "box_quantity",
    "propagate_extra": "extra_from_scaled",
    "combine_extras": "extra_total",
}
_TOKEN_RE = re.compile(r"\b\d+\b")
_CLAIM_RE = re.compile(
    r"(?:=|\bis\b|\bequals\b|(?<![A-Za-zА-Яа-я])е)\s+(\d+)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CompiledMilestone:
    milestone: str
    purpose: str
    expected: int
    prompt_key: str
    params: dict[str, Any]
    depends_on: tuple[str, ...]


def compile_logical_reasoning_puzzle(
    puzzle,
    language: str = "en",
) -> PrimarySchoolProblem:
    """Turn a verified puzzle into a PrimarySchoolProblem."""
    milestones = compile_milestones(puzzle)
    problem = _problem_from_milestones(puzzle, milestones)
    _validate_compiled_problem(problem, puzzle)
    return localize_generated_primary_school(
        problem,
        normalize_locale(language),
    )


def compile_milestones(puzzle) -> tuple[CompiledMilestone, ...]:
    _revalidate_puzzle(puzzle)
    if isinstance(puzzle, NumberDetectivePuzzle):
        milestones = _number_milestones(puzzle)
    elif isinstance(puzzle, DistributionPuzzle):
        milestones = _distribution_milestones(puzzle)
    elif isinstance(puzzle, LogicDetectivePuzzle):
        milestones = _logic_milestones(puzzle)
    else:
        raise LogicalReasoningVerificationError(
            "unsupported_family",
            "Unsupported logical-reasoning puzzle type.",
        )
    if not milestones:
        raise LogicalReasoningVerificationError(
            "compilation_failed",
            "Compiler produced no tutoring steps.",
        )
    _reject_duplicate_questions(milestones)
    return tuple(milestones)


def unique_extracted_value(
    values: Iterable[int],
) -> int | None:
    found = set()
    for value in values:
        if not isinstance(value, int) or isinstance(value, bool):
            raise LogicalReasoningVerificationError(
                "ambiguous_step",
                "Candidate value is not an integer.",
            )
        found.add(value)
        if len(found) > 1:
            return None
    if len(found) != 1:
        return None
    return next(iter(found))


def integer_tokens(text: str) -> tuple[int, ...]:
    return tuple(int(token) for token in _TOKEN_RE.findall(text or ""))


def discloses_protected(
    text: str,
    protected: Iterable[int],
    visible: Iterable[int],
) -> bool:
    """True when text states a protected result, not merely a clue number."""
    protected_set = {
        int(value)
        for value in protected
        if isinstance(value, int) and not isinstance(value, bool)
    }
    visible_set = {
        int(value)
        for value in visible
        if isinstance(value, int) and not isinstance(value, bool)
    }
    if not text or not protected_set:
        return False
    for match in _CLAIM_RE.finditer(text):
        claimed = int(match.group(1))
        if claimed in protected_set and claimed not in visible_set:
            return True
    for token in integer_tokens(text):
        if token in protected_set and token not in visible_set:
            return True
    return False


def public_exercise_view(
    problem: PrimarySchoolProblem,
    *,
    current_step: int | None = None,
) -> dict[str, Any]:
    known = problem.known or {}
    extra_known = set(known) - PUBLIC_KNOWN_KEYS
    if extra_known:
        raise LogicalReasoningVerificationError(
            "private_leak",
            "Public known has extra fields: "
            + ", ".join(sorted(extra_known)),
        )
    metadata = {
        key: value
        for key, value in (problem.metadata or {}).items()
        if key in PUBLIC_METADATA_KEYS
    }
    step = None
    if current_step is None:
        if problem.solution_steps:
            step = problem.solution_steps[0]
    else:
        step = problem.get_step(current_step)
    step_meta = {}
    prompt = ""
    if step is not None:
        prompt = step.prompt
        step_meta = {
            key: value
            for key, value in (step.metadata or {}).items()
            if key in PUBLIC_STEP_METADATA_KEYS
        }
    return {
        "family": known.get("family"),
        "difficulty": known.get("difficulty"),
        "visible_statement": problem.problem_text,
        "visible_clues": list(known.get("public_clues") or ()),
        "current_question": prompt,
        "title": problem.title,
        "language": problem.language,
        "domain": known.get("domain"),
        "target_object": known.get("target_object"),
        "metadata": metadata,
        "step_metadata": step_meta,
    }


def protected_answers_from(
    problem: PrimarySchoolProblem,
    current_step: int,
) -> tuple[int, ...]:
    values = []
    for step in problem.solution_steps:
        if step.step_number < current_step:
            continue
        if isinstance(step.expected_answer, int) and not isinstance(
            step.expected_answer,
            bool,
        ):
            values.append(int(step.expected_answer))
    return tuple(values)


def _revalidate_puzzle(puzzle) -> None:
    verify_unique_solution(puzzle.spec, puzzle.intended)
    if isinstance(puzzle, DistributionPuzzle):
        verify_distribution_blueprint(
            puzzle.blueprint,
            puzzle.spec,
            puzzle.intended,
        )
    elif isinstance(puzzle, LogicDetectivePuzzle):
        verify_logic_blueprint(
            puzzle.blueprint,
            puzzle.spec,
            puzzle.intended,
        )
    puzzle.public_view()


def _number_milestones(
    puzzle: NumberDetectivePuzzle,
) -> list[CompiledMilestone]:
    constraints = puzzle.spec.constraints
    kinds = tuple(item.kind for item in constraints)
    all_candidates = satisfying_candidates(puzzle.spec)
    number = unique_extracted_value(
        candidate.value for candidate in all_candidates
    )
    if number is None:
        raise LogicalReasoningVerificationError(
            "ambiguous_step",
            "The secret number is not uniquely determined.",
        )
    milestones: list[CompiledMilestone] = []
    if "digit_sum" in kinds and "digit_diff" in kinds:
        units = unique_extracted_value(
            candidate.units for candidate in all_candidates
        )
        tens = unique_extracted_value(
            candidate.tens for candidate in all_candidates
        )
        if units is None or tens is None:
            raise LogicalReasoningVerificationError(
                "ambiguous_step",
                "Digit-sum and digit-difference do not force both digits.",
            )
        if number != 10 * tens + units:
            raise LogicalReasoningVerificationError(
                "compilation_failed",
                "Reconstructed number does not match the unique value.",
            )
        milestones.append(
            CompiledMilestone(
                "units",
                "infer_units",
                units,
                "gen.logic.prompt.units",
                {},
                ("clues",),
            )
        )
        milestones.append(
            CompiledMilestone(
                "tens",
                "infer_tens",
                tens,
                "gen.logic.prompt.tens",
                {},
                ("clues", "units"),
            )
        )
        milestones.append(
            CompiledMilestone(
                "number",
                "construct_number",
                number,
                "gen.logic.prompt.number",
                {},
                ("clues", "units", "tens"),
            )
        )
        return milestones

    seen = set()
    for end in range(1, len(constraints)):
        prefix_spec = LogicalPuzzleSpec(
            family=FAMILY_NUMBER_DETECTIVE,
            domain=NumberDomain(),
            constraints=constraints[:end],
        )
        prefix = satisfying_candidates(prefix_spec)
        tens = unique_extracted_value(candidate.tens for candidate in prefix)
        units = unique_extracted_value(candidate.units for candidate in prefix)
        if tens is not None and "tens" not in seen and tens != number:
            milestones.append(
                CompiledMilestone(
                    "tens",
                    "infer_tens",
                    tens,
                    "gen.logic.prompt.tens",
                    {},
                    ("prefix_clues",),
                )
            )
            seen.add("tens")
        if units is not None and "units" not in seen and units != number:
            milestones.append(
                CompiledMilestone(
                    "units",
                    "infer_units",
                    units,
                    "gen.logic.prompt.units",
                    {},
                    ("prefix_clues",),
                )
            )
            seen.add("units")
    milestones.append(
        CompiledMilestone(
            "number",
            "construct_number",
            number,
            "gen.logic.prompt.number",
            {},
            ("clues",),
        )
    )
    return milestones


def _distribution_milestones(
    puzzle: DistributionPuzzle,
) -> list[CompiledMilestone]:
    known = _distribution_public_known(puzzle.spec)
    produced: dict[str, int] = {}
    milestones: list[CompiledMilestone] = []
    asked_expected: list[int] = []
    kept_steps: list = []
    for step in puzzle.blueprint.steps:
        try:
            operands = tuple(known[name] for name in step.uses)
        except KeyError as error:
            raise LogicalReasoningVerificationError(
                "invalid_blueprint",
                f"Student step is missing operand {error}.",
            ) from error
        result = _apply_operation(step.operation, operands)
        if result != step.result:
            raise LogicalReasoningVerificationError(
                "compilation_failed",
                "Blueprint result does not match public recomputation.",
            )
        known[step.produces] = result
        if _skip_distribution_step(step, known):
            continue
        determined = result
        box = _box_from_produces(step.produces)
        if box is not None:
            unique_qty = unique_extracted_value(
                candidate.get(box)
                for candidate in satisfying_candidates(puzzle.spec)
            )
            if unique_qty is None:
                raise LogicalReasoningVerificationError(
                    "ambiguous_step",
                    f"Quantity {box} is not uniquely determined.",
                )
            if unique_qty != determined:
                raise LogicalReasoningVerificationError(
                    "compilation_failed",
                    f"Blueprint quantity {box} is not the unique value.",
                )
        milestone = _PURPOSE_MILESTONE.get(step.purpose)
        if milestone is None:
            raise LogicalReasoningVerificationError(
                "compilation_failed",
                f"Unsupported distribution purpose {step.purpose}.",
            )
        params = _distribution_prompt_params(puzzle, milestone, box)
        prompt_key = (
            "gen.logic.prompt.box_quantity"
            if milestone == "box_quantity"
            else f"gen.logic.prompt.{milestone}"
        )
        produced[step.produces] = determined
        asked_expected.append(determined)
        milestones.append(
            CompiledMilestone(
                milestone,
                step.purpose,
                determined,
                prompt_key,
                params,
                tuple(step.uses),
            )
            )
        kept_steps.append(step)
    _fill_distribution_setups(puzzle, milestones, kept_steps)
    if not any(
        milestone.milestone == "box_quantity" for milestone in milestones
    ):
        raise LogicalReasoningVerificationError(
            "compilation_failed",
            "Distribution tutoring omitted reconstructed quantities.",
        )
    return milestones


def _skip_distribution_step(step, known: dict[str, int]) -> bool:
    if step.purpose == "count_shares" and step.result == 2:
        return all(
            name == UNIT_NAME or known.get(name) == 1
            for name in step.uses
        )
    if all(name == UNIT_NAME for name in step.uses) and step.result == 1:
        return True
    return False


def _distribution_public_known(spec: LogicalPuzzleSpec) -> dict[str, int]:
    known = {UNIT_NAME: 1}
    for constraint in spec.constraints:
        if isinstance(constraint, DistTotal):
            known["clue.total"] = constraint.total
        elif isinstance(constraint, DistTimes):
            known["clue.factor"] = constraint.factor
        elif isinstance(constraint, DistMoreThan):
            known["clue.extra"] = constraint.extra
        else:
            raise LogicalReasoningVerificationError(
                "invalid_constraint",
                "Distribution compiler met an unsupported clue.",
            )
    return known


def _distribution_prompt_params(puzzle, milestone: str, box: str | None):
    params: dict[str, Any] = {}
    known = _distribution_public_known(puzzle.spec)
    if "clue.total" in known:
        params["total"] = known["clue.total"]
    if "clue.extra" in known:
        params["extra"] = known["clue.extra"]
    if "clue.factor" in known:
        params["factor"] = known["clue.factor"]
    for constraint in puzzle.spec.constraints:
        if isinstance(constraint, DistTimes):
            params["left"] = constraint.left
            params["right"] = constraint.right
            params["factor"] = constraint.factor
        elif isinstance(constraint, DistMoreThan):
            params["extra_left"] = constraint.left
            params["extra_right"] = constraint.right
            params["extra"] = constraint.extra
    if box:
        params["box"] = box
    return params


def _fill_distribution_setups(puzzle, milestones, kept_steps) -> None:
    visible = set(_distribution_public_known(puzzle.spec).values())
    visible.discard(True)
    visible.discard(False)
    for index, (milestone, step) in enumerate(zip(milestones, kept_steps)):
        known = _distribution_public_known(puzzle.spec)
        for previous, previous_step in zip(
            milestones[:index],
            kept_steps[:index],
        ):
            known[previous_step.produces] = previous.expected
        protected = {item.expected for item in milestones[index:]}
        parts = [
            _operand_part(name, known, protected, visible)
            for name in step.uses
        ]
        milestone.params["setup_op"] = step.operation
        milestone.params["setup_parts"] = tuple(parts)
        milestone.params["setup"] = format_setup_expression(
            step.operation,
            parts,
            "en",
        )


def format_setup_expression(operation, parts, language: str | None = "en") -> str:
    from src.core.i18n.logical_reasoning import lrt

    tokens = []
    for part in parts:
        if isinstance(part, int) and not isinstance(part, bool):
            tokens.append(str(part))
        else:
            tokens.append(lrt(language, f"gen.logic.setup.{part}"))
    if operation == "addition":
        expression = " + ".join(tokens)
    elif operation == "subtraction" and len(tokens) == 2:
        expression = f"{tokens[0]} - {tokens[1]}"
    elif operation == "multiplication" and len(tokens) == 2:
        expression = f"{tokens[0]} × {tokens[1]}"
    elif operation == "exact_division" and len(tokens) == 2:
        expression = f"{tokens[0]} ÷ {tokens[1]}"
    else:
        expression = " ".join(tokens)
    return f"{expression} = ?"


def _operand_part(name, known, protected, visible):
    labels = {
        UNIT_NAME: 1,
        "clue.factor": "factor",
        "clue.extra": "extra",
        "clue.total": "total",
        "extra_from_scaled": "scaled_extra",
        "extra_total": "combined_extra",
        "remaining_total": "remaining_total",
        "share_count": "share_count",
    }
    if name == UNIT_NAME:
        return 1
    if name.startswith("qty."):
        labels[name] = "that_box"
    value = known.get(name)
    if not isinstance(value, int) or isinstance(value, bool):
        return labels.get(name, "known_amount")
    if name.startswith("clue.") or value in visible:
        return value
    if value in protected:
        return labels.get(name, "known_amount")
    return value


def _box_from_produces(produces: str) -> str | None:
    if produces.startswith("qty."):
        return produces.split(".", 1)[1]
    return None


def _logic_milestones(
    puzzle: LogicDetectivePuzzle,
) -> list[CompiledMilestone]:
    candidates = list(satisfying_candidates(puzzle.spec))
    if len(candidates) != 1:
        raise LogicalReasoningVerificationError(
            "ambiguous_step",
            "Logic Detective clues do not leave one assignment.",
        )
    inferred: list[tuple[str, int]] = []
    seen = set()
    placed = {
        constraint.item
        for constraint in puzzle.spec.constraints
        if isinstance(constraint, PlacedAt)
    }
    for step in puzzle.blueprint.steps:
        if step.kind not in _INFER_KINDS:
            continue
        if step.item in placed or step.item in seen:
            continue
        if len(step.after_positions) != 1:
            continue
        remaining = unique_extracted_value(
            candidate.position_of(step.item)
            for candidate in _with_placements(candidates, dict(inferred))
        )
        if remaining is None:
            raise LogicalReasoningVerificationError(
                "ambiguous_step",
                f"Position of {step.item} is not uniquely determined.",
            )
        if remaining != step.position:
            raise LogicalReasoningVerificationError(
                "compilation_failed",
                "Inferred position does not match the unique remaining value.",
            )
        inferred.append((step.item, remaining))
        seen.add(step.item)

    if puzzle.target_object not in seen:
        raise LogicalReasoningVerificationError(
            "compilation_failed",
            "Tutoring steps never ask for the target object.",
        )
    ordered = [
        item for item in inferred if item[0] != puzzle.target_object
    ]
    ordered.extend(
        item for item in inferred if item[0] == puzzle.target_object
    )
    established: dict[str, int] = {}
    milestones = []
    depends = ["clues"]
    for item, position in ordered:
        remaining = unique_extracted_value(
            candidate.position_of(item)
            for candidate in _with_placements(candidates, established)
        )
        if remaining is None:
            raise LogicalReasoningVerificationError(
                "ambiguous_step",
                f"Position of {item} is ambiguous before it is asked.",
            )
        if remaining != position:
            raise LogicalReasoningVerificationError(
                "compilation_failed",
                "Reordered Logic Detective step is not unique.",
            )
        milestones.append(
            CompiledMilestone(
                "infer_position",
                "infer_position",
                remaining,
                "gen.logic.prompt.infer_position",
                {"item": item},
                tuple(depends),
            )
        )
        established[item] = remaining
        depends = [*depends, f"pos.{item}"]
    if milestones[-1].params["item"] != puzzle.target_object:
        raise LogicalReasoningVerificationError(
            "compilation_failed",
            "The last Logic Detective question is not the target object.",
        )
    return milestones


def _with_placements(candidates, established: dict[str, int]):
    if not established:
        return candidates
    remaining = []
    for candidate in candidates:
        if all(
            candidate.position_of(item) == position
            for item, position in established.items()
        ):
            remaining.append(candidate)
    return remaining


def _reject_duplicate_questions(
    milestones: list[CompiledMilestone],
) -> None:
    seen = set()
    for item in milestones:
        key = (
            item.prompt_key,
            tuple(sorted(item.params.items())),
            item.expected,
        )
        if key in seen:
            raise LogicalReasoningVerificationError(
                "compilation_failed",
                "Compiler produced a duplicate tutoring question.",
            )
        seen.add(key)


def _problem_from_milestones(
    puzzle,
    milestones: tuple[CompiledMilestone, ...],
) -> PrimarySchoolProblem:
    family = puzzle.family
    public = puzzle.public_view()
    statement_parts = _statement_parts(puzzle, public)
    visible_numbers = _visible_numbers(public)
    step_specs = []
    for index, item in enumerate(milestones, start=1):
        params = dict(item.params)
        step_specs.append(
            integer_step(
                step_number=index,
                skill_id=SKILL_LOGICAL_REASONING,
                expected_answer=item.expected,
                prompt_key=item.prompt_key,
                hint_key=f"gen.logic.hint.{item.milestone}.1",
                params=params,
                step_type=SolutionStepType.REASONING,
            )
        )
        step_specs[-1]["milestone"] = item.milestone
        step_specs[-1]["purpose"] = item.purpose
        step_specs[-1]["family"] = family

    known = {
        "family": family,
        "difficulty": puzzle.difficulty,
        "statement_parts": statement_parts,
        "public_clues": [dict(clue) for clue in public["clues"]],
        "clue_kinds": [clue["kind"] for clue in public["clues"]],
        "visible_numbers": sorted(visible_numbers),
        "domain": dict(public["domain"]),
        "ask_key": statement_parts[-1]["key"],
    }
    if family == FAMILY_LOGIC_DETECTIVE:
        known["target_object"] = puzzle.target_object
    template_id = getattr(getattr(puzzle, "blueprint", None), "template_id", None)
    if template_id:
        known["template_id"] = template_id
    extra = set(known) - PUBLIC_KNOWN_KEYS
    if extra:
        raise LogicalReasoningVerificationError(
            "private_leak",
            "Compiler known has extra fields: " + ", ".join(sorted(extra)),
        )

    problem = build_problem_from_specs(
        problem_id="grade4_logical_reasoning",
        grade=4,
        topic=TOPIC_LOGICAL_REASONING,
        problem_type=ProblemType.LOGICAL_REASONING,
        language="en",
        skills=[SKILL_LOGICAL_REASONING],
        known=known,
        unknown=_unknown_payload(puzzle, milestones),
        strategy="logical_deduction",
        final_answer=milestones[-1].expected,
        step_specs=step_specs,
        metadata={
            "family": family,
            "difficulty": puzzle.difficulty,
        },
    )
    steps = []
    for spec, step in zip(step_specs, problem.solution_steps):
        meta = dict(step.metadata or {})
        meta["milestone"] = spec["milestone"]
        meta["purpose"] = spec["purpose"]
        meta["family"] = spec["family"]
        extra_meta = set(meta) - PUBLIC_STEP_METADATA_KEYS
        if extra_meta:
            raise LogicalReasoningVerificationError(
                "private_leak",
                "Step metadata has extra fields: "
                + ", ".join(sorted(extra_meta)),
            )
        steps.append(replace(step, metadata=meta))
    problem.solution_steps = steps
    return problem


def _unknown_payload(puzzle, milestones: tuple[CompiledMilestone, ...]):
    last = milestones[-1]
    payload = {
        "name": last.milestone,
        "milestone": last.milestone,
    }
    if isinstance(puzzle, LogicDetectivePuzzle):
        payload["target_object"] = puzzle.target_object
    return payload


def _statement_parts(puzzle, public: dict) -> list[dict[str, Any]]:
    parts = [
        _clue_statement_part(clue, public)
        for clue in public["clues"]
    ]
    if puzzle.family == FAMILY_NUMBER_DETECTIVE:
        parts.append({"key": "gen.logic.number.ask", "params": {}})
    elif puzzle.family == FAMILY_DISTRIBUTION:
        parts.append({"key": "gen.logic.distribution.ask", "params": {}})
    else:
        parts.append(
            {
                "key": "gen.logic.logic.ask",
                "params": {"item": puzzle.target_object},
            }
        )
    return parts


def _clue_statement_part(clue: dict, public: dict) -> dict[str, Any]:
    kind = clue["kind"]
    if kind == "digit_sum":
        return {
            "key": "gen.logic.clue.digit_sum",
            "params": {"total": clue["total"]},
        }
    if kind == "digit_diff":
        comparison = clue["comparison"]
        suffix = {
            "tens_greater": "tens_greater",
            "units_greater": "units_greater",
            "equal": "equal",
        }[comparison]
        return {
            "key": f"gen.logic.clue.digit_diff.{suffix}",
            "params": {
                "absolute_amount": clue["absolute_amount"],
                "amount": clue["amount"],
            },
        }
    if kind == "digit_order":
        return {
            "key": f"gen.logic.clue.digit_order.{clue['relation']}",
            "params": {},
        }
    if kind == "parity":
        suffix = "even" if clue["even"] else "odd"
        return {"key": f"gen.logic.clue.parity.{suffix}", "params": {}}
    if kind == "divisible_by":
        return {
            "key": "gen.logic.clue.divisible_by",
            "params": {"divisor": clue["divisor"]},
        }
    if kind == "in_interval":
        return {
            "key": "gen.logic.clue.in_interval",
            "params": {"low": clue["low"], "high": clue["high"]},
        }
    if kind == "total":
        count = "three" if len(public["domain"]["names"]) == 3 else "two"
        return {
            "key": f"gen.logic.clue.total.{count}",
            "params": {"total": clue["total"]},
        }
    if kind == "times_as_many":
        return {
            "key": "gen.logic.clue.times_as_many",
            "params": {
                "factor": clue["factor"],
                "left": clue["left"],
                "right": clue["right"],
            },
        }
    if kind == "more_than":
        return {
            "key": "gen.logic.clue.more_than",
            "params": {
                "extra": clue["extra"],
                "left": clue["left"],
                "right": clue["right"],
            },
        }
    if kind == "placed_at":
        return {
            "key": "gen.logic.clue.placed_at",
            "params": {
                "item": clue["item"],
                "position": clue["position"],
            },
        }
    if kind == "not_placed_at":
        return {
            "key": "gen.logic.clue.not_placed_at",
            "params": {
                "item": clue["item"],
                "position": clue["position"],
            },
        }
    raise LogicalReasoningVerificationError(
        "invalid_constraint",
        f"Cannot render clue kind {kind}.",
    )


def _visible_numbers(public: dict) -> set[int]:
    values = set()

    def walk(node):
        if isinstance(node, bool):
            return
        if isinstance(node, int):
            values.add(node)
            return
        if isinstance(node, dict):
            for item in node.values():
                walk(item)
            return
        if isinstance(node, (list, tuple)):
            for item in node:
                walk(item)

    walk(public.get("clues") or ())
    return values


def _validate_compiled_problem(problem, puzzle) -> None:
    if problem.topic != TOPIC_LOGICAL_REASONING:
        raise LogicalReasoningVerificationError(
            "compilation_failed",
            "Compiled topic is not logical_reasoning.",
        )
    if not problem.solution_steps:
        raise LogicalReasoningVerificationError(
            "compilation_failed",
            "Compiled problem has no steps.",
        )
    answers = [
        step.expected_answer for step in problem.solution_steps
    ]
    if any(
        not isinstance(value, int) or isinstance(value, bool)
        for value in answers
    ):
        raise LogicalReasoningVerificationError(
            "compilation_failed",
            "A compiled step is not an integer.",
        )
    if answers[-1] != problem.final_answer:
        raise LogicalReasoningVerificationError(
            "compilation_failed",
            "Final answer does not match the last tutoring step.",
        )
    if isinstance(puzzle, NumberDetectivePuzzle):
        if answers[-1] != puzzle.intended.value:
            raise LogicalReasoningVerificationError(
                "compilation_failed",
                "Number Detective final step is not the unique number.",
            )
    if isinstance(puzzle, LogicDetectivePuzzle):
        if answers[-1] != puzzle.target_position:
            raise LogicalReasoningVerificationError(
                "compilation_failed",
                "Logic Detective final step is not the target position.",
            )
        last_item = (problem.solution_steps[-1].metadata or {}).get("params", {}).get("item")
        if last_item != puzzle.target_object:
            raise LogicalReasoningVerificationError(
                "compilation_failed",
                "Last question is not about the target object.",
            )
    visible = set(problem.known.get("visible_numbers") or ())
    from src.core.i18n.primary_school import pst

    for step in problem.solution_steps:
        protected = protected_answers_from(problem, step.step_number)
        params = dict((step.metadata or {}).get("params") or {})
        _enrich_render_params(params, "en")
        prompt = pst("en", (step.metadata or {}).get("prompt_key"), **params)
        if discloses_protected(prompt, protected, visible):
            raise LogicalReasoningVerificationError(
                "private_leak",
                f"Prompt for step {step.step_number} discloses an answer.",
            )
        milestone = (step.metadata or {}).get("milestone")
        rendered = []
        for level in (1, 2, 3):
            hint = pst(
                "en",
                f"gen.logic.hint.{milestone}.{level}",
                **params,
            )
            rendered.append(hint)
            if discloses_protected(hint, protected, visible):
                raise LogicalReasoningVerificationError(
                    "private_leak",
                    f"Hint {level} for step {step.step_number} discloses "
                    "a protected answer.",
                )
        if len(set(rendered)) < 3:
            raise LogicalReasoningVerificationError(
                "duplicate_hints",
                f"Hints for step {step.step_number} are not all distinct.",
            )


def _enrich_render_params(params: dict[str, Any], locale: str) -> None:
    from src.core.i18n.primary_school import pst

    item = params.get("item")
    if item:
        params["item_name"] = pst(locale, f"gen.logic.object.{item}")
    box = params.get("box")
    if box:
        params["box_name"] = pst(locale, f"gen.logic.box.{box}")
    left = params.get("left")
    if left:
        params["left_name"] = pst(locale, f"gen.logic.box.{left}")
    right = params.get("right")
    if right:
        params["right_name"] = pst(locale, f"gen.logic.box.{right}")
    extra_left = params.get("extra_left")
    if extra_left:
        params["extra_left_name"] = pst(
            locale,
            f"gen.logic.box.{extra_left}",
        )
    extra_right = params.get("extra_right")
    if extra_right:
        params["extra_right_name"] = pst(
            locale,
            f"gen.logic.box.{extra_right}",
        )
    factor = params.get("factor")
    if isinstance(factor, int) and not isinstance(factor, bool):
        key = f"gen.logic.factor_word.{factor}"
        word = pst(locale, key)
        params["factor_word"] = str(factor) if word == key else word
