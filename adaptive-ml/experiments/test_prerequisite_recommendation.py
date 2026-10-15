from __future__ import annotations

from dataclasses import dataclass

from src.core.adaptive.prerequisites import (
    PREREQUISITE_FOUNDATION,
    resolve_prerequisite_topic,
)


LOW_MASTERY_THRESHOLD = 0.40


@dataclass(frozen=True)
class TopicState:
    mastery: object
    questions_completed: object


def resolve(
    topic_id: str,
    graph: dict[str, tuple[str, ...]],
    states: dict[str, TopicState],
    order: tuple[str, ...],
):
    return resolve_prerequisite_topic(
        topic_id,
        prerequisite_graph=graph,
        topic_states_by_id=states,
        ordered_topic_ids=order,
        low_mastery_threshold=LOW_MASTERY_THRESHOLD,
    )


def assert_no_prerequisite_is_unchanged():
    result = resolve(
        "number_patterns",
        {"number_patterns": ()},
        {},
        ("number_patterns",),
    )
    assert result.final_topic == "number_patterns"
    assert result.reason_code is None
    assert result.prerequisite_chain == ()


def assert_missing_prerequisite_state_is_unchanged():
    result = resolve(
        "story_problems",
        {"story_problems": ("arithmetic",)},
        {},
        ("story_problems",),
    )
    assert result.final_topic == "story_problems"


def assert_no_history_is_not_weak():
    result = resolve(
        "story_problems",
        {"story_problems": ("arithmetic",)},
        {"arithmetic": TopicState(0.20, 0)},
        ("arithmetic", "story_problems"),
    )
    assert result.final_topic == "story_problems"


def assert_demonstrated_weak_prerequisite_redirects():
    result = resolve(
        "story_problems",
        {"story_problems": ("arithmetic",)},
        {"arithmetic": TopicState(0.35, 3)},
        ("arithmetic", "story_problems"),
    )
    assert result.redirected is True
    assert result.initial_topic == "story_problems"
    assert result.final_topic == "arithmetic"
    assert result.prerequisite_chain == ("arithmetic",)
    assert result.reason_code == PREREQUISITE_FOUNDATION


def assert_mastery_at_threshold_is_unchanged():
    result = resolve(
        "story_problems",
        {"story_problems": ("arithmetic",)},
        {"arithmetic": TopicState(0.40, 4)},
        ("arithmetic", "story_problems"),
    )
    assert result.final_topic == "story_problems"


def assert_mastery_above_threshold_is_unchanged():
    result = resolve(
        "story_problems",
        {"story_problems": ("arithmetic",)},
        {"arithmetic": TopicState(0.75, 4)},
        ("arithmetic", "story_problems"),
    )
    assert result.final_topic == "story_problems"


def assert_non_runnable_prerequisite_is_not_selected():
    result = resolve(
        "story_problems",
        {"story_problems": ("arithmetic",)},
        {},
        ("story_problems",),
    )
    assert result.final_topic == "story_problems"


def assert_non_runnable_node_can_lead_to_foundation():
    result = resolve(
        "advanced",
        {
            "advanced": ("metadata_only",),
            "metadata_only": ("foundation",),
            "foundation": (),
        },
        {"foundation": TopicState(0.10, 3)},
        ("foundation", "advanced"),
    )
    assert result.final_topic == "foundation"
    assert result.prerequisite_chain == (
        "metadata_only",
        "foundation",
    )


def assert_transitive_weak_foundation_is_selected():
    result = resolve(
        "advanced",
        {
            "advanced": ("middle",),
            "middle": ("foundation",),
            "foundation": (),
        },
        {
            "middle": TopicState(0.20, 2),
            "foundation": TopicState(0.10, 3),
        },
        ("foundation", "middle", "advanced"),
    )
    assert result.final_topic == "foundation"
    assert result.prerequisite_chain == (
        "middle",
        "foundation",
    )


def assert_direct_weak_when_foundation_is_ready():
    result = resolve(
        "advanced",
        {
            "advanced": ("middle",),
            "middle": ("foundation",),
            "foundation": (),
        },
        {
            "middle": TopicState(0.20, 2),
            "foundation": TopicState(0.80, 3),
        },
        ("middle", "foundation", "advanced"),
    )
    assert result.final_topic == "middle"
    assert result.prerequisite_chain == ("middle",)


def assert_multiple_prerequisites_use_ranked_order():
    graph = {
        "target": ("first_declared", "ranked_first"),
        "first_declared": (),
        "ranked_first": (),
    }
    states = {
        "first_declared": TopicState(0.20, 1),
        "ranked_first": TopicState(0.30, 1),
    }
    result = resolve(
        "target",
        graph,
        states,
        ("ranked_first", "first_declared", "target"),
    )
    assert result.final_topic == "ranked_first"


def assert_cycle_is_safe():
    result = resolve(
        "target",
        {
            "target": ("cycle_a",),
            "cycle_a": ("cycle_b",),
            "cycle_b": ("cycle_a",),
        },
        {
            "cycle_a": TopicState(0.10, 3),
            "cycle_b": TopicState(0.10, 3),
        },
        ("cycle_a", "cycle_b", "target"),
    )
    assert result.final_topic == "target"


def assert_acyclic_sibling_survives_cyclic_branch():
    result = resolve(
        "target",
        {
            "target": ("cycle_a", "foundation"),
            "cycle_a": ("cycle_b",),
            "cycle_b": ("cycle_a",),
            "foundation": (),
        },
        {
            "cycle_a": TopicState(0.10, 3),
            "cycle_b": TopicState(0.10, 3),
            "foundation": TopicState(0.20, 2),
        },
        ("cycle_a", "cycle_b", "foundation", "target"),
    )
    assert result.final_topic == "foundation"


def assert_topic_absent_from_graph_is_unchanged():
    result = resolve(
        "missing",
        {"other": ("foundation",)},
        {"foundation": TopicState(0.10, 2)},
        ("foundation", "missing"),
    )
    assert result.final_topic == "missing"


def assert_malformed_mastery_fails_open():
    for mastery in ("0.10", None, float("nan")):
        result = resolve(
            "target",
            {"target": ("foundation",)},
            {"foundation": TopicState(mastery, 2)},
            ("foundation", "target"),
        )
        assert result.final_topic == "target"


def assert_malformed_questions_completed_fails_open():
    for questions_completed in ("2", None, 1.5, True):
        result = resolve(
            "target",
            {"target": ("foundation",)},
            {
                "foundation": TopicState(
                    0.10,
                    questions_completed,
                )
            },
            ("foundation", "target"),
        )
        assert result.final_topic == "target"


def assert_negative_questions_completed_fails_open():
    result = resolve(
        "target",
        {"target": ("foundation",)},
        {"foundation": TopicState(0.10, -1)},
        ("foundation", "target"),
    )
    assert result.final_topic == "target"


def main():
    tests = (
        assert_no_prerequisite_is_unchanged,
        assert_missing_prerequisite_state_is_unchanged,
        assert_no_history_is_not_weak,
        assert_demonstrated_weak_prerequisite_redirects,
        assert_mastery_at_threshold_is_unchanged,
        assert_mastery_above_threshold_is_unchanged,
        assert_non_runnable_prerequisite_is_not_selected,
        assert_non_runnable_node_can_lead_to_foundation,
        assert_transitive_weak_foundation_is_selected,
        assert_direct_weak_when_foundation_is_ready,
        assert_multiple_prerequisites_use_ranked_order,
        assert_cycle_is_safe,
        assert_acyclic_sibling_survives_cyclic_branch,
        assert_topic_absent_from_graph_is_unchanged,
        assert_malformed_mastery_fails_open,
        assert_malformed_questions_completed_fails_open,
        assert_negative_questions_completed_fails_open,
    )
    for test in tests:
        test()
    print(
        "prerequisite_recommendation tests passed "
        f"({len(tests)})"
    )


if __name__ == "__main__":
    main()
