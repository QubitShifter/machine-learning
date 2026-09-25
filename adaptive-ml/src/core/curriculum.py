from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRIMARY_SCHOOL_TOPICS_PATH = (
    _PROJECT_ROOT
    / "math"
    / "primary-school"
    / "curriculum"
    / "topics.json"
)


@dataclass(frozen=True)
class CurriculumTopic:
    id: str
    name: str = ""
    description: str = ""
    prerequisites: tuple[str, ...] = ()


@dataclass(frozen=True)
class Curriculum:
    subject: str | None
    topics: tuple[CurriculumTopic, ...]


def load_curriculum_topics(path: Path) -> Curriculum:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Curriculum JSON must be an object.")
    if "topics" not in raw:
        raise ValueError("Curriculum JSON is missing topics.")
    topics_raw = raw["topics"]
    if not isinstance(topics_raw, list):
        raise ValueError("Curriculum topics must be a list.")

    subject = raw.get("subject")
    if not isinstance(subject, str):
        subject = None

    topics: list[CurriculumTopic] = []
    seen: set[str] = set()
    for entry in topics_raw:
        topic = _parse_topic(entry)
        if topic.id in seen:
            raise ValueError(
                f"Duplicate curriculum topic id: {topic.id}."
            )
        seen.add(topic.id)
        topics.append(topic)

    topic_ids = {topic.id for topic in topics}
    for topic in topics:
        for prerequisite in topic.prerequisites:
            if prerequisite not in topic_ids:
                raise ValueError(
                    "Unknown prerequisite id "
                    f"{prerequisite!r} for topic {topic.id}."
                )

    return Curriculum(
        subject=subject,
        topics=tuple(topics),
    )


def prerequisite_graph(
    curriculum: Curriculum,
) -> dict[str, tuple[str, ...]]:
    return {
        topic.id: topic.prerequisites
        for topic in curriculum.topics
    }


def prerequisites_of(
    curriculum: Curriculum,
    topic_id: str,
) -> tuple[str, ...]:
    for topic in curriculum.topics:
        if topic.id == topic_id:
            return topic.prerequisites
    return ()


def _parse_topic(entry: object) -> CurriculumTopic:
    if not isinstance(entry, dict):
        raise ValueError("Curriculum topic must be an object.")
    topic_id = entry.get("id")
    if not isinstance(topic_id, str) or not topic_id.strip():
        raise ValueError("Curriculum topic id must be a non-empty string.")
    name = entry.get("name")
    description = entry.get("description")
    return CurriculumTopic(
        id=topic_id.strip(),
        name=name if isinstance(name, str) else "",
        description=(
            description if isinstance(description, str) else ""
        ),
        prerequisites=_parse_prerequisites(
            entry.get("prerequisites", ()),
            topic_id.strip(),
        ),
    )


def _parse_prerequisites(
    value: object,
    topic_id: str,
) -> tuple[str, ...]:
    if value == () or value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(
            f"Prerequisites for {topic_id} must be a list."
        )
    prerequisites: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"Prerequisite for {topic_id} must be a "
                "non-empty string."
            )
        prerequisites.append(item.strip())
    return tuple(prerequisites)
