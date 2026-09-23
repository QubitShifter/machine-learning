"""Phase 27 Stage D2a — Logical Reasoning family selection."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.mat_pal import adaptive_service
from src.api.mat_pal import progress_service
from src.api.mat_pal.app import app
from src.api.mat_pal.adaptive_service import (
    list_topic_states,
    record_session_completion,
    recommend_next,
)
from src.core.adaptive import (
    AdaptiveTopicState,
    RecentSession,
    RuleBasedAdaptivePolicy,
    SessionPerformanceSummary,
)
from src.core.adaptive.features import (
    FAMILY_MATH_ERROR_SESSION_THRESHOLD,
    LOGICAL_REASONING_FAMILY_ORDER,
    LOGICAL_REASONING_HISTORY_FAMILIES,
    family_window_stats,
)
from src.core.adaptive.policy import (
    FAMILY_INSUFFICIENT_HISTORY,
    FAMILY_LEAST_PRACTICED,
    FAMILY_RECENT_CORRECTIONS,
    FAMILY_VARIETY,
)
from src.core.student_model.progress_store import (
    DEFAULT_STUDENT_ID,
)

import test_performance_history as history
from src.core.student_model.student import StudentModel
from src.core.tutor_engine.primary_school.generation.logical_reasoning import (
    FAMILY_DISTRIBUTION,
    FAMILY_LOGIC_DETECTIVE,
    FAMILY_NUMBER_DETECTIVE,
    LOGICAL_REASONING_FAMILIES,
    select_logical_reasoning_family,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    SUPPORTED_FAMILIES,
)


client = TestClient(app)
REAL_PROGRESS_PATH = Path(
    "math/ode/data/student_progress.json"
)
LOGIC_KEY = "grade4_logical_reasoning"
STUDENT_A = "phase27_d2a_student_a"
STUDENT_B = "phase27_d2a_student_b"


def real_progress_bytes() -> bytes | None:
    if not REAL_PROGRESS_PATH.exists():
        return None
    return REAL_PROGRESS_PATH.read_bytes()


@contextmanager
def isolated_progress():
    before = real_progress_bytes()
    original_recommend = adaptive_service.recommend_next
    original_progress = (
        progress_service.get_student_progress
    )
    original_record = (
        adaptive_service.record_session_completion
    )
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"

        def recommend_with_temp(
            subject=None,
            domain=None,
            path=path,
            student_id=DEFAULT_STUDENT_ID,
        ):
            return original_recommend(
                subject=subject,
                domain=domain,
                path=path,
                student_id=student_id,
            )

        def progress_with_temp(
            subject=None,
            domain=None,
            path=path,
            student_id=None,
        ):
            return original_progress(
                subject=subject,
                domain=domain,
                path=path,
                student_id=student_id,
            )

        def record_with_temp(
            summary,
            path=path,
            student_id=DEFAULT_STUDENT_ID,
        ):
            return original_record(
                summary,
                path=path,
                student_id=student_id,
            )

        with patch.object(
            adaptive_service,
            "recommend_next",
            recommend_with_temp,
        ), patch.object(
            progress_service,
            "get_student_progress",
            progress_with_temp,
        ), patch.object(
            adaptive_service,
            "record_session_completion",
            record_with_temp,
        ):
            yield path
    assert real_progress_bytes() == before


def write_progress(path: Path, progress: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(progress, indent=4),
        encoding="utf-8",
    )


def family_session(
    family: str | None,
    *,
    incorrect: int = 0,
    invalid: int = 0,
    hints: int = 0,
    completed: bool = True,
) -> RecentSession:
    return RecentSession(
        completed=completed,
        total_attempts=max(1, incorrect + 1),
        incorrect_attempts=incorrect,
        hints_used=hints,
        first_attempt_success=(
            completed and incorrect == 0 and hints == 0
        ),
        steps_completed=1 if completed else 0,
        total_steps=1,
        family=family,
        difficulty=1,
        invalid_attempts=invalid,
    )


def logic_topic(
    recent_sessions: tuple[RecentSession, ...] = (),
    mastery: float = 0.40,
    questions_completed: int | None = None,
    generation_available: bool = True,
    problem_id: str | None = None,
    topic: str = "logical_reasoning",
) -> AdaptiveTopicState:
    return AdaptiveTopicState(
        subject="mathematics",
        domain="primary_school",
        topic=topic,
        topic_name="Logical Reasoning",
        mastery_key=LOGIC_KEY,
        mastery=mastery,
        questions_completed=(
            len(recent_sessions)
            if questions_completed is None
            else questions_completed
        ),
        first_attempt_streak=0,
        supported_difficulties=(1, 2, 3),
        generation_available=generation_available,
        problem_id=problem_id,
        recent_sessions=recent_sessions,
    )


def other_topic(
    topic: str,
    mastery: float,
    *,
    generation_available: bool = True,
    problem_id: str | None = None,
    recent_sessions: tuple[RecentSession, ...] = (),
) -> AdaptiveTopicState:
    return AdaptiveTopicState(
        subject="mathematics",
        domain="primary_school",
        topic=topic,
        topic_name=topic.replace("_", " ").title(),
        mastery_key=topic,
        mastery=mastery,
        questions_completed=len(recent_sessions),
        first_attempt_streak=0,
        supported_difficulties=(1, 2, 3),
        generation_available=generation_available,
        problem_id=problem_id,
        recent_sessions=recent_sessions,
    )


def recommend(topic: AdaptiveTopicState):
    return RuleBasedAdaptivePolicy().recommend_next(
        [topic]
    )


def session_payload(
    family: str | None,
    *,
    incorrect: int = 0,
    invalid: int = 0,
    hints: int = 0,
) -> dict:
    payload = {
        "completed": True,
        "total_attempts": max(1, incorrect + 1),
        "incorrect_attempts": incorrect,
        "hints_used": hints,
        "first_attempt_success": (
            incorrect == 0 and hints == 0
        ),
        "steps_completed": 1,
        "total_steps": 1,
        "invalid_attempts": invalid,
    }
    if family is not None:
        payload["family"] = family
    return payload


def skill_record(
    mastery: float,
    recent_sessions: list[dict],
) -> dict:
    last = recent_sessions[-1] if recent_sessions else {}
    return {
        "mastery": mastery,
        "questions_completed": len(recent_sessions),
        "first_attempt_streak": 0,
        "last_total_attempts": last.get(
            "total_attempts",
            0,
        ),
        "last_incorrect_attempts": last.get(
            "incorrect_attempts",
            0,
        ),
        "last_hints_used": last.get("hints_used", 0),
        "last_first_attempt_success": last.get(
            "first_attempt_success",
            False,
        ),
        "last_completed": bool(recent_sessions),
        "recent_sessions": recent_sessions,
    }


def completion_summary(
    family: str | None = FAMILY_NUMBER_DETECTIVE,
    incorrect: int = 0,
    invalid: int = 0,
    hints: int = 0,
    problem_id: str = "d2a_family_problem",
) -> SessionPerformanceSummary:
    return SessionPerformanceSummary(
        problem_id=problem_id,
        subject="mathematics",
        domain="primary_school",
        topic="logical_reasoning",
        difficulty=1,
        mastery_key=LOGIC_KEY,
        completed=True,
        total_attempts=max(1, incorrect + 1),
        incorrect_attempts=incorrect,
        hints_used=hints,
        first_attempt_success=(
            incorrect == 0 and hints == 0
        ),
        steps_completed=1,
        total_steps=1,
        family=family,
        invalid_attempts=invalid,
    )


def assert_canonical_family_list():
    assert LOGICAL_REASONING_FAMILY_ORDER == (
        FAMILY_NUMBER_DETECTIVE,
        FAMILY_DISTRIBUTION,
        FAMILY_LOGIC_DETECTIVE,
    )
    assert LOGICAL_REASONING_FAMILY_ORDER == (
        SUPPORTED_FAMILIES
    )
    assert LOGICAL_REASONING_FAMILY_ORDER == (
        LOGICAL_REASONING_FAMILIES
    )
    assert LOGICAL_REASONING_HISTORY_FAMILIES == set(
        LOGICAL_REASONING_FAMILY_ORDER
    )
    assert FAMILY_MATH_ERROR_SESSION_THRESHOLD == 2


def assert_cold_start():
    recommendation = recommend(logic_topic())
    assert recommendation.family == FAMILY_NUMBER_DETECTIVE
    assert recommendation.metadata["family_reason"] == (
        FAMILY_INSUFFICIENT_HISTORY
    )
    assert "Number Detective" in recommendation.reason
    assert "distribution_puzzles" not in recommendation.reason


def assert_legacy_history_is_cold_start():
    recommendation = recommend(
        logic_topic(
            (
                family_session(None, incorrect=2),
                family_session(None, incorrect=1),
            )
        )
    )
    assert recommendation.family == FAMILY_NUMBER_DETECTIVE
    assert recommendation.metadata["family_reason"] == (
        FAMILY_INSUFFICIENT_HISTORY
    )


def assert_one_family_avoids_repetition():
    recommendation = recommend(
        logic_topic(
            (family_session(FAMILY_NUMBER_DETECTIVE),)
        )
    )
    assert recommendation.family == FAMILY_DISTRIBUTION
    assert recommendation.metadata["family_reason"] == (
        FAMILY_LEAST_PRACTICED
    )
    assert "Distribution Puzzles" in recommendation.reason


def assert_targeted_mathematical_practice():
    recommendation = recommend(
        logic_topic(
            (
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                ),
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=1,
                ),
                family_session(FAMILY_DISTRIBUTION),
            )
        )
    )
    assert recommendation.family == FAMILY_NUMBER_DETECTIVE
    assert recommendation.metadata["family_reason"] == (
        FAMILY_RECENT_CORRECTIONS
    )
    assert "Number Detective" in recommendation.reason
    assert "variety" not in recommendation.reason.lower()


def assert_one_mathematical_error_is_insufficient():
    recommendation = recommend(
        logic_topic(
            (
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=4,
                ),
            )
        )
    )
    assert recommendation.family == FAMILY_DISTRIBUTION
    assert recommendation.metadata["family_reason"] == (
        FAMILY_LEAST_PRACTICED
    )
    assert recommendation.metadata["family_reason"] != (
        FAMILY_RECENT_CORRECTIONS
    )


def assert_repetition_guard_uses_variety():
    recommendation = recommend(
        logic_topic(
            (
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                ),
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=1,
                ),
            )
        )
    )
    assert recommendation.family == FAMILY_DISTRIBUTION
    assert recommendation.metadata["family_reason"] == (
        FAMILY_VARIETY
    )
    assert "different kind" in recommendation.reason
    assert "Recent Distribution" not in recommendation.reason


def assert_targeted_family_can_return():
    recommendation = recommend(
        logic_topic(
            (
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                ),
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=1,
                ),
                family_session(FAMILY_DISTRIBUTION),
            )
        )
    )
    assert recommendation.family == FAMILY_NUMBER_DETECTIVE
    assert recommendation.metadata["family_reason"] == (
        FAMILY_RECENT_CORRECTIONS
    )


def assert_format_only_errors_are_not_targeted():
    recommendation = recommend(
        logic_topic(
            (
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                    invalid=2,
                ),
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=3,
                    invalid=3,
                ),
            )
        )
    )
    assert recommendation.family == FAMILY_DISTRIBUTION
    assert recommendation.metadata["family_reason"] == (
        FAMILY_LEAST_PRACTICED
    )


def assert_hints_without_math_errors_are_not_targeted():
    recommendation = recommend(
        logic_topic(
            (
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    hints=2,
                ),
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    hints=3,
                ),
            )
        )
    )
    assert recommendation.family == FAMILY_DISTRIBUTION
    assert recommendation.metadata["family_reason"] == (
        FAMILY_LEAST_PRACTICED
    )


def assert_mixed_errors_count_only_math():
    one = recommend(
        logic_topic(
            (
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                    invalid=1,
                ),
            )
        )
    )
    assert one.family == FAMILY_DISTRIBUTION
    assert one.metadata["family_reason"] == (
        FAMILY_LEAST_PRACTICED
    )

    two = recommend(
        logic_topic(
            (
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                    invalid=1,
                ),
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=3,
                    invalid=1,
                ),
                family_session(FAMILY_LOGIC_DETECTIVE),
            )
        )
    )
    assert two.family == FAMILY_NUMBER_DETECTIVE
    assert two.metadata["family_reason"] == (
        FAMILY_RECENT_CORRECTIONS
    )


def assert_five_distribution_puzzles_cover_another():
    recommendation = recommend(
        logic_topic(
            tuple(
                family_session(FAMILY_DISTRIBUTION)
                for _ in range(5)
            )
        )
    )
    assert recommendation.family == FAMILY_NUMBER_DETECTIVE
    assert recommendation.metadata["family_reason"] == (
        FAMILY_LEAST_PRACTICED
    )


def assert_history_rollover_forgets_older_evidence():
    still_present = recommend(
        logic_topic(
            (
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                ),
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                ),
                family_session(FAMILY_DISTRIBUTION),
                family_session(FAMILY_LOGIC_DETECTIVE),
                family_session(FAMILY_DISTRIBUTION),
            )
        )
    )
    assert still_present.family == (
        FAMILY_NUMBER_DETECTIVE
    )
    assert still_present.metadata["family_reason"] == (
        FAMILY_RECENT_CORRECTIONS
    )

    forgotten = recommend(
        logic_topic(
            (
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                ),
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                ),
                family_session(FAMILY_DISTRIBUTION),
                family_session(FAMILY_LOGIC_DETECTIVE),
                family_session(FAMILY_DISTRIBUTION),
                family_session(FAMILY_LOGIC_DETECTIVE),
                family_session(FAMILY_DISTRIBUTION),
            )[-5:]
        )
    )
    stats = family_window_stats(
        forgotten.metadata
        and logic_topic(
            (
                family_session(FAMILY_DISTRIBUTION),
                family_session(FAMILY_LOGIC_DETECTIVE),
                family_session(FAMILY_DISTRIBUTION),
                family_session(FAMILY_LOGIC_DETECTIVE),
                family_session(FAMILY_DISTRIBUTION),
            )
        ).recent_sessions
    )
    assert stats[FAMILY_NUMBER_DETECTIVE].completed == 0
    assert forgotten.family != FAMILY_NUMBER_DETECTIVE or (
        forgotten.metadata["family_reason"]
        != FAMILY_RECENT_CORRECTIONS
    )
    assert forgotten.family == FAMILY_NUMBER_DETECTIVE
    assert forgotten.metadata["family_reason"] == (
        FAMILY_LEAST_PRACTICED
    )


def assert_difficulty_parity():
    topic = logic_topic(
        (
            family_session(
                FAMILY_NUMBER_DETECTIVE,
                incorrect=2,
            ),
            family_session(
                FAMILY_NUMBER_DETECTIVE,
                incorrect=1,
            ),
            family_session(FAMILY_DISTRIBUTION),
        ),
        mastery=0.50,
    )
    policy = RuleBasedAdaptivePolicy()
    recommendation = policy.recommend_next([topic])
    assert recommendation.difficulty == (
        policy.choose_difficulty(topic)
    )
    assert recommendation.family == (
        FAMILY_NUMBER_DETECTIVE
    )


def assert_topic_ranking_parity():
    policy = RuleBasedAdaptivePolicy()
    arithmetic = other_topic("arithmetic", 0.20)
    logic = logic_topic(
        (
            family_session(
                FAMILY_NUMBER_DETECTIVE,
                incorrect=2,
            ),
            family_session(
                FAMILY_NUMBER_DETECTIVE,
                incorrect=2,
            ),
        ),
        mastery=0.80,
    )
    recommendation = policy.recommend_next(
        [logic, arithmetic]
    )
    assert recommendation.topic == "arithmetic"
    assert recommendation.family is None
    assert "family_reason" not in recommendation.metadata


def assert_mastery_parity():
    with isolated_progress() as path:
        first = record_session_completion(
            completion_summary(
                family=FAMILY_NUMBER_DETECTIVE,
                problem_id="d2a_mastery_a",
            ),
            path=path,
            student_id=STUDENT_A,
        )
        second = record_session_completion(
            completion_summary(
                family=FAMILY_DISTRIBUTION,
                problem_id="d2a_mastery_b",
            ),
            path=path,
            student_id=STUDENT_B,
        )
        expected = StudentModel(student_id="expected")
        expected.initialize_skill(
            skill_id=LOGIC_KEY,
            initial_mastery=0.50,
        )
        after_one = expected.update_mastery_after_question(
            skill_id=LOGIC_KEY,
            attempts=1,
            final_evaluation={
                "correct": True,
                "parse_error": False,
            },
        )
        assert first["mastery"] == after_one
        assert second["mastery"] == after_one
        assert first["questions_completed"] == 1
        assert second["questions_completed"] == 1


def assert_non_logical_reasoning_has_null_family():
    recommendation = recommend(
        other_topic("arithmetic", 0.40)
    )
    assert recommendation.family is None
    assert "family" not in recommendation.metadata
    assert "family_reason" not in recommendation.metadata


def assert_static_catalog_has_null_family():
    recommendation = recommend(
        other_topic(
            "word_problems",
            0.40,
            generation_available=False,
            problem_id="hazelnuts",
        )
    )
    assert recommendation.family is None
    assert recommendation.difficulty is None
    assert "family_reason" not in recommendation.metadata


def assert_student_profiles_are_isolated():
    with isolated_progress() as path:
        write_progress(
            path,
            {
                "students": {
                    STUDENT_A: {
                        "skills": {
                            LOGIC_KEY: skill_record(
                                0.40,
                                [
                                    session_payload(
                                        FAMILY_NUMBER_DETECTIVE,
                                        incorrect=2,
                                    ),
                                    session_payload(
                                        FAMILY_NUMBER_DETECTIVE,
                                        incorrect=1,
                                    ),
                                ],
                            )
                        }
                    },
                    STUDENT_B: {
                        "skills": {
                            LOGIC_KEY: skill_record(
                                0.40,
                                [
                                    session_payload(
                                        FAMILY_DISTRIBUTION
                                    ),
                                ],
                            )
                        }
                    },
                }
            },
        )
        first = recommend_next(
            subject="mathematics",
            domain="primary_school",
            path=path,
            student_id=STUDENT_A,
        )
        second = recommend_next(
            subject="mathematics",
            domain="primary_school",
            path=path,
            student_id=STUDENT_B,
        )
        assert first.family == FAMILY_DISTRIBUTION
        assert first.metadata["family_reason"] == (
            FAMILY_VARIETY
        )
        assert second.family == FAMILY_NUMBER_DETECTIVE
        assert second.metadata["family_reason"] == (
            FAMILY_LEAST_PRACTICED
        )


def assert_duplicate_completion_does_not_double_count():
    previous = history.use_unavailable_model()
    try:
        with isolated_progress() as path:
            generated = history.generate_problem(
                topic="logical_reasoning",
                difficulty=1,
                family=FAMILY_LOGIC_DETECTIVE,
                seed=3,
            )
            completed = history.complete_generated(
                generated,
                STUDENT_A,
            )
            session_id = completed["_session_id"]
            first = history.skill_history(
                path,
                STUDENT_A,
                LOGIC_KEY,
            )
            extra = history.post_answer(session_id, "1")
            assert extra["completed"] is True
            second = history.skill_history(
                path,
                STUDENT_A,
                LOGIC_KEY,
            )
            assert first["questions_completed"] == 1
            assert second["questions_completed"] == 1
            assert first["mastery"] == second["mastery"]
            assert len(first["recent_sessions"]) == 1
            assert len(second["recent_sessions"]) == 1
            assert (
                first["recent_sessions"]
                == second["recent_sessions"]
            )
            topic = next(
                item
                for item in list_topic_states(
                    "mathematics",
                    "primary_school",
                    path,
                    STUDENT_A,
                )
                if item.topic == "logical_reasoning"
            )
            family, reason = (
                RuleBasedAdaptivePolicy().choose_family(
                    topic
                )
            )
            assert family == FAMILY_NUMBER_DETECTIVE
            assert reason == FAMILY_LEAST_PRACTICED
    finally:
        from src.api.mat_pal.session_store import (
            set_question_engine,
        )
        set_question_engine(previous)


def assert_recommendation_surfaces_agree():
    with isolated_progress() as path:
        write_progress(
            path,
            {
                "skills": {
                    LOGIC_KEY: skill_record(
                        0.35,
                        [
                            session_payload(
                                FAMILY_NUMBER_DETECTIVE,
                                incorrect=2,
                            ),
                            session_payload(
                                FAMILY_NUMBER_DETECTIVE,
                                incorrect=1,
                            ),
                            session_payload(
                                FAMILY_DISTRIBUTION
                            ),
                        ],
                    )
                }
            },
        )
        posted = client.post(
            "/adaptive/recommendation",
            json={
                "subject": "mathematics",
                "domain": "primary_school",
                "student_id": DEFAULT_STUDENT_ID,
            },
        )
        dashboard = client.get(
            "/progress"
            "?subject=mathematics"
            "&domain=primary_school"
            f"&student_id={DEFAULT_STUDENT_ID}"
        )
        assert posted.status_code == 200, posted.text
        assert dashboard.status_code == 200, dashboard.text
        recommendation = posted.json()
        progress = dashboard.json()["recommendation"]
        assert recommendation["family"] == (
            FAMILY_NUMBER_DETECTIVE
        )
        assert recommendation["metadata"][
            "family_reason"
        ] == FAMILY_RECENT_CORRECTIONS
        assert progress["family"] == recommendation["family"]
        assert progress["metadata"]["family_reason"] == (
            recommendation["metadata"]["family_reason"]
        )
        assert progress["topic"] == recommendation["topic"]
        assert progress["difficulty"] == (
            recommendation["difficulty"]
        )


def assert_explicit_family_wins_over_seed():
    assert select_logical_reasoning_family(
        family=FAMILY_LOGIC_DETECTIVE,
        seed=0,
    ) == FAMILY_LOGIC_DETECTIVE
    assert select_logical_reasoning_family(
        seed=0,
    ) == FAMILY_NUMBER_DETECTIVE


def assert_english_reason_uses_display_names():
    recommendation = recommend(logic_topic())
    assert "number_detective" not in recommendation.reason
    assert "Number Detective" in recommendation.reason


def assert_determinism():
    sessions = (
        family_session(
            FAMILY_DISTRIBUTION,
            incorrect=1,
        ),
        family_session(FAMILY_LOGIC_DETECTIVE),
        family_session(
            FAMILY_NUMBER_DETECTIVE,
            incorrect=2,
        ),
        family_session(
            FAMILY_NUMBER_DETECTIVE,
            incorrect=1,
        ),
        family_session(FAMILY_DISTRIBUTION),
    )
    first = recommend(logic_topic(sessions))
    second = recommend(logic_topic(sessions))
    assert first.family == second.family
    assert first.metadata["family_reason"] == (
        second.metadata["family_reason"]
    )
    assert first.difficulty == second.difficulty
    assert first.topic == second.topic
    assert first.reason == second.reason


def assert_window_stats_ignore_missing_family():
    stats = family_window_stats(
        (
            family_session(None, incorrect=3),
            family_session(FAMILY_DISTRIBUTION),
        )
    )
    assert stats[FAMILY_NUMBER_DETECTIVE].completed == 0
    assert stats[FAMILY_DISTRIBUTION].completed == 1
    assert (
        stats[FAMILY_NUMBER_DETECTIVE]
        .mathematical_error_sessions
        == 0
    )


def main():
    assert_canonical_family_list()
    assert_cold_start()
    assert_legacy_history_is_cold_start()
    assert_one_family_avoids_repetition()
    assert_targeted_mathematical_practice()
    assert_one_mathematical_error_is_insufficient()
    assert_repetition_guard_uses_variety()
    assert_targeted_family_can_return()
    assert_format_only_errors_are_not_targeted()
    assert_hints_without_math_errors_are_not_targeted()
    assert_mixed_errors_count_only_math()
    assert_five_distribution_puzzles_cover_another()
    assert_history_rollover_forgets_older_evidence()
    assert_difficulty_parity()
    assert_topic_ranking_parity()
    assert_mastery_parity()
    assert_non_logical_reasoning_has_null_family()
    assert_static_catalog_has_null_family()
    assert_student_profiles_are_isolated()
    assert_duplicate_completion_does_not_double_count()
    assert_recommendation_surfaces_agree()
    assert_explicit_family_wins_over_seed()
    assert_english_reason_uses_display_names()
    assert_determinism()
    assert_window_stats_ignore_missing_family()
    print("family_selection tests passed")


if __name__ == "__main__":
    main()
