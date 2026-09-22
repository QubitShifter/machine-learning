"""Phase 27 Stage B — performance history and event semantics."""

from __future__ import annotations

import inspect
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
    RuleBasedAdaptivePolicy,
    SessionPerformanceSummary,
)
from src.api.mat_pal.generated_problem_store import (
    get_generated_problem,
)
from src.api.mat_pal.session_store import (
    get_question_engine,
    set_question_engine,
)
from src.core.question_engine import (
    GeneralTutorQuestionEngine,
    NullTutorModelProvider,
    NullWebSearchProvider,
)
from src.core.student_model.progress_store import (
    DEFAULT_PROGRESS_PATH,
    DEFAULT_STUDENT_ID,
    get_skill_progress,
    get_student_record,
    load_progress,
)
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning import (
    FAMILY_DISTRIBUTION,
    FAMILY_LOGIC_DETECTIVE,
    FAMILY_NUMBER_DETECTIVE,
)


client = TestClient(app)
REAL_PROGRESS_PATH = Path(
    "math/ode/data/student_progress.json"
)
STUDENT_A = "phase27_b_student_a"
STUDENT_B = "phase27_b_student_b"
LOGIC_KEY = "grade4_logical_reasoning"
ARITHMETIC_KEY = "grade4_arithmetic"


def real_progress_bytes() -> bytes | None:
    if not REAL_PROGRESS_PATH.exists():
        return None
    return REAL_PROGRESS_PATH.read_bytes()


@contextmanager
def isolated_progress():
    before = real_progress_bytes()
    original_record = (
        adaptive_service.record_session_completion
    )
    original_recommend = adaptive_service.recommend_next
    original_progress = (
        progress_service.get_student_progress
    )
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"

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

        with patch.object(
            adaptive_service,
            "record_session_completion",
            record_with_temp,
        ), patch.object(
            adaptive_service,
            "recommend_next",
            recommend_with_temp,
        ), patch.object(
            progress_service,
            "get_student_progress",
            progress_with_temp,
        ):
            yield path
    assert real_progress_bytes() == before


def use_unavailable_model():
    previous = get_question_engine()
    set_question_engine(
        GeneralTutorQuestionEngine(
            model_provider=NullTutorModelProvider(),
            web_search_provider=NullWebSearchProvider(),
        )
    )
    return previous


def generate_problem(
    *,
    topic: str,
    difficulty: int,
    family: str | None = None,
    seed: int = 3,
    language: str = "en",
) -> dict:
    payload = {
        "subject": "mathematics",
        "domain": "primary_school",
        "topic": topic,
        "difficulty": difficulty,
        "seed": seed,
        "language": language,
    }
    if family is not None:
        payload["family"] = family
    response = client.post(
        "/problems/generate",
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


def private_engine(generated: dict) -> PrimarySchoolTutorEngine:
    registration = get_generated_problem(
        generated["problem_id"]
    )
    assert registration is not None
    engine = registration.create_engine(
        generated.get("language", "en")
    )
    assert isinstance(engine, PrimarySchoolTutorEngine)
    return engine


def start_session(
    problem_id: str,
    student_id: str,
    language: str = "en",
) -> dict:
    response = client.post(
        "/sessions/start",
        json={
            "problem_id": problem_id,
            "student_id": student_id,
            "language": language,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def post_answer(
    session_id: str,
    answer: str,
    metadata: dict | None = None,
) -> dict:
    payload = {
        "answer": answer,
        "input_type": "number",
    }
    if metadata is not None:
        payload["metadata"] = metadata
    response = client.post(
        f"/sessions/{session_id}/answer",
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


def post_hint(session_id: str) -> dict:
    response = client.post(
        f"/sessions/{session_id}/hint"
    )
    assert response.status_code == 200, response.text
    return response.json()


def complete_generated(
    generated: dict,
    student_id: str,
    *,
    extras: list[str] | None = None,
    hints: int = 0,
    guided: bool = False,
    answer_metadata: dict | None = None,
) -> dict:
    engine = private_engine(generated)
    session = start_session(
        generated["problem_id"],
        student_id,
    )
    session_id = session["session_id"]
    if guided:
        questions = session.get(
            "suggested_questions"
        ) or []
        assert questions
        question = client.post(
            f"/sessions/{session_id}/question",
            json={
                "question_id": questions[0][
                    "question_id"
                ]
            },
        )
        assert question.status_code == 200, question.text
        assert question.json()["completed"] is False
    for _ in range(hints):
        hinted = post_hint(session_id)
        assert hinted["completed"] is False
    for extra in extras or ():
        result = post_answer(
            session_id,
            extra,
            metadata=answer_metadata,
        )
        assert result["completed"] is False
    for step in engine.problem.solution_steps:
        session = post_answer(
            session_id,
            str(step.expected_answer),
            metadata=answer_metadata,
        )
    assert session["completed"] is True
    session["_session_id"] = session_id
    return session


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


def write_progress(path: Path, progress: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(progress, indent=4),
        encoding="utf-8",
    )


def assert_distribution_history_is_recorded():
    with isolated_progress() as path:
        generated = generate_problem(
            topic="logical_reasoning",
            difficulty=2,
            family=FAMILY_DISTRIBUTION,
            seed=11,
        )
        assert generated["metadata"]["family"] == (
            FAMILY_DISTRIBUTION
        )
        completed = complete_generated(
            generated,
            STUDENT_A,
        )
        assert completed["metadata"]["mastery_key"] == (
            LOGIC_KEY
        )
        stored = skill_history(
            path,
            STUDENT_A,
            LOGIC_KEY,
        )
        assert stored["questions_completed"] == 1
        assert stored["mastery"] == 0.6
        assert len(stored["recent_sessions"]) == 1
        record = stored["recent_sessions"][0]
        assert record["family"] == FAMILY_DISTRIBUTION
        assert record["difficulty"] == 2
        assert record["invalid_attempts"] == 0
        assert record["first_attempt_success"] is True


def assert_number_detective_does_not_overwrite_earlier_family():
    with isolated_progress() as path:
        first = generate_problem(
            topic="logical_reasoning",
            difficulty=2,
            family=FAMILY_DISTRIBUTION,
            seed=11,
        )
        complete_generated(first, STUDENT_A)
        second = generate_problem(
            topic="logical_reasoning",
            difficulty=1,
            family=FAMILY_NUMBER_DETECTIVE,
            seed=5,
        )
        complete_generated(second, STUDENT_A)
        stored = skill_history(
            path,
            STUDENT_A,
            LOGIC_KEY,
        )
        assert stored["questions_completed"] == 2
        assert stored["mastery"] == 0.7
        records = stored["recent_sessions"]
        assert len(records) == 2
        assert records[0]["family"] == FAMILY_DISTRIBUTION
        assert records[0]["difficulty"] == 2
        assert records[1]["family"] == (
            FAMILY_NUMBER_DETECTIVE
        )
        assert records[1]["difficulty"] == 1


def assert_logic_detective_history_is_recorded():
    with isolated_progress() as path:
        generated = generate_problem(
            topic="logical_reasoning",
            difficulty=3,
            family=FAMILY_LOGIC_DETECTIVE,
            seed=7,
        )
        complete_generated(generated, STUDENT_A)
        record = skill_history(
            path,
            STUDENT_A,
            LOGIC_KEY,
        )["recent_sessions"][0]
        assert record["family"] == FAMILY_LOGIC_DETECTIVE
        assert record["difficulty"] == 3
        assert "grade4_logical_reasoning" == LOGIC_KEY


def assert_arithmetic_has_no_invented_family():
    with isolated_progress() as path:
        generated = generate_problem(
            topic="arithmetic",
            difficulty=2,
            seed=4,
        )
        completed = complete_generated(
            generated,
            STUDENT_A,
        )
        assert completed["metadata"]["mastery_key"] == (
            ARITHMETIC_KEY
        )
        stored = skill_history(
            path,
            STUDENT_A,
            ARITHMETIC_KEY,
        )
        record = stored["recent_sessions"][0]
        assert "family" not in record
        assert record["difficulty"] == 2
        assert record["invalid_attempts"] == 0
        logic = skill_history(
            path,
            STUDENT_A,
            LOGIC_KEY,
        )
        assert logic["questions_completed"] == 0
        assert logic["recent_sessions"] == []


def assert_invalid_input_is_counted_separately():
    with isolated_progress() as path:
        generated = generate_problem(
            topic="arithmetic",
            difficulty=1,
            seed=8,
        )
        engine = private_engine(generated)
        session = start_session(
            generated["problem_id"],
            STUDENT_A,
        )
        session_id = session["session_id"]
        invalid = post_answer(session_id, "box 1")
        assert invalid["status"] == "incorrect"
        assert invalid["metadata"]["error_type"] == (
            "not_numeric"
        )
        assert invalid["completed"] is False
        wrong = post_answer(session_id, "0")
        expected_first = str(
            engine.problem.solution_steps[0]
            .expected_answer
        )
        if expected_first == "0":
            wrong = post_answer(session_id, "1")
        assert wrong["status"] == "incorrect"
        assert wrong["metadata"]["error_type"] == (
            "incorrect_answer"
        )
        for step in engine.problem.solution_steps:
            completed = post_answer(
                session_id,
                str(step.expected_answer),
            )
        assert completed["completed"] is True
        stored = skill_history(
            path,
            STUDENT_A,
            ARITHMETIC_KEY,
        )
        record = stored["recent_sessions"][0]
        assert record["invalid_attempts"] == 1
        assert record["incorrect_attempts"] >= 2
        assert record["invalid_attempts"] <= (
            record["incorrect_attempts"]
        )
        assert record["first_attempt_success"] is False
        assert stored["mastery"] == 0.53
        assert stored["questions_completed"] == 1


def assert_correct_and_incorrect_numeric_classifications():
    with isolated_progress() as path:
        generated = generate_problem(
            topic="arithmetic",
            difficulty=1,
            seed=9,
        )
        engine = private_engine(generated)
        session = start_session(
            generated["problem_id"],
            STUDENT_A,
        )
        session_id = session["session_id"]
        first_expected = str(
            engine.problem.solution_steps[0]
            .expected_answer
        )
        wrong_value = (
            "2" if first_expected != "2" else "3"
        )
        wrong = post_answer(session_id, wrong_value)
        assert wrong["status"] == "incorrect"
        assert wrong["metadata"]["error_type"] == (
            "incorrect_answer"
        )
        for step in engine.problem.solution_steps:
            completed = post_answer(
                session_id,
                str(step.expected_answer),
            )
        assert completed["status"] in {
            "correct",
            "complete",
        }
        record = skill_history(
            path,
            STUDENT_A,
            ARITHMETIC_KEY,
        )["recent_sessions"][0]
        assert record["invalid_attempts"] == 0
        assert record["incorrect_attempts"] == 1
        assert record["first_attempt_success"] is False
        assert skill_history(
            path,
            STUDENT_A,
            ARITHMETIC_KEY,
        )["mastery"] == 0.56


def assert_exhausted_hints_are_not_double_counted():
    previous = use_unavailable_model()
    try:
        with isolated_progress() as path:
            generated = generate_problem(
                topic="logical_reasoning",
                difficulty=1,
                family=FAMILY_DISTRIBUTION,
                seed=3,
            )
            completed = complete_generated(
                generated,
                STUDENT_A,
                hints=5,
                guided=True,
            )
            assert completed["completed"] is True
            stored = skill_history(
                path,
                STUDENT_A,
                LOGIC_KEY,
            )
            record = stored["recent_sessions"][0]
            assert record["hints_used"] == 3
            assert record["invalid_attempts"] == 0
            assert record["incorrect_attempts"] == 0
            assert record["first_attempt_success"] is False
            assert stored["mastery"] == 0.56
            assert stored["questions_completed"] == 1
    finally:
        set_question_engine(previous)


def assert_duplicate_completion_is_idempotent():
    with isolated_progress() as path:
        generated = generate_problem(
            topic="logical_reasoning",
            difficulty=1,
            family=FAMILY_LOGIC_DETECTIVE,
            seed=3,
        )
        completed = complete_generated(
            generated,
            STUDENT_A,
        )
        session_id = completed["_session_id"]
        first = skill_history(
            path,
            STUDENT_A,
            LOGIC_KEY,
        )
        again = client.get(
            f"/sessions/{session_id}"
        ).json()
        assert again["completed"] is True
        extra = post_answer(session_id, "1")
        assert extra["completed"] is True
        second = skill_history(
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


def assert_legacy_records_remain_usable():
    with isolated_progress() as path:
        write_progress(
            path,
            {
                "skills": {
                    "linear_first_order_ode": {
                        "mastery": 0.80,
                        "questions_completed": 4,
                        "first_attempt_streak": 3,
                        "recent_sessions": [
                            {
                                "completed": True,
                                "total_attempts": 1,
                                "incorrect_attempts": 0,
                                "hints_used": 0,
                                "first_attempt_success": True,
                            },
                            {
                                "completed": True,
                                "total_attempts": 1,
                                "incorrect_attempts": 0,
                                "hints_used": 0,
                                "first_attempt_success": True,
                            },
                            {
                                "completed": True,
                                "total_attempts": 1,
                                "incorrect_attempts": 0,
                                "hints_used": 0,
                                "first_attempt_success": True,
                            },
                        ],
                    },
                    "separable_equations": {
                        "mastery": 0.62,
                        "questions_completed": 3,
                        "first_attempt_streak": 3,
                        "recent_sessions": [
                            {
                                "completed": True,
                                "total_attempts": 1,
                                "incorrect_attempts": 0,
                                "hints_used": 0,
                                "first_attempt_success": True,
                            },
                            {
                                "completed": True,
                                "total_attempts": 1,
                                "incorrect_attempts": 0,
                                "hints_used": 0,
                                "first_attempt_success": True,
                            },
                            {
                                "completed": True,
                                "total_attempts": 1,
                                "incorrect_attempts": 0,
                                "hints_used": 0,
                                "first_attempt_success": True,
                            },
                        ],
                    },
                }
            },
        )
        recommendation = recommend_next(
            subject="mathematics",
            domain="ode",
            path=path,
        )
        assert recommendation.topic == (
            "separable_equations"
        )
        assert recommendation.difficulty == 3
        assert recommendation.metadata[
            "recent_trend"
        ] == "strong"
        assert recommendation.metadata[
            "adjustment"
        ] == 1
        dashboard = client.get(
            "/progress?subject=mathematics"
            "&domain=ode"
        )
        assert dashboard.status_code == 200
        payload = dashboard.json()
        topics = {
            topic["topic"]: topic
            for topic in payload["topics"]
        }
        assert topics["separable_equations"][
            "questions_completed"
        ] == 3
        assert topics["separable_equations"][
            "mastery"
        ] == 0.62


def assert_student_history_is_isolated():
    with isolated_progress() as path:
        first = generate_problem(
            topic="logical_reasoning",
            difficulty=2,
            family=FAMILY_DISTRIBUTION,
            seed=11,
        )
        complete_generated(first, STUDENT_A)
        second = generate_problem(
            topic="logical_reasoning",
            difficulty=1,
            family=FAMILY_NUMBER_DETECTIVE,
            seed=5,
        )
        complete_generated(second, STUDENT_B)
        student_a = skill_history(
            path,
            STUDENT_A,
            LOGIC_KEY,
        )
        student_b = skill_history(
            path,
            STUDENT_B,
            LOGIC_KEY,
        )
        assert student_a["questions_completed"] == 1
        assert student_b["questions_completed"] == 1
        assert student_a["recent_sessions"][0][
            "family"
        ] == FAMILY_DISTRIBUTION
        assert student_b["recent_sessions"][0][
            "family"
        ] == FAMILY_NUMBER_DETECTIVE
        guest = skill_history(
            path,
            "local_student",
            LOGIC_KEY,
        )
        assert guest["questions_completed"] == 0
        assert guest["recent_sessions"] == []


def assert_recommendation_parity_with_stage_a_rules():
    with isolated_progress() as path:
        write_progress(
            path,
            {
                "skills": {
                    "linear_first_order_ode": {
                        "mastery": 0.80,
                        "questions_completed": 3,
                        "first_attempt_streak": 1,
                    },
                    "separable_equations": {
                        "mastery": 0.45,
                        "questions_completed": 1,
                        "first_attempt_streak": 0,
                    },
                }
            },
        )
        lower = recommend_next(
            subject="mathematics",
            domain="ode",
            path=path,
        )
        assert lower.topic == "separable_equations"
        assert lower.difficulty == 2
        assert "0.45" in lower.reason
        assert lower.metadata[
            "adjustment_reason"
        ] == "insufficient_history"

        write_progress(
            path,
            {
                "skills": {
                    "linear_first_order_ode": {
                        "mastery": 0.80,
                        "questions_completed": 4,
                        "first_attempt_streak": 0,
                    },
                    "separable_equations": {
                        "mastery": 0.48,
                        "questions_completed": 3,
                        "first_attempt_streak": 0,
                        "recent_sessions": [
                            {
                                "completed": True,
                                "total_attempts": 4,
                                "incorrect_attempts": 2,
                                "hints_used": 2,
                                "first_attempt_success": False,
                            },
                            {
                                "completed": True,
                                "total_attempts": 3,
                                "incorrect_attempts": 2,
                                "hints_used": 1,
                                "first_attempt_success": False,
                            },
                        ],
                    },
                }
            },
        )
        weak = recommend_next(
            subject="mathematics",
            domain="ode",
            path=path,
        )
        assert weak.topic == "separable_equations"
        assert weak.difficulty == 1
        assert weak.metadata["recent_trend"] == (
            "needs_support"
        )
        assert weak.metadata["adjustment"] == -1
        annotated = recommend_next(
            subject="mathematics",
            domain="ode",
            path=path,
        )
        write_progress(
            path,
            {
                "skills": {
                    "linear_first_order_ode": {
                        "mastery": 0.80,
                        "questions_completed": 4,
                        "first_attempt_streak": 0,
                    },
                    "separable_equations": {
                        "mastery": 0.48,
                        "questions_completed": 3,
                        "first_attempt_streak": 0,
                        "recent_sessions": [
                            {
                                "completed": True,
                                "total_attempts": 4,
                                "incorrect_attempts": 2,
                                "hints_used": 2,
                                "first_attempt_success": False,
                                "family": "number_detective",
                                "difficulty": 2,
                                "invalid_attempts": 1,
                            },
                            {
                                "completed": True,
                                "total_attempts": 3,
                                "incorrect_attempts": 2,
                                "hints_used": 1,
                                "first_attempt_success": False,
                                "family": "logic_detective",
                                "difficulty": 3,
                                "invalid_attempts": 0,
                            },
                        ],
                    },
                }
            },
        )
        still_weak = recommend_next(
            subject="mathematics",
            domain="ode",
            path=path,
        )
        assert still_weak.topic == annotated.topic
        assert still_weak.difficulty == (
            annotated.difficulty
        )
        assert still_weak.metadata["adjustment"] == (
            annotated.metadata["adjustment"]
        )
        assert still_weak.metadata["recent_trend"] == (
            annotated.metadata["recent_trend"]
        )
        assert still_weak.reason == annotated.reason


def assert_omitted_path_keeps_production_default():
    record_default = inspect.signature(
        adaptive_service.record_session_completion
    ).parameters["path"].default
    recommend_default = inspect.signature(
        adaptive_service.recommend_next
    ).parameters["path"].default
    progress_default = inspect.signature(
        progress_service.get_student_progress
    ).parameters["path"].default
    list_default = inspect.signature(
        adaptive_service.list_topic_states
    ).parameters["path"].default

    assert record_default == DEFAULT_PROGRESS_PATH
    assert recommend_default == DEFAULT_PROGRESS_PATH
    assert progress_default == DEFAULT_PROGRESS_PATH
    assert list_default is inspect.Parameter.empty
    assert DEFAULT_PROGRESS_PATH == Path(
        "math/ode/data/student_progress.json"
    )


def assert_explicit_path_uses_temporary_file():
    before = real_progress_bytes()
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        record_session_completion(
            SessionPerformanceSummary(
                problem_id="stage_b_path_check",
                subject="mathematics",
                domain="ode",
                topic="separable_equations",
                difficulty=1,
                mastery_key="separable_equations",
                completed=True,
                total_attempts=1,
                incorrect_attempts=0,
                hints_used=0,
                first_attempt_success=True,
                steps_completed=1,
                total_steps=1,
            ),
            path=path,
            student_id=STUDENT_A,
        )
        stored = skill_history(
            path,
            STUDENT_A,
            "separable_equations",
        )
        recommendation = recommend_next(
            subject="mathematics",
            domain="ode",
            path=path,
            student_id=STUDENT_A,
        )
        dashboard = progress_service.get_student_progress(
            subject="mathematics",
            domain="ode",
            path=path,
            student_id=STUDENT_A,
        )
        assert path.exists()
        assert stored["questions_completed"] == 1
        assert stored["recent_sessions"][0][
            "difficulty"
        ] == 1
        assert "family" not in stored[
            "recent_sessions"
        ][0]
        assert recommendation.topic is not None
        assert dashboard.student_id == STUDENT_A
        topics = {
            topic.mastery_key: topic
            for topic in dashboard.topics
        }
        assert topics["separable_equations"].questions_completed == 1
        assert topics["separable_equations"].mastery == (
            stored["mastery"]
        )
    assert real_progress_bytes() == before


def assert_answer_metadata_cannot_override_family():
    with isolated_progress() as path:
        generated = generate_problem(
            topic="logical_reasoning",
            difficulty=2,
            family=FAMILY_DISTRIBUTION,
            seed=11,
        )
        complete_generated(
            generated,
            STUDENT_A,
            answer_metadata={
                "family": FAMILY_LOGIC_DETECTIVE,
                "difficulty": 1,
                "invalid_attempts": 9,
            },
        )
        record = skill_history(
            path,
            STUDENT_A,
            LOGIC_KEY,
        )["recent_sessions"][0]
        assert record["family"] == FAMILY_DISTRIBUTION
        assert record["difficulty"] == 2
        assert record["invalid_attempts"] == 0


def assert_student_difficulty_is_isolated():
    with isolated_progress() as path:
        write_progress(
            path,
            {
                "students": {
                    STUDENT_A: {
                        "skills": {
                            LOGIC_KEY: {
                                "mastery": 0.50,
                                "questions_completed": 1,
                                "first_attempt_streak": 0,
                                "last_incorrect_attempts": 2,
                                "last_hints_used": 0,
                                "last_first_attempt_success": False,
                                "last_completed": True,
                                "recent_sessions": [
                                    {
                                        "completed": True,
                                        "total_attempts": 3,
                                        "incorrect_attempts": 2,
                                        "invalid_attempts": 2,
                                        "hints_used": 0,
                                        "first_attempt_success": False,
                                        "steps_completed": 1,
                                        "total_steps": 1,
                                    }
                                ],
                            }
                        }
                    },
                    STUDENT_B: {
                        "skills": {
                            LOGIC_KEY: {
                                "mastery": 0.50,
                                "questions_completed": 1,
                                "first_attempt_streak": 0,
                                "last_incorrect_attempts": 2,
                                "last_hints_used": 0,
                                "last_first_attempt_success": False,
                                "last_completed": True,
                                "recent_sessions": [
                                    {
                                        "completed": True,
                                        "total_attempts": 3,
                                        "incorrect_attempts": 2,
                                        "invalid_attempts": 0,
                                        "hints_used": 0,
                                        "first_attempt_success": False,
                                        "steps_completed": 1,
                                        "total_steps": 1,
                                    }
                                ],
                            }
                        }
                    },
                }
            },
        )
        policy = RuleBasedAdaptivePolicy()
        topic_a = next(
            topic
            for topic in list_topic_states(
                "mathematics",
                "primary_school",
                path,
                STUDENT_A,
            )
            if topic.topic == "logical_reasoning"
        )
        topic_b = next(
            topic
            for topic in list_topic_states(
                "mathematics",
                "primary_school",
                path,
                STUDENT_B,
            )
            if topic.topic == "logical_reasoning"
        )
        assert policy.choose_difficulty(topic_a) == 2
        assert policy.choose_difficulty(topic_b) == 1
        assert topic_a.mastery == topic_b.mastery


def main():
    assert_omitted_path_keeps_production_default()
    assert_explicit_path_uses_temporary_file()
    assert_distribution_history_is_recorded()
    assert_number_detective_does_not_overwrite_earlier_family()
    assert_logic_detective_history_is_recorded()
    assert_arithmetic_has_no_invented_family()
    assert_invalid_input_is_counted_separately()
    assert_correct_and_incorrect_numeric_classifications()
    assert_exhausted_hints_are_not_double_counted()
    assert_duplicate_completion_is_idempotent()
    assert_legacy_records_remain_usable()
    assert_student_history_is_isolated()
    assert_recommendation_parity_with_stage_a_rules()
    assert_answer_metadata_cannot_override_family()
    assert_student_difficulty_is_isolated()
    print("performance_history tests passed")


if __name__ == "__main__":
    main()
