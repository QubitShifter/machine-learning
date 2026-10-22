"""Forecast evaluation contracts. Fixtures only — not agricultural skill."""

from __future__ import annotations

from typing import Sequence


class MetricContractError(ValueError):
    """A metric cannot be computed from the supplied pairs."""


def _pairs(
    observed: Sequence[float | None],
    predicted: Sequence[float | None],
) -> list[tuple[float, float]]:
    if len(observed) != len(predicted):
        raise MetricContractError("observed and predicted lengths differ.")
    pairs = []
    for y_i, yhat in zip(observed, predicted):
        if y_i is None or yhat is None:
            continue
        pairs.append((float(y_i), float(yhat)))
    return pairs


def mae(observed: Sequence[float | None], predicted: Sequence[float | None]) -> float | None:
    pairs = _pairs(observed, predicted)
    if not pairs:
        return None
    return sum(abs(yhat - y) for y, yhat in pairs) / len(pairs)


def rmse(observed: Sequence[float | None], predicted: Sequence[float | None]) -> float | None:
    pairs = _pairs(observed, predicted)
    if not pairs:
        return None
    return (sum((yhat - y) ** 2 for y, yhat in pairs) / len(pairs)) ** 0.5


def mbe(observed: Sequence[float | None], predicted: Sequence[float | None]) -> float | None:
    pairs = _pairs(observed, predicted)
    if not pairs:
        return None
    return sum(yhat - y for y, yhat in pairs) / len(pairs)


def r_squared(observed: Sequence[float | None], predicted: Sequence[float | None]) -> float | None:
    pairs = _pairs(observed, predicted)
    if len(pairs) < 2:
        return None
    y_bar = sum(y for y, _ in pairs) / len(pairs)
    ss_tot = sum((y - y_bar) ** 2 for y, _ in pairs)
    ss_res = sum((y - yhat) ** 2 for y, yhat in pairs)
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else None
    return 1.0 - ss_res / ss_tot


def skill_versus_persistence(
    model_mae: float | None,
    persistence_mae: float | None,
) -> float | None:
    if model_mae is None or persistence_mae is None:
        return None
    if persistence_mae == 0:
        return None if model_mae != 0 else 0.0
    return 1.0 - model_mae / persistence_mae


def wetting_drying_direction_accuracy(
    observed_delta: Sequence[float | None],
    predicted_delta: Sequence[float | None],
    *,
    tolerance: float = 1e-4,
) -> float | None:
    """Share of pairs whose wetting/drying sign matches, ignoring |Δθ| < tolerance."""
    if len(observed_delta) != len(predicted_delta):
        raise MetricContractError("delta series lengths differ.")
    considered = 0
    correct = 0
    for y, yhat in zip(observed_delta, predicted_delta):
        if y is None or yhat is None:
            continue
        if abs(y) < tolerance and abs(yhat) < tolerance:
            considered += 1
            correct += 1
            continue
        if abs(y) < tolerance or abs(yhat) < tolerance:
            considered += 1
            continue
        considered += 1
        if (y > 0) == (yhat > 0):
            correct += 1
    if not considered:
        return None
    return correct / considered
