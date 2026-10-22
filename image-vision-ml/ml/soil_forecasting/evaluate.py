"""Evaluation, physical sanity and error summaries on aligned prediction rows."""

from __future__ import annotations

from datetime import date
from typing import Any, Sequence

import numpy as np
import pandas as pd

from ml.agricultural_ml.metrics import (
    mae,
    mbe,
    r_squared,
    rmse,
    skill_versus_persistence,
    wetting_drying_direction_accuracy,
)
from ml.preprocessing.weather import _maybe_float


def _floats(series: Sequence[Any]) -> list[float | None]:
    return [_maybe_float(item) for item in series]


def aligned_metrics(
    observed: Sequence[Any],
    predicted: Sequence[Any],
    persistence: Sequence[Any],
    baseline: Sequence[Any],
    *,
    direction_tolerance: float,
) -> dict[str, Any]:
    y = _floats(observed)
    yhat = _floats(predicted)
    persist = _floats(persistence)
    prev = _floats(baseline)
    pairs = [(a, b, c, d) for a, b, c, d in zip(y, yhat, persist, prev) if None not in (a, b, c, d)]
    if not pairs:
        return {"n": 0, "mae": None, "rmse": None, "mbe": None, "r2": None, "skill_mae": None}
    obs, pred, pers, base = zip(*pairs)
    model_mae = mae(obs, pred)
    pers_mae = mae(obs, pers)
    delta_obs = [o - b for o, b in zip(obs, base)]
    delta_pred = [p - b for p, b in zip(pred, base)]
    return {
        "n": len(pairs),
        "mae": model_mae,
        "rmse": rmse(obs, pred),
        "mbe": mbe(obs, pred),
        "r2": r_squared(obs, pred),
        "skill_mae": skill_versus_persistence(model_mae, pers_mae),
        "persistence_mae": pers_mae,
        "change_mae": mae(delta_obs, delta_pred),
        "change_rmse": rmse(delta_obs, delta_pred),
        "change_mbe": mbe(delta_obs, delta_pred),
        "direction_accuracy": wetting_drying_direction_accuracy(
            delta_obs, delta_pred, tolerance=direction_tolerance,
        ),
        "note": (
            "Change MAE equals absolute MAE when both subtract the same D−1 baseline. "
            "It is not an independent improvement."
        ),
    }


def attach_predictions(frame: pd.DataFrame, predicted, *, persistence_feature: str) -> pd.DataFrame:
    out = frame.copy()
    out["prediction"] = list(predicted)
    out["persistence_prediction"] = out[persistence_feature].map(_maybe_float)
    out["error"] = [
        None if _maybe_float(y) is None or _maybe_float(yhat) is None
        else float(yhat) - float(y)
        for y, yhat in zip(out["absolute_target"], out["prediction"])
    ]
    out["derived_change_prediction"] = [
        None if _maybe_float(yhat) is None or _maybe_float(prev) is None
        else float(yhat) - float(prev)
        for yhat, prev in zip(out["prediction"], out["persistence_prediction"])
    ]
    return out


def season_name(stamp: str, seasons: dict[str, list[int]]) -> str | None:
    if not stamp:
        return None
    month = date.fromisoformat(str(stamp)[:10]).month
    for name, months in seasons.items():
        if month in months:
            return name
    return None


def subset_metrics(frame: pd.DataFrame, config: dict[str, Any]) -> list[dict[str, Any]]:
    eval_cfg = config.get("evaluation") or {}
    tolerance = float(eval_cfg.get("direction_tolerance") or 1e-4)
    persist = config["target"]["persistence_feature"]
    observed = "absolute_target" if "absolute_target" in frame.columns else "observed_modeled_target"
    persist_col = persist if persist in frame.columns else "persistence_prediction"
    rows = []
    seasons = eval_cfg.get("seasons") or {}
    rain_mm = float(eval_cfg.get("recent_rainfall_prev7_mm") or 10.0)
    dry_mm = float(eval_cfg.get("dry_prev7_mm") or 1.0)

    def add(label: str, mask: pd.Series) -> None:
        part = frame.loc[mask]
        metrics = aligned_metrics(
            part[observed], part["prediction"],
            part[persist_col], part[persist_col],
            direction_tolerance=tolerance,
        )
        metrics["subset"] = label
        rows.append(metrics)

    if "target_date_utc" in frame.columns:
        names = frame["target_date_utc"].map(lambda value: season_name(str(value or ""), seasons))
        for name in seasons:
            add(f"season_{name}", names == name)
    if "precip_prev_7d_mm" in frame.columns:
        rain = pd.to_numeric(frame["precip_prev_7d_mm"], errors="coerce")
        add("recent_rainfall_issue_time", rain >= rain_mm)
        add("extended_dry_issue_time", rain < dry_mm)
        rows[-2]["definition"] = f"precip_prev_7d_mm >= {rain_mm} at issue time"
        rows[-1]["definition"] = f"precip_prev_7d_mm < {dry_mm} at issue time"
    delta = pd.to_numeric(frame.get("change_target"), errors="coerce")
    add("observed_wetting", delta > tolerance)
    add("observed_drying", delta < -tolerance)
    return rows


def physical_sanity(predicted: Sequence[Any], observed: Sequence[Any], baseline: Sequence[Any], config: dict[str, Any]) -> dict[str, Any]:
    eval_cfg = config.get("evaluation") or {}
    lower = float(eval_cfg.get("volumetric_lower") or 0.0)
    upper = float(eval_cfg.get("volumetric_upper") or 1.0)
    extreme = float(eval_cfg.get("extreme_daily_change") or 0.15)
    yhat = [_maybe_float(item) for item in predicted]
    y = [_maybe_float(item) for item in observed]
    prev = [_maybe_float(item) for item in baseline]
    finite = [item for item in yhat if item is not None and np.isfinite(item)]
    below = sum(1 for item in finite if item < lower)
    above = sum(1 for item in finite if item > upper)
    missing = sum(1 for item in yhat if item is None or not np.isfinite(item))
    changes = [
        abs(p - b) for p, b in zip(yhat, prev)
        if p is not None and b is not None and np.isfinite(p) and np.isfinite(b)
    ]
    extreme_n = sum(1 for item in changes if item > extreme)
    train_like = [item for item in y if item is not None]
    lo = min(train_like) if train_like else None
    hi = max(train_like) if train_like else None
    outside = 0
    if lo is not None and hi is not None:
        outside = sum(1 for item in finite if item < lo or item > hi)
    constant = False
    if len(finite) >= 2:
        constant = max(finite) - min(finite) < 1e-12
    return {
        "n": len(yhat),
        "finite": len(finite),
        "missing_or_nonfinite": missing,
        "below_zero": below,
        "above_one": above,
        "extreme_daily_change_count": extreme_n,
        "extreme_daily_change_threshold": extreme,
        "outside_observed_range": outside,
        "constant_predictions": constant,
        "clipped_before_evaluation": False,
        "volumetric_bounds_note": "0–1 is a generic volumetric bound, not field capacity or wilting point.",
    }


def prediction_records(
    frame: pd.DataFrame,
    *,
    model_id: str,
    feature_set: str,
    partition: str,
    config: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    persist = config["target"]["persistence_feature"]
    extra = extra or {}
    records = []
    for _, row in frame.iterrows():
        records.append({
            "experiment_id": config["experiment_id"],
            "model_id": model_id,
            "feature_set": feature_set,
            "partition": partition,
            "issue_date_utc": row.get("issue_date_utc"),
            "target_date_utc": row.get("target_date_utc"),
            "horizon_days": int(row["horizon_days"]),
            "target_variable": row.get("target_variable"),
            "depth_label": config["target"].get("depth_label"),
            "observed_modeled_target": _maybe_float(row.get("absolute_target")),
            "prediction": _maybe_float(row.get("prediction")),
            "persistence_prediction": _maybe_float(row.get(persist)),
            "error": _maybe_float(row.get("error")),
            "change_target": _maybe_float(row.get("change_target")),
            "derived_change_prediction": _maybe_float(row.get("derived_change_prediction")),
            "precip_prev_7d_mm": _maybe_float(row.get("precip_prev_7d_mm")),
            "path": extra.get("path"),
            "alpha": extra.get("alpha"),
            "max_depth": extra.get("max_depth"),
            "learning_rate": extra.get("learning_rate"),
            "max_iter": extra.get("max_iter"),
            "target_source_kind": "modeled_reanalysis",
            "is_ground_truth": False,
            "research_mode": "research_reanalysis",
            "unit": "m3 m-3",
        })
    return records
