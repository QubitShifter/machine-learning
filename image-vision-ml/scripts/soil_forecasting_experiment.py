"""Phase 4.1 soil-moisture forecasting experiment CLI. No CDS. No operational predict."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from ml.preprocessing.errors import (
    AgriculturalMlError,
    MissingProcessedOutputError,
    SoilForecastingError,
)
from ml.soil_forecasting.pipeline import (
    check_experiment,
    compare_models,
    evaluate_test,
    prepare_experiment,
    report_experiment,
    train_models,
    validate_models,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Train and evaluate research soil-moisture forecasts on ERA5-Land modeled "
            "targets. Does not deploy operational forecasts."
        ),
    )
    parser.add_argument("--log-level", default="INFO")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("check", "Validate Phase 4.0 artifacts, leakage and experiment config"),
        ("prepare", "Join features, targets and splits; write fingerprints"),
        ("train", "Fit models on the training partition only"),
        ("validate", "Score candidates on 2024 validation"),
        ("compare", "Select models on validation and freeze the experiment"),
        ("evaluate-test", "Score frozen models on 2025 exactly; does not retrain"),
        ("report", "Summarize artifacts without training"),
    ):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("--config", default="configs/soil_forecasting_experiment.yaml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    config = Path(args.config)
    try:
        result = _run(args.command, config)
    except KeyboardInterrupt:
        logging.error("Interrupted.")
        return 130
    except (SoilForecastingError, AgriculturalMlError, MissingProcessedOutputError, FileNotFoundError, ValueError) as exc:
        logging.error("%s", exc)
        return 1
    print(json.dumps(_jsonable(result), indent=2, default=str))
    return 0


def _run(command: str, config: Path) -> dict:
    if command == "check":
        return check_experiment(config)
    if command == "prepare":
        return prepare_experiment(config)
    if command == "train":
        return train_models(config)
    if command == "validate":
        return validate_models(config)
    if command == "compare":
        return compare_models(config)
    if command == "evaluate-test":
        return evaluate_test(config)
    if command == "report":
        return report_experiment(config)
    raise SoilForecastingError(f"Unknown command {command}.")


def _jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
