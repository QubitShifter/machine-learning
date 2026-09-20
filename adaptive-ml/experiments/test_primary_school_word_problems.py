import re

from src.core.i18n.primary_school import PRIMARY_SCHOOL_TEXT, pst
from src.core.question_engine.contracts import TutorQuestionContext
from src.core.tutor_engine.concept_guidance.word_problem_guidance import (
    match_word_problem_explanation,
)
from src.core.tutor_engine.contracts import StudentSubmission
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.generation import (
    PrimarySchoolGenerationError,
    generate_word_problem,
    localize_generated_primary_school,
)
from src.core.tutor_engine.primary_school.generation.word_problems.compile import (
    compile_story_problem,
)
from src.core.tutor_engine.primary_school.generation.word_problems.model import (
    FAMILY_COMPARISON,
    FAMILY_REVERSE,
    FAMILY_SEVERAL,
)
from src.core.tutor_engine.primary_school.generation.word_problems.templates import (
    FORBIDDEN_GLOBAL_BG,
    FORBIDDEN_GLOBAL_EN,
    STORY_TEMPLATES,
    TEMPLATES_BY_ID,
)
from src.core.tutor_engine.primary_school.generation.word_problems.verify import (
    verify_word_problem,
)
from src.core.tutor_engine.primary_school.problem_types import (
    SolutionStepType as StepType,
)
from src.core.tutor_engine.primary_school.reverse_reasoning_solver import (
    load_reverse_reasoning_problem,
)


CANONICAL_SLOTS = {
    "cards_total": {"red": 8, "blue": 5},
    "stamps_then_stickers": {
        "stamps": 8,
        "more": 5,
        "times": 3,
    },
    "boxes_then_stickers": {
        "boxes": 3,
        "each": 8,
        "more": 5,
        "times": 2,
    },
    "more_than": {"base": 9, "extra": 4},
    "fewer_than": {"base": 13, "fewer": 4},
    "twice_as_many": {"base": 9},
    "more_then_together": {"base": 9, "extra": 4},
    "books_from_class": {"girls": 6, "extra": 3},
    "remaining_after_taken": {"start": 15, "taken": 6},
    "removed_then_doubled": {"start": 15, "taken": 6},
    "removed_doubled_then_added": {
        "start": 15,
        "taken": 6,
        "added": 4,
    },
}


def make_canonical(template_id, language="en"):
    template = TEMPLATES_BY_ID[template_id]
    problem = compile_story_problem(
        template,
        dict(CANONICAL_SLOTS[template_id]),
        template.difficulty,
    )
    verify_word_problem(problem)
    localized = localize_generated_primary_school(
        problem,
        language,
    )
    verify_word_problem(localized)
    return localized


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


def assert_canonical_verified_examples():
    stamps = make_canonical("stamps_then_stickers")
    quantities = stamps.known["quantities"]
    assert quantities["stamps_now"] == 13
    assert quantities["stickers"] == 39
    assert stamps.final_answer == 39
    assert stamps.known["relation_count"] == 2

    doubled = make_canonical("removed_then_doubled")
    quantities = doubled.known["quantities"]
    assert quantities["remaining"] == 9
    assert quantities["final"] == 18
    assert quantities["start"] == 15
    assert doubled.final_answer == 15
    assert quantities["final"] == 2 * quantities["remaining"]
    assert quantities["final"] != 3 * quantities["remaining"]
    assert (15 - 6) * 2 == 18
    answers = [
        step.expected_answer
        for step in doubled.solution_steps
    ]
    assert answers == [18, 9, 15]

    more = make_canonical("more_than")
    assert more.known["quantities"]["nina"] == 13
    assert more.known["quantities"]["nina"] > more.known[
        "quantities"
    ]["base"]


def assert_all_templates_have_reviewed_semantics():
    for template in STORY_TEMPLATES:
        english = make_canonical(template.template_id, "en")
        bulgarian = make_canonical(template.template_id, "bg")
        params = english.known["statement_params"]
        _assert_wording(
            english.problem_text.lower(),
            template.semantics.en_required,
            template.semantics.en_forbidden + FORBIDDEN_GLOBAL_EN,
            params,
        )
        _assert_wording(
            bulgarian.problem_text.lower(),
            template.semantics.bg_required,
            template.semantics.bg_forbidden + FORBIDDEN_GLOBAL_BG,
            params,
        )
        assert english.known == bulgarian.known
        assert english.final_answer == bulgarian.final_answer
        assert english.problem_text != bulgarian.problem_text
        visible = set(params.values())
        assert {
            int(match)
            for match in re.findall(r"\d+", english.problem_text)
        } == visible
        assert {
            int(match)
            for match in re.findall(r"\d+", bulgarian.problem_text)
        } == visible
        if template.semantics.larger_id:
            quantities = english.known["quantities"]
            assert quantities[template.semantics.larger_id] > (
                quantities[template.semantics.smaller_id]
            )
        if template.semantics.double_output:
            quantities = english.known["quantities"]
            source = quantities[template.semantics.double_input]
            doubled = quantities[template.semantics.double_output]
            assert doubled == source * 2
            assert doubled != source * 3
            assert doubled != source + 2


def assert_families_and_difficulty_across_seeds():
    families = {1: set(), 2: set(), 3: set()}
    templates = {1: set(), 2: set(), 3: set()}
    seen_answers = []
    for difficulty in (1, 2, 3):
        for seed in range(40):
            problem = generate_word_problem(
                difficulty=difficulty,
                seed=seed,
            )
            verify_word_problem(problem)
            again = generate_word_problem(
                difficulty=difficulty,
                seed=seed,
            )
            assert again.known["quantities"] == (
                problem.known["quantities"]
            )
            assert again.final_answer == problem.final_answer
            assert again.problem_text == problem.problem_text
            assert problem.known["relation_count"] == difficulty
            calc_steps = [
                step
                for step in problem.solution_steps
                if step.step_type == StepType.CALCULATION
            ]
            assert len(calc_steps) == difficulty
            assert len(problem.solution_steps) == difficulty + 1
            assert problem.solution_steps[-1].expected_answer == (
                problem.final_answer
            )
            assert problem.final_answer == problem.known[
                "quantities"
            ][problem.known["ask"]]
            families[difficulty].add(problem.known["family"])
            templates[difficulty].add(
                problem.known["template_id"]
            )
            seen_answers.append(problem.final_answer)
            _assert_hints_do_not_reveal(problem)
    assert FAMILY_SEVERAL in families[1]
    assert FAMILY_COMPARISON in families[1]
    assert FAMILY_REVERSE in families[1]
    assert FAMILY_SEVERAL in families[2]
    assert FAMILY_COMPARISON in families[2]
    assert FAMILY_REVERSE in families[2]
    assert FAMILY_SEVERAL in families[3]
    assert FAMILY_COMPARISON in families[3]
    assert FAMILY_REVERSE in families[3]
    assert len(set(seen_answers)) > 1
    assert templates[2] >= {
        "stamps_then_stickers",
        "removed_then_doubled",
    }


def assert_reverse_recovers_start_and_is_not_hazelnuts():
    found = False
    for seed in range(60):
        problem = generate_word_problem(
            difficulty=2,
            seed=seed,
        )
        if problem.known["template_id"] != "removed_then_doubled":
            continue
        found = True
        quantities = problem.known["quantities"]
        start = quantities["start"]
        taken = quantities["taken"]
        remaining = quantities["remaining"]
        final = quantities["final"]
        assert (start - taken) * 2 == final
        assert remaining * 2 == final
        assert remaining + taken == start
        text = problem.problem_text.lower()
        assert "was doubled" in text
        assert "twice as many as remained were put in" not in text
        assert "hazelnut" not in text
        assert "squirrel" not in text
        assert "hollow" not in text
        bulgarian = generate_word_problem(
            difficulty=2,
            seed=seed,
            language="bg",
        )
        assert "удвоен" in bulgarian.problem_text.lower()
        assert "катерица" not in bulgarian.problem_text.lower()
        assert "лешник" not in bulgarian.problem_text.lower()
    assert found is True

    static = load_reverse_reasoning_problem(
        "grade4_reverse_reasoning_001"
    )
    assert static.get_number_of_steps() == 7
    assert static.final_answer == 116
    assert static.topic == "word_problems"


def assert_engine_grading_and_hints():
    problem = make_canonical("stamps_then_stickers")
    engine = PrimarySchoolTutorEngine(problem=problem)
    first = engine.get_current_response()
    assert first.expected_input_type == "number"
    wrong = engine.submit(
        StudentSubmission(answer="99999", input_type="number")
    )
    assert wrong.status == "incorrect"
    assert wrong.current_step == 1
    hint = engine.request_hint()
    assert hint.status == "hint"
    assert hint.current_step == 1
    assert str(problem.final_answer) not in hint.feedback
    completed = _complete_with_expected(engine)
    assert completed.completed is True
    assert completed.metadata["final_answer"] == 39


def assert_vocabulary_questions_are_local():
    problem = make_canonical("twice_as_many")
    context = TutorQuestionContext(
        language="en",
        subject="mathematics",
        domain="primary_school",
        topic="story_problems",
        problem_id="story-test",
        problem_title=problem.title,
        problem_statement=problem.problem_text,
        current_step=1,
        total_steps=problem.get_number_of_steps(),
        current_prompt=problem.solution_steps[0].prompt,
        expected_input_type="number",
        tutor_metadata={"family": "comparison"},
    )
    twice = match_word_problem_explanation(
        'What does "twice as many" mean?',
        context,
    )
    assert twice is not None
    assert "two times" in twice.lower()
    assert str(problem.final_answer) not in twice
    more = match_word_problem_explanation(
        "What does more than mean?",
        context,
    )
    assert more is not None
    remaining = match_word_problem_explanation(
        "Какво означава останали?",
        TutorQuestionContext(
            language="bg",
            subject="mathematics",
            domain="primary_school",
            topic="story_problems",
            problem_id="story-test",
            problem_title=problem.title,
            problem_statement=make_canonical(
                "remaining_after_taken",
                "bg",
            ).problem_text,
            current_step=1,
            total_steps=2,
            current_prompt="x",
            expected_input_type="number",
            tutor_metadata={},
        ),
    )
    assert remaining is not None
    assert "останали" in remaining.lower()
    method = match_word_problem_explanation(
        "How do I solve this?",
        context,
    )
    assert method is not None
    assert "starting amount is found only after" in method.lower()
    other_topic = match_word_problem_explanation(
        'What does "twice as many" mean?',
        TutorQuestionContext(
            language="en",
            subject="mathematics",
            domain="ode",
            topic="first_order_linear",
            problem_id="ode",
            problem_title="ODE",
            problem_statement="Solve y",
            current_step=1,
            total_steps=4,
            current_prompt="x",
            expected_input_type="math",
            tutor_metadata={},
        ),
    )
    assert other_topic is None


def assert_invalid_candidates_fail_closed():
    def always_bad(difficulty, rng):
        raise ValueError("invalid on purpose")

    try:
        generate_word_problem(
            difficulty=1,
            seed=1,
            max_attempts=3,
            attempt_builder=always_bad,
        )
    except PrimarySchoolGenerationError:
        pass
    else:
        raise AssertionError("Invalid candidates must fail closed.")


def assert_localization_keys_exist():
    assert set(PRIMARY_SCHOOL_TEXT["en"]) == set(
        PRIMARY_SCHOOL_TEXT["bg"]
    )
    for template in STORY_TEMPLATES:
        problem = make_canonical(template.template_id, "bg")
        assert not problem.problem_text.startswith("gen.")
        for step in problem.solution_steps:
            assert not step.prompt.startswith("gen.")
            assert step.hint is not None
            assert not step.hint.startswith("gen.")
        assert pst("bg", "gen.story.title") == (
            "Текстова задача за 4. клас"
        )


def _assert_wording(text, required, forbidden, params):
    for phrase in required:
        expected = phrase
        if "{" in phrase:
            expected = phrase.format(**params)
        assert expected.lower() in text, (expected, text)
    for phrase in forbidden:
        assert phrase.lower() not in text, (phrase, text)


def _assert_hints_do_not_reveal(problem):
    answers = [
        step.expected_answer
        for step in problem.solution_steps
    ]
    final = str(problem.final_answer)
    for index, step in enumerate(problem.solution_steps):
        hint = step.hint or ""
        assert final not in hint
        for later in answers[index + 1 :]:
            if later in problem.known["statement_params"].values():
                continue
            assert str(later) not in hint


def main():
    assert_canonical_verified_examples()
    assert_all_templates_have_reviewed_semantics()
    assert_families_and_difficulty_across_seeds()
    assert_reverse_recovers_start_and_is_not_hazelnuts()
    assert_engine_grading_and_hints()
    assert_vocabulary_questions_are_local()
    assert_invalid_candidates_fail_closed()
    assert_localization_keys_exist()
    print("primary_school_word_problems tests passed")


if __name__ == "__main__":
    main()
