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
from src.api.mat_pal.tutor_registry import (
    LINEAR_ODE_FIXED_PROBLEM_ID,
    SEPARABLE_ODE_FIXED_PROBLEM_ID,
)
from src.core.physics.kinematics.problems import (
    KINEMATICS_FIXED_PROBLEM_ID,
)
from src.core.question_engine import (
    FakeTutorModelProvider,
    FakeWebSearchProvider,
    GeneralTutorQuestionEngine,
)
from src.core.question_engine.guided_questions import (
    GuidedQuestionError,
)
from src.core.tutor_engine.primary_school.generation import (
    generate_arithmetic_problem,
    generate_sequence_or_chain_problem,
    generate_unknown_number_problem,
    generate_word_problem,
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


client = TestClient(app)

CANONICAL_SLOTS = {
    "cards_total": {"red": 8, "blue": 5},
    "more_than": {"base": 9, "extra": 4},
    "fewer_than": {"base": 13, "fewer": 4},
    "twice_as_many": {"base": 9},
    "books_from_class": {"girls": 6, "extra": 3},
    "remaining_after_taken": {"start": 15, "taken": 6},
    "removed_then_doubled": {"start": 15, "taken": 6},
    "removed_doubled_then_added": {
        "start": 11,
        "taken": 4,
        "added": 5,
    },
}

HAZELNUTS_ID = "grade4_reverse_reasoning_001"
HIDDEN_KEYS = {
    "x",
    "expected_answer",
    "final_answer",
    "slots",
    "quantities",
    "relations",
    "ask",
}


def make_engine(model, web):
    return GeneralTutorQuestionEngine(
        model_provider=model,
        web_search_provider=web,
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


def generate_unknown(form, language="en"):
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


def ids_of(session):
    return [
        item.question_id
        if hasattr(item, "question_id")
        else item["question_id"]
        for item in session.suggested_questions
    ]


def labels_of(session):
    return [
        item.label if hasattr(item, "label") else item["label"]
        for item in session.suggested_questions
    ]


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
        len(stored.question_history),
    )


def assert_public_payload(session):
    for item in session.suggested_questions:
        payload = (
            item.model_dump()
            if hasattr(item, "model_dump")
            else dict(item)
        )
        assert set(payload) == {
            "question_id",
            "label",
            "category",
        }
    metadata = session.metadata
    for key in HIDDEN_KEYS:
        assert key not in metadata


def assert_unknown_discovery():
    addition = start_registered(generate_unknown("x+a=b"))
    assert ids_of(addition) == [
        "unknown.addend.identify_known",
        "unknown.addend.definition",
        "unknown.addend.unknown",
        "unknown.addend.find_unknown",
    ]
    subtraction = start_registered(generate_unknown("x-a=b"))
    assert ids_of(subtraction) == [
        "unknown.subtrahend.identify_known",
        "unknown.subtrahend.definition",
        "unknown.minuend.definition",
        "unknown.minuend.find_unknown",
    ]
    multiplication = start_registered(generate_unknown("a*x=b"))
    assert ids_of(multiplication) == [
        "unknown.factor.identify_known",
        "unknown.factor.definition",
        "unknown.product.definition",
        "unknown.factor.find_unknown",
    ]
    assert "What is a factor?" in labels_of(multiplication)
    bulgarian = start_registered(
        generate_unknown("a*x=b", "bg"),
        "bg",
    )
    assert "Какво е множител?" in labels_of(bulgarian)


def assert_story_discovery_and_relations():
    more = start_registered(make_canonical_story("more_than"))
    more_ids = ids_of(more)
    assert "story.step.how_to_start" in more_ids
    assert "story.known.what_is_given" in more_ids
    assert "story.unknown.what_to_find" in more_ids
    assert "story.phrase.more_than" in more_ids
    assert "story.phrase.fewer" not in more_ids
    assert "story.phrase.twice_as_many" not in more_ids

    fewer = start_registered(make_canonical_story("fewer_than"))
    assert "story.phrase.fewer" in ids_of(fewer)
    assert "story.phrase.more_than" not in ids_of(fewer)

    twice = start_registered(make_canonical_story("twice_as_many"))
    assert "story.phrase.twice_as_many" in ids_of(twice)
    assert "story.phrase.more_than" not in ids_of(twice)

    reverse = start_registered(
        make_canonical_story("remaining_after_taken")
    )
    assert "story.phrase.remaining" in ids_of(reverse)
    assert "story.phrase.doubled" not in ids_of(reverse)

    doubled = start_registered(
        make_canonical_story("removed_then_doubled")
    )
    assert "story.phrase.doubled" in ids_of(doubled)

    cards = start_registered(make_canonical_story("cards_total"))
    assert "story.phrase.in_all" in ids_of(cards)
    assert "story.phrase.more_than" not in ids_of(cards)


def assert_story_stale_after_step_change():
    started = start_registered(
        make_canonical_story("books_from_class")
    )
    first_ids = ids_of(started)
    assert "story.phrase.more_than" in first_ids
    assert "story.phrase.twice_as_many" not in first_ids
    stored = _sessions[started.session_id]
    live = started
    while (
        live is not None
        and not live.completed
        and "story.phrase.twice_as_many" not in ids_of(live)
    ):
        step = stored.engine.session.get_current_step()
        assert step is not None
        live = submit_answer(
            started.session_id,
            AnswerRequest(
                answer=str(step.expected_answer),
                input_type="number",
            ),
        )
    assert live is not None
    later_ids = ids_of(live)
    assert "story.phrase.twice_as_many" in later_ids
    assert "story.phrase.more_than" not in later_ids
    try:
        submit_question(
            started.session_id,
            QuestionRequest(question_id="story.phrase.more_than"),
        )
        raise AssertionError("Stale story ID must be rejected.")
    except GuidedQuestionError:
        pass


def assert_arithmetic_and_pattern_discovery():
    simple = start_registered(
        generate_arithmetic_problem(difficulty=1, seed=9)
    )
    assert ids_of(simple) == ["arith.left_to_right"]
    order = start_registered(
        generate_arithmetic_problem(difficulty=2, seed=4)
    )
    assert "arith.order.first" in ids_of(order)
    parens = start_registered(
        generate_arithmetic_problem(difficulty=3, seed=3)
    )
    assert "arith.parentheses.definition" in ids_of(parens)
    assert "arith.parentheses.why" in ids_of(parens)

    sequence = start_registered(
        generate_sequence_or_chain_problem(difficulty=1, seed=2)
    )
    assert ids_of(sequence) == [
        "pattern.sequence.what",
        "pattern.sequence.rule",
    ]
    chain = start_registered(
        generate_sequence_or_chain_problem(difficulty=2, seed=5)
    )
    assert "pattern.chain.what" in ids_of(chain)
    assert "pattern.chain.follow" in ids_of(chain)
    reverse_chain = None
    for seed in range(40):
        problem = generate_sequence_or_chain_problem(
            difficulty=3,
            seed=seed,
        )
        if (
            problem.known.get("variant") == "chain"
            and problem.known.get("direction") == "reverse"
        ):
            reverse_chain = problem
            break
    assert reverse_chain is not None
    reverse_session = start_registered(reverse_chain)
    assert "pattern.chain.undo" in ids_of(reverse_session)


def assert_unsupported_contexts_are_empty():
    hazelnuts = start_session(HAZELNUTS_ID)
    assert ids_of(hazelnuts) == []
    ode = start_session(LINEAR_ODE_FIXED_PROBLEM_ID)
    assert ids_of(ode) == []
    separable = start_session(SEPARABLE_ODE_FIXED_PROBLEM_ID)
    assert ids_of(separable) == []
    physics = start_session(KINEMATICS_FIXED_PROBLEM_ID)
    assert ids_of(physics) == []


def assert_each_displayed_id_has_handler():
    previous = get_question_engine()
    model = FakeTutorModelProvider()
    web = FakeWebSearchProvider()
    set_question_engine(make_engine(model, web))
    try:
        sessions = [
            start_registered(generate_unknown("x+a=b")),
            start_registered(generate_unknown("x-a=b")),
            start_registered(generate_unknown("a*x=b")),
            start_registered(make_canonical_story("more_than")),
            start_registered(make_canonical_story("fewer_than")),
            start_registered(make_canonical_story("twice_as_many")),
            start_registered(
                generate_arithmetic_problem(difficulty=3, seed=3)
            ),
            start_registered(
                generate_sequence_or_chain_problem(
                    difficulty=1,
                    seed=2,
                )
            ),
        ]
        for session in sessions:
            for question_id in ids_of(session):
                before = snapshot_state(session.session_id)
                answered = submit_question(
                    session.session_id,
                    QuestionRequest(question_id=question_id),
                )
                assert answered is not None
                assert answered.status == "concept"
                assert answered.metadata["answer_source"] == "local"
                assert answered.metadata["used_web"] is False
                assert answered.metadata["question_route"] == "local_only"
                assert answered.feedback
                after = snapshot_state(session.session_id)
                assert after[:6] == before[:6]
                assert after[6] in {before[6], min(before[6] + 1, 3)}
                assert after[6] <= 3
                assert_public_payload(answered)
        assert model.calls == []
        assert web.queries == []
    finally:
        set_question_engine(previous)


def assert_guided_ids_never_call_providers():
    previous = get_question_engine()
    model = FakeTutorModelProvider()
    web = FakeWebSearchProvider()
    set_question_engine(make_engine(model, web))
    try:
        started = start_registered(generate_unknown("a*x=b"))
        submit_question(
            started.session_id,
            QuestionRequest(question_id="unknown.factor.definition"),
        )
        submit_question(
            started.session_id,
            QuestionRequest(
                question_id="unknown.factor.find_unknown"
            ),
        )
        story = start_registered(make_canonical_story("more_than"))
        submit_question(
            story.session_id,
            QuestionRequest(question_id="story.known.what_is_given"),
        )
        assert model.calls == []
        assert web.queries == []
    finally:
        set_question_engine(previous)


def assert_invalid_ids_rejected():
    previous = get_question_engine()
    model = FakeTutorModelProvider()
    web = FakeWebSearchProvider()
    set_question_engine(make_engine(model, web))
    try:
        addition = start_registered(generate_unknown("x+a=b"))
        before = snapshot_state(addition.session_id)
        for question_id in (
            "unknown.factor.definition",
            "not.a.real.id",
            "unknown.factor.complete",
            "complete.solution",
        ):
            try:
                submit_question(
                    addition.session_id,
                    QuestionRequest(question_id=question_id),
                )
                raise AssertionError(
                    f"{question_id} must be rejected."
                )
            except GuidedQuestionError:
                pass
        after = snapshot_state(addition.session_id)
        assert after == before
        assert model.calls == []
        assert web.queries == []

        http = client.post(
            f"/sessions/{addition.session_id}/question",
            json={"question_id": "unknown.factor.definition"},
        )
        assert http.status_code == 400
        assert snapshot_state(addition.session_id) == before
        assert model.calls == []
        assert web.queries == []
    finally:
        set_question_engine(previous)


def assert_server_derived_history_and_explanations():
    previous = get_question_engine()
    model = FakeTutorModelProvider()
    web = FakeWebSearchProvider()
    set_question_engine(make_engine(model, web))
    try:
        problem = generate_unknown("a*x=b", "bg")
        started = start_registered(problem, "bg")
        x_value = problem.known["x"]
        answered = submit_question(
            started.session_id,
            QuestionRequest(
                question="client supplied label",
                question_id="unknown.factor.definition",
            ),
        )
        assert answered is not None
        stored = _sessions[started.session_id]
        history_question = stored.question_history[-1].question
        assert history_question == "Какво е множител?"
        assert "множител" in answered.feedback
        assert f"x = {x_value}" not in answered.feedback
        method = submit_question(
            started.session_id,
            QuestionRequest(
                question_id="unknown.factor.find_unknown"
            ),
        )
        assert method is not None
        assert "÷" in method.feedback or "Разделете" in method.feedback
        assert f"x = {x_value}" not in method.feedback
        assert f"Значи x = {x_value}" not in method.feedback

        english = start_registered(generate_unknown("a*x=b"))
        en_method = submit_question(
            english.session_id,
            QuestionRequest(
                question_id="unknown.factor.find_unknown"
            ),
        )
        assert en_method is not None
        assert "x =" in en_method.feedback
        assert "÷" in en_method.feedback
        assert "So x =" not in en_method.feedback
        assert model.calls == []
        assert web.queries == []
    finally:
        set_question_engine(previous)


def assert_hint_and_history_bounds():
    previous = get_question_engine()
    set_question_engine(
        make_engine(
            FakeTutorModelProvider(),
            FakeWebSearchProvider(),
        )
    )
    try:
        started = start_registered(generate_unknown("x+a=b"))
        hinted = request_hint(started.session_id)
        assert hinted is not None
        stored = _sessions[started.session_id]
        hint_count = stored.hint_requests
        assert hint_count == 1
        for question_id in ids_of(started):
            submit_question(
                started.session_id,
                QuestionRequest(question_id=question_id),
            )
        assert stored.hint_requests == hint_count
        assert len(stored.question_history) == 3
        last = stored.question_history[-1].question
        assert last
        assert last != "unknown.addend.find_unknown"
    finally:
        set_question_engine(previous)


def assert_free_form_unchanged():
    previous = get_question_engine()
    model = FakeTutorModelProvider()
    web = FakeWebSearchProvider()
    set_question_engine(make_engine(model, web))
    try:
        started = start_registered(generate_unknown("a*x=b", "bg"), "bg")
        asked = submit_question(
            started.session_id,
            QuestionRequest(question="Какво е множител?"),
        )
        assert asked is not None
        assert asked.metadata["answer_source"] == "local"
        assert asked.metadata.get("guided_question") is not True
        general = submit_question(
            started.session_id,
            QuestionRequest(
                question="Where are equations used in real life?",
            ),
        )
        assert general is not None
        assert general.metadata["answer_source"] == "model"
        assert model.calls
    finally:
        set_question_engine(previous)


def assert_existing_regressions():
    previous = get_question_engine()
    model = FakeTutorModelProvider()
    web = FakeWebSearchProvider()
    set_question_engine(make_engine(model, web))
    try:
        ode = start_session(LINEAR_ODE_FIXED_PROBLEM_ID, language="bg")
        assert ids_of(ode) == []
        local = submit_question(
            ode.session_id,
            QuestionRequest(
                question="Защо ни е нужен интегриращ фактор?",
            ),
        )
        assert local.metadata["answer_source"] == "local"
        alt = submit_question(
            ode.session_id,
            QuestionRequest(question="Може ли да се реши по друг начин?"),
        )
        assert alt.metadata["answer_source"] == "local"
        general = submit_question(
            ode.session_id,
            QuestionRequest(question="Какво е erfi?"),
        )
        assert general.metadata["answer_source"] == "model"

        hazelnuts = start_session(HAZELNUTS_ID)
        assert ids_of(hazelnuts) == []
        problem = load_reverse_reasoning_problem(HAZELNUTS_ID)
        assert problem.get_number_of_steps() == 7
        assert problem.final_answer == 116

        generated = generate_word_problem(difficulty=1, seed=8)
        again = generate_word_problem(difficulty=1, seed=8)
        assert generated.problem_text == again.problem_text
        assert generated.known["template_id"] == again.known["template_id"]
    finally:
        set_question_engine(previous)


def hidden_numbers(problem):
    statement_ids = set(problem.known.get("statement_ids") or ())
    hidden = set()
    for name, value in (problem.known.get("quantities") or {}).items():
        if name not in statement_ids and isinstance(value, int):
            hidden.add(value)
    return hidden


def visible_numbers(problem):
    return set((problem.known.get("statement_params") or {}).values())


def assert_no_hidden_numbers(text, problem):
    for value in hidden_numbers(problem):
        if value in visible_numbers(problem):
            continue
        assert str(value) not in text, (
            f"Hidden quantity {value} leaked in: {text}"
        )


def ask_guided(session_id, question_id):
    result = submit_question(
        session_id,
        QuestionRequest(question_id=question_id),
    )
    assert result is not None
    return result


def assert_bottle_story_context_aware_explanations():
    previous = get_question_engine()
    model = FakeTutorModelProvider()
    web = FakeWebSearchProvider()
    set_question_engine(make_engine(model, web))
    try:
        bg_problem = make_canonical_story(
            "removed_doubled_then_added",
            "bg",
        )
        assert bg_problem.known["statement_params"] == {
            "taken": 4,
            "added": 5,
            "final": 19,
        }
        assert bg_problem.final_answer == 11
        bg = start_registered(bg_problem, "bg")
        before = snapshot_state(bg.session_id)
        given = ask_guided(bg.session_id, "story.known.what_is_given")
        assert given.feedback == (
            "Знаем, че първо са извадили 4 бутилки, "
            "после броят на останалите е бил удвоен, "
            "след това са добавили още 5 бутилки и "
            "накрая е имало 19 бутилки. Първоначалният "
            "брой не е даден — него трябва да намерим."
        )
        asked = ask_guided(bg.session_id, "story.unknown.what_to_find")
        assert asked.feedback == (
            "Търсим колко бутилки е имало в касата в "
            "самото начало, преди да извадят 4 бутилки."
        )
        start_step = ask_guided(
            bg.session_id,
            "story.step.how_to_start",
        )
        assert start_step.feedback == (
            "Първата стъпка пита колко бутилки е имало "
            "накрая. Прочети условието: „Накрая имало "
            "19 бутилки.“ Този брой вече е даден."
        )
        doubled = ask_guided(
            bg.session_id,
            "story.phrase.doubled",
        )
        assert "Удвоен означава умножен по 2." in doubled.feedback
        assert "3 бутилки" in doubled.feedback
        assert "6" in doubled.feedback
        assert "останали след изваждането" in doubled.feedback
        assert_no_hidden_numbers(given.feedback, bg_problem)
        assert_no_hidden_numbers(asked.feedback, bg_problem)
        assert_no_hidden_numbers(start_step.feedback, bg_problem)
        assert_no_hidden_numbers(doubled.feedback, bg_problem)
        after = snapshot_state(bg.session_id)
        assert after[:6] == before[:6]
        assert model.calls == []
        assert web.queries == []

        stored = _sessions[bg.session_id]
        first = stored.engine.session.get_current_step()
        submit_answer(
            bg.session_id,
            AnswerRequest(
                answer=str(first.expected_answer),
                input_type="number",
            ),
        )
        undo_add = ask_guided(
            bg.session_id,
            "story.step.how_to_start",
        )
        assert undo_add.feedback == (
            "В последното действие са добавили 5 "
            "бутилки. За да се върнем една стъпка "
            "назад, трябва да използваме обратното "
            "действие — изваждане. Помисли какво "
            "трябва да извадиш от крайния брой."
        )
        assert "14" not in undo_add.feedback
        second = stored.engine.session.get_current_step()
        submit_answer(
            bg.session_id,
            AnswerRequest(
                answer=str(second.expected_answer),
                input_type="number",
            ),
        )
        undo_double = ask_guided(
            bg.session_id,
            "story.step.how_to_start",
        )
        assert undo_double.feedback == (
            "Броят е бил удвоен, тоест умножен по 2. "
            "За да се върнем назад, използваме обратното "
            "действие — деление на 2."
        )
        assert "7" not in undo_double.feedback
        third = stored.engine.session.get_current_step()
        submit_answer(
            bg.session_id,
            AnswerRequest(
                answer=str(third.expected_answer),
                input_type="number",
            ),
        )
        undo_taken = ask_guided(
            bg.session_id,
            "story.step.how_to_start",
        )
        assert undo_taken.feedback == (
            "Първоначално са извадили 4 бутилки. За да "
            "възстановим началния брой, трябва да "
            "върнем тези 4 бутилки чрез събиране."
        )
        assert "11" not in undo_taken.feedback
        assert snapshot_state(bg.session_id)[0] == 3
        assert snapshot_state(bg.session_id)[3] is False

        en_problem = make_canonical_story(
            "removed_doubled_then_added",
            "en",
        )
        en = start_registered(en_problem, "en")
        en_given = ask_guided(en.session_id, "story.known.what_is_given")
        assert en_given.feedback == (
            "We know that 4 bottles were removed, the "
            "remaining number was doubled, 5 bottles "
            "were then added, and there were 19 bottles "
            "at the end. The starting number is not "
            "given — that is what we need to find."
        )
        en_ask = ask_guided(en.session_id, "story.unknown.what_to_find")
        assert en_ask.feedback == (
            "We need to find how many bottles were in "
            "the crate at the very beginning, before 4 "
            "bottles were removed."
        )
        en_start = ask_guided(en.session_id, "story.step.how_to_start")
        assert "19 bottles" in en_start.feedback
        assert "already given" in en_start.feedback
        assert_public_payload(en_given)
        assert "quantities" not in en_given.metadata
        assert "relations" not in en_given.metadata
        assert "slots" not in en_given.metadata
    finally:
        set_question_engine(previous)


def assert_story_family_guidance():
    previous = get_question_engine()
    model = FakeTutorModelProvider()
    web = FakeWebSearchProvider()
    set_question_engine(make_engine(model, web))
    try:
        several = start_registered(
            make_canonical_story("cards_total"),
            "en",
        )
        several_problem = _sessions[several.session_id].engine.problem
        given = ask_guided(
            several.session_id,
            "story.known.what_is_given",
        )
        assert "8 red cards" in given.feedback
        assert "5 blue cards" in given.feedback
        assert "total is not given" in given.feedback
        asked = ask_guided(
            several.session_id,
            "story.unknown.what_to_find",
        )
        assert "in all" in asked.feedback
        start = ask_guided(
            several.session_id,
            "story.step.how_to_start",
        )
        assert "8 red cards" in start.feedback
        assert_no_hidden_numbers(given.feedback, several_problem)
        first = _sessions[several.session_id].engine.session.get_current_step()
        submit_answer(
            several.session_id,
            AnswerRequest(
                answer=str(first.expected_answer),
                input_type="number",
            ),
        )
        total_step = ask_guided(
            several.session_id,
            "story.step.how_to_start",
        )
        assert "in all" in total_step.feedback
        assert "13" not in total_step.feedback

        comparison = start_registered(
            make_canonical_story("more_than", "bg"),
            "bg",
        )
        comparison_problem = _sessions[
            comparison.session_id
        ].engine.problem
        given_bg = ask_guided(
            comparison.session_id,
            "story.known.what_is_given",
        )
        assert "9 топчета" in given_bg.feedback
        assert "с 4 повече" in given_bg.feedback
        asked_bg = ask_guided(
            comparison.session_id,
            "story.unknown.what_to_find",
        )
        assert "Нина" in asked_bg.feedback
        assert_no_hidden_numbers(given_bg.feedback, comparison_problem)
        assert_no_hidden_numbers(asked_bg.feedback, comparison_problem)

        fewer = start_registered(make_canonical_story("fewer_than"))
        fewer_given = ask_guided(
            fewer.session_id,
            "story.known.what_is_given",
        )
        assert "13 marbles" in fewer_given.feedback
        assert "4 fewer" in fewer_given.feedback
        assert "Leo's number is not given" in fewer_given.feedback
        assert model.calls == []
        assert web.queries == []
    finally:
        set_question_engine(previous)


def assert_story_guidance_across_seeds():
    previous = get_question_engine()
    model = FakeTutorModelProvider()
    web = FakeWebSearchProvider()
    set_question_engine(make_engine(model, web))
    try:
        families = {
            1: {
                "cards_total",
                "more_than",
                "fewer_than",
                "twice_as_many",
                "remaining_after_taken",
            },
            2: {
                "stamps_then_stickers",
                "more_then_together",
                "removed_then_doubled",
            },
            3: {
                "boxes_then_stickers",
                "books_from_class",
                "removed_doubled_then_added",
            },
        }
        seen = set()
        for difficulty, expected in families.items():
            for seed in range(24):
                problem = generate_word_problem(
                    difficulty=difficulty,
                    seed=seed,
                    language="en",
                )
                template_id = problem.known["template_id"]
                if template_id in seen:
                    continue
                started = start_registered(problem, "en")
                given = ask_guided(
                    started.session_id,
                    "story.known.what_is_given",
                )
                asked = ask_guided(
                    started.session_id,
                    "story.unknown.what_to_find",
                )
                step = ask_guided(
                    started.session_id,
                    "story.step.how_to_start",
                )
                for text in (
                    given.feedback,
                    asked.feedback,
                    step.feedback,
                ):
                    assert text
                    assert "the numbers written in the story" not in text
                    assert "one unknown quantity" not in text
                    assert_no_hidden_numbers(text, problem)
                for value in visible_numbers(problem):
                    if str(value) in given.feedback:
                        break
                else:
                    raise AssertionError(
                        "Given-facts text omitted visible "
                        f"numbers for {template_id}: "
                        f"{given.feedback}"
                    )
                seen.add(template_id)
                if expected <= seen:
                    break
        assert expected_templates_covered(seen, families)
        assert model.calls == []
        assert web.queries == []
    finally:
        set_question_engine(previous)


def expected_templates_covered(seen, families):
    needed = set()
    for group in families.values():
        needed.update(group)
    return needed <= seen


def assert_completion_clears_suggestions():
    started = start_registered(generate_unknown("x+a=b"))
    stored = _sessions[started.session_id]
    live = started
    while live is not None and not live.completed:
        step = stored.engine.session.get_current_step()
        assert step is not None
        live = submit_answer(
            started.session_id,
            AnswerRequest(
                answer=str(step.expected_answer),
                input_type="number",
            ),
        )
    assert live is not None
    assert live.completed is True
    assert ids_of(live) == []
    try:
        submit_question(
            started.session_id,
            QuestionRequest(question_id="unknown.addend.definition"),
        )
        raise AssertionError("Completed session IDs must be stale.")
    except GuidedQuestionError:
        pass


def main():
    try:
        assert_unknown_discovery()
        assert_story_discovery_and_relations()
        assert_story_stale_after_step_change()
        assert_arithmetic_and_pattern_discovery()
        assert_unsupported_contexts_are_empty()
        assert_each_displayed_id_has_handler()
        assert_guided_ids_never_call_providers()
        assert_invalid_ids_rejected()
        assert_server_derived_history_and_explanations()
        assert_hint_and_history_bounds()
        assert_free_form_unchanged()
        assert_existing_regressions()
        assert_completion_clears_suggestions()
        assert_bottle_story_context_aware_explanations()
        assert_story_family_guidance()
        assert_story_guidance_across_seeds()
        print("guided_questions tests passed")
    finally:
        clear_generated_problems()


if __name__ == "__main__":
    main()
