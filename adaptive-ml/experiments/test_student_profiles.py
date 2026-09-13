import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.api.mat_pal import adaptive_service
from src.api.mat_pal import session_store
from src.api.mat_pal.adaptive_service import (
    record_session_completion,
    recommend_next,
)
from src.api.mat_pal.schemas import AnswerRequest
from src.api.mat_pal.progress_service import (
    get_student_progress,
)
from src.core.adaptive import SessionPerformanceSummary
from src.core.student_model.progress_store import (
    DEFAULT_STUDENT_ID,
    get_skill_progress,
    get_student_record,
    is_multi_student_progress,
    load_progress,
    normalize_student_id,
    save_student_record,
)


LINEAR_KEY = "linear_first_order_ode"
SEPARABLE_KEY = "separable_equations"
STUDENT_A = "student_a"
STUDENT_B = "student_b"


def write_progress(path: Path, progress: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(progress, indent=4),
        encoding="utf-8",
    )


def skill_record(
    mastery: float,
    questions_completed: int = 0,
    first_attempt_streak: int = 0,
    recent_sessions: list | None = None,
) -> dict:
    return {
        "mastery": mastery,
        "questions_completed": questions_completed,
        "first_attempt_streak": first_attempt_streak,
        "last_total_attempts": 1 if questions_completed else 0,
        "last_incorrect_attempts": 0,
        "last_hints_used": 0,
        "last_first_attempt_success": questions_completed > 0,
        "last_completed": questions_completed > 0,
        "recent_sessions": recent_sessions or [],
    }


def completion_summary(
    mastery_key: str = LINEAR_KEY,
    completed: bool = True,
    first_attempt_success: bool = True,
) -> SessionPerformanceSummary:
    return SessionPerformanceSummary(
        problem_id="profile_isolation_test",
        subject="mathematics",
        domain="ode",
        topic="first_order_linear",
        difficulty=1,
        mastery_key=mastery_key,
        completed=completed,
        total_attempts=1 if completed else 2,
        incorrect_attempts=0 if completed else 1,
        hints_used=0,
        first_attempt_success=first_attempt_success,
        steps_completed=1 if completed else 0,
        total_steps=1,
    )


def skill_for(path: Path, student_id: str, skill: str) -> dict:
    return get_skill_progress(
        get_student_record(load_progress(path), student_id),
        skill,
    )


def assert_default_student_is_local_student():
    assert DEFAULT_STUDENT_ID == "local_student"
    assert normalize_student_id(None) == "local_student"
    assert normalize_student_id("") == "local_student"
    assert normalize_student_id("  ") == "local_student"
    assert normalize_student_id("student_a") == "student_a"

    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        progress = get_student_progress(path=path)

    assert progress.student_id == "local_student"


def assert_legacy_local_student_progress_loads():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        write_progress(
            path,
            {
                "skills": {
                    LINEAR_KEY: skill_record(
                        0.88,
                        questions_completed=4,
                        first_attempt_streak=2,
                        recent_sessions=[
                            {
                                "completed": True,
                                "total_attempts": 1,
                                "incorrect_attempts": 0,
                                "hints_used": 0,
                                "first_attempt_success": True,
                                "steps_completed": 1,
                                "total_steps": 1,
                            }
                        ],
                    )
                }
            },
        )
        loaded = load_progress(path)
        guest = get_student_record(loaded, None)
        other = get_student_record(loaded, STUDENT_B)

        assert is_multi_student_progress(loaded) is False
        assert guest["skills"][LINEAR_KEY]["mastery"] == 0.88
        assert guest["skills"][LINEAR_KEY]["questions_completed"] == 4
        assert guest["skills"][LINEAR_KEY]["first_attempt_streak"] == 2
        assert len(guest["skills"][LINEAR_KEY]["recent_sessions"]) == 1
        assert other["skills"] == {}
        assert load_progress(path)["skills"][LINEAR_KEY]["mastery"] == 0.88

        dashboard = get_student_progress(path=path)
        linear = next(
            topic
            for topic in dashboard.topics
            if topic.mastery_key == LINEAR_KEY
        )
        assert dashboard.student_id == "local_student"
        assert linear.mastery == 0.88


def assert_unknown_student_gets_empty_isolated_progress():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        write_progress(
            path,
            {
                "skills": {
                    LINEAR_KEY: skill_record(0.91, 3, 1)
                }
            },
        )
        loaded = load_progress(path)
        unknown = get_skill_progress(
            get_student_record(loaded, "unknown_student"),
            LINEAR_KEY,
        )

        assert unknown["mastery"] == 0.5
        assert unknown["questions_completed"] == 0
        assert unknown["first_attempt_streak"] == 0
        assert unknown["recent_sessions"] == []
        assert load_progress(path)["skills"][LINEAR_KEY]["mastery"] == 0.91


def assert_student_updates_are_isolated():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        write_progress(path, {"skills": {}})

        record_session_completion(
            completion_summary(),
            path=path,
            student_id=STUDENT_A,
        )
        a_after = skill_for(path, STUDENT_A, LINEAR_KEY)
        b_fresh = skill_for(path, STUDENT_B, LINEAR_KEY)

        assert a_after["questions_completed"] == 1
        assert a_after["first_attempt_streak"] == 1
        assert a_after["mastery"] != 0.5
        assert len(a_after["recent_sessions"]) == 1
        assert b_fresh["mastery"] == 0.5
        assert b_fresh["questions_completed"] == 0
        assert b_fresh["first_attempt_streak"] == 0
        assert b_fresh["recent_sessions"] == []

        record_session_completion(
            completion_summary(first_attempt_success=False),
            path=path,
            student_id=STUDENT_B,
        )
        a_again = skill_for(path, STUDENT_A, LINEAR_KEY)
        b_after = skill_for(path, STUDENT_B, LINEAR_KEY)

        assert a_again["mastery"] == a_after["mastery"]
        assert a_again["questions_completed"] == 1
        assert a_again["first_attempt_streak"] == 1
        assert a_again["recent_sessions"] == a_after["recent_sessions"]
        assert b_after["questions_completed"] == 1
        assert b_after["first_attempt_streak"] == 0
        assert b_after["mastery"] != a_again["mastery"]
        assert len(b_after["recent_sessions"]) == 1


def assert_adaptive_recommendation_uses_selected_student():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        write_progress(path, {"skills": {}})
        file_data = load_progress(path)

        save_student_record(
            file_data,
            STUDENT_A,
            {
                "skills": {
                    LINEAR_KEY: skill_record(0.90, 4, 2),
                    SEPARABLE_KEY: skill_record(0.30, 1, 0),
                }
            },
            path,
        )
        file_data = load_progress(path)
        save_student_record(
            file_data,
            STUDENT_B,
            {
                "skills": {
                    LINEAR_KEY: skill_record(0.30, 1, 0),
                    SEPARABLE_KEY: skill_record(0.90, 4, 2),
                }
            },
            path,
        )

        rec_a = recommend_next(
            subject="mathematics",
            domain="ode",
            path=path,
            student_id=STUDENT_A,
        )
        rec_b = recommend_next(
            subject="mathematics",
            domain="ode",
            path=path,
            student_id=STUDENT_B,
        )

        assert rec_a.recommendation_available is True
        assert rec_b.recommendation_available is True
        assert rec_a.topic == "separable_equations"
        assert rec_b.topic == "first_order_linear"
        assert rec_a.topic != rec_b.topic


def assert_session_completion_updates_owner_only():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        write_progress(
            path,
            {
                "students": {
                    STUDENT_A: {
                        "skills": {
                            LINEAR_KEY: skill_record(0.50)
                        }
                    },
                    STUDENT_B: {
                        "skills": {
                            LINEAR_KEY: skill_record(
                                0.42,
                                questions_completed=3,
                                first_attempt_streak=2,
                                recent_sessions=[
                                    {
                                        "completed": True,
                                        "total_attempts": 1,
                                        "incorrect_attempts": 0,
                                        "hints_used": 0,
                                        "first_attempt_success": True,
                                        "steps_completed": 1,
                                        "total_steps": 1,
                                    }
                                ],
                            )
                        }
                    },
                }
            },
        )
        before_b = skill_for(path, STUDENT_B, LINEAR_KEY)

        record_session_completion(
            completion_summary(),
            path=path,
            student_id=STUDENT_A,
        )

        after_a = skill_for(path, STUDENT_A, LINEAR_KEY)
        after_b = skill_for(path, STUDENT_B, LINEAR_KEY)

        assert after_a["questions_completed"] == 1
        assert after_a["first_attempt_streak"] == 1
        assert len(after_a["recent_sessions"]) == 1
        assert after_b == before_b


def assert_incomplete_session_does_not_contaminate():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        write_progress(path, {"skills": {}})

        record_session_completion(
            completion_summary(completed=False),
            path=path,
            student_id=STUDENT_A,
        )
        a_incomplete = skill_for(path, STUDENT_A, LINEAR_KEY)
        b_untouched = skill_for(path, STUDENT_B, LINEAR_KEY)

        assert a_incomplete["questions_completed"] == 0
        assert a_incomplete["recent_sessions"] == []
        assert a_incomplete["last_completed"] is False
        assert b_untouched["mastery"] == 0.5
        assert b_untouched["questions_completed"] == 0
        assert b_untouched["recent_sessions"] == []


def assert_started_session_stores_owner():
    captured: list[str] = []
    original = adaptive_service.record_session_completion

    def fake_record(summary, path=None, student_id=DEFAULT_STUDENT_ID):
        captured.append(student_id)
        return {"mastery": 0.5}

    adaptive_service.record_session_completion = fake_record
    try:
        default_session = session_store.start_session(
            "grade4_reverse_reasoning_001"
        )
        owned_session = session_store.start_session(
            "grade4_reverse_reasoning_001",
            student_id=STUDENT_A,
        )

        assert default_session.metadata["student_id"] == "local_student"
        assert owned_session.metadata["student_id"] == STUDENT_A

        session_store.submit_answer(
            owned_session.session_id,
            AnswerRequest(
                answer="not-the-answer",
                input_type="text",
            ),
        )
        assert captured == []
    finally:
        adaptive_service.record_session_completion = original


def assert_legacy_migration_preserves_unrelated_fields():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        write_progress(
            path,
            {
                "skills": {
                    LINEAR_KEY: skill_record(0.88, 4, 2),
                },
                "future_note": "keep-me",
                "schema_hint": 2,
            },
        )
        file_data = load_progress(path)

        save_student_record(
            file_data,
            STUDENT_A,
            {
                "skills": {
                    LINEAR_KEY: skill_record(0.31, 1, 0),
                },
                "nickname": "Alice",
            },
            path,
        )

        migrated = load_progress(path)
        guest = migrated["students"][DEFAULT_STUDENT_ID]
        alice = migrated["students"][STUDENT_A]

        assert is_multi_student_progress(migrated) is True
        assert guest["future_note"] == "keep-me"
        assert guest["schema_hint"] == 2
        assert guest["skills"][LINEAR_KEY]["mastery"] == 0.88
        assert alice["nickname"] == "Alice"
        assert alice["skills"][LINEAR_KEY]["mastery"] == 0.31


def assert_legacy_local_student_save_stays_legacy_and_lossless():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        write_progress(
            path,
            {
                "skills": {
                    LINEAR_KEY: skill_record(0.5),
                },
                "future_note": "root-field",
            },
        )
        file_data = load_progress(path)
        record = get_student_record(
            file_data,
            DEFAULT_STUDENT_ID,
        )
        record["another"] = True
        save_student_record(
            file_data,
            DEFAULT_STUDENT_ID,
            record,
            path,
        )
        saved = load_progress(path)

        assert is_multi_student_progress(saved) is False
        assert saved["future_note"] == "root-field"
        assert saved["another"] is True
        assert "skills" in saved


def main():
    assert_default_student_is_local_student()
    assert_legacy_local_student_progress_loads()
    assert_unknown_student_gets_empty_isolated_progress()
    assert_legacy_migration_preserves_unrelated_fields()
    assert_legacy_local_student_save_stays_legacy_and_lossless()
    assert_student_updates_are_isolated()
    assert_adaptive_recommendation_uses_selected_student()
    assert_session_completion_updates_owner_only()
    assert_incomplete_session_does_not_contaminate()
    assert_started_session_stores_owner()
    print("student_profiles tests passed")


if __name__ == "__main__":
    main()
