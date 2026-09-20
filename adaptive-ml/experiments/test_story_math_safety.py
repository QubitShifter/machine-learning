import json

from fastapi.testclient import TestClient

from src.api.mat_pal.app import app
from src.api.mat_pal.generated_problem_store import (
    add_generated_problem,
    clear_generated_problems,
)
from src.api.mat_pal.problem_generation import (
    _create_primary_school_registration,
)
from src.api.mat_pal.schemas import AnswerRequest, QuestionRequest
from src.api.mat_pal.session_store import (
    _sessions,
    get_question_engine,
    request_hint,
    set_question_engine,
    start_session,
    submit_answer,
    submit_question,
)
from src.api.mat_pal.tutor_registry import LINEAR_ODE_FIXED_PROBLEM_ID
from src.core.physics.kinematics.problems import KINEMATICS_FIXED_PROBLEM_ID
from src.core.question_engine import (
    FakeTutorModelProvider,
    FakeWebSearchProvider,
    GeneralTutorQuestionEngine,
)
from src.core.question_engine.guided_questions import GuidedQuestionError
from src.core.tutor_engine.contracts import StudentSubmission
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.generation import (
    generate_arithmetic_problem,
    generate_sequence_or_chain_problem,
    generate_unknown_number_problem,
    localize_generated_primary_school,
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


BOTTLE_SLOTS = {"start": 13, "taken": 4, "added": 8}
BROWSER_BOTTLE_SLOTS = {"start": 10, "taken": 6, "added": 5}
HIDDEN = {13, 9, 18}
BROWSER_HIDDEN = {10, 4, 8}
HOSTILE_MODEL = (
    "26 - 8 = 18, then 18 / 2 = 9, so the crate "
    "started with 9 bottles."
)
client = TestClient(app)


def make_engine(model=None):
    return GeneralTutorQuestionEngine(
        model_provider=model or FakeTutorModelProvider(),
        web_search_provider=FakeWebSearchProvider(),
    )


def register_problem(problem, language="en"):
    known = problem.known or {}
    registration = _create_primary_school_registration(
        problem,
        prefix=problem.problem_id,
        topic=problem.topic,
        topic_name=problem.topic,
        generator_name=problem.problem_id,
        difficulty=int(known.get("difficulty") or 3),
        seed=None,
        language=language,
    )
    return add_generated_problem(registration)


def start_registered(problem, language="en"):
    registration = register_problem(problem, language)
    return start_session(
        registration.problem_id,
        language=language,
    )


def make_bottle(language="en"):
    template = TEMPLATES_BY_ID["removed_doubled_then_added"]
    problem = compile_story_problem(
        template,
        dict(BOTTLE_SLOTS),
        template.difficulty,
    )
    verify_word_problem(problem)
    localized = localize_generated_primary_school(
        problem,
        language,
    )
    verify_word_problem(localized)
    assert localized.known["quantities"]["final"] == 26
    assert localized.known["quantities"]["doubled"] == 18
    assert localized.known["quantities"]["remaining"] == 9
    assert localized.final_answer == 13
    return localized


def make_browser_bottle(language="bg"):
    template = TEMPLATES_BY_ID["removed_doubled_then_added"]
    problem = compile_story_problem(
        template,
        dict(BROWSER_BOTTLE_SLOTS),
        template.difficulty,
    )
    verify_word_problem(problem)
    localized = localize_generated_primary_school(
        problem,
        language,
    )
    verify_word_problem(localized)
    quantities = localized.known["quantities"]
    assert quantities["final"] == 13
    assert quantities["added"] == 5
    assert quantities["taken"] == 6
    assert quantities["doubled"] == 8
    assert quantities["remaining"] == 4
    assert localized.final_answer == 10
    return localized


def make_canonical(template_id, language="en"):
    slots = {
        "cards_total": {"red": 8, "blue": 5},
        "more_than": {"base": 9, "extra": 4},
        "remaining_after_taken": {"start": 15, "taken": 6},
    }[template_id]
    template = TEMPLATES_BY_ID[template_id]
    problem = compile_story_problem(
        template,
        dict(slots),
        template.difficulty,
    )
    verify_word_problem(problem)
    return localize_generated_primary_school(problem, language)


def snapshot(session_id):
    stored = _sessions[session_id]
    live = stored.engine.get_current_response()
    return (
        stored.answer_submissions,
        stored.incorrect_submissions,
        stored.hint_requests,
        stored.mastery_updated,
        live.current_step,
        live.completed,
        len(stored.question_history),
    )


def advance_to_step_two(session_id):
    stored = _sessions[session_id]
    step = stored.engine.session.get_current_step()
    assert step is not None
    assert int(step.expected_answer) == 26
    live = submit_answer(
        session_id,
        AnswerRequest(answer="26", input_type="number"),
    )
    assert live is not None
    assert live.current_step == 2
    return live


def assert_no_hidden(text, extra=()):
    lowered = text.lower()
    assert "so the crate started with 9" not in lowered
    assert "началн" not in lowered or "9" not in text
    for value in set(HIDDEN) | set(extra):
        assert f"= {value}" not in text
        assert f"= {value}." not in text
    assert "18 / 2" not in text
    assert "18 ÷ 2 = 9" not in text
    assert "26 - 8 = 18" not in text


def assert_bottle_freeform_is_local_and_safe():
    previous = get_question_engine()
    model = FakeTutorModelProvider(text=HOSTILE_MODEL)
    set_question_engine(make_engine(model))
    try:
        problem = make_bottle("bg")
        started = start_registered(problem, "bg")
        advance_to_step_two(started.session_id)
        before = snapshot(started.session_id)
        answered = submit_question(
            started.session_id,
            QuestionRequest(
                question="Как да намеря отговора на тази стъпка?",
            ),
        )
        assert answered is not None
        assert answered.metadata["answer_source"] == "local"
        assert answered.metadata["question_route"] == "local_only"
        assert model.calls == []
        assert answered.current_step == 2
        feedback = answered.feedback
        assert "изваждан" in feedback.lower() or "изваждане" in feedback
        assert "26 - 8 = ?" in feedback
        assert "26 - 8 = 18" not in feedback
        assert "9" not in feedback
        assert "13" not in feedback
        assert "18" not in feedback
        assert HOSTILE_MODEL not in feedback
        assert_no_hidden(feedback)
        after = snapshot(started.session_id)
        assert after[:6] == before[:6]
        assert after[6] == before[6] + 1

        english = start_registered(make_bottle("en"), "en")
        advance_to_step_two(english.session_id)
        method = submit_question(
            english.session_id,
            QuestionRequest(question="How do I solve this step?"),
        )
        assert method.metadata["answer_source"] == "local"
        assert "subtraction" in method.feedback.lower()
        assert "26 - 8 = ?" in method.feedback
        assert "26 - 8 = 18" not in method.feedback
        assert "starting" not in method.feedback.lower() or (
            "only after" in method.feedback.lower()
        )
        assert "9" not in method.feedback
        assert model.calls == []
        action = submit_question(
            english.session_id,
            QuestionRequest(
                question="What action should I use?",
            ),
        )
        assert action.metadata["answer_source"] == "local"
        general = submit_question(
            english.session_id,
            QuestionRequest(
                question="Where are story problems used in real life?",
            ),
        )
        assert general.metadata["answer_source"] == "model"
        assert model.calls
    finally:
        set_question_engine(previous)


def assert_progressive_hints_and_incorrect():
    previous = get_question_engine()
    model = FakeTutorModelProvider(text=HOSTILE_MODEL)
    set_question_engine(make_engine(model))
    try:
        started = start_registered(make_bottle("en"), "en")
        advance_to_step_two(started.session_id)
        before = snapshot(started.session_id)
        first = request_hint(started.session_id)
        assert first.status == "hint"
        assert first.metadata["hint_level"] == 1
        assert first.hint_available is True
        assert "8" in first.feedback
        assert "26 - 8 = ?" not in first.feedback
        assert_no_hidden(first.feedback)
        second = request_hint(started.session_id)
        assert second.metadata["hint_level"] == 2
        assert first.feedback != second.feedback
        assert "subtraction" in second.feedback.lower()
        assert_no_hidden(second.feedback)
        third = request_hint(started.session_id)
        assert third.metadata["hint_level"] == 3
        assert third.metadata["hint_exhausted"] is True
        assert third.hint_available is False
        assert "26 - 8 = ?" in third.feedback
        assert "26 - 8 = 18" not in third.feedback
        assert "last hint" in third.feedback.lower()
        fourth = request_hint(started.session_id)
        assert fourth.hint_available is False
        assert "all the hints" in fourth.feedback.lower()
        assert "26 - 8 = ?" in fourth.feedback
        after_hints = snapshot(started.session_id)
        assert after_hints[2] == before[2] + 3
        assert after_hints[4] == 2
        assert after_hints[0] == before[0]
        assert after_hints[6] == before[6]
        assert fourth.metadata["hints_used_on_step"] == 3
        assert fourth.metadata["hint_counted"] is False
        assert model.calls == []

        wrong = submit_answer(
            started.session_id,
            AnswerRequest(answer="9", input_type="number"),
        )
        assert wrong.status == "incorrect"
        assert wrong.current_step == 2
        assert "undo" in wrong.feedback.lower()
        assert "26 - 8 = 18" not in (wrong.feedback or "")
        assert "13" not in wrong.feedback
        assert wrong.suggestion is None

        stored = _sessions[started.session_id]
        used_after_wrong = (
            stored.engine.session.get_hints_for_current_step()
        )
        assert used_after_wrong == 3
        step = stored.engine.session.get_current_step()
        correct = submit_answer(
            started.session_id,
            AnswerRequest(
                answer=str(step.expected_answer),
                input_type="number",
            ),
        )
        assert correct.current_step == 3
        reset = request_hint(started.session_id)
        assert reset.metadata["hint_level"] == 1
        assert reset.hint_available is True
        assert "18 ÷ 2 = ?" in reset.feedback or (
            "doubled" in reset.feedback.lower()
        )
        assert "18 ÷ 2 = 9" not in reset.feedback
        assert "13" not in reset.feedback

        bulgarian = start_registered(make_bottle("bg"), "bg")
        advance_to_step_two(bulgarian.session_id)
        bg_wrong = submit_answer(
            bulgarian.session_id,
            AnswerRequest(answer="7", input_type="number"),
        )
        assert "върнеш назад" in bg_wrong.feedback
        bg_hint = request_hint(bulgarian.session_id)
        assert "добавили" in bg_hint.feedback or "8" in bg_hint.feedback
        bg_second = request_hint(bulgarian.session_id)
        assert bg_second.feedback != bg_hint.feedback
        assert "изваждане" in bg_second.feedback
        bg_last = request_hint(bulgarian.session_id)
        assert bg_last.feedback != bg_second.feedback
        assert "26 - 8 = ?" in bg_last.feedback
        assert bg_last.hint_available is False
    finally:
        set_question_engine(previous)


def assert_families_and_other_engines():
    previous = get_question_engine()
    model = FakeTutorModelProvider(text=HOSTILE_MODEL)
    set_question_engine(make_engine(model))
    try:
        for template_id in (
            "cards_total",
            "more_than",
            "remaining_after_taken",
        ):
            started = start_registered(
                make_canonical(template_id),
            )
            method = submit_question(
                started.session_id,
                QuestionRequest(question="How do I solve this?"),
            )
            assert method.metadata["answer_source"] == "local"
            first = request_hint(started.session_id)
            second = request_hint(started.session_id)
            third = request_hint(started.session_id)
            assert first.status == "hint"
            assert first.feedback != second.feedback
            assert second.feedback != third.feedback
            assert first.metadata["hint_level"] == 1
            assert second.metadata["hint_level"] == 2
            assert third.metadata["hint_level"] == 3
            assert third.hint_available is False
            assert model.calls == []

        unknown = generate_unknown_number_problem(
            difficulty=1,
            seed=2,
        )
        started = start_registered(unknown)
        method = submit_question(
            started.session_id,
            QuestionRequest(question="How do I solve this?"),
        )
        assert method.metadata["answer_source"] == "local"
        arith = start_registered(
            generate_arithmetic_problem(difficulty=1, seed=9)
        )
        request_hint(arith.session_id)
        generate_sequence_or_chain_problem(difficulty=1, seed=2)

        hazelnuts = load_reverse_reasoning_problem(
            "grade4_reverse_reasoning_001"
        )
        engine = PrimarySchoolTutorEngine(problem=hazelnuts)
        first = engine.request_hint()
        second = engine.request_hint()
        assert first.feedback == second.feedback
        assert first.hint_available is True

        ode = start_session(LINEAR_ODE_FIXED_PROBLEM_ID)
        assert ode.suggested_questions == []
        physics = start_session(KINEMATICS_FIXED_PROBLEM_ID)
        assert physics.suggested_questions == []
    finally:
        set_question_engine(previous)


def assert_questions_do_not_consume_hints():
    previous = get_question_engine()
    model = FakeTutorModelProvider(text=HOSTILE_MODEL)
    set_question_engine(make_engine(model))
    try:
        started = start_registered(make_bottle(), "en")
        advance_to_step_two(started.session_id)
        before = snapshot(started.session_id)
        submit_question(
            started.session_id,
            QuestionRequest(question_id="story.step.how_to_start"),
        )
        submit_question(
            started.session_id,
            QuestionRequest(question="How do I solve this step?"),
        )
        after = snapshot(started.session_id)
        assert after[2] == before[2]
        assert after[4] == before[4]
        payload = json.dumps(
            submit_question(
                started.session_id,
                QuestionRequest(question="How do I solve this?"),
            ).metadata,
            default=str,
        )
        assert "disclosed_values" not in payload
        assert "quantities" not in payload
        assert "expected_answer" not in payload
    finally:
        set_question_engine(previous)


def assert_guided_id_still_validated():
    previous = get_question_engine()
    set_question_engine(make_engine())
    try:
        started = start_registered(make_bottle())
        try:
            submit_question(
                started.session_id,
                QuestionRequest(question_id="unknown.factor.definition"),
            )
            raise AssertionError("Wrong-family ID must fail.")
        except GuidedQuestionError:
            pass
    finally:
        set_question_engine(previous)


def assert_engine_level_bottle_repro():
    problem = make_bottle("en")
    engine = PrimarySchoolTutorEngine(problem=problem)
    engine.submit(
        StudentSubmission(answer="26", input_type="number")
    )
    first = engine.request_hint()
    second = engine.request_hint()
    third = engine.request_hint()
    fourth = engine.request_hint()
    assert first.feedback != second.feedback
    assert second.feedback != third.feedback
    assert "26 - 8 = ?" in third.feedback
    assert engine.session.get_hints_for_current_step() == 3
    assert fourth.metadata["hint_counted"] is False
    assert engine.session.get_hints_for_current_step() == 3


def assert_browser_bottle_three_distinct_hints():
    previous = get_question_engine()
    model = FakeTutorModelProvider(text=HOSTILE_MODEL)
    set_question_engine(make_engine(model))
    try:
        problem = make_browser_bottle("bg")
        engine = PrimarySchoolTutorEngine(problem=problem)
        first_step = engine.submit(
            StudentSubmission(answer="13", input_type="number")
        )
        assert first_step.current_step == 2
        first = engine.request_hint()
        second = engine.request_hint()
        third = engine.request_hint()
        fourth = engine.request_hint()
        assert first.metadata["hint_level"] == 1
        assert second.metadata["hint_level"] == 2
        assert third.metadata["hint_level"] == 3
        assert first.feedback != second.feedback
        assert second.feedback != third.feedback
        assert "добавили още 5" in first.feedback
        assert "изваждане" in second.feedback
        assert "13 - 5 = ?" in third.feedback
        assert "13 - 5 = 8" not in first.feedback
        assert "13 - 5 = 8" not in second.feedback
        assert "13 - 5 = 8" not in third.feedback
        assert "10" not in first.feedback
        assert "10" not in second.feedback
        assert first.hint_available is True
        assert second.hint_available is True
        assert third.hint_available is False
        assert fourth.hint_available is False
        assert "всички подсказки" in fourth.feedback
        assert engine.session.get_hints_for_current_step() == 3
        assert fourth.metadata["hint_counted"] is False
        assert engine.session.get_attempts_for_current_step() == 0

        english = PrimarySchoolTutorEngine(
            problem=make_browser_bottle("en"),
        )
        english.submit(
            StudentSubmission(answer="13", input_type="number")
        )
        en1 = english.request_hint()
        en2 = english.request_hint()
        en3 = english.request_hint()
        assert en1.feedback != en2.feedback
        assert en2.feedback != en3.feedback
        assert "subtraction" in en2.feedback.lower()
        assert "13 - 5 = ?" in en3.feedback
        assert "13 - 5 = 8" not in en3.feedback

        started = start_registered(make_browser_bottle("bg"), "bg")
        submit_answer(
            started.session_id,
            AnswerRequest(answer="13", input_type="number"),
        )
        before = snapshot(started.session_id)
        api1 = request_hint(started.session_id)
        api2 = request_hint(started.session_id)
        wrong = submit_answer(
            started.session_id,
            AnswerRequest(answer="7", input_type="number"),
        )
        assert wrong.status == "incorrect"
        assert wrong.current_step == 2
        stored = _sessions[started.session_id]
        assert stored.engine.session.get_hints_for_current_step() == 2
        api3 = request_hint(started.session_id)
        assert api1.feedback != api2.feedback
        assert api2.feedback != api3.feedback
        assert api1.metadata["hint_level"] == 1
        assert api2.metadata["hint_level"] == 2
        assert api3.metadata["hint_level"] == 3
        assert "изваждане" in api2.feedback
        assert "13 - 5 = ?" in api3.feedback
        assert api3.hint_available is False
        after = snapshot(started.session_id)
        assert after[2] == before[2] + 3
        assert after[3] is False
        assert after[4] == 2
        assert model.calls == []

        http_problem = make_browser_bottle("bg")
        registration = register_problem(http_problem, "bg")
        started_http = client.post(
            "/sessions/start",
            json={
                "problem_id": registration.problem_id,
                "language": "bg",
            },
        )
        assert started_http.status_code == 200
        session_id = started_http.json()["session_id"]
        answered = client.post(
            f"/sessions/{session_id}/answer",
            json={"answer": "13", "input_type": "number"},
        )
        assert answered.json()["current_step"] == 2
        http1 = client.post(f"/sessions/{session_id}/hint")
        http2 = client.post(f"/sessions/{session_id}/hint")
        http3 = client.post(f"/sessions/{session_id}/hint")
        http4 = client.post(f"/sessions/{session_id}/hint")
        body1 = http1.json()
        body2 = http2.json()
        body3 = http3.json()
        body4 = http4.json()
        assert body1["feedback"] != body2["feedback"]
        assert body2["feedback"] != body3["feedback"]
        assert body1["metadata"]["hint_level"] == 1
        assert body2["metadata"]["hint_level"] == 2
        assert body3["metadata"]["hint_level"] == 3
        assert "изваждане" in body2["feedback"]
        assert "13 - 5 = ?" in body3["feedback"]
        assert "13 - 5 = 8" not in body3["feedback"]
        assert body3["hint_available"] is False
        assert body4["hint_available"] is False
        assert body4["metadata"]["hints_used_on_step"] == 3
        live = _sessions[session_id]
        assert live.hint_requests == 3
        assert live.mastery_updated is False
        assert live.answer_submissions == 1
    finally:
        set_question_engine(previous)


def main():
    try:
        assert_engine_level_bottle_repro()
        assert_browser_bottle_three_distinct_hints()
        assert_bottle_freeform_is_local_and_safe()
        assert_progressive_hints_and_incorrect()
        assert_families_and_other_engines()
        assert_questions_do_not_consume_hints()
        assert_guided_id_still_validated()
        print("story_math_safety tests passed")
    finally:
        clear_generated_problems()


if __name__ == "__main__":
    main()
