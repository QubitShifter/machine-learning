import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from src.api.mat_pal import adaptive_service
from src.api.mat_pal.app import app
from src.api.mat_pal.progress_service import (
    get_student_progress,
)
from src.api.mat_pal.tutor_registry import (
    KINEMATICS_FIXED_PROBLEM_ID,
)
from src.core.adaptive import (
    SessionPerformanceSummary,
)
from src.core.student_model.progress_store import (
    DEFAULT_PROGRESS_PATH,
    get_skill_progress,
    get_student_record,
    load_progress,
)


client = TestClient(app)
FIXED_ANSWERS = [
    ("0 m/s", "units"),
    ("3 m/s^2", "units"),
    ("4 s", "units"),
    ("v = v0 + a*t", "math"),
    ("12 m/s", "units"),
    ("dx = v0*t + (1/2)*a*t**2", "math"),
    ("24 m", "units"),
    ("12 m/s and 24 m", "text"),
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


def post_answer(session_id, answer, input_type):
    response = client.post(
        f"/sessions/{session_id}/answer",
        json={
            "answer": answer,
            "input_type": input_type,
        },
    )
    assert response.status_code == 200
    return response.json()


def start_session(student_id="local_student"):
    response = client.post(
        "/sessions/start",
        json={
            "problem_id": KINEMATICS_FIXED_PROBLEM_ID,
            "student_id": student_id,
        },
    )
    assert response.status_code == 200
    return response.json()


def topic(progress, topic_id="kinematics"):
    return next(
        item
        for item in progress.topics
        if item.topic == topic_id
    )


def assert_complete_fixed_session_updates_owner_only():
    write_progress({"skills": {}})
    started = start_session("student_a")
    assert started["metadata"]["student_id"] == "student_a"
    assert started["metadata"]["topic"] == "kinematics"
    assert started["expected_input_type"] == "units"

    hint = client.post(
        f"/sessions/{started['session_id']}/hint"
    )
    assert hint.status_code == 200
    assert hint.json()["status"] == "hint"

    result = started
    for answer, input_type in FIXED_ANSWERS:
        result = post_answer(
            started["session_id"],
            answer,
            input_type,
        )

    assert result["status"] == "complete"
    assert result["completed"] is True
    assert result["metadata"]["student_id"] == "student_a"

    stored = get_skill_progress(
        get_student_record(
            load_progress(),
            "student_a",
        ),
        "kinematics",
    )
    other = get_skill_progress(
        get_student_record(
            load_progress(),
            "student_b",
        ),
        "kinematics",
    )

    assert stored["questions_completed"] == 1
    assert stored["mastery"] != 0.5
    assert len(stored["recent_sessions"]) == 1
    assert other["questions_completed"] == 0
    assert other["mastery"] == 0.5
    assert other["recent_sessions"] == []


def assert_adaptive_kinematics_is_student_scoped():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        path.write_text("{}", encoding="utf-8")

        adaptive_service.record_session_completion(
            SessionPerformanceSummary(
                problem_id=KINEMATICS_FIXED_PROBLEM_ID,
                subject="physics",
                domain="classical_mechanics",
                topic="kinematics",
                difficulty=2,
                mastery_key="kinematics",
                completed=True,
                total_attempts=8,
                incorrect_attempts=0,
                hints_used=0,
                first_attempt_success=True,
                steps_completed=8,
                total_steps=8,
            ),
            path=path,
            student_id="student_a",
        )

        progress_a = get_student_progress(
            subject="physics",
            domain="classical_mechanics",
            path=path,
            student_id="student_a",
        )
        progress_b = get_student_progress(
            subject="physics",
            domain="classical_mechanics",
            path=path,
            student_id="student_b",
        )
        kinematics_a = topic(progress_a)
        kinematics_b = topic(progress_b)

        assert kinematics_a.questions_completed == 1
        assert kinematics_a.mastery != 0.5
        assert kinematics_a.recent_session_count == 1
        assert kinematics_a.recommended_difficulty is not None
        assert kinematics_b.questions_completed == 0
        assert kinematics_b.mastery == 0.5
        assert progress_a.recommendation.topic == "kinematics"
        assert progress_b.recommendation.topic == "kinematics"
        assert progress_a.recommendation.mastery != (
            progress_b.recommendation.mastery
        )


def main():
    assert_complete_fixed_session_updates_owner_only()
    assert_adaptive_kinematics_is_student_scoped()
    print("kinematics_api_session tests passed")


if __name__ == "__main__":
    main()
