import json
import time

from src.core.question_engine.context import sanitize_tutor_metadata
from src.core.tutor_engine.contracts import StudentSubmission
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning import (
    FAMILY_DISTRIBUTION,
    FAMILY_LOGIC_DETECTIVE,
    FAMILY_NUMBER_DETECTIVE,
    PRIVATE_PUZZLE_FIELDS,
    generate_distribution_puzzle,
    generate_logic_detective,
    generate_number_detective,
    satisfying_candidates,
    verify_unique_solution,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.compile import (
    compile_logical_reasoning_puzzle,
    compile_milestones,
    discloses_protected,
    protected_answers_from,
    public_exercise_view,
    unique_extracted_value,
    _with_placements,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.distribution_puzzles import (
    verify_blueprint as verify_distribution_blueprint,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.families.logic_detective import (
    verify_blueprint as verify_logic_blueprint,
)
from src.core.tutor_engine.primary_school.problem_types import ProblemType


GENERATORS = {
    FAMILY_NUMBER_DETECTIVE: generate_number_detective,
    FAMILY_DISTRIBUTION: generate_distribution_puzzle,
    FAMILY_LOGIC_DETECTIVE: generate_logic_detective,
}
SWEEP_PER_DIFFICULTY = 30
PRIVATE_MARKERS = (
    "intended",
    "blueprint",
    "elimination",
    "satisfying",
    "candidates",
    "expected_answer",
    "hidden_steps",
    "target_position",
    "assignment",
)


def _live(step_number):
    return type("Live", (), {"current_step": step_number})()


def assert_unique_intermediates(puzzle, problem):
    family = puzzle.family
    if family == FAMILY_NUMBER_DETECTIVE:
        candidates = satisfying_candidates(puzzle.spec)
        for step in problem.solution_steps:
            milestone = (step.metadata or {}).get("milestone")
            if milestone == "units":
                unique = unique_extracted_value(
                    candidate.units for candidate in candidates
                )
            elif milestone == "tens":
                unique = unique_extracted_value(
                    candidate.tens for candidate in candidates
                )
            else:
                unique = unique_extracted_value(
                    candidate.value for candidate in candidates
                )
            assert unique is not None, milestone
            assert unique == step.expected_answer
        return
    if family == FAMILY_DISTRIBUTION:
        candidates = satisfying_candidates(puzzle.spec)
        for step in problem.solution_steps:
            box = ((step.metadata or {}).get("params") or {}).get("box")
            if box:
                unique = unique_extracted_value(
                    candidate.get(box) for candidate in candidates
                )
                assert unique is not None, box
                assert unique == step.expected_answer
        return
    candidates = list(satisfying_candidates(puzzle.spec))
    established = {}
    for step in problem.solution_steps:
        item = ((step.metadata or {}).get("params") or {}).get("item")
        unique = unique_extracted_value(
            candidate.position_of(item)
            for candidate in _with_placements(candidates, established)
        )
        assert unique is not None, item
        assert unique == step.expected_answer
        established[item] = unique


def assert_no_private_payload(problem, extra_text=""):
    view = public_exercise_view(problem)
    dumped = json.dumps(view, default=str) + extra_text
    for marker in PRIVATE_MARKERS:
        assert marker not in dumped, marker
    for field in PRIVATE_PUZZLE_FIELDS:
        assert field not in (problem.known or {})
    answers = [
        step.expected_answer for step in problem.solution_steps
    ]
    dumped_view = json.dumps(view, default=str)
    for answer in answers:
        if answer not in set(problem.known.get("visible_numbers") or ()):
            assert (
                f'"{answer}"' not in dumped_view
                and f": {answer}" not in dumped_view
            ) or "current_question" in view


def assert_problem_compiles(puzzle, language="en"):
    verify_unique_solution(puzzle.spec, puzzle.intended)
    if puzzle.family == FAMILY_DISTRIBUTION:
        verify_distribution_blueprint(
            puzzle.blueprint,
            puzzle.spec,
            puzzle.intended,
        )
    if puzzle.family == FAMILY_LOGIC_DETECTIVE:
        verify_logic_blueprint(
            puzzle.blueprint,
            puzzle.spec,
            puzzle.intended,
        )
    problem = compile_logical_reasoning_puzzle(puzzle, language)
    assert problem.topic == "logical_reasoning"
    assert problem.problem_type == ProblemType.LOGICAL_REASONING
    assert problem.language == language
    assert problem.solution_steps
    answers = [step.expected_answer for step in problem.solution_steps]
    assert all(isinstance(value, int) and not isinstance(value, bool) for value in answers)
    assert answers[-1] == problem.final_answer
    prompts = [step.prompt for step in problem.solution_steps]
    assert all(prompts)
    assert len(set(prompts)) == len(prompts)
    assert "{" not in problem.problem_text
    assert_unique_intermediates(puzzle, problem)
    visible = set(problem.known.get("visible_numbers") or ())
    for step in problem.solution_steps:
        protected = protected_answers_from(problem, step.step_number)
        assert not discloses_protected(step.prompt, protected, visible)
        engine = PrimarySchoolTutorEngine(problem)
        while engine.session.current_step_index < step.step_number - 1:
            current = engine.session.get_current_step()
            engine.submit(StudentSubmission(str(current.expected_answer)))
        hints = []
        for _ in range(3):
            hint = engine.request_hint()
            assert not discloses_protected(
                hint.feedback,
                protected,
                visible,
            )
            hints.append(hint.feedback)
        bodies = [
            text.replace(
                "This is the last hint for this step.",
                "",
            ).strip()
            for text in hints
        ]
        assert len(set(bodies)) == 3, (
            step.step_number,
            (step.metadata or {}).get("milestone"),
            bodies,
        )
    return problem


def simulate_exercise(problem):
    engine = PrimarySchoolTutorEngine(problem)
    started = engine.get_current_response()
    assert started.status == "waiting_for_answer"
    assert started.hint_available is True
    wrong = engine.submit(StudentSubmission("0"))
    assert wrong.status == "incorrect"
    assert not engine.session.is_complete()
    assert engine.session.get_current_step().step_number == 1
    invalid = engine.submit(StudentSubmission("not-a-number"))
    assert invalid.status == "incorrect"
    assert invalid.metadata["error_type"] == "not_numeric"
    assert invalid.metadata.get("guidance_mode") == "independent"
    assert engine.session.get_current_step().step_number == 1
    for step in problem.solution_steps:
        current = engine.session.get_current_step()
        assert current.step_number == step.step_number
        result = engine.submit(
            StudentSubmission(str(step.expected_answer))
        )
        if step.step_number < problem.get_number_of_steps():
            assert result.status == "correct"
            assert result.completed is False
        else:
            assert result.status == "complete"
            assert result.completed is True
    assert engine.session.is_complete()
    return engine


def assert_family_examples():
    number = generate_number_detective(difficulty=1, seed=7)
    compiled = compile_logical_reasoning_puzzle(number, "en")
    print("Number Detective example")
    print(compiled.problem_text)
    for step in compiled.solution_steps:
        print(
            f"  step {step.step_number}: {step.prompt} "
            f"-> {step.expected_answer}"
        )
    distribution = generate_distribution_puzzle(difficulty=2, seed=7)
    compiled_d = compile_logical_reasoning_puzzle(distribution, "en")
    print("Distribution example")
    print(compiled_d.problem_text)
    for step in compiled_d.solution_steps:
        print(
            f"  step {step.step_number}: {step.prompt} "
            f"-> {step.expected_answer}"
        )
    logic = generate_logic_detective(difficulty=3, seed=7)
    compiled_l = compile_logical_reasoning_puzzle(logic, "en")
    print("Logic Detective example")
    print(compiled_l.problem_text)
    for step in compiled_l.solution_steps:
        print(
            f"  step {step.step_number}: {step.prompt} "
            f"-> {step.expected_answer}"
        )
    return compiled, compiled_d, compiled_l


def assert_localization_equivalence():
    for family, generator in GENERATORS.items():
        puzzle = generator(difficulty=1, seed=11)
        english = compile_logical_reasoning_puzzle(puzzle, "en")
        bulgarian = compile_logical_reasoning_puzzle(puzzle, "bg")
        english_answers = [
            step.expected_answer for step in english.solution_steps
        ]
        bulgarian_answers = [
            step.expected_answer for step in bulgarian.solution_steps
        ]
        assert english_answers == bulgarian_answers
        assert english.known["public_clues"] == bulgarian.known["public_clues"]
        assert english.problem_text != bulgarian.problem_text
        assert "{" not in english.problem_text
        assert "{" not in bulgarian.problem_text
        assert family.split("_")[0] not in {"missing"}


def assert_privacy_and_sanitize():
    puzzle = generate_number_detective(difficulty=1, seed=3)
    problem = compile_logical_reasoning_puzzle(puzzle, "en")
    view = public_exercise_view(problem)
    dumped = json.dumps(view, default=str)
    assert str(puzzle.intended.value) not in dumped or (
        puzzle.intended.value in set(problem.known["visible_numbers"])
    )
    engine = PrimarySchoolTutorEngine(problem)
    response = engine.get_current_response()
    metadata = sanitize_tutor_metadata(dict(response.metadata or {}))
    assert "expected_answer" not in metadata
    assert "step_specs" not in metadata
    assert "intended" not in (problem.known or {})
    assert "blueprint" not in (problem.known or {})
    assert "elimination" not in (problem.known or {})


def assert_ambiguous_digit_is_not_forced():
    puzzle = generate_number_detective(difficulty=2, seed=4)
    milestones = compile_milestones(puzzle)
    candidates = satisfying_candidates(puzzle.spec)
    number = unique_extracted_value(
        candidate.value for candidate in candidates
    )
    assert milestones[-1].expected == number
    assert milestones[-1].expected == puzzle.intended.value
    prefix = satisfying_candidates(
        type(puzzle.spec)(
            family=puzzle.spec.family,
            domain=puzzle.spec.domain,
            constraints=puzzle.spec.constraints[:1],
        )
    )
    prefix_units = unique_extracted_value(
        candidate.units for candidate in prefix
    )
    if prefix_units is None:
        assert all(item.milestone != "units" for item in milestones)


def run_sweep():
    started = time.time()
    stats = {
        "attempted": 0,
        "compiled": 0,
        "completed": 0,
        "invalid_sequences": 0,
        "ambiguous": 0,
        "incorrect_expected": 0,
        "hint_disclosure": 0,
        "compilation_errors": 0,
    }
    for family, generator in GENERATORS.items():
        for difficulty in (1, 2, 3):
            for index in range(SWEEP_PER_DIFFICULTY):
                stats["attempted"] += 1
                try:
                    puzzle = generator(
                        difficulty=difficulty,
                        seed=1000 * difficulty + index,
                    )
                    verify_unique_solution(puzzle.spec, puzzle.intended)
                    if family == FAMILY_DISTRIBUTION:
                        verify_distribution_blueprint(
                            puzzle.blueprint,
                            puzzle.spec,
                            puzzle.intended,
                        )
                    if family == FAMILY_LOGIC_DETECTIVE:
                        verify_logic_blueprint(
                            puzzle.blueprint,
                            puzzle.spec,
                            puzzle.intended,
                        )
                    problem = compile_logical_reasoning_puzzle(puzzle, "en")
                    compile_logical_reasoning_puzzle(puzzle, "bg")
                    stats["compiled"] += 1
                    assert_unique_intermediates(puzzle, problem)
                    visible = set(problem.known.get("visible_numbers") or ())
                    engine = PrimarySchoolTutorEngine(problem)
                    for step in problem.solution_steps:
                        protected = protected_answers_from(
                            problem,
                            step.step_number,
                        )
                        for _ in range(3):
                            hint = engine.request_hint()
                            if discloses_protected(
                                hint.feedback,
                                protected,
                                visible,
                            ):
                                stats["hint_disclosure"] += 1
                                raise AssertionError("hint disclosure")
                        result = engine.submit(
                            StudentSubmission(str(step.expected_answer))
                        )
                    if not result.completed:
                        stats["incorrect_expected"] += 1
                        raise AssertionError("did not complete")
                    stats["completed"] += 1
                    public_exercise_view(problem)
                except Exception as error:
                    message = str(error)
                    if "ambiguous" in message:
                        stats["ambiguous"] += 1
                    elif "compilation" in message or "compile" in message:
                        stats["compilation_errors"] += 1
                    elif "hint disclosure" in message:
                        pass
                    else:
                        stats["compilation_errors"] += 1
                    raise
    stats["runtime_seconds"] = round(time.time() - started, 3)
    assert stats["attempted"] == 3 * 3 * SWEEP_PER_DIFFICULTY
    assert stats["compiled"] == stats["attempted"]
    assert stats["completed"] == stats["attempted"]
    assert stats["invalid_sequences"] == 0
    assert stats["ambiguous"] == 0
    assert stats["incorrect_expected"] == 0
    assert stats["hint_disclosure"] == 0
    assert stats["compilation_errors"] == 0
    print("logical reasoning tutoring sweep", stats)
    return stats


def main():
    examples = assert_family_examples()
    for problem in examples:
        assert_problem_compiles_from_problem = problem
        simulate_exercise(problem)
        assert_no_private_payload(problem)
    for family, generator in GENERATORS.items():
        for difficulty in (1, 2, 3):
            puzzle = generator(difficulty=difficulty, seed=21)
            problem = assert_problem_compiles(puzzle, "en")
            simulate_exercise(problem)
            bulgarian = assert_problem_compiles(puzzle, "bg")
            assert [
                step.expected_answer for step in problem.solution_steps
            ] == [
                step.expected_answer for step in bulgarian.solution_steps
            ]
    assert_localization_equivalence()
    assert_privacy_and_sanitize()
    assert_ambiguous_digit_is_not_forced()
    run_sweep()
    print("logical_reasoning_tutoring tests passed")


if __name__ == "__main__":
    main()
