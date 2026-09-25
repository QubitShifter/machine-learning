import inspect
import os

from src.core.i18n.primary_school import pst
from src.core.tutor_engine.concept_guidance.logical_reasoning_guidance import (
    build_logical_guidance_context,
    incorrect_logical_nudge,
    _hint_text as logical_hint_text,
)
from src.core.tutor_engine.concept_guidance.story_step_guidance import (
    build_story_guidance_context,
    incorrect_story_nudge,
    unevaluated_setup,
    _hint_text as story_hint_text,
)
from src.core.tutor_engine.contracts import StudentSubmission
from src.core.tutor_engine.guidance_policy import (
    FORMAT_ERROR_TYPES,
    GUIDANCE_TOPICS,
    MATH_ERROR_TYPE,
    choose_guidance_mode,
)
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.generation import (
    generate_arithmetic_problem,
    localize_generated_primary_school,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning import (
    generate_distribution_puzzle,
    generate_number_detective,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.compile import (
    compile_logical_reasoning_puzzle,
    discloses_protected,
    protected_answers_from,
)
from src.core.tutor_engine.primary_school.generation.word_problems.compile import (
    compile_story_problem,
)
from src.core.tutor_engine.primary_school.generation.word_problems.templates import (
    TEMPLATES_BY_ID,
)
from src.core.tutor_engine.primary_school.generation.word_problems.verify import (
    verify_word_problem,
)
from src.core.tutor_engine.primary_school.reverse_reasoning_solver import (
    load_reverse_reasoning_problem,
)


os.environ.setdefault("MATPAL_MODEL_PROVIDER", "none")


def wrong_integer(expected) -> str:
    value = 0
    expected_value = int(expected)
    while value == expected_value:
        value += 1
    return str(value)


def make_bottle(language="en"):
    template = TEMPLATES_BY_ID["removed_doubled_then_added"]
    problem = compile_story_problem(
        template,
        {"start": 13, "taken": 4, "added": 8},
        template.difficulty,
    )
    verify_word_problem(problem)
    localized = localize_generated_primary_school(
        problem,
        language,
    )
    verify_word_problem(localized)
    return localized


def make_logic(family="number_detective", seed=8, language="en"):
    generator = (
        generate_number_detective
        if family == "number_detective"
        else generate_distribution_puzzle
    )
    puzzle = generator(difficulty=1, seed=seed)
    return compile_logical_reasoning_puzzle(puzzle, language)


def story_context(engine):
    step = engine.session.get_current_step()
    live = type("Live", (), {"current_step": step.step_number})()
    return build_story_guidance_context(
        engine.problem,
        live,
        engine.problem.language,
    )


def logic_context(engine):
    step = engine.session.get_current_step()
    live = type("Live", (), {"current_step": step.step_number})()
    return build_logical_guidance_context(
        engine.problem,
        live,
        engine.problem.language,
    )


def submit_wrong(engine):
    step = engine.session.get_current_step()
    return engine.submit(
        StudentSubmission(wrong_integer(step.expected_answer))
    )


def assert_policy_helper():
    expected = {
        0: ("independent", "guidance_independent"),
        1: ("independent", "guidance_after_error"),
        2: ("guided", "guidance_repeated_errors"),
        3: ("supported", "guidance_supported"),
        4: ("supported", "guidance_supported"),
        9: ("supported", "guidance_supported"),
    }
    for count, result in expected.items():
        assert choose_guidance_mode(count) == result
        assert choose_guidance_mode(count) == result
    parameters = list(
        inspect.signature(choose_guidance_mode).parameters
    )
    assert parameters == ["math_errors_on_step"]
    source = inspect.getsource(choose_guidance_mode)
    assert "mastery" not in source
    assert "difficulty" not in source
    assert "family" not in source
    assert MATH_ERROR_TYPE == "incorrect_answer"
    assert FORMAT_ERROR_TYPES == {
        "empty_answer",
        "not_numeric",
        "not_integer",
    }
    assert GUIDANCE_TOPICS == {
        "story_problems",
        "logical_reasoning",
    }


def assert_format_errors(engine, language="en"):
    before = engine.session.get_math_errors_for_current_step()
    empty = engine.submit(StudentSubmission(""))
    assert empty.status == "incorrect"
    assert empty.metadata["error_type"] == "empty_answer"
    assert empty.feedback == pst(language, "empty_answer")
    assert empty.metadata["guidance_mode"] == "independent"
    assert empty.metadata["guidance_reason"] == "guidance_independent"
    assert empty.suggestion is None
    assert engine.session.get_math_errors_for_current_step() == before

    numeric = engine.submit(StudentSubmission("twelve"))
    assert numeric.metadata["error_type"] == "not_numeric"
    assert numeric.feedback == pst(language, "not_numeric")
    assert numeric.metadata["guidance_mode"] == "independent"
    assert engine.session.get_math_errors_for_current_step() == before

    fractional = engine.submit(StudentSubmission("1.5"))
    assert fractional.metadata["error_type"] == "not_integer"
    assert fractional.feedback == pst(language, "not_integer")
    assert fractional.metadata["guidance_mode"] == "independent"
    assert engine.session.get_math_errors_for_current_step() == before
    return empty, numeric, fractional


def assert_story_format_and_escalation():
    engine = PrimarySchoolTutorEngine(make_bottle())
    assert_format_errors(engine)
    first = submit_wrong(engine)
    assert first.metadata["error_type"] == MATH_ERROR_TYPE
    assert first.metadata["guidance_mode"] == "independent"
    assert first.metadata["guidance_reason"] == "guidance_after_error"
    assert engine.session.get_math_errors_for_current_step() == 1
    story = story_context(engine)
    assert first.feedback == incorrect_story_nudge(story)
    assert first.suggestion is None
    assert "26 - 8 = 18" not in (first.feedback or "")
    assert "13" not in first.feedback

    second = submit_wrong(engine)
    assert second.metadata["guidance_mode"] == "guided"
    assert second.metadata["guidance_reason"] == (
        "guidance_repeated_errors"
    )
    assert engine.session.get_math_errors_for_current_step() == 2
    assert second.feedback == story_hint_text(story, 1)
    assert second.suggestion is None
    assert second.feedback != first.feedback

    engine.session.advance()
    step = engine.session.get_current_step()
    assert step.step_number == 2
    assert engine.session.get_math_errors_for_current_step() == 0

    later = PrimarySchoolTutorEngine(make_bottle())
    later.submit(
        StudentSubmission(str(later.session.get_current_step().expected_answer))
    )
    assert later.session.get_current_step().step_number == 2
    submit_wrong(later)
    submit_wrong(later)
    third = submit_wrong(later)
    assert third.metadata["guidance_mode"] == "supported"
    assert third.metadata["guidance_reason"] == "guidance_supported"
    story_two = story_context(later)
    setup = unevaluated_setup(story_two)
    assert setup == "26 - 8 = ?"
    assert third.suggestion == setup
    assert "26 - 8 = 18" not in (third.suggestion or "")
    assert "26 - 8 = 18" not in (third.feedback or "")
    assert later.problem.final_answer == 13
    assert "13" not in (third.suggestion or "")
    assert "final_answer" not in third.metadata
    assert later.session.get_hints_for_current_step() == 0


def assert_story_reset_and_hints():
    engine = PrimarySchoolTutorEngine(make_bottle())
    first_hints = engine.session.get_hints_for_current_step()
    for level in (1, 2, 3):
        hinted = engine.request_hint()
        assert hinted.status == "hint"
        assert hinted.metadata["hint_level"] == level
    assert engine.session.get_hints_for_current_step() == 3
    assert engine.session.get_math_errors_for_current_step() == 0
    assert first_hints == 0

    one = submit_wrong(engine)
    assert one.metadata["guidance_mode"] == "independent"
    assert one.metadata["guidance_reason"] == "guidance_after_error"
    assert engine.session.get_math_errors_for_current_step() == 1
    assert engine.session.get_hints_for_current_step() == 3
    assert one.suggestion is None

    submit_wrong(engine)
    submit_wrong(engine)
    supported = submit_wrong(engine)
    assert supported.metadata["guidance_mode"] == "supported"
    assert engine.session.get_hints_for_current_step() == 3
    assert engine.session.get_current_step().step_number == 1

    correct = engine.submit(
        StudentSubmission(
            str(engine.session.get_current_step().expected_answer)
        )
    )
    assert correct.status == "correct"
    assert engine.session.get_current_step().step_number == 2
    assert engine.session.get_math_errors_for_current_step() == 0
    next_wrong = submit_wrong(engine)
    assert next_wrong.metadata["guidance_mode"] == "independent"
    assert next_wrong.metadata["guidance_reason"] == (
        "guidance_after_error"
    )
    assert engine.session.get_math_errors_for_current_step() == 1
    assert engine.session.get_hints_for_current_step() == 0


def assert_logical_format_and_escalation():
    engine = PrimarySchoolTutorEngine(make_logic())
    visible = set(engine.problem.known.get("visible_numbers") or ())
    protected = protected_answers_from(engine.problem, 1)
    assert_format_errors(engine)

    first = submit_wrong(engine)
    logic = logic_context(engine)
    assert first.metadata["guidance_mode"] == "independent"
    assert first.metadata["guidance_reason"] == "guidance_after_error"
    assert first.feedback == incorrect_logical_nudge(logic)
    assert first.suggestion is None
    assert engine.session.get_math_errors_for_current_step() == 1
    assert not discloses_protected(first.feedback, protected, visible)

    second = submit_wrong(engine)
    assert second.metadata["guidance_mode"] == "guided"
    assert second.feedback == logical_hint_text(logic, 1)
    assert second.suggestion is None
    assert not discloses_protected(second.feedback, protected, visible)

    third = submit_wrong(engine)
    assert third.metadata["guidance_mode"] == "supported"
    assert third.metadata["guidance_reason"] == "guidance_supported"
    assert third.suggestion == logical_hint_text(logic, 3)
    assert not discloses_protected(
        third.suggestion or "",
        protected,
        visible,
    )
    assert "final_answer" not in third.metadata
    assert engine.session.get_hints_for_current_step() == 0

    hinted = engine.request_hint()
    assert hinted.status == "hint"
    assert hinted.metadata["hint_level"] == 1
    assert hinted.metadata["hints_used_on_step"] == 1
    assert engine.session.get_math_errors_for_current_step() == 3


def assert_logical_reset():
    engine = PrimarySchoolTutorEngine(make_logic(seed=11))
    if engine.problem.get_number_of_steps() < 2:
        engine = PrimarySchoolTutorEngine(
            make_logic(family="distribution_puzzles", seed=8)
        )
    assert engine.problem.get_number_of_steps() >= 2
    submit_wrong(engine)
    submit_wrong(engine)
    third = submit_wrong(engine)
    assert third.metadata["guidance_mode"] == "supported"
    engine.submit(
        StudentSubmission(
            str(engine.session.get_current_step().expected_answer)
        )
    )
    assert engine.session.get_current_step().step_number == 2
    assert engine.session.get_math_errors_for_current_step() == 0
    next_wrong = submit_wrong(engine)
    assert next_wrong.metadata["guidance_mode"] == "independent"
    assert next_wrong.metadata["guidance_reason"] == (
        "guidance_after_error"
    )


def assert_format_then_math_stays_independent():
    for factory in (make_bottle, make_logic):
        engine = PrimarySchoolTutorEngine(factory())
        engine.submit(StudentSubmission(""))
        engine.submit(StudentSubmission("abc"))
        result = submit_wrong(engine)
        assert engine.session.get_math_errors_for_current_step() == 1
        assert result.metadata["guidance_mode"] == "independent"
        assert result.metadata["guidance_reason"] == (
            "guidance_after_error"
        )


def assert_out_of_scope_topics():
    arithmetic = PrimarySchoolTutorEngine(
        generate_arithmetic_problem(difficulty=1, seed=9)
    )
    first = submit_wrong(arithmetic)
    second = submit_wrong(arithmetic)
    assert "guidance_mode" not in first.metadata
    assert "guidance_reason" not in second.metadata
    assert second.suggestion == arithmetic.session.get_current_step().hint
    assert arithmetic.session.get_math_errors_for_current_step() == 0

    legacy = PrimarySchoolTutorEngine(
        load_reverse_reasoning_problem(
            "grade4_reverse_reasoning_001"
        )
    )
    legacy_first = submit_wrong(legacy)
    legacy_second = submit_wrong(legacy)
    assert legacy.problem.topic == "word_problems"
    assert "guidance_mode" not in legacy_first.metadata
    assert legacy_second.suggestion == (
        legacy.session.get_current_step().hint
    )
    assert legacy.session.get_math_errors_for_current_step() == 0


def assert_other_engines_do_not_use_policy():
    import sympy as sp

    from src.core.physics.kinematics.engine import (
        KinematicsTutorEngine,
    )
    from src.core.physics.kinematics.problems import (
        load_fixed_kinematics_problem,
    )
    from src.core.tutor_engine.adapters.linear_ode_adapter import (
        LinearODETutorAdapter,
    )
    from src.core.tutor_engine.adapters.separable_ode_adapter import (
        SeparableODETutorAdapter,
    )

    x, y = sp.symbols("x y")
    linear = LinearODETutorAdapter(
        p_expression=2 * x,
        q_expression=x,
    )
    linear_wrong = linear.submit(StudentSubmission("nope"))
    assert "guidance_mode" not in (linear_wrong.metadata or {})
    assert "choose_guidance_mode" not in inspect.getsource(
        LinearODETutorAdapter
    )

    separable = SeparableODETutorAdapter(
        rhs_expression=2 * x * y,
    )
    separable_wrong = separable.submit(StudentSubmission("nope"))
    assert "guidance_mode" not in (separable_wrong.metadata or {})
    assert "choose_guidance_mode" not in inspect.getsource(
        SeparableODETutorAdapter
    )

    kinematics = KinematicsTutorEngine(
        load_fixed_kinematics_problem()
    )
    kinematics_wrong = kinematics.submit(StudentSubmission("nope"))
    assert "guidance_mode" not in (kinematics_wrong.metadata or {})
    assert "choose_guidance_mode" not in inspect.getsource(
        KinematicsTutorEngine
    )


def assert_no_progress_or_selection_coupling():
    from src.core.adaptive.policy import RuleBasedAdaptivePolicy
    from src.core.student_model.progress_store import (
        update_skill_progress,
    )
    from src.api.mat_pal.schemas import SessionResponse

    policy_source = inspect.getsource(RuleBasedAdaptivePolicy)
    assert "choose_guidance_mode" not in policy_source
    progress_source = inspect.getsource(update_skill_progress)
    assert "guidance_mode" not in progress_source
    fields = set(SessionResponse.model_fields)
    assert "guidance_mode" not in fields
    assert "guidance_reason" not in fields


def main():
    assert os.environ["MATPAL_MODEL_PROVIDER"] == "none"
    assert_policy_helper()
    assert_story_format_and_escalation()
    assert_story_reset_and_hints()
    assert_logical_format_and_escalation()
    assert_logical_reset()
    assert_format_then_math_stays_independent()
    assert_out_of_scope_topics()
    assert_other_engines_do_not_use_policy()
    assert_no_progress_or_selection_coupling()
    print("adaptive_guidance tests passed")


if __name__ == "__main__":
    main()
