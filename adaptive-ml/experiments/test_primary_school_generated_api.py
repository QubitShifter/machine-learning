import json

from fastapi.testclient import TestClient

from src.api.mat_pal.app import app
from src.api.mat_pal.generated_problem_store import (
    clear_generated_problems,
    get_generated_problem,
)
from src.api.mat_pal.problem_generation import (
    DEFAULT_PROBLEM_GENERATOR_REGISTRY,
)
from src.api.mat_pal.schemas import QuestionRequest
from src.api.mat_pal.session_store import (
    get_question_engine,
    set_question_engine,
    start_session as store_start_session,
    submit_question,
)
from src.core.question_engine import (
    FakeTutorModelProvider,
    FakeWebSearchProvider,
    GeneralTutorQuestionEngine,
)
from src.core.student_model.progress_store import (
    DEFAULT_PROGRESS_PATH,
)
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.generation import (
    generate_arithmetic_problem,
    generate_unknown_number_problem,
)


client = TestClient(app)

REVERSE_ANSWERS = [
    "7",
    "12",
    "24",
    "28",
    "56",
    "58",
    "116",
]


def write_progress(progress: dict) -> None:
    DEFAULT_PROGRESS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    DEFAULT_PROGRESS_PATH.write_text(
        json.dumps(progress, indent=4),
        encoding="utf-8",
    )


def generate_problem(
    topic: str,
    difficulty: int,
    seed: int | None = None,
    language: str = "en",
) -> dict:
    payload = {
        "subject": "mathematics",
        "domain": "primary_school",
        "topic": topic,
        "difficulty": difficulty,
        "language": language,
    }
    if seed is not None:
        payload["seed"] = seed
    response = client.post(
        "/problems/generate",
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


def post_answer(
    session_id: str,
    answer: str,
    input_type: str = "number",
) -> dict:
    response = client.post(
        f"/sessions/{session_id}/answer",
        json={
            "answer": answer,
            "input_type": input_type,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def complete_generated_session(generated: dict) -> dict:
    registration = get_generated_problem(
        generated["problem_id"]
    )
    assert registration is not None
    engine = registration.create_engine(
        generated.get("language", "en")
    )
    assert isinstance(engine, PrimarySchoolTutorEngine)
    start = client.post(
        "/sessions/start",
        json={"problem_id": generated["problem_id"]},
    )
    assert start.status_code == 200
    session = start.json()
    session_id = session["session_id"]
    assert session["expected_input_type"] == "number"
    assert session["current_step"] == 1

    for step in engine.problem.solution_steps:
        session = post_answer(
            session_id,
            str(step.expected_answer),
        )
    assert session["completed"] is True
    assert session["status"] == "complete"
    return session


def assert_catalog_exposes_generated_families():
    response = client.get("/catalog")
    assert response.status_code == 200
    mathematics = next(
        subject
        for subject in response.json()["subjects"]
        if subject["id"] == "mathematics"
    )
    primary = next(
        domain
        for domain in mathematics["domains"]
        if domain["id"] == "primary_school"
    )
    topics = {
        topic["id"]: topic
        for topic in primary["topics"]
    }
    assert topics["word_problems"][
        "generation_available"
    ] is False
    assert "grade4_reverse_reasoning_001" in (
        topics["word_problems"]["problem_ids"]
    )
    assert [
        topic["id"]
        for topic in primary["topics"]
    ] == [
        "arithmetic",
        "number_patterns",
        "unknown_numbers",
        "word_problems",
    ]
    for topic_id in (
        "arithmetic",
        "unknown_numbers",
        "number_patterns",
    ):
        assert topics[topic_id]["generation_available"] is True
        assert topics[topic_id]["supported_difficulties"] == [
            1,
            2,
            3,
        ]
        assert topics[topic_id]["available_problem_count"] == 0


def assert_generate_start_answer_completion():
    clear_generated_problems()
    write_progress({"skills": {}})
    generated = generate_problem(
        topic="arithmetic",
        difficulty=1,
        seed=6,
    )
    assert generated["generated"] is True
    assert generated["topic"] == "arithmetic"
    assert "step_specs" not in generated["metadata"]
    assert generated["expected_input_type"] == "number"
    session = complete_generated_session(generated)
    assert session["metadata"]["mastery_key"] == (
        "grade4_arithmetic"
    )
    progress = json.loads(
        DEFAULT_PROGRESS_PATH.read_text(encoding="utf-8")
    )
    skills = progress["skills"]
    assert "grade4_arithmetic" in skills
    assert "grade4_reverse_reasoning" not in skills
    assert skills["grade4_arithmetic"][
        "questions_completed"
    ] == 1


def assert_unknown_and_pattern_mastery_keys_are_separate():
    clear_generated_problems()
    write_progress({"skills": {}})
    unknown = generate_problem(
        topic="unknown_numbers",
        difficulty=1,
        seed=2,
    )
    complete_generated_session(unknown)
    patterns = generate_problem(
        topic="number_patterns",
        difficulty=1,
        seed=2,
    )
    complete_generated_session(patterns)
    progress = json.loads(
        DEFAULT_PROGRESS_PATH.read_text(encoding="utf-8")
    )
    skills = progress["skills"]
    assert "grade4_unknown_number" in skills
    assert "grade4_number_patterns" in skills
    assert "grade4_arithmetic" not in skills
    assert "grade4_reverse_reasoning" not in skills


def assert_seed_reproduces_statement():
    first = generate_problem(
        topic="arithmetic",
        difficulty=2,
        seed=11,
    )
    second = generate_problem(
        topic="arithmetic",
        difficulty=2,
        seed=11,
    )
    assert first["problem_id"] != second["problem_id"]
    assert first["problem_text"] == second["problem_text"]
    assert first["metadata"]["shape"] == (
        second["metadata"]["shape"]
    )


def assert_english_and_bulgarian_generation():
    english = generate_problem(
        topic="unknown_numbers",
        difficulty=2,
        seed=5,
        language="en",
    )
    bulgarian = generate_problem(
        topic="unknown_numbers",
        difficulty=2,
        seed=5,
        language="bg",
    )
    assert english["problem_text"] != bulgarian["problem_text"]
    assert "Find the integer x" in english["problem_text"]
    assert "Намерете цялото число x" in bulgarian["problem_text"]
    start = client.post(
        "/sessions/start",
        json={
            "problem_id": bulgarian["problem_id"],
            "language": "bg",
        },
    )
    assert start.status_code == 200
    payload = start.json()
    feedback = payload["feedback"].lower()
    assert "число" in payload["problem_statement"]
    assert "x" in payload["feedback"]
    assert "съчетано" not in feedback
    assert (
        "събираемо" in feedback
        or "умалител" in feedback
        or "множител" in feedback
    )
    assert "x" not in bulgarian["metadata"]
    assert "expected_answer" not in bulgarian["metadata"]
    assert "final_answer" not in bulgarian["metadata"]
    assert "step_specs" not in bulgarian["metadata"]
    assert bulgarian["metadata"].get("equation")


def assert_invalid_integer_does_not_complete():
    generated = generate_problem(
        topic="arithmetic",
        difficulty=1,
        seed=1,
    )
    start = client.post(
        "/sessions/start",
        json={"problem_id": generated["problem_id"]},
    )
    session_id = start.json()["session_id"]
    current = start.json()["current_step"]
    bad = post_answer(session_id, "7.5")
    assert bad["completed"] is False
    assert bad["status"] == "incorrect"
    assert bad["current_step"] == current
    empty = post_answer(session_id, "   ")
    assert empty["status"] == "incorrect"
    assert empty["current_step"] == current


def assert_unknown_number_question_uses_local_method():
    previous = get_question_engine()
    model = FakeTutorModelProvider()
    set_question_engine(
        GeneralTutorQuestionEngine(
            model_provider=model,
            web_search_provider=FakeWebSearchProvider(),
        )
    )
    try:
        generated = generate_problem(
            topic="unknown_numbers",
            difficulty=1,
            seed=2,
            language="en",
        )
        started = store_start_session(
            generated["problem_id"],
            language="en",
        )
        before_step = started.current_step
        method = submit_question(
            started.session_id,
            QuestionRequest(question="How do I solve this?"),
        )
        assert method is not None
        assert method.status == "concept"
        assert method.metadata["answer_source"] == "local"
        assert method.current_step == before_step
        assert "Subtract" in method.feedback
        assert "So x =" not in method.feedback
        general = submit_question(
            started.session_id,
            QuestionRequest(
                question="Where are equations used in real life?",
            ),
        )
        assert general is not None
        assert general.metadata["answer_source"] == "model"
        assert general.current_step == before_step
        assert started.completed is False
        live = client.get(f"/sessions/{started.session_id}")
        assert live.json()["current_step"] == before_step
        assert live.json()["completed"] is False
        assert "x" not in generated["metadata"]
        assert generated["metadata"]["form"] == "x+a=b"
    finally:
        set_question_engine(previous)


def assert_unknown_number_vocabulary_question_is_local():
    previous = get_question_engine()
    model = FakeTutorModelProvider()
    set_question_engine(
        GeneralTutorQuestionEngine(
            model_provider=model,
            web_search_provider=FakeWebSearchProvider(),
        )
    )
    try:
        generated = None
        for seed in range(40):
            candidate = generate_problem(
                topic="unknown_numbers",
                difficulty=3,
                seed=seed,
                language="bg",
            )
            if candidate["metadata"].get("form") == "a*x=b":
                generated = candidate
                break
        assert generated is not None
        started = store_start_session(
            generated["problem_id"],
            language="bg",
        )
        before_step = started.current_step
        asked = submit_question(
            started.session_id,
            QuestionRequest(question="Какво е множител?"),
        )
        assert asked is not None
        assert asked.status == "concept"
        assert asked.metadata["answer_source"] == "local"
        assert asked.current_step == before_step
        assert asked.completed is False
        assert "множител" in asked.feedback
        assert "Разделете" not in asked.feedback
        live = client.get(f"/sessions/{started.session_id}")
        assert live.json()["current_step"] == before_step
        assert live.json()["completed"] is False
        assert model.calls == []
    finally:
        set_question_engine(previous)


def assert_question_does_not_grade_or_advance():
    previous = get_question_engine()
    set_question_engine(
        GeneralTutorQuestionEngine(
            model_provider=FakeTutorModelProvider(),
            web_search_provider=FakeWebSearchProvider(),
        )
    )
    try:
        generated = generate_problem(
            topic="arithmetic",
            difficulty=1,
            seed=9,
        )
        started = store_start_session(
            generated["problem_id"],
            language="en",
        )
        before_step = started.current_step
        asked = submit_question(
            started.session_id,
            QuestionRequest(
                question="What is an expression?",
            ),
        )
        assert asked is not None
        assert asked.status == "concept"
        assert asked.current_step == before_step
        assert asked.completed is False
        live = client.get(
            f"/sessions/{started.session_id}"
        )
        assert live.status_code == 200
        assert live.json()["current_step"] == before_step
        assert live.json()["completed"] is False
    finally:
        set_question_engine(previous)


def assert_reverse_reasoning_api_regression():
    write_progress({"skills": {}})
    start = client.post(
        "/sessions/start",
        json={
            "problem_id": "grade4_reverse_reasoning_001",
        },
    )
    assert start.status_code == 200
    session = start.json()
    assert session["expected_input_type"] == "text"
    assert session["total_steps"] == 7
    session_id = session["session_id"]
    for answer in REVERSE_ANSWERS:
        session = client.post(
            f"/sessions/{session_id}/answer",
            json={
                "answer": answer,
                "input_type": "text",
            },
        ).json()
    assert session["completed"] is True
    assert session["metadata"]["final_answer"] == 116
    assert session["metadata"]["mastery_key"] == (
        "grade4_reverse_reasoning"
    )


def assert_generators_are_registered():
    registry = DEFAULT_PROBLEM_GENERATOR_REGISTRY
    for topic, name in (
        ("arithmetic", "grade4_arithmetic"),
        ("unknown_numbers", "grade4_unknown_number"),
        ("number_patterns", "grade4_number_patterns"),
    ):
        registration = registry.get(
            "mathematics",
            "primary_school",
            topic,
        )
        assert registration.generator_name == name
        assert registration.supported_difficulties == (
            1,
            2,
            3,
        )


def assert_direct_generators_match_api_seed():
    local = generate_arithmetic_problem(
        difficulty=2,
        seed=11,
        language="en",
    )
    generated = generate_problem(
        topic="arithmetic",
        difficulty=2,
        seed=11,
        language="en",
    )
    assert local.problem_text == generated["problem_text"]
    unknown = generate_unknown_number_problem(
        difficulty=1,
        seed=2,
        language="en",
    )
    generated_unknown = generate_problem(
        topic="unknown_numbers",
        difficulty=1,
        seed=2,
        language="en",
    )
    assert unknown.problem_text == (
        generated_unknown["problem_text"]
    )


def main():
    had_progress = DEFAULT_PROGRESS_PATH.exists()
    original_progress = (
        DEFAULT_PROGRESS_PATH.read_text(encoding="utf-8")
        if had_progress
        else None
    )
    try:
        assert_generators_are_registered()
        assert_catalog_exposes_generated_families()
        assert_generate_start_answer_completion()
        assert_unknown_and_pattern_mastery_keys_are_separate()
        assert_seed_reproduces_statement()
        assert_english_and_bulgarian_generation()
        assert_invalid_integer_does_not_complete()
        assert_unknown_number_question_uses_local_method()
        assert_unknown_number_vocabulary_question_is_local()
        assert_question_does_not_grade_or_advance()
        assert_reverse_reasoning_api_regression()
        assert_direct_generators_match_api_seed()
        print("primary_school_generated_api tests passed")
    finally:
        clear_generated_problems()
        if had_progress and original_progress is not None:
            DEFAULT_PROGRESS_PATH.write_text(
                original_progress,
                encoding="utf-8",
            )
        elif DEFAULT_PROGRESS_PATH.exists():
            DEFAULT_PROGRESS_PATH.unlink()


if __name__ == "__main__":
    main()
