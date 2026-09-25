"""Runtime curriculum loader tests. No adaptive policy."""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

from src.core.curriculum import (
    PRIMARY_SCHOOL_TOPICS_PATH,
    Curriculum,
    CurriculumTopic,
    load_curriculum_topics,
    prerequisite_graph,
    prerequisites_of,
)


EXPECTED_PRIMARY_SCHOOL_GRAPH = {
    "arithmetic": (),
    "unknown_numbers": ("arithmetic",),
    "fractions": (),
    "word_problems": (),
    "story_problems": ("arithmetic",),
    "geometry": (),
    "number_patterns": (),
    "logical_reasoning": (),
}
ODE_TOPICS_PATH = (
    Path(__file__).resolve().parents[1]
    / "math"
    / "ode"
    / "curriculum"
    / "topics.json"
)
PHYSICS_TOPICS_PATH = (
    Path(__file__).resolve().parents[1]
    / "physics"
    / "classical_mechanics"
    / "curriculum"
    / "topics.json"
)
FORBIDDEN_SOURCE_FRAGMENTS = (
    "src.core.adaptive",
    "progress_store",
    "student_model",
    "src.api.mat_pal",
    "model_provider",
    "ollama",
)


def _write_curriculum(payload: object) -> Path:
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        encoding="utf-8",
        delete=False,
    )
    with handle:
        json.dump(payload, handle)
    return Path(handle.name)


def assert_primary_school_file_loads():
    curriculum = load_curriculum_topics(
        PRIMARY_SCHOOL_TOPICS_PATH
    )
    assert curriculum.subject == "primary_school_math"
    assert [
        topic.id for topic in curriculum.topics
    ] == list(EXPECTED_PRIMARY_SCHOOL_GRAPH)
    graph = prerequisite_graph(curriculum)
    assert graph == EXPECTED_PRIMARY_SCHOOL_GRAPH
    assert prerequisites_of(
        curriculum,
        "unknown_numbers",
    ) == ("arithmetic",)
    assert prerequisites_of(curriculum, "missing") == ()


def assert_ode_file_parses():
    curriculum = load_curriculum_topics(ODE_TOPICS_PATH)
    assert (
        curriculum.subject
        == "ordinary_differential_equations"
    )
    ids = [topic.id for topic in curriculum.topics]
    assert "algebra_review" in ids
    assert "linear_first_order" in ids
    assert "separable_equations" in ids
    graph = prerequisite_graph(curriculum)
    assert graph["algebra_review"] == ()
    assert graph["derivatives"] == ("algebra_review",)
    assert graph["linear_first_order"] == (
        "ode_basics",
        "integration",
    )
    for prerequisites in graph.values():
        assert isinstance(prerequisites, tuple)


def assert_physics_file_parses():
    curriculum = load_curriculum_topics(PHYSICS_TOPICS_PATH)
    assert curriculum.subject == "physics"
    assert [topic.id for topic in curriculum.topics] == [
        "kinematics"
    ]
    assert prerequisite_graph(curriculum) == {
        "kinematics": (),
    }


def assert_unknown_fields_are_ignored():
    path = _write_curriculum(
        {
            "subject": "demo",
            "grade": 4,
            "future_flag": True,
            "topics": [
                {
                    "id": "root",
                    "name": "Root",
                    "level": 9,
                    "domain": "ignored",
                    "prerequisites": [],
                }
            ],
        }
    )
    try:
        curriculum = load_curriculum_topics(path)
        assert curriculum.subject == "demo"
        assert curriculum.topics[0].id == "root"
        assert curriculum.topics[0].prerequisites == ()
        assert not hasattr(curriculum.topics[0], "level")
    finally:
        path.unlink()


def assert_missing_prerequisites_become_empty():
    path = _write_curriculum(
        {
            "topics": [
                {"id": "solo", "name": "Solo"}
            ]
        }
    )
    try:
        curriculum = load_curriculum_topics(path)
        assert curriculum.topics[0].prerequisites == ()
        assert prerequisite_graph(curriculum) == {
            "solo": (),
        }
    finally:
        path.unlink()


def assert_duplicate_ids_rejected():
    path = _write_curriculum(
        {
            "topics": [
                {"id": "a"},
                {"id": "a"},
            ]
        }
    )
    try:
        try:
            load_curriculum_topics(path)
        except ValueError as error:
            assert "a" in str(error)
        else:
            raise AssertionError(
                "Duplicate topic ids should raise ValueError."
            )
    finally:
        path.unlink()


def assert_invalid_prerequisites_type_rejected():
    string_path = _write_curriculum(
        {
            "topics": [
                {
                    "id": "a",
                    "prerequisites": "arithmetic",
                }
            ]
        }
    )
    number_path = _write_curriculum(
        {
            "topics": [
                {
                    "id": "a",
                    "prerequisites": [123],
                }
            ]
        }
    )
    try:
        try:
            load_curriculum_topics(string_path)
        except ValueError:
            pass
        else:
            raise AssertionError(
                "String prerequisites should raise ValueError."
            )
        try:
            load_curriculum_topics(number_path)
        except ValueError:
            pass
        else:
            raise AssertionError(
                "Non-string prerequisites should raise ValueError."
            )
    finally:
        string_path.unlink()
        number_path.unlink()


def assert_unknown_prerequisite_rejected():
    path = _write_curriculum(
        {
            "topics": [
                {
                    "id": "b",
                    "prerequisites": ["missing"],
                }
            ]
        }
    )
    try:
        try:
            load_curriculum_topics(path)
        except ValueError as error:
            assert "missing" in str(error)
        else:
            raise AssertionError(
                "Unknown prerequisite should raise ValueError."
            )
    finally:
        path.unlink()


def assert_invalid_json_raises():
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        encoding="utf-8",
        delete=False,
    )
    with handle:
        handle.write("{not json")
    path = Path(handle.name)
    try:
        try:
            load_curriculum_topics(path)
        except json.JSONDecodeError:
            pass
        else:
            raise AssertionError(
                "Malformed JSON should raise JSONDecodeError."
            )
    finally:
        path.unlink()


def assert_missing_file_raises():
    missing = Path(tempfile.gettempdir()) / (
        "matpal-missing-curriculum.json"
    )
    if missing.exists():
        missing.unlink()
    try:
        load_curriculum_topics(missing)
    except FileNotFoundError:
        return
    raise AssertionError(
        "Missing file should raise FileNotFoundError."
    )


def assert_loader_is_deterministic():
    first = load_curriculum_topics(
        PRIMARY_SCHOOL_TOPICS_PATH
    )
    second = load_curriculum_topics(
        PRIMARY_SCHOOL_TOPICS_PATH
    )
    assert first == second
    assert prerequisite_graph(first) == prerequisite_graph(
        second
    )
    assert list(prerequisite_graph(first)) == list(
        EXPECTED_PRIMARY_SCHOOL_GRAPH
    )


def assert_runtime_objects_are_frozen():
    curriculum = load_curriculum_topics(
        PRIMARY_SCHOOL_TOPICS_PATH
    )
    topic = curriculum.topics[0]
    assert isinstance(curriculum, Curriculum)
    assert isinstance(topic, CurriculumTopic)
    assert isinstance(curriculum.topics, tuple)
    assert isinstance(topic.prerequisites, tuple)
    try:
        curriculum.subject = "changed"
    except Exception:
        pass
    else:
        raise AssertionError("Curriculum should be frozen.")
    try:
        topic.id = "changed"
    except Exception:
        pass
    else:
        raise AssertionError(
            "CurriculumTopic should be frozen."
        )


def assert_path_is_file_relative():
    assert PRIMARY_SCHOOL_TOPICS_PATH.is_absolute()
    assert PRIMARY_SCHOOL_TOPICS_PATH.exists()
    assert PRIMARY_SCHOOL_TOPICS_PATH.name == "topics.json"
    assert "primary-school" in PRIMARY_SCHOOL_TOPICS_PATH.parts


def assert_import_boundaries():
    source = inspect.getsource(
        inspect.getmodule(load_curriculum_topics)
    )
    lowered = source.lower()
    for fragment in FORBIDDEN_SOURCE_FRAGMENTS:
        assert fragment.lower() not in lowered, (
            f"curriculum.py must not mention {fragment}."
        )


def main():
    assert_path_is_file_relative()
    assert_primary_school_file_loads()
    assert_ode_file_parses()
    assert_physics_file_parses()
    assert_unknown_fields_are_ignored()
    assert_missing_prerequisites_become_empty()
    assert_duplicate_ids_rejected()
    assert_invalid_prerequisites_type_rejected()
    assert_unknown_prerequisite_rejected()
    assert_invalid_json_raises()
    assert_missing_file_raises()
    assert_loader_is_deterministic()
    assert_runtime_objects_are_frozen()
    assert_import_boundaries()
    print("curriculum_loader tests passed")


if __name__ == "__main__":
    main()
