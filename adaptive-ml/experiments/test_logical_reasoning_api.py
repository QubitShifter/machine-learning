"""Phase 26 Stage G — curriculum, API, mastery, privacy, sweep."""

from __future__ import annotations

import json
import time
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.mat_pal.app import app
from src.api.mat_pal.generated_problem_store import (
    clear_generated_problems,
    get_generated_problem,
)
from src.api.mat_pal.problem_generation import (
    DEFAULT_PROBLEM_GENERATOR_REGISTRY,
)
from src.api.mat_pal.session_store import (
    _sessions,
    get_question_engine,
    set_question_engine,
)
from src.core.i18n.primary_school import PRIMARY_SCHOOL_TEXT
from src.core.i18n.question import question_fallback_message
from src.core.question_engine import (
    GeneralTutorQuestionEngine,
    NullTutorModelProvider,
    NullWebSearchProvider,
)
from src.core.student_model.progress_store import (
    DEFAULT_PROGRESS_PATH,
)
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.generation.errors import (
    PrimarySchoolGenerationError,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning import (
    FAMILY_DISTRIBUTION,
    FAMILY_LOGIC_DETECTIVE,
    FAMILY_NUMBER_DETECTIVE,
    LOGICAL_REASONING_FAMILIES,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.compile import (
    discloses_protected,
    integer_tokens,
    protected_answers_from,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.generate import (
    select_logical_reasoning_family,
)
from src.core.tutor_engine.primary_school.generation.logical_reasoning.model import (
    LogicalReasoningVerificationError,
)


client = TestClient(app)

FAMILIES = (
    FAMILY_NUMBER_DETECTIVE,
    FAMILY_DISTRIBUTION,
    FAMILY_LOGIC_DETECTIVE,
)
DIFFICULTIES = (1, 2, 3)
SWEEP_SEEDS = 20
EXISTING_MASTERY_KEYS = (
    "grade4_arithmetic",
    "grade4_unknown_number",
    "grade4_number_patterns",
    "grade4_word_problems",
    "grade4_reverse_reasoning",
)
PRIVATE_KEYS = {
    "intended",
    "blueprint",
    "expected_answer",
    "expected_answers",
    "step_specs",
    "assignment",
    "candidates",
    "satisfying",
    "elimination",
    "hidden_steps",
    "future_steps",
    "target_position",
    "solution",
    "compiled_steps",
    "step_plan",
    "private_clues",
    "enumeration",
}
SKIP_TEXT_KEYS = {
    "session_id",
    "problem_id",
    "student_id",
    "mastery_key",
    "generator_name",
    "prompt_key",
    "hint_key",
    "question_id",
}
STATEMENT_KEYS = {
    "problem_statement",
    "problem_text",
    "title",
    "problem_title",
}
CURRICULUM_DIR = Path("math/primary-school/curriculum")
EXISTING_TOPICS = (
    "arithmetic",
    "unknown_numbers",
    "fractions",
    "word_problems",
    "story_problems",
    "geometry",
    "number_patterns",
)
EXISTING_SKILL_TOPICS = {
    "grade4_arithmetic_addition": "arithmetic",
    "grade4_unknown_number": "unknown_numbers",
    "grade4_reverse_reasoning": "word_problems",
    "grade4_word_problems": "story_problems",
    "grade4_number_sequence": "number_patterns",
}


def write_progress(progress: dict) -> None:
    DEFAULT_PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_PROGRESS_PATH.write_text(
        json.dumps(progress, indent=4),
        encoding="utf-8",
    )


def read_progress() -> dict:
    return json.loads(
        DEFAULT_PROGRESS_PATH.read_text(encoding="utf-8")
    )


def baseline_progress() -> dict:
    skills = {
        key: {
            "mastery": 0.72,
            "questions_completed": 3,
            "first_attempt_streak": 1,
            "last_total_attempts": 4,
            "last_incorrect_attempts": 1,
            "last_hints_used": 0,
            "last_first_attempt_success": True,
            "last_completed": True,
            "recent_sessions": [],
        }
        for key in EXISTING_MASTERY_KEYS
    }
    return {"skills": skills}


def generate_problem(
    *,
    difficulty: int = 1,
    seed: int | None = None,
    language: str = "en",
    family: str | None = None,
    topic: str = "logical_reasoning",
):
    payload = {
        "subject": "mathematics",
        "domain": "primary_school",
        "topic": topic,
        "difficulty": difficulty,
        "language": language,
    }
    if seed is not None:
        payload["seed"] = seed
    if family is not None:
        payload["family"] = family
    return client.post("/problems/generate", json=payload)


def start_session(problem_id: str, language: str = "en"):
    return client.post(
        "/sessions/start",
        json={"problem_id": problem_id, "language": language},
    )


def post_answer(session_id: str, answer: str):
    return client.post(
        f"/sessions/{session_id}/answer",
        json={"answer": answer, "input_type": "number"},
    )


def private_engine(generated: dict) -> PrimarySchoolTutorEngine:
    registration = get_generated_problem(generated["problem_id"])
    assert registration is not None
    engine = registration.create_engine(
        generated.get("language", "en")
    )
    assert isinstance(engine, PrimarySchoolTutorEngine)
    return engine


def visible_numbers(engine: PrimarySchoolTutorEngine) -> tuple[int, ...]:
    known = engine.problem.known or {}
    values = known.get("visible_numbers") or ()
    return tuple(int(item) for item in values)


def public_strings(payload, skip_keys=SKIP_TEXT_KEYS):
    found = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in skip_keys:
                continue
            found.extend(public_strings(value, skip_keys))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(public_strings(item, skip_keys))
    elif isinstance(payload, str):
        found.append(payload)
    return found


def assert_no_private_keys(payload, *, allow_final_answer: bool = False):
    forbidden = set(PRIVATE_KEYS)
    if not allow_final_answer:
        forbidden.add("final_answer")

    def walk(obj):
        if isinstance(obj, dict):
            extra = set(obj) & forbidden
            assert not extra, extra
            if not allow_final_answer:
                assert obj.get("final_answer") is None or (
                    "final_answer" not in obj
                )
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(payload)


def collect_fields(payload, keys):
    found = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys and isinstance(value, str):
                found.append(value)
            found.extend(collect_fields(value, keys))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(collect_fields(item, keys))
    return found


def assert_no_answer_leak(payload, engine, current_step: int):
    protected = protected_answers_from(engine.problem, current_step)
    visible = visible_numbers(engine)
    hidden = set(protected) - set(visible)
    for text in collect_fields(payload, STATEMENT_KEYS):
        for token in integer_tokens(text):
            assert token not in hidden, text
    skip = set(SKIP_TEXT_KEYS) | set(STATEMENT_KEYS)
    for text in public_strings(payload, skip):
        assert not discloses_protected(text, protected, visible), text


def complete_session(generated: dict, language: str = "en") -> dict:
    engine = private_engine(generated)
    started = start_session(generated["problem_id"], language)
    assert started.status_code == 200, started.text
    session = started.json()
    session_id = session["session_id"]
    assert session["completed"] is False
    assert "final_answer" not in session["metadata"]
    for step in engine.problem.solution_steps:
        result = post_answer(session_id, str(step.expected_answer))
        assert result.status_code == 200, result.text
        session = result.json()
    assert session["completed"] is True
    assert session["status"] == "complete"
    return session


def use_unavailable_model():
    previous = get_question_engine()
    set_question_engine(
        GeneralTutorQuestionEngine(
            model_provider=NullTutorModelProvider(),
            web_search_provider=NullWebSearchProvider(),
        )
    )
    return previous


def assert_curriculum_registration():
    topics = json.loads(
        (CURRICULUM_DIR / "topics.json").read_text(encoding="utf-8")
    )
    skills = json.loads(
        (CURRICULUM_DIR / "skills.json").read_text(encoding="utf-8")
    )
    topic_ids = [item["id"] for item in topics["topics"]]
    skill_ids = [item["id"] for item in skills["skills"]]
    assert topic_ids.count("logical_reasoning") == 1
    assert skill_ids.count("grade4_logical_reasoning") == 1
    for topic_id in EXISTING_TOPICS:
        assert topic_id in topic_ids
    topic = next(
        item for item in topics["topics"] if item["id"] == "logical_reasoning"
    )
    skill = next(
        item
        for item in skills["skills"]
        if item["id"] == "grade4_logical_reasoning"
    )
    assert topic["name"] == "Logical Reasoning"
    assert "number clues" in topic["description"].lower()
    assert skill["topic"] == "logical_reasoning"
    for skill_id, mapped in EXISTING_SKILL_TOPICS.items():
        found = next(
            item for item in skills["skills"] if item["id"] == skill_id
        )
        assert found["topic"] == mapped
    english = PRIMARY_SCHOOL_TEXT["en"]
    bulgarian = PRIMARY_SCHOOL_TEXT["bg"]
    assert english["catalog.topic.logical_reasoning"] == (
        "Logical Reasoning"
    )
    assert bulgarian["catalog.topic.logical_reasoning"] == (
        "Логическо мислене"
    )
    assert "catalog.skill.grade4_logical_reasoning" in english
    assert "catalog.skill.grade4_logical_reasoning" in bulgarian


def assert_generator_registration():
    registration = DEFAULT_PROBLEM_GENERATOR_REGISTRY.get(
        "mathematics",
        "primary_school",
        "logical_reasoning",
    )
    assert registration.generator_name == "grade4_logical_reasoning"
    assert registration.supported_difficulties == (1, 2, 3)
    assert select_logical_reasoning_family(seed=0) == (
        FAMILY_NUMBER_DETECTIVE
    )
    assert select_logical_reasoning_family(seed=1) == (
        FAMILY_DISTRIBUTION
    )
    assert select_logical_reasoning_family(seed=2) == (
        FAMILY_LOGIC_DETECTIVE
    )
    assert select_logical_reasoning_family(
        family=FAMILY_LOGIC_DETECTIVE,
        seed=0,
    ) == FAMILY_LOGIC_DETECTIVE
    try:
        select_logical_reasoning_family(family="hazelnuts")
    except PrimarySchoolGenerationError as error:
        assert "Unsupported" in str(error)
    else:
        raise AssertionError("unsupported family should fail")


def assert_catalog_exposes_topic():
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
    topics = {topic["id"]: topic for topic in primary["topics"]}
    assert "logical_reasoning" in topics
    topic = topics["logical_reasoning"]
    assert topic["name"] == "Logical Reasoning"
    assert topic["generation_available"] is True
    assert topic["supported_difficulties"] == [1, 2, 3]
    assert topic["available_problem_count"] == 0
    for topic_id in (
        "arithmetic",
        "unknown_numbers",
        "number_patterns",
        "story_problems",
        "word_problems",
    ):
        assert topic_id in topics
    assert_no_private_keys(response.json())


def assert_generation_families_and_languages():
    clear_generated_problems()
    seen = {}
    for index, family in enumerate(FAMILIES):
        for difficulty in DIFFICULTIES:
            english = generate_problem(
                difficulty=difficulty,
                seed=10 + index,
                language="en",
                family=family,
            )
            assert english.status_code == 200, english.text
            payload = english.json()
            assert payload["topic"] == "logical_reasoning"
            assert payload["generated"] is True
            assert payload["expected_input_type"] == "number"
            assert payload["metadata"]["family"] == family
            assert payload["metadata"]["generator_name"] == (
                "grade4_logical_reasoning"
            )
            assert payload["metadata"]["difficulty"] == difficulty
            assert_no_private_keys(payload)
            engine = private_engine(payload)
            assert_no_answer_leak(payload, engine, 1)
            seen[(family, difficulty)] = payload["problem_text"]
            bulgarian = generate_problem(
                difficulty=difficulty,
                seed=10 + index,
                language="bg",
                family=family,
            )
            assert bulgarian.status_code == 200, bulgarian.text
            bg = bulgarian.json()
            assert bg["problem_text"] != payload["problem_text"]
            assert bg["language"] == "bg"
            assert_no_private_keys(bg)
    default_families = []
    for seed in range(9):
        response = generate_problem(difficulty=1, seed=seed)
        assert response.status_code == 200, response.text
        default_families.append(response.json()["metadata"]["family"])
    assert set(default_families) == set(FAMILIES)
    assert default_families[:3] == list(LOGICAL_REASONING_FAMILIES)


def assert_generation_errors():
    clear_generated_problems()
    unsupported_family = generate_problem(
        difficulty=1,
        seed=1,
        family="hazelnuts",
    )
    assert unsupported_family.status_code == 400
    assert "family" in unsupported_family.json()["detail"].lower()
    unsupported_difficulty = generate_problem(difficulty=4, seed=1)
    assert unsupported_difficulty.status_code == 400
    assert "difficulty" in unsupported_difficulty.json()["detail"].lower()
    with patch(
        "src.api.mat_pal.problem_generation.generate_logical_reasoning_problem",
        side_effect=PrimarySchoolGenerationError(
            "Could not generate a unique logical puzzle."
        ),
    ):
        exhausted = generate_problem(
            difficulty=1,
            seed=1,
            family=FAMILY_NUMBER_DETECTIVE,
        )
    assert exhausted.status_code == 400
    assert "unique" in exhausted.json()["detail"].lower()
    with patch(
        "src.core.tutor_engine.primary_school.generation.logical_reasoning.generate.compile_logical_reasoning_puzzle",
        side_effect=LogicalReasoningVerificationError(
            "compile_failed",
            "Tutoring compilation failed.",
        ),
    ):
        compile_fail = generate_problem(
            difficulty=1,
            seed=2,
            family=FAMILY_NUMBER_DETECTIVE,
        )
    assert compile_fail.status_code == 400
    assert "compilation" in compile_fail.json()["detail"].lower()
    compatible = generate_problem(
        topic="arithmetic",
        difficulty=1,
        seed=6,
        family=FAMILY_NUMBER_DETECTIVE,
    )
    assert compatible.status_code == 200, compatible.text
    assert compatible.json()["topic"] == "arithmetic"


def assert_session_grading_and_invalid_input():
    clear_generated_problems()
    write_progress(baseline_progress())
    generated = generate_problem(
        difficulty=1,
        seed=4,
        family=FAMILY_NUMBER_DETECTIVE,
        language="en",
    ).json()
    engine = private_engine(generated)
    started = start_session(generated["problem_id"])
    assert started.status_code == 200
    session = started.json()
    session_id = session["session_id"]
    assert session["expected_input_type"] == "number"
    assert session["current_step"] == 1
    assert session["completed"] is False
    assert_no_private_keys(session)
    assert_no_answer_leak(session, engine, 1)
    current = session["current_step"]
    bad = post_answer(session_id, "99999").json()
    assert bad["status"] == "incorrect"
    assert bad["completed"] is False
    assert bad["current_step"] == current
    invalid = post_answer(session_id, "7.5").json()
    assert invalid["status"] == "incorrect"
    empty = post_answer(session_id, "   ").json()
    assert empty["status"] == "incorrect"
    first = engine.problem.solution_steps[0]
    correct = post_answer(session_id, str(first.expected_answer)).json()
    assert correct["status"] in {"correct", "complete"}
    if not correct["completed"]:
        assert correct["current_step"] == current + 1
        assert_no_private_keys(correct)
        assert_no_answer_leak(correct, engine, correct["current_step"])
    bg_generated = generate_problem(
        difficulty=2,
        seed=5,
        family=FAMILY_DISTRIBUTION,
        language="bg",
    )
    assert bg_generated.status_code == 200, bg_generated.text
    completed = complete_session(
        bg_generated.json(),
        language="bg",
    )
    assert completed["metadata"]["final_answer"] is not None
    assert completed["metadata"]["mastery_key"] == (
        "grade4_logical_reasoning"
    )


def assert_hints_and_guided_questions():
    previous = use_unavailable_model()
    try:
        write_progress(baseline_progress())
        before = deepcopy(read_progress()["skills"])
        for family in FAMILIES:
            for difficulty in DIFFICULTIES:
                generated = generate_problem(
                    difficulty=difficulty,
                    seed=8,
                    family=family,
                    language="en",
                ).json()
                engine = private_engine(generated)
                started = start_session(generated["problem_id"])
                session = started.json()
                session_id = session["session_id"]
                current = session["current_step"]
                hints = []
                for _ in range(3):
                    hint = client.post(f"/sessions/{session_id}/hint")
                    assert hint.status_code == 200, hint.text
                    payload = hint.json()
                    assert payload["status"] == "hint"
                    assert payload["current_step"] == current
                    assert payload["completed"] is False
                    assert_no_private_keys(payload)
                    assert_no_answer_leak(payload, engine, current)
                    hints.append(payload["feedback"])
                assert len(set(hints)) == 3
                fourth = client.post(f"/sessions/{session_id}/hint").json()
                assert fourth["metadata"]["hint_exhausted"] is True
                assert fourth["metadata"]["hint_counted"] is False
                assert fourth["metadata"]["hints_used_on_step"] == 3
                live = client.get(f"/sessions/{session_id}").json()
                assert live["current_step"] == current
                wrong = post_answer(session_id, "99999").json()
                assert wrong["status"] == "incorrect"
                after_wrong = client.post(
                    f"/sessions/{session_id}/hint"
                ).json()
                assert after_wrong["metadata"]["hints_used_on_step"] == 3
                suggested = session["suggested_questions"]
                assert suggested
                question_id = suggested[0]["question_id"]
                asked = client.post(
                    f"/sessions/{session_id}/question",
                    json={"question_id": question_id},
                )
                assert asked.status_code == 200, asked.text
                guided = asked.json()
                assert guided["status"] == "concept"
                assert guided["current_step"] == current
                assert guided["completed"] is False
                assert guided["metadata"]["answer_source"] == "local"
                assert "hint_level" not in guided["metadata"]
                assert guided["hint_available"] is False
                assert_no_private_keys(guided)
                assert_no_answer_leak(guided, engine, current)
                after_guided = client.post(
                    f"/sessions/{session_id}/hint"
                ).json()
                assert after_guided["metadata"]["hints_used_on_step"] == 3
                assert after_guided["metadata"]["hint_counted"] is False
                assert after_guided["hint_available"] is False
                assert after_guided["metadata"]["hint_exhausted"] is True
                stale = client.post(
                    f"/sessions/{session_id}/question",
                    json={"question_id": "unknown.factor.definition"},
                )
                assert stale.status_code == 400
                if family == FAMILY_DISTRIBUTION:
                    rejected = client.post(
                        f"/sessions/{session_id}/question",
                        json={"question_id": "logic.eliminate"},
                    )
                    assert rejected.status_code == 400
                method = client.post(
                    f"/sessions/{session_id}/question",
                    json={"question": "How do I solve this?"},
                )
                assert method.status_code == 200, method.text
                method_payload = method.json()
                assert method_payload["current_step"] == current
                assert method_payload["completed"] is False
                assert method_payload["metadata"]["answer_source"] in {
                    "local",
                    "fallback",
                }
                assert_no_answer_leak(method_payload, engine, current)
                first = engine.problem.solution_steps[0]
                if engine.problem.get_number_of_steps() > 1:
                    advanced = post_answer(
                        session_id,
                        str(first.expected_answer),
                    ).json()
                    assert advanced["completed"] is False
                    reset = client.post(
                        f"/sessions/{session_id}/hint"
                    ).json()
                    assert reset["current_step"] == advanced["current_step"]
                    assert reset["metadata"]["hints_used_on_step"] == 1
                    assert reset["metadata"]["hint_level"] == 1
                    assert reset["hint_available"] is True
                    assert reset["metadata"].get("hint_exhausted") is not True
        after = read_progress()["skills"]
        for key in EXISTING_MASTERY_KEYS:
            assert after[key] == before[key]
        assert "grade4_logical_reasoning" not in after
    finally:
        set_question_engine(previous)


def assert_mastery_and_progress():
    write_progress(baseline_progress())
    before = deepcopy(read_progress()["skills"])
    generated = generate_problem(
        difficulty=1,
        seed=3,
        family=FAMILY_LOGIC_DETECTIVE,
    ).json()
    engine = private_engine(generated)
    started = start_session(generated["problem_id"])
    session_id = started.json()["session_id"]
    after_start = read_progress()["skills"]
    assert after_start == before
    client.post(f"/sessions/{session_id}/hint")
    after_hint = read_progress()["skills"]
    assert after_hint == before
    question_id = started.json()["suggested_questions"][0]["question_id"]
    guided = client.post(
        f"/sessions/{session_id}/question",
        json={"question_id": question_id},
    )
    assert guided.status_code == 200, guided.text
    after_guided = read_progress()["skills"]
    assert after_guided == before
    session = started.json()
    for step in engine.problem.solution_steps:
        result = post_answer(session_id, str(step.expected_answer))
        assert result.status_code == 200, result.text
        session = result.json()
    assert session["completed"] is True
    assert session["metadata"]["mastery_key"] == (
        "grade4_logical_reasoning"
    )
    skills = read_progress()["skills"]
    for key in EXISTING_MASTERY_KEYS:
        assert skills[key] == before[key]
    logic = skills["grade4_logical_reasoning"]
    assert logic["questions_completed"] == 1
    assert logic["last_completed"] is True
    again = client.get(f"/sessions/{session_id}").json()
    assert again["completed"] is True
    duplicate = read_progress()["skills"]["grade4_logical_reasoning"]
    assert duplicate["questions_completed"] == 1
    extra = post_answer(session_id, "1").json()
    assert extra["completed"] is True
    still = read_progress()["skills"]["grade4_logical_reasoning"]
    assert still["questions_completed"] == 1
    write_progress({"skills": {}})
    progress = client.get(
        "/progress?subject=mathematics&domain=primary_school"
    )
    assert progress.status_code == 200
    payload = progress.json()
    topics = {topic["topic"]: topic for topic in payload["topics"]}
    assert "logical_reasoning" in topics
    topic = topics["logical_reasoning"]
    assert topic["mastery_key"] == "grade4_logical_reasoning"
    assert topic["mastery"] == 0.5
    assert topic["generation_available"] is True
    assert topic["questions_completed"] == 0
    assert "story_problems" in topics
    assert topics["story_problems"]["mastery_key"] == (
        "grade4_word_problems"
    )
    assert_no_private_keys(payload)


def assert_answer_format_question_does_not_mutate_session():
    previous = use_unavailable_model()
    try:
        write_progress(baseline_progress())
        before = deepcopy(read_progress()["skills"])
        generated = generate_problem(
            difficulty=1,
            seed=4,
            family=FAMILY_DISTRIBUTION,
            language="en",
        ).json()
        engine = private_engine(generated)
        started = start_session(generated["problem_id"])
        assert started.status_code == 200, started.text
        session = started.json()
        session_id = session["session_id"]
        current = session["current_step"]
        for _ in range(3):
            hint = client.post(f"/sessions/{session_id}/hint")
            assert hint.status_code == 200, hint.text
        exhausted = client.get(f"/sessions/{session_id}").json()
        assert exhausted["current_step"] == current
        assert exhausted["completed"] is False
        assert exhausted["metadata"]["hint_exhausted"] is True
        assert exhausted["metadata"]["hints_used_on_step"] == 3
        assert exhausted["hint_available"] is False
        question = (
            "Should I enter the answer for two boxes "
            "separated by comma?"
        )
        asked = client.post(
            f"/sessions/{session_id}/question",
            json={"question": question},
        )
        assert asked.status_code == 200, asked.text
        payload = asked.json()
        assert payload["status"] == "concept"
        assert payload["current_step"] == current
        assert payload["completed"] is False
        assert payload["metadata"]["answer_source"] == "local"
        assert payload["hint_available"] is False
        assert "hint_level" not in payload["metadata"]
        assert "one number" in payload["feedback"].lower()
        assert payload["feedback"] != question_fallback_message("en")
        assert "can't provide a reliable extended answer" not in (
            payload["feedback"].lower()
        )
        assert_no_private_keys(payload)
        assert_no_answer_leak(payload, engine, current)
        for value in (
            step.expected_answer
            for step in engine.problem.solution_steps
        ):
            if isinstance(value, int):
                assert str(value) not in payload["feedback"]
        after = read_progress()["skills"]
        assert after == before
        still_exhausted = client.post(
            f"/sessions/{session_id}/hint"
        ).json()
        assert still_exhausted["current_step"] == current
        assert still_exhausted["completed"] is False
        assert still_exhausted["hint_available"] is False
        assert still_exhausted["metadata"]["hint_exhausted"] is True
        assert still_exhausted["metadata"]["hints_used_on_step"] == 3
        assert still_exhausted["metadata"]["hint_counted"] is False
        first = engine.problem.solution_steps[0]
        advanced = post_answer(
            session_id,
            str(first.expected_answer),
        ).json()
        assert advanced["status"] in {"correct", "complete"}
        if not advanced["completed"]:
            assert advanced["current_step"] == current + 1
    finally:
        set_question_engine(previous)


def assert_distribution_terminology_question_is_local():
    previous = use_unavailable_model()
    try:
        write_progress(baseline_progress())
        before = deepcopy(read_progress()["skills"])
        generated = generate_problem(
            difficulty=3,
            seed=1,
            family=FAMILY_DISTRIBUTION,
            language="en",
        ).json()
        engine = private_engine(generated)
        started = start_session(generated["problem_id"])
        assert started.status_code == 200, started.text
        session = started.json()
        session_id = session["session_id"]
        current = session["current_step"]
        prompt = session["feedback"]
        assert "scaled box" not in prompt.lower()
        times = next(
            clue
            for clue in engine.problem.known["public_clues"]
            if clue["kind"] == "times_as_many"
        )
        from src.core.i18n.logical_reasoning import lrt

        left_name = lrt("en", f"gen.logic.box.{times['left']}")
        assert left_name in prompt
        asked = client.post(
            f"/sessions/{session_id}/question",
            json={
                "question": (
                    "What does 'scaled box' mean in this problem? "
                    "Explain it without giving me the answer."
                )
            },
        )
        assert asked.status_code == 200, asked.text
        payload = asked.json()
        assert payload["status"] == "concept"
        assert payload["current_step"] == current
        assert payload["completed"] is False
        assert payload["metadata"]["answer_source"] == "local"
        assert payload["feedback"] != question_fallback_message("en")
        assert left_name in payload["feedback"]
        assert str(times["factor"]) in payload["feedback"] or (
            lrt("en", f"gen.logic.factor_word.{times['factor']}")
            in payload["feedback"]
        )
        assert_no_private_keys(payload)
        assert_no_answer_leak(payload, engine, current)
        after = read_progress()["skills"]
        assert after == before
        live = client.get(f"/sessions/{session_id}").json()
        assert live["current_step"] == current
        assert live["completed"] is False
        hint = client.post(f"/sessions/{session_id}/hint").json()
        assert hint["current_step"] == current
        assert hint["metadata"]["hints_used_on_step"] == 1
    finally:
        set_question_engine(previous)


def assert_distribution_extra_method_question_is_local():
    previous = use_unavailable_model()
    try:
        write_progress(baseline_progress())
        before = deepcopy(read_progress()["skills"])
        generated = generate_problem(
            difficulty=3,
            seed=58,
            family=FAMILY_DISTRIBUTION,
            language="bg",
        ).json()
        engine = private_engine(generated)
        started = start_session(generated["problem_id"], "bg")
        assert started.status_code == 200, started.text
        session = started.json()
        session_id = session["session_id"]
        current = session["current_step"]
        times = next(
            clue
            for clue in engine.problem.known["public_clues"]
            if clue["kind"] == "times_as_many"
        )
        more = next(
            clue
            for clue in engine.problem.known["public_clues"]
            if clue["kind"] == "more_than"
        )
        exhausted = None
        for _ in range(2):
            exhausted = client.post(f"/sessions/{session_id}/hint").json()
        assert exhausted["metadata"]["hints_used_on_step"] == 2
        asked = client.post(
            f"/sessions/{session_id}/question",
            json={
                "question": (
                    "Как точно да намерим излишъкът в "
                    "първата кутия?"
                )
            },
        )
        assert asked.status_code == 200, asked.text
        payload = asked.json()
        assert payload["status"] == "concept"
        assert payload["current_step"] == current
        assert payload["completed"] is False
        assert payload["metadata"]["answer_source"] == "local"
        assert payload["feedback"] != question_fallback_message("bg")
        assert "надежден разширен отговор" not in payload["feedback"]
        assert str(times["factor"]) in payload["feedback"]
        assert str(more["extra"]) in payload["feedback"]
        assert f"{times['factor']} × {more['extra']} = ?" in (
            payload["feedback"]
        )
        product = times["factor"] * more["extra"]
        assert str(product) not in {
            str(token)
            for token in integer_tokens(payload["feedback"])
        }
        assert_no_private_keys(payload)
        assert_no_answer_leak(payload, engine, current)
        after = read_progress()["skills"]
        assert after == before
        live = client.get(f"/sessions/{session_id}").json()
        assert live["current_step"] == current
        assert live["completed"] is False
        hint = client.post(f"/sessions/{session_id}/hint").json()
        assert hint["current_step"] == current
        assert hint["metadata"]["hints_used_on_step"] == 3
        stale = client.post(
            f"/sessions/{session_id}/question",
            json={"question_id": "logic.eliminate"},
        )
        assert stale.status_code == 400
    finally:
        set_question_engine(previous)


def assert_model_independence():
    previous = use_unavailable_model()
    try:
        catalog = client.get("/catalog")
        assert catalog.status_code == 200
        generated = generate_problem(
            difficulty=1,
            seed=1,
            family=FAMILY_NUMBER_DETECTIVE,
        )
        assert generated.status_code == 200
        session = start_session(generated.json()["problem_id"])
        assert session.status_code == 200
        session_id = session.json()["session_id"]
        hint = client.post(f"/sessions/{session_id}/hint")
        assert hint.status_code == 200
        question_id = session.json()["suggested_questions"][0][
            "question_id"
        ]
        guided = client.post(
            f"/sessions/{session_id}/question",
            json={"question_id": question_id},
        )
        assert guided.status_code == 200
        progress = client.get("/progress")
        assert progress.status_code == 200
    finally:
        set_question_engine(previous)


def assert_integration_sweep():
    clear_generated_problems()
    write_progress(baseline_progress())
    before = deepcopy(read_progress()["skills"])
    stats = {
        "attempted": 0,
        "created": 0,
        "completed": 0,
        "failed_generations": 0,
        "failed_api": 0,
        "incorrect_grading": 0,
        "incorrect_mastery": 0,
        "privacy_violations": 0,
    }
    started_at = time.perf_counter()
    for family in FAMILIES:
        for difficulty in DIFFICULTIES:
            for seed in range(SWEEP_SEEDS):
                stats["attempted"] += 1
                language = "en" if seed % 2 == 0 else "bg"
                generated = generate_problem(
                    difficulty=difficulty,
                    seed=1000 + seed,
                    family=family,
                    language=language,
                )
                if generated.status_code != 200:
                    stats["failed_generations"] += 1
                    continue
                payload = generated.json()
                try:
                    engine = private_engine(payload)
                    assert_no_private_keys(payload)
                    assert_no_answer_leak(payload, engine, 1)
                except AssertionError:
                    stats["privacy_violations"] += 1
                    continue
                started = start_session(
                    payload["problem_id"],
                    language,
                )
                if started.status_code != 200:
                    stats["failed_api"] += 1
                    continue
                session = started.json()
                stats["created"] += 1
                try:
                    assert_no_private_keys(session)
                    assert_no_answer_leak(session, engine, 1)
                except AssertionError:
                    stats["privacy_violations"] += 1
                session_id = session["session_id"]
                failed = False
                for step in engine.problem.solution_steps:
                    result = post_answer(
                        session_id,
                        str(step.expected_answer),
                    )
                    if result.status_code != 200:
                        stats["failed_api"] += 1
                        failed = True
                        break
                    body = result.json()
                    if body["status"] not in {"correct", "complete"}:
                        stats["incorrect_grading"] += 1
                        failed = True
                        break
                    if body["completed"]:
                        break
                    try:
                        assert_no_private_keys(body)
                        assert_no_answer_leak(
                            body,
                            engine,
                            body["current_step"],
                        )
                    except AssertionError:
                        stats["privacy_violations"] += 1
                if failed:
                    continue
                live = client.get(f"/sessions/{session_id}")
                if live.status_code != 200:
                    stats["failed_api"] += 1
                    continue
                completed = live.json()
                if (
                    completed.get("completed") is not True
                    or completed.get("status") != "complete"
                ):
                    stats["incorrect_grading"] += 1
                    continue
                if completed["metadata"].get("mastery_key") != (
                    "grade4_logical_reasoning"
                ):
                    stats["incorrect_mastery"] += 1
                    continue
                skills = read_progress()["skills"]
                for key in EXISTING_MASTERY_KEYS:
                    if skills[key] != before[key]:
                        stats["incorrect_mastery"] += 1
                        failed = True
                        break
                if failed:
                    continue
                if skills.get("grade4_logical_reasoning", {}).get(
                    "questions_completed",
                    0,
                ) != stats["completed"] + 1:
                    stats["incorrect_mastery"] += 1
                    continue
                stats["completed"] += 1
    runtime = time.perf_counter() - started_at
    stats["runtime_seconds"] = round(runtime, 3)
    print("logical_reasoning integration sweep:", json.dumps(stats))
    assert stats["attempted"] == 180
    assert stats["failed_generations"] == 0
    assert stats["failed_api"] == 0
    assert stats["incorrect_grading"] == 0
    assert stats["incorrect_mastery"] == 0
    assert stats["privacy_violations"] == 0
    assert stats["created"] == 180
    assert stats["completed"] == 180
    return stats


def main():
    had_progress = DEFAULT_PROGRESS_PATH.exists()
    original_progress = (
        DEFAULT_PROGRESS_PATH.read_text(encoding="utf-8")
        if had_progress
        else None
    )
    previous_engine = get_question_engine()
    try:
        assert_curriculum_registration()
        assert_generator_registration()
        assert_catalog_exposes_topic()
        assert_generation_families_and_languages()
        assert_generation_errors()
        assert_session_grading_and_invalid_input()
        assert_hints_and_guided_questions()
        assert_answer_format_question_does_not_mutate_session()
        assert_distribution_terminology_question_is_local()
        assert_distribution_extra_method_question_is_local()
        assert_mastery_and_progress()
        assert_model_independence()
        assert_integration_sweep()
        print("logical_reasoning_api tests passed")
    finally:
        set_question_engine(previous_engine)
        clear_generated_problems()
        _sessions.clear()
        if had_progress and original_progress is not None:
            DEFAULT_PROGRESS_PATH.write_text(
                original_progress,
                encoding="utf-8",
            )
        elif DEFAULT_PROGRESS_PATH.exists():
            DEFAULT_PROGRESS_PATH.unlink()


if __name__ == "__main__":
    main()
