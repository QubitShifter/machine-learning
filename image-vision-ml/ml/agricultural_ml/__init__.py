"""Leakage-safe agricultural ML research-dataset construction (Phase 4.0).

This package prepares features, targets, splits and audits. It does not train
forecasting models and does not alter `suitable_for_modeling`.
"""

from ml.agricultural_ml.pipeline import (
    PIPELINE_VERSION,
    audit_leakage,
    build_dataset,
    check_config,
    report_dataset,
    split_summary,
    validate_dataset,
)

__all__ = [
    "PIPELINE_VERSION",
    "audit_leakage",
    "build_dataset",
    "check_config",
    "report_dataset",
    "split_summary",
    "validate_dataset",
]
