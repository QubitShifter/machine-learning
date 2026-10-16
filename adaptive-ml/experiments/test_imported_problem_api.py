import json
import os

os.environ.setdefault("MATPAL_MODEL_PROVIDER", "none")
os.environ.setdefault("MATPAL_VISION_PROVIDER", "none")

from fastapi.testclient import TestClient

from src.api.mat_pal.app import app
from src.api.mat_pal.generated_problem_store import (
    clear_generated_problems,
    get_generated_problem,
)
from src.api.mat_pal.imported_problem import (
    DETAIL_NOT_SUPPORTED,
    DETAIL_PARSE,
    DETAIL_TIMEOUT,
    DETAIL_UNAVAILABLE,
)
from src.api.mat_pal.session_store import (
    _sessions,
    set_question_engine,
)
from src.core.imported_problem.contracts import (
    PLAN_SCHEMA_ID,
    PlannedStep,
    StructuredSolutionPlan,
)
from src.core.imported_problem.errors import (
    ImportedPlanParseError,
    ImportedPlannerTimeoutError,
)
from src.core.imported_problem.openai_compatible import (
    OpenAICompatibleImportedProblemPlanner,
)
from src.core.imported_problem.planner import (
    FakeImportedProblemPlanner,
    NullImportedProblemPlanner,
    set_imported_planner,
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


client = TestClient(app)

EN_STORY = (
    "Maria has 3 times as many apples as Ivan. "
    "Together they have 48. How many does Ivan have?"
)
BG_STORY = (
    "Иван има 4 ябълки. Мария има 3 пъти повече ябълки от Иван. "
    "Колко ябълки има Мария?"
)


def post_confirmed(**overrides):
    payload = {
        "transcription": "12 + 7",
        "language": "en",
        "latex_expressions": [],
        "topic_hint": None,
        "problem_type_hint": None,
    }
    payload.update(overrides)
    return client.post("/problems/from-confirmed", json=payload)


def dump_plan(**overrides) -> str:
    payload = {
        "schema": PLAN_SCHEMA_ID,
        "supported": True,
        "normalized_topic": "arithmetic",
        "title": "Arithmetic problem",
        "statement": "12 + 7",
        "final_answer": 19,
        "steps": [
            {
                "instruction": "What is 12 + 7?",
                "expected_answer": 19,
                "hints": ["Add 12 and 7."],
            }
        ],
        "unsupported_reason": None,
    }
    payload.update(overrides)
    return json.dumps(payload)


def complete_imported(problem_id: str, student_id: str) -> dict:
    registration = get_generated_problem(problem_id)
    assert registration is not None
    engine = registration.create_engine("en")
    assert isinstance(engine, PrimarySchoolTutorEngine)
    start = client.post(
        "/sessions/start",
        json={
            "problem_id": problem_id,
            "student_id": student_id,
            "language": "en",
        },
    )
    assert start.status_code == 200, start.text
    session = start.json()
    session_id = session["session_id"]
    hint = client.post(f"/sessions/{session_id}/hint")
    assert hint.status_code == 200
    assert hint.json()["status"] == "hint"
    for step in engine.problem.solution_steps:
        answer = client.post(
            f"/sessions/{session_id}/answer",
            json={
                "answer": str(step.expected_answer),
                "input_type": "number",
            },
        )
        assert answer.status_code == 200, answer.text
        session = answer.json()
    assert session["completed"] is True
    return session


def progress_snapshot() -> str:
    if not DEFAULT_PROGRESS_PATH.exists():
        return ""
    return DEFAULT_PROGRESS_PATH.read_text(encoding="utf-8")


def assert_arithmetic():
    set_imported_planner(FakeImportedProblemPlanner())
    response = post_confirmed(
        transcription="12 + 7",
        topic_hint="geometry",
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["topic"] == "arithmetic"
    assert payload["language"] == "en"
    assert payload["title"]
    assert payload["problem_id"].startswith("imported_generated_")
    assert "final_answer" not in payload
    assert "steps" not in payload
    assert "19" not in json.dumps(payload)
    stored = get_generated_problem(payload["problem_id"])
    assert stored is not None
    assert stored.metadata["imported"] is True
    assert stored.metadata["source"] == "image"
    assert stored.problem_statement == "12 + 7"


def assert_unknown_number():
    set_imported_planner(FakeImportedProblemPlanner())
    response = post_confirmed(
        transcription="2x + 5 = 17",
        latex_expressions=["2x + 5 = 17"],
        topic_hint="geometry",
        problem_type_hint="triangle",
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["topic"] == "unknown_numbers"
    stored = get_generated_problem(payload["problem_id"])
    assert stored.problem_statement == "2x + 5 = 17"


def assert_story():
    set_imported_planner(FakeImportedProblemPlanner())
    response = post_confirmed(transcription=EN_STORY)
    assert response.status_code == 200, response.text
    assert response.json()["topic"] == "story_problems"


def assert_bg_preserved():
    set_imported_planner(FakeImportedProblemPlanner())
    response = post_confirmed(
        transcription=BG_STORY,
        language="bg",
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["language"] == "bg"
    stored = get_generated_problem(payload["problem_id"])
    assert stored.problem_statement == BG_STORY
    assert stored.language == "bg"


def assert_unsupported_planner_result():
    set_imported_planner(FakeImportedProblemPlanner())
    response = post_confirmed(
        transcription="Find the perimeter of a triangle.",
        topic_hint="arithmetic",
    )
    assert response.status_code == 422
    assert response.json()["detail"] == DETAIL_NOT_SUPPORTED


def assert_unsupported_normalized_topic():
    set_imported_planner(
        FakeImportedProblemPlanner(
            StructuredSolutionPlan(
                supported=True,
                normalized_topic="geometry",
                title="Triangle",
                statement="Find the perimeter.",
                final_answer=12,
                steps=(
                    PlannedStep(
                        "What is the perimeter?",
                        12,
                        ("Add the sides.",),
                    ),
                ),
            )
        )
    )
    response = post_confirmed(
        transcription="Find the perimeter of a triangle."
    )
    assert response.status_code == 422
    assert response.json()["detail"] == DETAIL_NOT_SUPPORTED


def assert_empty_transcription():
    set_imported_planner(FakeImportedProblemPlanner())
    missing = post_confirmed(transcription="")
    assert missing.status_code == 422
    blank = post_confirmed(transcription="   ")
    assert blank.status_code == 422


def assert_unavailable():
    set_imported_planner(NullImportedProblemPlanner())
    response = post_confirmed()
    assert response.status_code == 503
    assert response.json()["detail"] == DETAIL_UNAVAILABLE


def assert_timeout():
    set_imported_planner(
        FakeImportedProblemPlanner(
            error=ImportedPlannerTimeoutError("slow")
        )
    )
    response = post_confirmed()
    assert response.status_code == 504
    assert response.json()["detail"] == DETAIL_TIMEOUT


def assert_malformed_after_retry():
    set_imported_planner(
        FakeImportedProblemPlanner(
            error=ImportedPlanParseError("bad json")
        )
    )
    response = post_confirmed()
    assert response.status_code == 422
    assert response.json()["detail"] == DETAIL_PARSE


def assert_repair_via_openai_planner():
    class ScriptedTransport:
        def __init__(self):
            self.calls = 0

        def __call__(self, payload, timeout):
            self.calls += 1
            if self.calls == 1:
                return "not-json"
            return dump_plan()

    planner = OpenAICompatibleImportedProblemPlanner(
        api_key="test-not-a-secret",
        base_url="https://example.invalid/v1",
        model="test-model",
        transport=ScriptedTransport(),
    )
    set_imported_planner(planner)
    response = post_confirmed()
    assert response.status_code == 200, response.text
    assert planner._transport.calls == 2


def assert_unknown_schema_and_extra_and_empty_steps():
    set_imported_planner(
        FakeImportedProblemPlanner(
            raw=dump_plan(schema="other.v1")
        )
    )
    unknown = post_confirmed()
    assert unknown.status_code == 422

    extra = json.loads(dump_plan())
    extra["notes"] = "no"
    set_imported_planner(
        FakeImportedProblemPlanner(raw=json.dumps(extra))
    )
    assert post_confirmed().status_code == 422

    set_imported_planner(
        FakeImportedProblemPlanner(raw=dump_plan(steps=[]))
    )
    assert post_confirmed().status_code == 422

    missing = json.loads(dump_plan())
    del missing["steps"][0]["expected_answer"]
    set_imported_planner(
        FakeImportedProblemPlanner(raw=json.dumps(missing))
    )
    assert post_confirmed().status_code == 422


def assert_session_answer_hint_question():
    set_imported_planner(FakeImportedProblemPlanner())
    set_question_engine(
        GeneralTutorQuestionEngine(
            model_provider=FakeTutorModelProvider(),
            web_search_provider=FakeWebSearchProvider(),
        )
    )
    created = post_confirmed(transcription="12 + 7")
    problem_id = created.json()["problem_id"]
    start = client.post(
        "/sessions/start",
        json={"problem_id": problem_id, "language": "en"},
    )
    assert start.status_code == 200, start.text
    session_id = start.json()["session_id"]
    assert start.json()["problem_statement"] == "12 + 7"
    hint = client.post(f"/sessions/{session_id}/hint")
    assert hint.status_code == 200
    assert hint.json()["status"] == "hint"
    question = client.post(
        f"/sessions/{session_id}/question",
        json={"question": "What should I do first?"},
    )
    assert question.status_code == 200, question.text
    payload = question.json()
    assert "expected_answer" not in json.dumps(payload)
    encoded = json.dumps(payload)
    assert '"final_answer"' not in encoded
    session = complete_imported(problem_id, "imported_skip_student")
    assert session["completed"] is True


def assert_imported_skips_mastery_generated_still_records():
    set_imported_planner(FakeImportedProblemPlanner())
    before = progress_snapshot()
    created = post_confirmed(transcription="12 + 7")
    complete_imported(
        created.json()["problem_id"],
        "imported_skip_student",
    )
    after_imported = progress_snapshot()
    assert after_imported == before

    generated = client.post(
        "/problems/generate",
        json={
            "subject": "mathematics",
            "domain": "primary_school",
            "topic": "arithmetic",
            "difficulty": 1,
            "seed": 3,
            "language": "en",
        },
    )
    assert generated.status_code == 200, generated.text
    assert generated.json()["metadata"].get("imported") is not True
    complete_imported(
        generated.json()["problem_id"],
        "imported_normal_student",
    )
    after_generated = progress_snapshot()
    assert after_generated != before or after_generated != after_imported


def assert_adaptive_unchanged():
    before = client.post(
        "/adaptive/recommendation",
        json={"subject": "mathematics", "domain": "ode"},
    )
    assert before.status_code == 200
    set_imported_planner(FakeImportedProblemPlanner())
    created = post_confirmed(transcription="12 + 7")
    complete_imported(
        created.json()["problem_id"],
        "imported_skip_student",
    )
    after = client.post(
        "/adaptive/recommendation",
        json={"subject": "mathematics", "domain": "ode"},
    )
    assert after.status_code == 200
    assert after.json()["topic"] == before.json()["topic"]
    assert after.json()["difficulty"] == before.json()["difficulty"]


def assert_no_image_data():
    body = {
        "transcription": "12 + 7",
        "language": "en",
        "latex_expressions": [],
    }
    encoded = json.dumps(body)
    assert "image" not in encoded.lower()
    assert "base64" not in encoded.lower()
    set_imported_planner(FakeImportedProblemPlanner())
    response = post_confirmed()
    stored = get_generated_problem(response.json()["problem_id"])
    metadata = json.dumps(stored.metadata)
    assert "base64" not in metadata
    assert "filename" not in metadata
    assert stored.metadata["source"] == "image"


def main():
    previous = list(_sessions.keys())
    try:
        assert_arithmetic()
        assert_unknown_number()
        assert_story()
        assert_bg_preserved()
        assert_unsupported_planner_result()
        assert_unsupported_normalized_topic()
        assert_empty_transcription()
        assert_unavailable()
        assert_timeout()
        assert_malformed_after_retry()
        assert_repair_via_openai_planner()
        assert_unknown_schema_and_extra_and_empty_steps()
        assert_session_answer_hint_question()
        assert_imported_skips_mastery_generated_still_records()
        assert_adaptive_unchanged()
        assert_no_image_data()
        print("imported_problem_api tests passed")
    finally:
        set_imported_planner(None)
        set_question_engine(None)
        clear_generated_problems()
        for session_id in list(_sessions):
            if session_id not in previous:
                _sessions.pop(session_id, None)


if __name__ == "__main__":
    main()
