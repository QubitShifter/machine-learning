"""Persistence, seasonal, Ridge and gradient-boosting estimators. Training data only."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.preprocessing.errors import SoilForecastingError
from ml.preprocessing.weather import _maybe_float
from ml.soil_forecasting.dataset import matrix


def persistence_predict(frame, feature: str = "swvl1_prev1") -> np.ndarray:
    values = frame[feature].map(_maybe_float).to_numpy()
    return np.array([None if item is None else float(item) for item in values], dtype=object)


def fit_seasonal_monthly(frame) -> dict[int, float]:
    buckets: dict[int, list[float]] = defaultdict(list)
    for _, row in frame.iterrows():
        target = _maybe_float(row.get("absolute_target"))
        stamp = str(row.get("target_date_utc") or "")[:10]
        if target is None or not stamp:
            continue
        month = date.fromisoformat(stamp).month
        buckets[month].append(float(target))
    if not buckets:
        raise SoilForecastingError("Seasonal baseline has no training targets.")
    return {month: float(sum(values) / len(values)) for month, values in buckets.items()}


def seasonal_predict(frame, monthly: dict[int, float]) -> np.ndarray:
    output = []
    for _, row in frame.iterrows():
        stamp = str(row.get("target_date_utc") or "")[:10]
        if not stamp:
            output.append(None)
            continue
        output.append(monthly.get(date.fromisoformat(stamp).month))
    return np.array(output, dtype=object)


def ridge_pipeline(alpha: float) -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("ridge", Ridge(alpha=float(alpha))),
    ])


def boosting_estimator(*, max_depth: int, learning_rate: float, max_iter: int, seed: int) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        max_depth=int(max_depth),
        learning_rate=float(learning_rate),
        max_iter=int(max_iter),
        random_state=int(seed),
        early_stopping=False,
    )


def fit_sklearn(estimator, train_frame, columns: list[str]):
    features, target = matrix(train_frame, columns)
    if len(target) == 0:
        raise SoilForecastingError("Cannot fit a model on an empty training partition.")
    estimator.fit(features, target)
    return estimator


def predict_sklearn(estimator, frame, columns: list[str]) -> np.ndarray:
    features, _ = matrix(frame, columns)
    if len(features) == 0:
        return np.array([], dtype=float)
    return np.asarray(estimator.predict(features), dtype=float)


def save_joblib(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, path)


def load_joblib(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SoilForecastingError(f"Model artifact is missing: {path.name}")
    return joblib.load(path)
