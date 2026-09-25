"""Phase 27 Stage D2b — bounded per-family performance memory."""

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
    recommend_next,
    record_session_completion,
)
from src.core.adaptive import (
    AdaptiveTopicState,
    RecentSession,
    RuleBasedAdaptivePolicy,
    SessionPerformanceSummary,
)
from src.core.adaptive.features import (
    FAMILY_HISTORY_LIMIT,
    FAMILY_MATH_ERROR_SESSION_THRESHOLD,
    append_family_outcome,
    derive_family_history_from_sessions,
    family_history_to_dict,
    family_is_targeted,
    parse_family_history,
    resolve_family_history,
    session_has_mathematical_error,
)
from src.core.adaptive.policy import (
    FAMILY_LEAST_PRACTICED,
    FAMILY_RECENT_CORRECTIONS,
    FAMILY_VARIETY,
)
from src.core.student_model.progress_store import (
    DEFAULT_STUDENT_ID,
    get_skill_progress,
    get_student_record,
    load_progress,
    update_skill_progress,
)
from src.core.student_model.student import StudentModel
from src.core.tutor_engine.primary_school.generation.logical_reasoning import (
    FAMILY_DISTRIBUTION,
    FAMILY_LOGIC_DETECTIVE,
    FAMILY_NUMBER_DETECTIVE,
)

import test_performance_history as history


client = TestClient(app)
REAL_PROGRESS_PATH = Path(
    "math/ode/data/student_progress.json"
)
LOGIC_KEY = "grade4_logical_reasoning"
ARITHMETIC_KEY = "grade4_arithmetic"
STUDENT_A = "phase27_d2b_student_a"
STUDENT_B = "phase27_d2b_student_b"


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


def skill_history(
    path: Path,
    student_id: str,
    skill: str,
) -> dict:
    return get_skill_progress(
        get_student_record(
            load_progress(path),
            student_id,
        ),
        skill,
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
    family_history: dict | None = None,
    mastery: float = 0.40,
) -> AdaptiveTopicState:
    return AdaptiveTopicState(
        subject="mathematics",
        domain="primary_school",
        topic="logical_reasoning",
        topic_name="Logical Reasoning",
        mastery_key=LOGIC_KEY,
        mastery=mastery,
        questions_completed=len(recent_sessions),
        first_attempt_streak=0,
        supported_difficulties=(1, 2, 3),
        generation_available=True,
        recent_sessions=recent_sessions,
        family_history=family_history or {},
    )


def other_topic(
    topic: str,
    mastery: float,
) -> AdaptiveTopicState:
    return AdaptiveTopicState(
        subject="mathematics",
        domain="primary_school",
        topic=topic,
        topic_name=topic.replace("_", " ").title(),
        mastery_key=topic,
        mastery=mastery,
        questions_completed=0,
        first_attempt_streak=0,
        supported_difficulties=(1, 2, 3),
        generation_available=True,
    )


def recommend(topic: AdaptiveTopicState):
    return RuleBasedAdaptivePolicy().recommend_next(
        [topic]
    )


def choose_family(topic: AdaptiveTopicState):
    return RuleBasedAdaptivePolicy().choose_family(
        topic
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
    family_history: dict | None = None,
) -> dict:
    last = recent_sessions[-1] if recent_sessions else {}
    record = {
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
    if family_history is not None:
        record["family_history"] = family_history
    return record


def completion_summary(
    family: str | None = FAMILY_NUMBER_DETECTIVE,
    *,
    incorrect: int = 0,
    invalid: int = 0,
    hints: int = 0,
    topic: str = "logical_reasoning",
    mastery_key: str = LOGIC_KEY,
    completed: bool = True,
    problem_id: str = "d2b_family_problem",
) -> SessionPerformanceSummary:
    return SessionPerformanceSummary(
        problem_id=problem_id,
        subject="mathematics",
        domain="primary_school",
        topic=topic,
        difficulty=1,
        mastery_key=mastery_key,
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
        invalid_attempts=invalid,
    )


def record(
    path: Path,
    family: str | None,
    *,
    incorrect: int = 0,
    invalid: int = 0,
    hints: int = 0,
    topic: str = "logical_reasoning",
    mastery_key: str = LOGIC_KEY,
    completed: bool = True,
    student_id: str = STUDENT_A,
    problem_id: str = "d2b_family_problem",
) -> dict:
    return record_session_completion(
        completion_summary(
            family,
            incorrect=incorrect,
            invalid=invalid,
            hints=hints,
            topic=topic,
            mastery_key=mastery_key,
            completed=completed,
            problem_id=problem_id,
        ),
        path=path,
        student_id=student_id,
    )


def math_errors(values: list[bool]) -> list[dict]:
    return [
        {"math_error": value}
        for value in values
    ]


def assert_queue(history: dict, family: str, values: list[bool]):
    assert history.get(family) == math_errors(values)
    assert len(history.get(family, [])) <= FAMILY_HISTORY_LIMIT


def assert_constants():
    assert FAMILY_HISTORY_LIMIT == 3
    assert FAMILY_MATH_ERROR_SESSION_THRESHOLD == 2


def assert_normalization_ignores_malformed():
    parsed = parse_family_history(
        {
            "number_detective": [
                {"math_error": True, "hint": "no"},
                "skip",
                {"wrong": True},
                {"math_error": False},
            ],
            "unknown_family": [
                {"math_error": True},
            ],
            "distribution_puzzles": "bad",
        }
    )
    assert parsed == {
        FAMILY_NUMBER_DETECTIVE: (
            {"math_error": True},
            {"math_error": False},
        ),
    }
    assert parse_family_history(["bad"]) == {}
    assert parse_family_history(None) == {}
    payload = family_history_to_dict(parsed)
    assert payload == {
        FAMILY_NUMBER_DETECTIVE: math_errors(
            [True, False]
        ),
    }
    assert parse_family_history(parsed) == parsed
    assert parse_family_history(payload) == parsed


def assert_bounded_append():
    history = {}
    expected = [
        [True],
        [True, True],
        [True, True, False],
        [True, False, False],
    ]
    for index, error in enumerate(
        [True, True, False, False]
    ):
        history = append_family_outcome(
            history,
            FAMILY_NUMBER_DETECTIVE,
            error,
        )
        assert list(
            outcome["math_error"]
            for outcome in history[FAMILY_NUMBER_DETECTIVE]
        ) == expected[index]
        assert (
            len(history[FAMILY_NUMBER_DETECTIVE])
            <= FAMILY_HISTORY_LIMIT
        )


def assert_targeting_matrix():
    cases = (
        ([True, True], True),
        ([True, True, False], True),
        ([True, False, False], False),
        ([False, True, True], True),
        ([True, False, True], True),
        ([False, True, False], False),
        ([True], False),
        ([False, False, True], False),
    )
    for values, targeted in cases:
        outcomes = math_errors(values)
        assert family_is_targeted(outcomes) is targeted


def assert_first_valid_lr_completion_creates_history():
    with isolated_progress() as path:
        updated = record(
            path,
            FAMILY_NUMBER_DETECTIVE,
            incorrect=2,
        )
        history = updated["family_history"]
        assert_queue(
            history,
            FAMILY_NUMBER_DETECTIVE,
            [True],
        )
        assert FAMILY_DISTRIBUTION not in history
        assert FAMILY_LOGIC_DETECTIVE not in history


def assert_non_lr_completion_does_not_create_history():
    with isolated_progress() as path:
        updated = record(
            path,
            None,
            topic="arithmetic",
            mastery_key=ARITHMETIC_KEY,
            problem_id="d2b_arithmetic",
        )
        assert "family_history" not in updated
        logic = skill_history(path, STUDENT_A, LOGIC_KEY)
        assert "family_history" not in logic


def assert_invalid_family_does_not_create_history():
    with isolated_progress() as path:
        unknown = record(
            path,
            "not_a_family",
            incorrect=3,
        )
        missing = record(
            path,
            None,
            incorrect=3,
            problem_id="d2b_missing_family",
        )
        assert "family_history" not in unknown
        assert "family_history" not in missing


def assert_manual_and_recommended_update_history():
    previous = history.use_unavailable_model()
    try:
        with isolated_progress() as path:
            manual = history.generate_problem(
                topic="logical_reasoning",
                difficulty=1,
                family=FAMILY_LOGIC_DETECTIVE,
                seed=3,
            )
            history.complete_generated(manual, STUDENT_A)
            after_manual = skill_history(
                path,
                STUDENT_A,
                LOGIC_KEY,
            )
            assert after_manual["family_history"][
                FAMILY_LOGIC_DETECTIVE
            ] == math_errors([False])

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
            recommended_family, reason = choose_family(
                topic
            )
            assert recommended_family is not None
            assert reason in {
                FAMILY_LEAST_PRACTICED,
                FAMILY_RECENT_CORRECTIONS,
                FAMILY_VARIETY,
            }
            generated = history.generate_problem(
                topic="logical_reasoning",
                difficulty=1,
                family=recommended_family,
                seed=7,
            )
            history.complete_generated(
                generated,
                STUDENT_A,
            )
            after_recommended = skill_history(
                path,
                STUDENT_A,
                LOGIC_KEY,
            )
            assert recommended_family in (
                after_recommended["family_history"]
            )
    finally:
        from src.api.mat_pal.session_store import (
            set_question_engine,
        )
        set_question_engine(previous)


def assert_surprise_me_updates_history():
    previous = history.use_unavailable_model()
    try:
        with isolated_progress() as path:
            generated = history.generate_problem(
                topic="logical_reasoning",
                difficulty=1,
                seed=5,
            )
            family = generated["metadata"]["family"]
            assert family in {
                FAMILY_NUMBER_DETECTIVE,
                FAMILY_DISTRIBUTION,
                FAMILY_LOGIC_DETECTIVE,
            }
            history.complete_generated(
                generated,
                STUDENT_A,
            )
            stored = skill_history(
                path,
                STUDENT_A,
                LOGIC_KEY,
            )
            assert stored["family_history"][family] == (
                math_errors([False])
            )
    finally:
        from src.api.mat_pal.session_store import (
            set_question_engine,
        )
        set_question_engine(previous)


def assert_outcome_semantics():
    with isolated_progress() as path:
        format_only = record(
            path,
            FAMILY_NUMBER_DETECTIVE,
            incorrect=2,
            invalid=2,
            problem_id="d2b_format",
        )
        assert format_only["family_history"][
            FAMILY_NUMBER_DETECTIVE
        ] == math_errors([False])

        hints_only = record(
            path,
            FAMILY_NUMBER_DETECTIVE,
            hints=2,
            problem_id="d2b_hints",
        )
        assert hints_only["family_history"][
            FAMILY_NUMBER_DETECTIVE
        ] == math_errors([False, False])

        genuine = record(
            path,
            FAMILY_DISTRIBUTION,
            incorrect=2,
            problem_id="d2b_math",
        )
        assert genuine["family_history"][
            FAMILY_DISTRIBUTION
        ] == math_errors([True])

        mixed = record(
            path,
            FAMILY_LOGIC_DETECTIVE,
            incorrect=3,
            invalid=1,
            problem_id="d2b_mixed",
        )
        assert mixed["family_history"][
            FAMILY_LOGIC_DETECTIVE
        ] == math_errors([True])

        hints_and_math = record(
            path,
            FAMILY_LOGIC_DETECTIVE,
            incorrect=1,
            hints=2,
            problem_id="d2b_hints_math",
        )
        assert hints_and_math["family_history"][
            FAMILY_LOGIC_DETECTIVE
        ] == math_errors([True, True])


def assert_incomplete_does_not_update_history():
    with isolated_progress() as path:
        updated = record(
            path,
            FAMILY_NUMBER_DETECTIVE,
            incorrect=2,
            completed=False,
        )
        assert "family_history" not in updated


def assert_duplicate_completion_does_not_append():
    previous = history.use_unavailable_model()
    try:
        with isolated_progress() as path:
            generated = history.generate_problem(
                topic="logical_reasoning",
                difficulty=1,
                family=FAMILY_NUMBER_DETECTIVE,
                seed=3,
            )
            completed = history.complete_generated(
                generated,
                STUDENT_A,
            )
            first = skill_history(
                path,
                STUDENT_A,
                LOGIC_KEY,
            )
            extra = history.post_answer(
                completed["_session_id"],
                "1",
            )
            assert extra["completed"] is True
            second = skill_history(
                path,
                STUDENT_A,
                LOGIC_KEY,
            )
            assert first["family_history"] == (
                second["family_history"]
            )
            assert first["family_history"][
                FAMILY_NUMBER_DETECTIVE
            ] == math_errors([False])
            assert first["questions_completed"] == 1
            assert second["questions_completed"] == 1
    finally:
        from src.api.mat_pal.session_store import (
            set_question_engine,
        )
        set_question_engine(previous)


def assert_family_history_survives_load_save_and_restart():
    with isolated_progress() as path:
        record(
            path,
            FAMILY_NUMBER_DETECTIVE,
            incorrect=2,
        )
        first = skill_history(path, STUDENT_A, LOGIC_KEY)
        reloaded = load_progress(path)
        student = get_student_record(
            reloaded,
            STUDENT_A,
        )
        stored = get_skill_progress(
            student,
            LOGIC_KEY,
        )
        assert stored["family_history"] == (
            first["family_history"]
        )
        raw = json.loads(
            path.read_text(encoding="utf-8")
        )
        persisted = raw["students"][STUDENT_A][
            "skills"
        ][LOGIC_KEY]["family_history"]
        assert persisted == first["family_history"]
        assert "difficulty" not in json.dumps(
            persisted
        )
        assert "timestamp" not in json.dumps(
            persisted
        )


def assert_students_are_isolated():
    with isolated_progress() as path:
        record(
            path,
            FAMILY_NUMBER_DETECTIVE,
            incorrect=2,
            student_id=STUDENT_A,
        )
        record(
            path,
            FAMILY_DISTRIBUTION,
            student_id=STUDENT_B,
            problem_id="d2b_student_b",
        )
        first = skill_history(path, STUDENT_A, LOGIC_KEY)
        second = skill_history(path, STUDENT_B, LOGIC_KEY)
        assert first["family_history"] == {
            FAMILY_NUMBER_DETECTIVE: math_errors([True]),
        }
        assert second["family_history"] == {
            FAMILY_DISTRIBUTION: math_errors([False]),
        }


def assert_progress_store_preserves_without_copying_unknowns():
    progress = {
        "skills": {
            LOGIC_KEY: skill_record(
                0.40,
                [
                    session_payload(
                        FAMILY_NUMBER_DETECTIVE,
                        incorrect=2,
                    )
                ],
                family_history={
                    FAMILY_NUMBER_DETECTIVE: math_errors(
                        [True]
                    ),
                    "mystery": [{"math_error": True}],
                },
            )
        }
    }
    progress["skills"][LOGIC_KEY]["mystery_key"] = 1
    update_skill_progress(
        progress=progress,
        skill=LOGIC_KEY,
        mastery=0.41,
        questions_completed=2,
        first_attempt_streak=0,
    )
    updated = progress["skills"][LOGIC_KEY]
    assert updated["family_history"] == {
        FAMILY_NUMBER_DETECTIVE: math_errors([True]),
    }
    assert "mystery_key" not in updated
    assert "mystery" not in updated["family_history"]

    update_skill_progress(
        progress=progress,
        skill=ARITHMETIC_KEY,
        mastery=0.20,
        questions_completed=1,
        first_attempt_streak=0,
    )
    assert "family_history" not in progress["skills"][
        ARITHMETIC_KEY
    ]


def assert_bounded_history_queue():
    with isolated_progress() as path:
        expected = [
            [True],
            [True, True],
            [True, True, False],
            [True, False, False],
        ]
        flags = [True, True, False, False]
        for index, error in enumerate(flags):
            updated = record(
                path,
                FAMILY_NUMBER_DETECTIVE,
                incorrect=2 if error else 0,
                problem_id=f"d2b_queue_{index}",
            )
            assert_queue(
                updated["family_history"],
                FAMILY_NUMBER_DETECTIVE,
                expected[index],
            )
            family, reason = choose_family(
                logic_topic(
                    family_history=parse_family_history(
                        updated["family_history"]
                    ),
                    recent_sessions=(
                        family_session(
                            FAMILY_DISTRIBUTION
                        ),
                    ),
                )
            )
            targeted = family_is_targeted(
                parse_family_history(
                    updated["family_history"]
                ).get(FAMILY_NUMBER_DETECTIVE, ())
            )
            if targeted:
                assert family == FAMILY_NUMBER_DETECTIVE
                assert reason == FAMILY_RECENT_CORRECTIONS
            else:
                assert reason != FAMILY_RECENT_CORRECTIONS


def assert_additional_targeting_queues():
    cases = (
        ([False, True, True], True),
        ([True, False, True], True),
        ([False, True, False], False),
    )
    for values, targeted in cases:
        history = {
            FAMILY_NUMBER_DETECTIVE: math_errors(values)
        }
        family, reason = choose_family(
            logic_topic(
                recent_sessions=(
                    family_session(FAMILY_DISTRIBUTION),
                ),
                family_history=parse_family_history(
                    history
                ),
            )
        )
        assert family_is_targeted(
            parse_family_history(history)[
                FAMILY_NUMBER_DETECTIVE
            ]
        ) is targeted
        if targeted:
            assert family == FAMILY_NUMBER_DETECTIVE
            assert reason == FAMILY_RECENT_CORRECTIONS
        else:
            assert family != FAMILY_NUMBER_DETECTIVE or (
                reason != FAMILY_RECENT_CORRECTIONS
            )


def assert_other_family_completions_do_not_age_queue():
    with isolated_progress() as path:
        record(
            path,
            FAMILY_NUMBER_DETECTIVE,
            incorrect=2,
            problem_id="d2b_roll_1",
        )
        record(
            path,
            FAMILY_NUMBER_DETECTIVE,
            incorrect=2,
            problem_id="d2b_roll_2",
        )
        others = (
            FAMILY_DISTRIBUTION,
            FAMILY_LOGIC_DETECTIVE,
            FAMILY_DISTRIBUTION,
            FAMILY_LOGIC_DETECTIVE,
            FAMILY_DISTRIBUTION,
        )
        for index, family in enumerate(others):
            record(
                path,
                family,
                problem_id=f"d2b_other_{index}",
            )
        stored = skill_history(path, STUDENT_A, LOGIC_KEY)
        assert_queue(
            stored["family_history"],
            FAMILY_NUMBER_DETECTIVE,
            [True, True],
        )
        families = [
            session.get("family")
            for session in stored["recent_sessions"]
        ]
        assert FAMILY_NUMBER_DETECTIVE not in families
        assert len(stored["recent_sessions"]) == 5

        logic = next(
            item
            for item in list_topic_states(
                "mathematics",
                "primary_school",
                path,
                STUDENT_A,
            )
            if item.topic == "logical_reasoning"
        )
        family, reason = choose_family(logic)
        recommendation = RuleBasedAdaptivePolicy().recommend_next(
            [logic]
        )
        assert family == FAMILY_NUMBER_DETECTIVE
        assert reason == FAMILY_RECENT_CORRECTIONS
        assert recommendation.family == (
            FAMILY_NUMBER_DETECTIVE
        )
        assert recommendation.metadata["family_reason"] == (
            FAMILY_RECENT_CORRECTIONS
        )


def assert_recovery_and_relapse():
    with isolated_progress() as path:
        sequence = (
            (True, [True], False),
            (True, [True, True], True),
            (False, [True, True, False], True),
            (False, [True, False, False], False),
            (True, [False, False, True], False),
            (True, [False, True, True], True),
        )
        for index, (
            error,
            expected,
            targeted,
        ) in enumerate(sequence):
            updated = record(
                path,
                FAMILY_NUMBER_DETECTIVE,
                incorrect=2 if error else 0,
                problem_id=f"d2b_recover_{index}",
            )
            assert_queue(
                updated["family_history"],
                FAMILY_NUMBER_DETECTIVE,
                expected,
            )
            family, reason = choose_family(
                logic_topic(
                    recent_sessions=(
                        family_session(
                            FAMILY_DISTRIBUTION
                        ),
                    ),
                    family_history=parse_family_history(
                        updated["family_history"]
                    ),
                )
            )
            assert family_is_targeted(
                parse_family_history(
                    updated["family_history"]
                )[FAMILY_NUMBER_DETECTIVE]
            ) is targeted
            if targeted:
                assert family == FAMILY_NUMBER_DETECTIVE
                assert reason == FAMILY_RECENT_CORRECTIONS
            else:
                assert reason != FAMILY_RECENT_CORRECTIONS


def assert_bootstrap_reads_do_not_write():
    with isolated_progress() as path:
        write_progress(
            path,
            {
                "students": {
                    STUDENT_A: {
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
                    }
                }
            },
        )
        before = path.read_text(encoding="utf-8")
        recommendation = recommend_next(
            subject="mathematics",
            domain="primary_school",
            path=path,
            student_id=STUDENT_A,
        )
        posted = client.post(
            "/adaptive/recommendation",
            json={
                "subject": "mathematics",
                "domain": "primary_school",
                "student_id": STUDENT_A,
            },
        )
        dashboard = client.get(
            "/progress"
            "?subject=mathematics"
            "&domain=primary_school"
            f"&student_id={STUDENT_A}"
        )
        assert posted.status_code == 200, posted.text
        assert dashboard.status_code == 200, dashboard.text
        assert recommendation.family == (
            FAMILY_NUMBER_DETECTIVE
        )
        assert recommendation.metadata["family_reason"] == (
            FAMILY_RECENT_CORRECTIONS
        )
        assert posted.json()["family"] == (
            FAMILY_NUMBER_DETECTIVE
        )
        assert dashboard.json()["recommendation"][
            "family"
        ] == FAMILY_NUMBER_DETECTIVE
        after = path.read_text(encoding="utf-8")
        assert after == before
        raw = json.loads(after)
        assert "family_history" not in raw["students"][
            STUDENT_A
        ]["skills"][LOGIC_KEY]


def assert_bootstrap_seeds_pre_append_once():
    with isolated_progress() as path:
        write_progress(
            path,
            {
                "students": {
                    STUDENT_A: {
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
                                ],
                            )
                        }
                    }
                }
            },
        )
        updated = record(
            path,
            FAMILY_NUMBER_DETECTIVE,
            problem_id="d2b_bootstrap_append",
        )
        assert_queue(
            updated["family_history"],
            FAMILY_NUMBER_DETECTIVE,
            [True, True, False],
        )
        assert updated["family_history"][
            FAMILY_NUMBER_DETECTIVE
        ] != math_errors([True, False, False])


def assert_bootstrap_ignores_invalid_families():
    with isolated_progress() as path:
        write_progress(
            path,
            {
                "students": {
                    STUDENT_A: {
                        "skills": {
                            LOGIC_KEY: skill_record(
                                0.35,
                                [
                                    session_payload(
                                        None,
                                        incorrect=3,
                                    ),
                                    session_payload(
                                        "bogus",
                                        incorrect=3,
                                    ),
                                    session_payload(
                                        FAMILY_DISTRIBUTION,
                                        incorrect=2,
                                    ),
                                ],
                            )
                        }
                    }
                }
            },
        )
        updated = record(
            path,
            FAMILY_NUMBER_DETECTIVE,
            problem_id="d2b_bootstrap_invalid",
        )
        history = updated["family_history"]
        assert_queue(
            history,
            FAMILY_DISTRIBUTION,
            [True],
        )
        assert_queue(
            history,
            FAMILY_NUMBER_DETECTIVE,
            [False],
        )
        assert "bogus" not in history
        assert None not in history


def assert_persisted_history_is_not_merged():
    family, reason = choose_family(
        logic_topic(
            recent_sessions=(
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                ),
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                ),
            ),
            family_history=parse_family_history(
                {
                    FAMILY_NUMBER_DETECTIVE: math_errors(
                        [False]
                    )
                }
            ),
        )
    )
    assert family == FAMILY_DISTRIBUTION
    assert reason == FAMILY_LEAST_PRACTICED


def assert_derived_history_used_when_absent():
    family, reason = choose_family(
        logic_topic(
            recent_sessions=(
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
    assert family == FAMILY_NUMBER_DETECTIVE
    assert reason == FAMILY_RECENT_CORRECTIONS


def assert_repetition_guard_unchanged():
    family, reason = choose_family(
        logic_topic(
            recent_sessions=(
                family_session(FAMILY_DISTRIBUTION),
            ),
            family_history=parse_family_history(
                {
                    FAMILY_NUMBER_DETECTIVE: math_errors(
                        [True, True]
                    )
                }
            ),
        )
    )
    assert family == FAMILY_NUMBER_DETECTIVE
    assert reason == FAMILY_RECENT_CORRECTIONS

    guarded, guarded_reason = choose_family(
        logic_topic(
            recent_sessions=(
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                ),
                family_session(
                    FAMILY_NUMBER_DETECTIVE,
                    incorrect=2,
                ),
            ),
            family_history=parse_family_history(
                {
                    FAMILY_NUMBER_DETECTIVE: math_errors(
                        [True, True]
                    )
                }
            ),
        )
    )
    assert guarded == FAMILY_DISTRIBUTION
    assert guarded_reason == FAMILY_VARIETY


def assert_c2_math_error_unchanged():
    clean = family_session(FAMILY_NUMBER_DETECTIVE)
    format_only = family_session(
        FAMILY_NUMBER_DETECTIVE,
        incorrect=2,
        invalid=2,
    )
    hints_only = family_session(
        FAMILY_NUMBER_DETECTIVE,
        hints=3,
    )
    genuine = family_session(
        FAMILY_NUMBER_DETECTIVE,
        incorrect=2,
    )
    mixed = family_session(
        FAMILY_NUMBER_DETECTIVE,
        incorrect=3,
        invalid=1,
    )
    assert session_has_mathematical_error(clean) is False
    assert session_has_mathematical_error(
        format_only
    ) is False
    assert session_has_mathematical_error(
        hints_only
    ) is False
    assert session_has_mathematical_error(genuine) is True
    assert session_has_mathematical_error(mixed) is True


def assert_mastery_and_counts_unchanged():
    with isolated_progress() as path:
        first = record(
            path,
            FAMILY_NUMBER_DETECTIVE,
            problem_id="d2b_mastery_a",
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
        assert first["questions_completed"] == 1


def assert_topic_ranking_and_difficulty_parity():
    policy = RuleBasedAdaptivePolicy()
    arithmetic = other_topic("arithmetic", 0.20)
    logic = logic_topic(
        recent_sessions=(
            family_session(
                FAMILY_NUMBER_DETECTIVE,
                incorrect=2,
            ),
            family_session(
                FAMILY_NUMBER_DETECTIVE,
                incorrect=2,
            ),
        ),
        family_history=parse_family_history(
            {
                FAMILY_NUMBER_DETECTIVE: math_errors(
                    [True, True]
                )
            }
        ),
        mastery=0.80,
    )
    recommendation = policy.recommend_next(
        [logic, arithmetic]
    )
    assert recommendation.topic == "arithmetic"
    assert recommendation.family is None
    assert "family_reason" not in recommendation.metadata

    targeted = logic_topic(
        recent_sessions=(
            family_session(FAMILY_DISTRIBUTION),
        ),
        family_history=parse_family_history(
            {
                FAMILY_NUMBER_DETECTIVE: math_errors(
                    [True, True]
                )
            }
        ),
        mastery=0.50,
    )
    selected = policy.recommend_next([targeted])
    assert selected.difficulty == policy.choose_difficulty(
        targeted
    )
    assert selected.family == FAMILY_NUMBER_DETECTIVE


def assert_api_family_contract():
    recommendation = recommend(
        logic_topic(
            recent_sessions=(
                family_session(FAMILY_DISTRIBUTION),
            ),
            family_history=parse_family_history(
                {
                    FAMILY_NUMBER_DETECTIVE: math_errors(
                        [True, True]
                    )
                }
            ),
        )
    )
    assert recommendation.family == FAMILY_NUMBER_DETECTIVE
    assert recommendation.metadata["family_reason"] == (
        FAMILY_RECENT_CORRECTIONS
    )
    non_lr = recommend(other_topic("arithmetic", 0.40))
    assert non_lr.family is None
    assert "family_reason" not in non_lr.metadata


def assert_derive_helper_bounds_per_family():
    derived = derive_family_history_from_sessions(
        (
            family_session(
                FAMILY_NUMBER_DETECTIVE,
                incorrect=1,
            ),
            family_session(
                FAMILY_NUMBER_DETECTIVE,
                incorrect=1,
            ),
            family_session(FAMILY_NUMBER_DETECTIVE),
            family_session(FAMILY_NUMBER_DETECTIVE),
            family_session(
                FAMILY_DISTRIBUTION,
                incorrect=2,
            ),
        )
    )
    assert list(
        outcome["math_error"]
        for outcome in derived[FAMILY_NUMBER_DETECTIVE]
    ) == [True, False, False]
    assert resolve_family_history(
        {
            FAMILY_NUMBER_DETECTIVE: math_errors(
                [False]
            )
        },
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
    ) == {
        FAMILY_NUMBER_DETECTIVE: (
            {"math_error": False},
        )
    }


def main():
    assert_constants()
    assert_normalization_ignores_malformed()
    assert_bounded_append()
    assert_targeting_matrix()
    assert_first_valid_lr_completion_creates_history()
    assert_non_lr_completion_does_not_create_history()
    assert_invalid_family_does_not_create_history()
    assert_manual_and_recommended_update_history()
    assert_surprise_me_updates_history()
    assert_outcome_semantics()
    assert_incomplete_does_not_update_history()
    assert_duplicate_completion_does_not_append()
    assert_family_history_survives_load_save_and_restart()
    assert_students_are_isolated()
    assert_progress_store_preserves_without_copying_unknowns()
    assert_bounded_history_queue()
    assert_additional_targeting_queues()
    assert_other_family_completions_do_not_age_queue()
    assert_recovery_and_relapse()
    assert_bootstrap_reads_do_not_write()
    assert_bootstrap_seeds_pre_append_once()
    assert_bootstrap_ignores_invalid_families()
    assert_persisted_history_is_not_merged()
    assert_derived_history_used_when_absent()
    assert_repetition_guard_unchanged()
    assert_c2_math_error_unchanged()
    assert_mastery_and_counts_unchanged()
    assert_topic_ranking_and_difficulty_parity()
    assert_api_family_contract()
    assert_derive_helper_bounds_per_family()
    print("family_history tests passed")


if __name__ == "__main__":
    main()
