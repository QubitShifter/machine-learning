"""Validate Primary School prerequisite metadata. No runtime policy."""

from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path


TOPICS_PATH = (
    Path(__file__).resolve().parents[1]
    / "math"
    / "primary-school"
    / "curriculum"
    / "topics.json"
)
CANONICAL_TOPIC_IDS = (
    "arithmetic",
    "unknown_numbers",
    "fractions",
    "word_problems",
    "story_problems",
    "geometry",
    "number_patterns",
    "logical_reasoning",
)
EXPECTED_PREREQUISITES = {
    "arithmetic": [],
    "unknown_numbers": ["arithmetic"],
    "fractions": [],
    "word_problems": [],
    "story_problems": ["arithmetic"],
    "geometry": [],
    "number_patterns": [],
    "logical_reasoning": [],
}
FORBIDDEN_TOPIC_KEYS = (
    "required_mastery",
    "unlock_score",
    "completed_required",
    "mastery_key",
    "mastery",
    "generation_available",
    "unlock_state",
)
REJECTED_EDGES = (
    ("logical_reasoning", "arithmetic"),
    ("number_patterns", "arithmetic"),
    ("story_problems", "unknown_numbers"),
    ("word_problems", "arithmetic"),
    ("fractions", "arithmetic"),
    ("geometry", "arithmetic"),
)


def load_topics() -> dict:
    return json.loads(TOPICS_PATH.read_text(encoding="utf-8"))


def topic_records(data: dict) -> list[dict]:
    topics = data["topics"]
    assert isinstance(topics, list)
    return topics


def prerequisite_map(topics: list[dict]) -> dict[str, list[str]]:
    return {
        topic["id"]: list(topic["prerequisites"])
        for topic in topics
    }


def topological_order(prereqs: dict[str, list[str]]) -> list[str]:
    dependents: dict[str, list[str]] = defaultdict(list)
    indegree = {topic_id: 0 for topic_id in prereqs}
    for topic_id, required in prereqs.items():
        for prerequisite in required:
            dependents[prerequisite].append(topic_id)
            indegree[topic_id] += 1

    ready = deque(
        sorted(
            topic_id
            for topic_id, count in indegree.items()
            if count == 0
        )
    )
    order: list[str] = []
    while ready:
        current = ready.popleft()
        order.append(current)
        for dependent in sorted(dependents[current]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
        ready = deque(sorted(ready))

    if len(order) != len(prereqs):
        raise AssertionError(
            "Primary School prerequisite graph contains a cycle."
        )
    return order


def assert_topics_parse():
    data = load_topics()
    assert isinstance(data, dict)
    assert data["subject"] == "primary_school_math"
    assert data["grade"] == 4
    topics = topic_records(data)
    assert topics


def assert_prerequisite_field_shape():
    topics = topic_records(load_topics())
    for topic in topics:
        assert "prerequisites" in topic, (
            f"{topic.get('id')} is missing prerequisites."
        )
        prerequisites = topic["prerequisites"]
        assert isinstance(prerequisites, list), (
            f"{topic['id']} prerequisites must be a list."
        )
        for entry in prerequisites:
            assert isinstance(entry, str), (
                f"{topic['id']} has a non-string prerequisite."
            )
            assert entry, (
                f"{topic['id']} has an empty prerequisite id."
            )
        for key in FORBIDDEN_TOPIC_KEYS:
            assert key not in topic, (
                f"{topic['id']} must not store {key}."
            )


def assert_canonical_topic_ids():
    topics = topic_records(load_topics())
    topic_ids = [topic["id"] for topic in topics]
    assert topic_ids == list(CANONICAL_TOPIC_IDS), (
        "Primary School topic ids changed."
    )
    assert len(topic_ids) == len(set(topic_ids))


def assert_prerequisite_ids_exist_and_are_unique():
    topics = topic_records(load_topics())
    topic_ids = {topic["id"] for topic in topics}
    for topic in topics:
        prerequisites = topic["prerequisites"]
        assert len(prerequisites) == len(set(prerequisites)), (
            f"{topic['id']} has duplicate prerequisites."
        )
        for prerequisite in prerequisites:
            assert prerequisite in topic_ids, (
                f"{topic['id']} depends on missing id {prerequisite}."
            )
            assert prerequisite != topic["id"], (
                f"{topic['id']} depends on itself."
            )


def assert_approved_edges():
    prereqs = prerequisite_map(topic_records(load_topics()))
    assert prereqs == EXPECTED_PREREQUISITES
    nonempty = [
        topic_id
        for topic_id, required in prereqs.items()
        if required
    ]
    assert sorted(nonempty) == [
        "story_problems",
        "unknown_numbers",
    ]
    assert prereqs["unknown_numbers"] == ["arithmetic"]
    assert prereqs["story_problems"] == ["arithmetic"]
    for topic_id in (
        "arithmetic",
        "fractions",
        "word_problems",
        "geometry",
        "number_patterns",
        "logical_reasoning",
    ):
        assert prereqs[topic_id] == []


def assert_rejected_edges_absent():
    prereqs = prerequisite_map(topic_records(load_topics()))
    for topic_id, forbidden in REJECTED_EDGES:
        assert forbidden not in prereqs[topic_id], (
            f"Rejected edge {forbidden} -> {topic_id} is present."
        )


def assert_graph_is_acyclic_and_ordered():
    prereqs = prerequisite_map(topic_records(load_topics()))
    order = topological_order(prereqs)
    assert set(order) == set(CANONICAL_TOPIC_IDS)
    assert order.index("arithmetic") < order.index(
        "unknown_numbers"
    )
    assert order.index("arithmetic") < order.index(
        "story_problems"
    )


def main():
    assert_topics_parse()
    assert_prerequisite_field_shape()
    assert_canonical_topic_ids()
    assert_prerequisite_ids_exist_and_are_unique()
    assert_approved_edges()
    assert_rejected_edges_absent()
    assert_graph_is_acyclic_and_ordered()
    print("primary_school_curriculum tests passed")


if __name__ == "__main__":
    main()
