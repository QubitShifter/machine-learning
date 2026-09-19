from src.core.i18n.primary_school import PRIMARY_SCHOOL_TEXT, pst
from src.core.tutor_engine.contracts import StudentSubmission
from src.core.tutor_engine.primary_school.checker import (
    evaluate_integer_answer,
    evaluate_step_answer,
    parse_exact_integer,
)
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.generation import (
    PrimarySchoolGenerationError,
    generate_arithmetic_problem,
    generate_sequence_or_chain_problem,
    generate_unknown_number_problem,
)
from src.core.tutor_engine.primary_school.generation.arithmetic import (
    verify_arithmetic_problem,
)
from src.core.tutor_engine.primary_school.generation.expr import (
    expr_from_dict,
)
from src.core.tutor_engine.primary_school.generation.sequences import (
    verify_sequence_or_chain_problem,
)
from src.core.tutor_engine.primary_school.generation.unknown_number import (
    verify_unknown_number_problem,
)
from src.core.tutor_engine.primary_school.reverse_reasoning_solver import (
    load_reverse_reasoning_problem,
)


def _complete_with_expected(engine: PrimarySchoolTutorEngine):
    while not engine.session.is_complete():
        step = engine.session.get_current_step()
        response = engine.submit(
            StudentSubmission(
                answer=str(step.expected_answer),
                input_type="number",
            )
        )
        if response.status not in {"correct", "complete"}:
            raise AssertionError(
                f"Expected progress, got {response.status}: "
                f"{response.feedback}"
            )
    return engine.get_current_response()


def assert_arithmetic_validity_and_reproducibility():
    seen = []
    for difficulty in (1, 2, 3):
        for seed in range(40):
            problem = generate_arithmetic_problem(
                difficulty=difficulty,
                seed=seed,
            )
            verify_arithmetic_problem(problem)
            tree = expr_from_dict(problem.known["expr"])
            assert tree.evaluate() == problem.final_answer
            assert tree.render() == problem.known["expression"]
            assert "÷" not in problem.known["expression"]
            assert "/" not in problem.known["expression"]
            seen.append(problem.final_answer)

            again = generate_arithmetic_problem(
                difficulty=difficulty,
                seed=seed,
            )
            assert again.known["expr"] == problem.known["expr"]
            assert again.final_answer == problem.final_answer
            assert again.known["expression"] == (
                problem.known["expression"]
            )

    assert len(set(seen)) > 1


def assert_unknown_number_uniqueness_and_substitution():
    forms = set()
    for difficulty in (1, 2, 3):
        for seed in range(40):
            problem = generate_unknown_number_problem(
                difficulty=difficulty,
                seed=seed,
            )
            verify_unknown_number_problem(problem)
            known = problem.known
            forms.add(known["form"])
            x = known["x"]
            a = known["a"]
            b = known["b"]
            assert a != 0
            if known["form"] == "x+a=b":
                assert x + a == b
            elif known["form"] == "x-a=b":
                assert x - a == b
            else:
                assert a * x == b
            assert problem.final_answer == x

            again = generate_unknown_number_problem(
                difficulty=difficulty,
                seed=seed,
            )
            assert again.known == problem.known

    assert "x+a=b" in forms
    assert "x-a=b" in forms
    assert "a*x=b" in forms


def assert_sequence_and_chain_are_distinguished():
    sequence = generate_sequence_or_chain_problem(
        difficulty=1,
        seed=3,
    )
    chain = generate_sequence_or_chain_problem(
        difficulty=2,
        seed=3,
    )
    verify_sequence_or_chain_problem(sequence)
    verify_sequence_or_chain_problem(chain)
    assert sequence.known["variant"] == "sequence"
    assert chain.known["variant"] == "chain"
    assert sequence.final_answer == sequence.known["next_term"]
    assert chain.final_answer == chain.known["result"]
    assert "→" not in sequence.problem_text
    assert "→" in chain.problem_text

    for difficulty in (1, 2, 3):
        for seed in range(30):
            problem = generate_sequence_or_chain_problem(
                difficulty=difficulty,
                seed=seed,
            )
            verify_sequence_or_chain_problem(problem)
            again = generate_sequence_or_chain_problem(
                difficulty=difficulty,
                seed=seed,
            )
            assert again.known == problem.known
            assert again.final_answer == problem.final_answer


def assert_reverse_chain_recovers_start():
    found = False
    for seed in range(80):
        problem = generate_sequence_or_chain_problem(
            difficulty=3,
            seed=seed,
        )
        if problem.known.get("direction") != "reverse":
            continue
        found = True
        verify_sequence_or_chain_problem(problem)
        assert problem.final_answer == problem.known["start"]
        assert problem.problem_text.startswith(
            "This operation chain is missing"
        ) or "липсва началното" in problem.problem_text
        break
    assert found is True


def assert_bounded_generation_retries():
    attempts = {"count": 0}

    def counting_fail(difficulty, rng):
        attempts["count"] += 1
        raise ValueError("invalid candidate")

    try:
        generate_arithmetic_problem(
            difficulty=1,
            seed=1,
            max_attempts=5,
            attempt_builder=counting_fail,
        )
    except PrimarySchoolGenerationError:
        pass
    else:
        raise AssertionError("Retries should fail closed.")

    assert attempts["count"] == 5

    try:
        generate_unknown_number_problem(
            difficulty=4,
        )
    except PrimarySchoolGenerationError as error:
        assert "difficulty" in str(error)
    else:
        raise AssertionError("Bad difficulty should fail.")


def assert_integer_input_rules():
    accepted = {
        "7": 7,
        " 12 ": 12,
        "+3": 3,
        "-4": -4,
        "7.0": 7,
        "7,0": 7,
        "08": 8,
    }
    for text, value in accepted.items():
        parsed, error = parse_exact_integer(text)
        assert error is None
        assert parsed == value
        result = evaluate_integer_answer(text, value)
        assert result["correct"] is True

    rejected = {
        "": "empty_answer",
        "   ": "empty_answer",
        "hello": "not_numeric",
        "NaN": "not_numeric",
        "inf": "not_numeric",
        "1e2": "not_numeric",
        "7.1": "not_integer",
        "7.10": "not_integer",
        "1/2": "not_numeric",
        "+": "not_numeric",
        "7 0": "not_numeric",
        "x" * 25: "not_numeric",
    }
    for text, error_type in rejected.items():
        parsed, error = parse_exact_integer(text)
        assert parsed is None
        assert error == error_type
        result = evaluate_integer_answer(text, 7)
        assert result["correct"] is False
        assert result["error_type"] == error_type

    rounded = evaluate_integer_answer("7.6", 8)
    assert rounded["correct"] is False
    assert rounded["error_type"] == "not_integer"


def assert_legacy_checker_is_unchanged_for_reverse_reasoning():
    result = evaluate_step_answer("7.0", 7)
    assert result["correct"] is True
    result = evaluate_step_answer("7.1", 7)
    assert result["correct"] is False
    result = evaluate_step_answer("hello", 7)
    assert result["error_type"] == "not_numeric"


def assert_engine_hints_and_incorrect_answers():
    problem = generate_arithmetic_problem(
        difficulty=2,
        seed=4,
        language="en",
    )
    engine = PrimarySchoolTutorEngine(problem=problem)
    first = engine.get_current_response()
    assert first.expected_input_type == "number"
    assert first.current_step == 1
    assert problem.known["expression"] in first.feedback

    wrong = engine.submit(
        StudentSubmission(
            answer="99999",
            input_type="number",
        )
    )
    assert wrong.status == "incorrect"
    assert wrong.current_step == 1
    assert engine.session.get_current_step().step_number == 1

    hint = engine.request_hint()
    assert hint.status == "hint"
    assert hint.current_step == 1
    assert "multiplication" in hint.feedback.lower()
    assert str(problem.final_answer) not in hint.feedback

    completed = _complete_with_expected(engine)
    assert completed.completed is True
    assert completed.status == "complete"


def assert_english_and_bulgarian_templates():
    english = generate_unknown_number_problem(
        difficulty=3,
        seed=8,
        language="en",
    )
    bulgarian = generate_unknown_number_problem(
        difficulty=3,
        seed=8,
        language="bg",
    )
    assert english.known == bulgarian.known
    assert english.final_answer == bulgarian.final_answer
    assert english.language == "en"
    assert bulgarian.language == "bg"
    assert "Find the integer x" in english.problem_text
    assert "Намерете цялото число x" in bulgarian.problem_text
    assert english.known["equation"] in english.problem_text
    assert bulgarian.known["equation"] in bulgarian.problem_text
    assert english.solution_steps[0].prompt != (
        bulgarian.solution_steps[0].prompt
    )
    form = english.known["form"]
    if form == "x+a=b":
        assert "known addend" in english.solution_steps[0].prompt
        assert "събираемо" in bulgarian.solution_steps[0].prompt
    elif form == "x-a=b":
        assert "known subtrahend" in english.solution_steps[0].prompt
        assert "умалител" in bulgarian.solution_steps[0].prompt
    else:
        assert "known factor" in english.solution_steps[0].prompt
        assert "множител" in bulgarian.solution_steps[0].prompt
    assert "combined with" not in english.solution_steps[0].prompt
    assert "съчетано" not in bulgarian.solution_steps[0].prompt
    x = english.known["x"]
    for step in english.solution_steps:
        assert str(x) not in (step.hint or "")
    assert pst("bg", "not_integer") == (
        "Моля, въведете цяло число."
    )
    assert set(PRIMARY_SCHOOL_TEXT["en"]) == set(
        PRIMARY_SCHOOL_TEXT["bg"]
    )
    for step in english.solution_steps:
        assert not step.prompt.startswith("gen.")
        assert step.hint is not None
        assert not step.hint.startswith("gen.")


def assert_reverse_reasoning_regression():
    problem = load_reverse_reasoning_problem(
        "grade4_reverse_reasoning_001"
    )
    assert problem.get_number_of_steps() == 7
    assert problem.final_answer == 116
    engine = PrimarySchoolTutorEngine(problem=problem)
    start = engine.get_current_response()
    assert start.expected_input_type == "text"
    assert start.total_steps == 7
    assert "hazelnuts" in problem.problem_text.lower()

    answers = [7, 12, 24, 28, 56, 58, 116]
    for expected in answers:
        step = engine.session.get_current_step()
        assert step.input_type is None
        assert step.answer_format is None
        response = engine.submit(
            StudentSubmission(
                answer=str(expected),
                input_type="text",
            )
        )
        if expected != 116:
            assert response.status == "correct"
            assert response.completed is False
        else:
            assert response.status == "complete"
            assert response.completed is True
            assert response.metadata["final_answer"] == 116

    bulgarian = load_reverse_reasoning_problem(
        "grade4_reverse_reasoning_001",
        language="bg",
    )
    assert "катерица" in bulgarian.problem_text
    assert bulgarian.final_answer == 116
    assert bulgarian.get_number_of_steps() == 7


def assert_zero_coefficient_is_rejected():
    def zero_coeff(difficulty, rng):
        problem = generate_unknown_number_problem(
            difficulty=3,
            seed=1,
            rng=rng,
        )
        problem.known["a"] = 0
        problem.known["form"] = "a*x=b"
        problem.known["b"] = 0
        return problem

    try:
        generate_unknown_number_problem(
            difficulty=3,
            seed=1,
            max_attempts=3,
            attempt_builder=zero_coeff,
        )
    except PrimarySchoolGenerationError:
        pass
    else:
        raise AssertionError(
            "Zero coefficients must be rejected."
        )


def main():
    assert_arithmetic_validity_and_reproducibility()
    assert_unknown_number_uniqueness_and_substitution()
    assert_sequence_and_chain_are_distinguished()
    assert_reverse_chain_recovers_start()
    assert_bounded_generation_retries()
    assert_integer_input_rules()
    assert_legacy_checker_is_unchanged_for_reverse_reasoning()
    assert_engine_hints_and_incorrect_answers()
    assert_english_and_bulgarian_templates()
    assert_reverse_reasoning_regression()
    assert_zero_coefficient_is_rejected()
    print("primary_school_generators tests passed")


if __name__ == "__main__":
    main()
