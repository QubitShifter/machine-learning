from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from typing import Mapping, Protocol, Sequence


PREREQUISITE_FOUNDATION = "prerequisite_foundation"


class PrerequisiteTopicState(Protocol):
    mastery: float
    questions_completed: int


@dataclass(frozen=True)
class PrerequisiteResolution:
    initial_topic: str
    final_topic: str
    prerequisite_chain: tuple[str, ...] = ()
    reason_code: str | None = None

    @property
    def redirected(self) -> bool:
        return self.initial_topic != self.final_topic


def resolve_prerequisite_topic(
    topic_id: str,
    *,
    prerequisite_graph: Mapping[str, tuple[str, ...]],
    topic_states_by_id: Mapping[str, PrerequisiteTopicState],
    ordered_topic_ids: Sequence[str],
    low_mastery_threshold: float,
) -> PrerequisiteResolution:
    unchanged = PrerequisiteResolution(
        initial_topic=topic_id,
        final_topic=topic_id,
    )
    if (
        not isinstance(topic_id, str)
        or not _valid_number(low_mastery_threshold)
    ):
        return unchanged

    try:
        if topic_id not in prerequisite_graph:
            return unchanged

        order = {
            candidate_id: index
            for index, candidate_id in enumerate(
                ordered_topic_ids
            )
            if isinstance(candidate_id, str)
        }
        active: list[str] = []
        cyclic_nodes: set[str] = set()
        memo: dict[
            str,
            tuple[str, tuple[str, ...]] | None,
        ] = {}

        def ordered_prerequisites(node_id: str) -> tuple[str, ...]:
            raw = prerequisite_graph.get(node_id, ())
            if not isinstance(raw, (tuple, list)):
                return ()

            unique: list[str] = []
            for prerequisite_id in raw:
                if (
                    isinstance(prerequisite_id, str)
                    and prerequisite_id not in unique
                ):
                    unique.append(prerequisite_id)
            declaration_order = {
                prerequisite_id: index
                for index, prerequisite_id in enumerate(unique)
            }
            return tuple(
                sorted(
                    unique,
                    key=lambda prerequisite_id: (
                        order.get(
                            prerequisite_id,
                            len(order),
                        ),
                        declaration_order[prerequisite_id],
                    ),
                )
            )

        def search(
            node_id: str,
        ) -> tuple[str, tuple[str, ...]] | None:
            if node_id in active:
                cycle_start = active.index(node_id)
                cyclic_nodes.update(active[cycle_start:])
                return None
            if node_id in memo:
                return memo[node_id]

            active.append(node_id)
            for prerequisite_id in ordered_prerequisites(
                node_id
            ):
                descendant = search(prerequisite_id)
                if descendant is not None:
                    final_topic, descendant_chain = descendant
                    result = (
                        final_topic,
                        (node_id, *descendant_chain),
                    )
                    active.pop()
                    if node_id not in cyclic_nodes:
                        memo[node_id] = result
                    return result

            active.pop()
            if (
                node_id not in cyclic_nodes
                and _is_demonstrated_weak(
                    topic_states_by_id.get(node_id),
                    low_mastery_threshold,
                )
            ):
                result = (node_id, (node_id,))
                memo[node_id] = result
                return result

            if node_id not in cyclic_nodes:
                memo[node_id] = None
            return None

        for prerequisite_id in ordered_prerequisites(topic_id):
            found = search(prerequisite_id)
            if found is None:
                continue
            final_topic, chain = found
            return PrerequisiteResolution(
                initial_topic=topic_id,
                final_topic=final_topic,
                prerequisite_chain=chain,
                reason_code=PREREQUISITE_FOUNDATION,
            )
    except (
        AttributeError,
        KeyError,
        OverflowError,
        RecursionError,
        TypeError,
        ValueError,
    ):
        return unchanged

    return unchanged


def _is_demonstrated_weak(
    topic_state: PrerequisiteTopicState | None,
    low_mastery_threshold: float,
) -> bool:
    if topic_state is None:
        return False

    try:
        mastery = topic_state.mastery
        questions_completed = topic_state.questions_completed
    except (AttributeError, TypeError):
        return False

    if (
        not _valid_number(mastery)
        or not _valid_number(questions_completed)
    ):
        return False
    if not float(questions_completed).is_integer():
        return False

    return (
        questions_completed > 0
        and mastery < low_mastery_threshold
    )


def _valid_number(value: object) -> bool:
    if (
        not isinstance(value, Real)
        or isinstance(value, bool)
    ):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, TypeError, ValueError):
        return False
