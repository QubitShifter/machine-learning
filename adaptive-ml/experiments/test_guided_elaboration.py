import json
import os
from unittest.mock import patch

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
    set_question_engine,
    start_session,
    submit_answer,
    submit_question,
)
from src.core.i18n.story_guidance import sgt
from src.core.question_engine import (
    FakeTutorModelProvider,
    FakeWebSearchProvider,
    GeneralTutorQuestionEngine,
    NullTutorModelProvider,
)
from src.core.question_engine.guided_elaboration import (
    GUIDED_STRATEGY_SCHEMA,
    outgoing_strategy_request,
    parse_strategy_response,
)
from src.core.question_engine.guided_questions import (
    GuidedQuestionError,
)
from src.core.question_engine.providers import (
    ModelProviderError,
)
from src.core.tutor_engine.primary_school.generation import (
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


client = TestClient(app)

CANONICAL_SLOTS = {
    "removed_then_doubled": {"start": 15, "taken": 6},
    "more_than": {"base": 9, "extra": 4},
}

HIDDEN_METADATA_KEYS = {
    "x",
    "expected_answer",
    "final_answer",
    "slots",
    "quantities",
    "relations",
    "ask",
    "hidden",
    "must_not_state_values",
}

QUESTION_ID = "story.phrase.doubled"


def make_engine(model, web=None):
    return GeneralTutorQuestionEngine(
        model_provider=model,
        web_search_provider=web or FakeWebSearchProvider(),
    )


def register_problem(problem, language="en"):
    known = problem.known or {}
    registration = _create_primary_school_registration(
        problem,
        prefix=problem.problem_id,
        topic=problem.topic,
        topic_name=problem.topic,
        generator_name=problem.problem_id,
        difficulty=int(known.get("difficulty") or 1),
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


def make_canonical_story(template_id, language="en"):
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


def generate_unknown(form="a*x=b", language="en"):
    difficulty = 1 if form == "x+a=b" else 3
    for seed in range(80):
        problem = generate_unknown_number_problem(
            difficulty=difficulty,
            seed=seed,
            language=language,
        )
        if problem.known["form"] == form:
            return problem
    raise AssertionError(f"Could not generate form {form}.")


def snapshot_state(session_id):
    stored = _sessions[session_id]
    live = stored.engine.get_current_response()
    return (
        stored.answer_submissions,
        stored.incorrect_submissions,
        stored.hint_requests,
        stored.mastery_updated,
        live.current_step,
        live.completed,
        tuple(
            (turn.question, turn.answer, turn.answer_source)
            for turn in stored.question_history
        ),
    )


def strategy_text(strategy, example_id=None):
    return json.dumps(
        {
            "schema": GUIDED_STRATEGY_SCHEMA,
            "strategy": strategy,
            "example_id": example_id,
        }
    )


def ask_local(session_id, question_id=QUESTION_ID):
    return submit_question(
        session_id,
        QuestionRequest(question_id=question_id),
    )


def ask_elaborate(session_id, question_id=QUESTION_ID):
    return submit_question(
        session_id,
        QuestionRequest(
            question_id=question_id,
            explanation_mode="elaborate",
        ),
    )


def optional_env(**overrides):
    values = {
        "MATPAL_GUIDED_AI_MODE": "optional",
    }
    values.update(overrides)
    return patch.dict(os.environ, values, clear=False)


def off_env():
    return patch.dict(
        os.environ,
        {"MATPAL_GUIDED_AI_MODE": "off"},
        clear=False,
    )


def hidden_values(problem):
    known = problem.known or {}
    quantities = known.get("quantities") or {}
    statement_ids = set(known.get("statement_ids") or ())
    visible = {
        name: int(quantities[name])
        for name in statement_ids
        if name in quantities
    }
    hidden = {
        name: int(value)
        for name, value in quantities.items()
        if name not in statement_ids
    }
    return visible, hidden


def serialized_provider_request(call):
    return json.dumps(
        {
            "question": call["question"],
            "prompt": call["prompt"],
            "context": call["context"],
            "messages": outgoing_strategy_request(
                question_id=QUESTION_ID,
                language=call["language"],
            )["messages"],
        },
        ensure_ascii=True,
    )


def assert_no_hidden_in_request(call, problem, session):
    visible, hidden = hidden_values(problem)
    payload = serialized_provider_request(call)
    context = call["context"]
    assert context["session_id"] is None
    assert context["student_id"] is None
    assert context["problem_id"] == ""
    assert context["problem_title"] == ""
    assert context["problem_statement"] == ""
    assert context["current_prompt"] == ""
    assert context["tutor_metadata"] == {}
    assert context["recent_question_history"] == []
    assert "must_not_state_values" not in payload
    assert "expected_answer" not in payload
    assert '"hidden"' not in payload
    assert "slots" not in payload
    assert session.session_id not in payload
    assert session.problem_id not in payload
    student_id = session.metadata.get("student_id")
    if isinstance(student_id, str) and student_id:
        assert student_id not in payload
    for name, value in hidden.items():
        marker = f'"{name}": {value}'
        assert marker not in payload
        assert f"{name}={value}" not in payload
    for value in hidden.values():
        if value in visible.values():
            continue
        assert str(value) not in call["prompt"]
        assert str(value) not in call["question"]
        assert str(value) not in json.dumps(context)


def assert_public_metadata(session):
    metadata = session.metadata
    for key in HIDDEN_METADATA_KEYS:
        assert key not in metadata
    assert "connective_before" not in metadata
    assert "connective_after" not in metadata


def start_doubled(language="en"):
    problem = make_canonical_story(
        "removed_then_doubled",
        language,
    )
    started = start_registered(problem, language)
    return problem, started


def with_fake(text=None, error=None, on_call=None):
    previous = get_question_engine()
    model = FakeTutorModelProvider(
        text=text,
        error=error,
        on_call=on_call,
    )
    set_question_engine(make_engine(model))
    return previous, model


def restore_engine(previous):
    set_question_engine(previous)


def assert_default_mode_off():
    previous, model = with_fake(text=strategy_text("analogy"))
    try:
        with off_env():
            problem, started = start_doubled()
            local = ask_local(started.session_id)
            assert local.metadata["elaboration_available"] is False
            before = snapshot_state(started.session_id)
            elaborated = ask_elaborate(started.session_id)
            assert model.calls == []
            assert elaborated.feedback == local.feedback
            assert elaborated.metadata["elaboration_status"] == "off"
            assert snapshot_state(started.session_id) == before
            assert_public_metadata(elaborated)
            assert problem.problem_id
    finally:
        restore_engine(previous)


def assert_optional_strategy_selection_and_locales():
    previous, model = with_fake(text=strategy_text("analogy"))
    try:
        with optional_env():
            _problem, started = start_doubled()
            local = ask_local(started.session_id)
            assert local.metadata["elaboration_available"] is True
            before = snapshot_state(started.session_id)
            elaborated = ask_elaborate(started.session_id)
            expected = sgt("en", "story.guide.phrase.doubled.analogy")
            assert expected in elaborated.feedback
            assert elaborated.feedback != local.feedback
            assert elaborated.metadata["elaboration_status"] == "applied"
            assert elaborated.metadata["elaboration_strategy"] == "analogy"
            assert elaborated.metadata["answer_source"] == "local"
            assert (
                elaborated.metadata["mathematical_source"]
                == "deterministic_backend"
            )
            assert (
                elaborated.metadata["explanation_selected_by_model"]
                is True
            )
            assert (
                elaborated.metadata["guided_local_explanation"]
                == local.feedback
            )
            assert snapshot_state(started.session_id)[0:6] == before[0:6]
            assert snapshot_state(started.session_id)[6] == before[6]
            assert len(model.calls) == 1
            assert model.calls[0]["timeout_seconds"] == 15.0
            assert_public_metadata(elaborated)
    finally:
        restore_engine(previous)

    previous, model = with_fake(
        text=strategy_text("simpler_words"),
    )
    try:
        with optional_env():
            _problem, started = start_doubled("bg")
            local = ask_local(started.session_id)
            elaborated = ask_elaborate(started.session_id)
            expected = sgt(
                "bg",
                "story.guide.phrase.doubled.simpler_words",
            )
            assert expected in elaborated.feedback
            assert local.feedback != elaborated.feedback
    finally:
        restore_engine(previous)

    previous, model = with_fake(
        text=strategy_text(
            "concrete_example",
            "double.apples.3x2",
        ),
    )
    try:
        with optional_env():
            _problem, started = start_doubled()
            ask_local(started.session_id)
            elaborated = ask_elaborate(started.session_id)
            expected = sgt(
                "en",
                "story.guide.phrase.doubled.example.apples",
            )
            assert expected in elaborated.feedback
            assert "separate example" in elaborated.feedback
            assert (
                elaborated.metadata["elaboration_example_id"]
                == "double.apples.3x2"
            )
    finally:
        restore_engine(previous)


def assert_fallbacks():
    cases = [
        ("not-json", "malformed JSON"),
        (
            json.dumps(
                {
                    "schema": GUIDED_STRATEGY_SCHEMA,
                    "strategy": "poem",
                    "example_id": None,
                }
            ),
            "unknown strategy",
        ),
        (
            json.dumps(
                {
                    "schema": GUIDED_STRATEGY_SCHEMA,
                    "strategy": "analogy",
                    "example_id": None,
                    "connective_before": "the start is 15",
                }
            ),
            "unexpected field",
        ),
        (
            json.dumps(
                {
                    "schema": GUIDED_STRATEGY_SCHEMA,
                    "strategy": "concrete_example",
                    "example_id": "double.oranges",
                }
            ),
            "unsupported example",
        ),
        ("", "empty output"),
    ]
    for text, label in cases:
        previous, model = with_fake(text=text)
        try:
            with optional_env():
                _problem, started = start_doubled()
                local = ask_local(started.session_id)
                before = snapshot_state(started.session_id)
                elaborated = ask_elaborate(started.session_id)
                assert elaborated.feedback == local.feedback, label
                assert (
                    elaborated.metadata["elaboration_status"]
                    == "failed"
                ), label
                assert "connective_before" not in elaborated.feedback
                assert "the start is 15" not in elaborated.feedback
                assert snapshot_state(started.session_id) == before
                assert len(model.calls) == 1
        finally:
            restore_engine(previous)

    previous, model = with_fake(
        error=ModelProviderError("provider exploded"),
    )
    try:
        with optional_env():
            _problem, started = start_doubled()
            local = ask_local(started.session_id)
            elaborated = ask_elaborate(started.session_id)
            assert elaborated.feedback == local.feedback
            assert elaborated.metadata["elaboration_status"] == "failed"
            assert "provider exploded" not in elaborated.feedback
            assert "provider exploded" not in json.dumps(
                elaborated.metadata,
                default=str,
            )
    finally:
        restore_engine(previous)

    previous, model = with_fake(error=TimeoutError("timed out"))
    try:
        with optional_env():
            _problem, started = start_doubled()
            local = ask_local(started.session_id)
            elaborated = ask_elaborate(started.session_id)
            assert elaborated.feedback == local.feedback
            assert elaborated.metadata["elaboration_status"] == "failed"
            assert "timed out" not in elaborated.feedback
            assert model.calls[0]["timeout_seconds"] == 15.0
    finally:
        restore_engine(previous)

    previous = get_question_engine()
    set_question_engine(make_engine(NullTutorModelProvider()))
    try:
        with optional_env():
            _problem, started = start_doubled()
            local = ask_local(started.session_id)
            assert local.metadata["elaboration_available"] is False
            elaborated = ask_elaborate(started.session_id)
            assert elaborated.feedback == local.feedback
            assert (
                elaborated.metadata["elaboration_status"]
                == "unavailable"
            )
    finally:
        restore_engine(previous)


def assert_unsupported_and_stale_ids():
    previous, model = with_fake(text=strategy_text("analogy"))
    try:
        with optional_env():
            _problem, started = start_doubled()
            ask_local(started.session_id)
            before = snapshot_state(started.session_id)
            unsupported = ask_elaborate(
                started.session_id,
                "story.known.what_is_given",
            )
            assert model.calls == []
            assert (
                unsupported.metadata.get("elaboration_status")
                == "unsupported"
            )
            assert snapshot_state(started.session_id)[6] == before[6]

            unknown = start_registered(generate_unknown())
            try:
                ask_elaborate(
                    unknown.session_id,
                    QUESTION_ID,
                )
                raise AssertionError(
                    "Wrong-family elaboration must be rejected."
                )
            except GuidedQuestionError:
                pass
            assert model.calls == []

            more = start_registered(
                make_canonical_story("more_than")
            )
            try:
                ask_elaborate(
                    more.session_id,
                    QUESTION_ID,
                )
                raise AssertionError(
                    "Unsupported live ID must be rejected."
                )
            except GuidedQuestionError:
                pass
            assert model.calls == []

            stored = _sessions[started.session_id]
            live = started
            while live is not None and not live.completed:
                step = stored.engine.session.get_current_step()
                if step is None:
                    break
                live = submit_answer(
                    started.session_id,
                    AnswerRequest(
                        answer=str(step.expected_answer),
                        input_type="number",
                    ),
                )
            try:
                ask_elaborate(started.session_id)
                raise AssertionError(
                    "Stale elaboration ID must be rejected."
                )
            except GuidedQuestionError:
                pass
            assert model.calls == []
    finally:
        restore_engine(previous)


def assert_duplicate_and_step_change():
    duplicate = {}

    def on_duplicate():
        duplicate["session"] = ask_elaborate(session_id)

    previous, model = with_fake(
        text=strategy_text("analogy"),
        on_call=on_duplicate,
    )
    try:
        with optional_env():
            _problem, started = start_doubled()
            session_id = started.session_id
            local = ask_local(session_id)
            before = snapshot_state(session_id)
            first = ask_elaborate(session_id)
            assert duplicate["session"].feedback == local.feedback
            assert (
                duplicate["session"].metadata["elaboration_status"]
                == "duplicate"
            )
            assert "analogy" in first.feedback.lower() or (
                "row of bottles" in first.feedback
            )
            assert snapshot_state(session_id)[6] == before[6]
            assert len(model.calls) == 1
    finally:
        restore_engine(previous)

    def on_advance():
        stored = _sessions[session_id]
        step = stored.engine.session.get_current_step()
        assert step is not None
        submit_answer(
            session_id,
            AnswerRequest(
                answer=str(step.expected_answer),
                input_type="number",
            ),
        )

    previous, model = with_fake(
        text=strategy_text("analogy"),
        on_call=on_advance,
    )
    try:
        with optional_env():
            _problem, started = start_doubled()
            session_id = started.session_id
            local = ask_local(session_id)
            before = snapshot_state(session_id)
            late = ask_elaborate(session_id)
            assert late.current_step != local.current_step
            assert late.feedback != sgt(
                "en",
                "story.guide.phrase.doubled.analogy",
            )
            after = snapshot_state(session_id)
            assert after[4] == before[4] + 1
            assert after[6] == before[6]
            assert after[0] == before[0] + 1
    finally:
        restore_engine(previous)


def assert_no_hidden_data_or_model_prose():
    previous, model = with_fake(
        text=strategy_text("analogy")
        + "\nThe starting number is 15.",
    )
    try:
        with optional_env():
            problem, started = start_doubled()
            local = ask_local(started.session_id)
            elaborated = ask_elaborate(started.session_id)
            assert elaborated.feedback == local.feedback
            assert "The starting number is 15." not in (
                elaborated.feedback
            )
            call = model.calls[0]
            assert_no_hidden_in_request(call, problem, started)
            _, hidden = hidden_values(problem)
            for value in hidden.values():
                visible, _hidden = hidden_values(problem)
                if value in visible.values():
                    continue
                assert str(value) not in elaborated.feedback
            assert_public_metadata(elaborated)
            http = client.post(
                f"/sessions/{started.session_id}/question",
                json={
                    "question_id": QUESTION_ID,
                    "explanation_mode": "elaborate",
                    "explanation": "the answer is 15",
                    "expected_answer": 15,
                },
            )
            assert http.status_code == 200
            body = http.json()
            assert "the answer is 15" not in body["feedback"]
            assert "expected_answer" not in body["metadata"]
    finally:
        restore_engine(previous)

    selection = parse_strategy_response(
        strategy_text("analogy"),
        question_id=QUESTION_ID,
    )
    assert selection is not None
    assert selection.strategy == "analogy"
    assert (
        parse_strategy_response(
            '{"schema":"nope","strategy":"analogy","example_id":null}',
            question_id=QUESTION_ID,
        )
        is None
    )


def assert_free_form_and_existing_guided_unchanged():
    previous, model = with_fake(text=strategy_text("analogy"))
    try:
        with optional_env():
            _problem, started = start_doubled()
            free = submit_question(
                started.session_id,
                QuestionRequest(
                    question="Where are story problems used in real life?",
                ),
            )
            assert free.status == "concept"
            assert model.calls
            prompt = model.calls[0]["prompt"]
            assert "matpal.guided_strategy.v1" not in prompt
            assert "Allowed strategies" not in prompt

            unknown = start_registered(generate_unknown())
            guided = ask_local(
                unknown.session_id,
                "unknown.factor.definition",
            )
            assert guided.metadata["answer_source"] == "local"
            assert guided.metadata["elaboration_available"] is False
            assert "factor" in guided.feedback.lower()
    finally:
        restore_engine(previous)


def assert_no_grading_or_mastery_mutation():
    previous, model = with_fake(text=strategy_text("analogy"))
    try:
        with optional_env():
            _problem, started = start_doubled()
            local = ask_local(started.session_id)
            before = snapshot_state(started.session_id)
            ask_elaborate(started.session_id)
            after = snapshot_state(started.session_id)
            assert after[0:6] == before[0:6]
            assert after[6] == before[6]
            stored = _sessions[started.session_id]
            assert stored.last_response.status == "concept"
            assert local.status == "concept"
    finally:
        restore_engine(previous)


def main():
    try:
        assert_default_mode_off()
        assert_optional_strategy_selection_and_locales()
        assert_fallbacks()
        assert_unsupported_and_stale_ids()
        assert_duplicate_and_step_change()
        assert_no_hidden_data_or_model_prose()
        assert_free_form_and_existing_guided_unchanged()
        assert_no_grading_or_mastery_mutation()
        print("guided_elaboration tests passed")
    finally:
        clear_generated_problems()


if __name__ == "__main__":
    main()
