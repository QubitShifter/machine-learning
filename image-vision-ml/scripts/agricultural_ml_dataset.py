"""Leakage-safe agricultural ML research-dataset commands. No training."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from ml.agricultural_ml.pipeline import (
    audit_leakage,
    build_dataset,
    check_config,
    report_dataset,
    split_summary,
    validate_dataset,
)
from ml.preprocessing.errors import AgriculturalMlError, MissingProcessedOutputError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build and audit the leakage-safe agricultural ML research dataset. Does not train models.",
    )
    parser.add_argument("--log-level", default="INFO")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("check", "Validate configuration and local source files (no network)"),
        ("build", "Generate features, targets, splits and audits"),
        ("validate", "Validate generated outputs without rewriting sources"),
        ("audit-leakage", "Print the stored temporal leakage report"),
        ("splits", "Print split membership summary"),
        ("features", "Alias of build (features are generated with targets)"),
        ("targets", "Alias of build"),
        ("report", "Print dataset_summary.json"),
    ):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("--config", default="configs/agricultural_ml_dataset.yaml")
        if name in {"build", "features", "targets"}:
            command.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    config = Path(args.config)
    try:
        return _run(args, config)
    except KeyboardInterrupt:
        logging.error("Interrupted.")
        return 130
    except (AgriculturalMlError, MissingProcessedOutputError, FileNotFoundError) as exc:
        logging.error("%s", exc)
        return 1


def _run(args, config: Path) -> int:
    if args.command == "check":
        result = check_config(config)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 2
    if args.command in {"build", "features", "targets"}:
        result = build_dataset(config, dry_run=bool(getattr(args, "dry_run", False)))
        print(json.dumps(_jsonable(result), indent=2))
        return 0
    if args.command == "validate":
        print(json.dumps(validate_dataset(config), indent=2))
        return 0
    if args.command == "audit-leakage":
        print(json.dumps(audit_leakage(config), indent=2))
        return 0
    if args.command == "splits":
        print(json.dumps(split_summary(config), indent=2))
        return 0
    if args.command == "report":
        print(json.dumps(report_dataset(config), indent=2))
        return 0
    return 2


def _jsonable(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
