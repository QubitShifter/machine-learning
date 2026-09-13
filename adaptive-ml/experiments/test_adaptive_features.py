from pathlib import Path
from tempfile import TemporaryDirectory

from src.api.mat_pal.adaptive_service import (
    record_session_completion,
)
from src.core.adaptive import (
    SessionPerformanceSummary,
    build_adaptive_features,
)
from src.core.adaptive.features import (
    RECENT_HISTORY_LIMIT,
    TREND_INSUFFICIENT,
    TREND_NEEDS_SUPPORT,
    TREND_STABLE,
    TREND_STRONG,
    bound_recent_sessions,
)
from src.core.student_model.progress_store import (
    get_skill_progress,
    load_progress,
    update_skill_progress,
)


def session(
    completed: bool = True,
    total_attempts: int = 1,
    incorrect_attempts: int = 0,
    hints_used: int = 0,
    first_attempt_success: bool = True,
    steps_completed: int = 1,
    total_steps: int = 1,
) -> dict:
    return {
        "completed": completed,
        "total_attempts": total_attempts,
        "incorrect_attempts": incorrect_attempts,
        "hints_used": hints_used,
        "first_attempt_success": first_attempt_success,
        "steps_completed": steps_completed,
        "total_steps": total_steps,
    }


def summary(
    completed: bool = True,
    total_attempts: int = 1,
    incorrect_attempts: int = 0,
    hints_used: int = 0,
    first_attempt_success: bool = True,
) -> SessionPerformanceSummary:
    return SessionPerformanceSummary(
        problem_id="generated_test",
        subject="mathematics",
        domain="ode",
        topic="separable_equations",
        difficulty=1,
        mastery_key="separable_equations",
        completed=completed,
        total_attempts=total_attempts,
        incorrect_attempts=incorrect_attempts,
        hints_used=hints_used,
        first_attempt_success=first_attempt_success,
        steps_completed=1,
        total_steps=1,
    )


def assert_empty_history():
    features = build_adaptive_features(
        mastery=0.50,
        questions_completed=0,
        first_attempt_streak=0,
    )

    assert features.recent_session_count == 0
    assert features.recent_completion_rate == 0.0
    assert features.recent_first_attempt_success_rate == 0.0
    assert features.recent_hint_rate == 0.0
    assert features.recent_incorrect_rate == 0.0
    assert features.recent_average_attempts_per_step == 0.0
    assert features.has_recent_history is False
    assert features.has_enough_recent_history is False
    assert features.recent_trend == TREND_INSUFFICIENT


def assert_one_recent_session():
    features = build_adaptive_features(
        mastery=0.50,
        questions_completed=1,
        first_attempt_streak=1,
        last_total_attempts=1,
        last_completed=True,
        last_first_attempt_success=True,
        recent_sessions=[session()],
    )

    assert features.recent_session_count == 1
    assert features.recent_first_attempt_success_rate == 1.0
    assert features.recent_hint_rate == 0.0
    assert features.has_enough_recent_history is False
    assert features.recent_trend == TREND_INSUFFICIENT


def assert_multiple_successful_sessions():
    features = build_adaptive_features(
        mastery=0.62,
        questions_completed=3,
        first_attempt_streak=3,
        recent_sessions=[
            session(),
            session(),
            session(),
        ],
    )

    assert features.recent_session_count == 3
    assert features.recent_completion_rate == 1.0
    assert features.recent_first_attempt_success_rate == 1.0
    assert features.recent_hint_rate == 0.0
    assert features.recent_incorrect_rate == 0.0
    assert features.recent_average_attempts_per_step == 1.0
    assert features.recent_trend == TREND_STRONG


def assert_multiple_weak_sessions():
    features = build_adaptive_features(
        mastery=0.90,
        questions_completed=4,
        first_attempt_streak=0,
        recent_sessions=[
            session(
                total_attempts=4,
                incorrect_attempts=2,
                hints_used=2,
                first_attempt_success=False,
                steps_completed=1,
                total_steps=1,
            ),
            session(
                total_attempts=3,
                incorrect_attempts=2,
                hints_used=1,
                first_attempt_success=False,
                steps_completed=1,
                total_steps=1,
            ),
            session(
                total_attempts=5,
                incorrect_attempts=3,
                hints_used=2,
                first_attempt_success=False,
                steps_completed=1,
                total_steps=1,
            ),
        ],
    )

    assert features.recent_first_attempt_success_rate == 0.0
    assert features.recent_hint_rate == 1.0
    assert features.recent_incorrect_rate == 1.0
    assert features.recent_average_attempts_per_step > 2.0
    assert features.recent_trend == TREND_NEEDS_SUPPORT


def assert_mixed_sessions():
    features = build_adaptive_features(
        mastery=0.55,
        questions_completed=3,
        first_attempt_streak=1,
        recent_sessions=[
            session(),
            session(
                total_attempts=3,
                incorrect_attempts=1,
                hints_used=1,
                first_attempt_success=False,
            ),
            session(),
        ],
    )

    assert features.recent_session_count == 3
    assert features.recent_first_attempt_success_rate == (
        0.6667
    )
    assert features.recent_hint_rate == 0.3333
    assert features.recent_incorrect_rate == 0.3333
    assert features.recent_trend == TREND_STABLE


def assert_division_by_zero_safety():
    features = build_adaptive_features(
        mastery=0.40,
        questions_completed=0,
        first_attempt_streak=0,
        recent_sessions=[],
    )

    assert features.recent_completion_rate == 0.0
    assert features.recent_average_attempts_per_step == 0.0


def assert_bounded_recent_history():
    sessions = [
        session(total_attempts=index + 1)
        for index in range(8)
    ]
    bounded = bound_recent_sessions(sessions)

    assert len(bounded) == RECENT_HISTORY_LIMIT
    assert bounded[0]["total_attempts"] == 4
    assert bounded[-1]["total_attempts"] == 8


def assert_legacy_progress_uses_one_synthetic_session():
    features = build_adaptive_features(
        mastery=0.80,
        questions_completed=4,
        first_attempt_streak=1,
        last_total_attempts=9,
        last_incorrect_attempts=1,
        last_hints_used=0,
        last_first_attempt_success=False,
        last_completed=True,
    )

    assert features.recent_session_count == 1
    assert features.recent_incorrect_rate == 1.0
    assert features.recent_hint_rate == 0.0
    assert features.recent_average_attempts_per_step == 0.0
    assert features.recent_trend == TREND_INSUFFICIENT


def assert_legacy_defaults_do_not_invent_history():
    features = build_adaptive_features(
        mastery=0.50,
        questions_completed=0,
        first_attempt_streak=0,
        last_total_attempts=0,
        last_incorrect_attempts=0,
        last_hints_used=0,
        last_first_attempt_success=False,
        last_completed=False,
    )

    assert features.recent_session_count == 0
    assert features.has_recent_history is False


def assert_persisted_history_is_capped_and_legacy_safe():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        progress = load_progress(path)
        current = get_skill_progress(
            progress,
            "separable_equations",
        )

        assert current["recent_sessions"] == []
        assert current["mastery"] == 0.5

        for index in range(7):
            update_skill_progress(
                progress=progress,
                skill="separable_equations",
                mastery=0.60,
                questions_completed=index + 1,
                first_attempt_streak=1,
                last_total_attempts=index + 1,
                last_incorrect_attempts=0,
                last_hints_used=0,
                last_first_attempt_success=True,
                last_completed=True,
                recent_session=session(
                    total_attempts=index + 1
                ),
            )

        stored = get_skill_progress(
            progress,
            "separable_equations",
        )

        assert stored["mastery"] == 0.6
        assert stored["questions_completed"] == 7
        assert len(stored["recent_sessions"]) == (
            RECENT_HISTORY_LIMIT
        )
        assert stored["recent_sessions"][0][
            "total_attempts"
        ] == 3
        assert stored["recent_sessions"][-1][
            "total_attempts"
        ] == 7


def assert_incomplete_session_does_not_append_history():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        record_session_completion(
            summary(
                completed=False,
                total_attempts=2,
                incorrect_attempts=1,
                first_attempt_success=False,
            ),
            path=path,
        )
        stored = get_skill_progress(
            load_progress(path),
            "separable_equations",
        )

        assert stored["recent_sessions"] == []
        assert stored["last_completed"] is False
        assert stored["questions_completed"] == 0


def assert_completed_session_appends_history():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        record_session_completion(
            summary(),
            path=path,
        )
        stored = get_skill_progress(
            load_progress(path),
            "separable_equations",
        )

        assert stored["questions_completed"] == 1
        assert stored["last_completed"] is True
        assert stored["mastery"] == 0.6
        assert len(stored["recent_sessions"]) == 1
        assert stored["recent_sessions"][0][
            "first_attempt_success"
        ] is True
        assert stored["recent_sessions"][0][
            "steps_completed"
        ] == 1
        assert stored["recent_sessions"][0][
            "total_steps"
        ] == 1


def assert_clean_seven_step_sessions_are_strong():
    features = build_adaptive_features(
        mastery=0.50,
        questions_completed=2,
        first_attempt_streak=2,
        recent_sessions=[
            session(
                total_attempts=7,
                steps_completed=7,
                total_steps=7,
            ),
            session(
                total_attempts=7,
                steps_completed=7,
                total_steps=7,
            ),
        ],
    )

    assert features.recent_average_attempts_per_step == 1.0
    assert features.recent_trend == TREND_STRONG


def assert_clean_eight_step_sessions_are_strong():
    features = build_adaptive_features(
        mastery=0.50,
        questions_completed=2,
        first_attempt_streak=2,
        recent_sessions=[
            session(
                total_attempts=8,
                steps_completed=8,
                total_steps=8,
            ),
            session(
                total_attempts=8,
                steps_completed=8,
                total_steps=8,
            ),
        ],
    )

    assert features.recent_average_attempts_per_step == 1.0
    assert features.recent_trend == TREND_STRONG


def assert_heavily_retried_sessions_need_support():
    features = build_adaptive_features(
        mastery=0.50,
        questions_completed=2,
        first_attempt_streak=0,
        recent_sessions=[
            session(
                total_attempts=14,
                incorrect_attempts=1,
                first_attempt_success=False,
                steps_completed=7,
                total_steps=7,
            ),
            session(
                total_attempts=14,
                incorrect_attempts=1,
                first_attempt_success=False,
                steps_completed=7,
                total_steps=7,
            ),
        ],
    )

    assert features.recent_average_attempts_per_step == 2.0
    assert features.recent_trend == TREND_NEEDS_SUPPORT


def assert_strong_and_weak_together_are_stable():
    features = build_adaptive_features(
        mastery=0.50,
        questions_completed=2,
        first_attempt_streak=2,
        recent_sessions=[
            session(
                total_attempts=14,
                steps_completed=7,
                total_steps=7,
            ),
            session(
                total_attempts=14,
                steps_completed=7,
                total_steps=7,
            ),
        ],
    )

    assert features.recent_first_attempt_success_rate == 1.0
    assert features.recent_hint_rate == 0.0
    assert features.recent_incorrect_rate == 0.0
    assert features.recent_average_attempts_per_step == 2.0
    assert features.recent_trend == TREND_STABLE


def assert_legacy_recent_sessions_without_step_counts_load():
    features = build_adaptive_features(
        mastery=0.50,
        questions_completed=2,
        first_attempt_streak=2,
        recent_sessions=[
            {
                "completed": True,
                "total_attempts": 7,
                "incorrect_attempts": 0,
                "hints_used": 0,
                "first_attempt_success": True,
            },
            {
                "completed": True,
                "total_attempts": 8,
                "incorrect_attempts": 0,
                "hints_used": 0,
                "first_attempt_success": True,
            },
        ],
    )

    assert features.recent_session_count == 2
    assert features.recent_first_attempt_success_rate == 1.0
    assert features.recent_average_attempts_per_step == 0.0
    assert features.recent_trend == TREND_STRONG


def main():
    assert_empty_history()
    assert_one_recent_session()
    assert_multiple_successful_sessions()
    assert_multiple_weak_sessions()
    assert_mixed_sessions()
    assert_division_by_zero_safety()
    assert_bounded_recent_history()
    assert_legacy_progress_uses_one_synthetic_session()
    assert_legacy_defaults_do_not_invent_history()
    assert_persisted_history_is_capped_and_legacy_safe()
    assert_incomplete_session_does_not_append_history()
    assert_completed_session_appends_history()
    assert_clean_seven_step_sessions_are_strong()
    assert_clean_eight_step_sessions_are_strong()
    assert_heavily_retried_sessions_need_support()
    assert_strong_and_weak_together_are_stable()
    assert_legacy_recent_sessions_without_step_counts_load()

    print("adaptive_features tests passed")


if __name__ == "__main__":
    main()
