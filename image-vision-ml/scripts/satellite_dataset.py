"""Satellite time-series dataset commands."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from ml.ingestion.pipeline import (
    download_dataset,
    generate_dataset_report,
    generate_dataset_timeseries,
    preview_dataset_candidates,
    process_dataset,
    search_dataset,
    validate_dataset,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Discover, download, and analyse Sentinel-2 time series.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search", help="Search STAC without downloading rasters")
    search.add_argument("--config", required=True)

    download = sub.add_parser("download", help="Download AOI windows")
    download.add_argument("--config", required=True)
    download.add_argument("--limit", type=int, default=5)
    download.add_argument(
        "--scene-id",
        action="append",
        dest="scene_ids",
        help="Download a specific STAC scene ID. Repeat for a controlled batch. "
        "When set, stratified --limit selection is not used.",
    )
    download.add_argument("--dry-run", action="store_true")

    process = sub.add_parser("process", help="Process downloaded scenes")
    process.add_argument("--config", required=True)
    process.add_argument("--force", action="store_true")

    timeseries = sub.add_parser("timeseries", help="Build NDVI time series")
    timeseries.add_argument("--config", required=True)

    validate = sub.add_parser("validate", help="Validate local dataset quality")
    validate.add_argument("--config", required=True)

    report = sub.add_parser("report", help="Write quality and time-series reports")
    report.add_argument("--config", required=True)

    candidates = sub.add_parser(
        "candidates",
        help="Preview missing-month expansion candidates without downloading",
    )
    candidates.add_argument("--config", required=True)
    candidates.add_argument("--limit", type=int, default=12)
    candidates.add_argument(
        "--refresh-stac",
        action="store_true",
        help="Opt-in live STAC search. Default uses local discovery evidence only.",
    )

    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    config = Path(args.config)

    try:
        return _run_command(args, config, parser)
    except KeyboardInterrupt:
        logging.error("Interrupted.")
        return 130
    except Exception as exc:
        logging.error("%s", exc)
        return 1


def _run_command(args, config: Path, parser: argparse.ArgumentParser) -> int:
    if args.command == "search":
        result = search_dataset(config)
        print(json.dumps({
            "dataset_id": result["dataset_id"],
            "discovered": result["discovered"],
            "scene_ids": [item["scene_id"] for item in result["records"]],
        }, indent=2))
        return 0
    if args.command == "download":
        result = download_dataset(
            config,
            limit=args.limit,
            dry_run=args.dry_run,
            scene_ids=args.scene_ids,
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "process":
        result = process_dataset(config, force=args.force)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "timeseries":
        result = generate_dataset_timeseries(config)
        print(json.dumps({
            "dataset_id": result["dataset_id"],
            "observation_count": result["observation_count"],
            "observations": result["observations"],
            "monthly": result.get("monthly"),
            "yearly": result.get("yearly"),
            "missing_months": result["missing_months"],
        }, indent=2))
        return 0
    if args.command == "validate":
        result = validate_dataset(config)
        print(json.dumps({
            "dataset_id": result["dataset_id"],
            "dataset": result["dataset"],
            "training_readiness": result["training_readiness"],
            "coverage": (result.get("coverage") or {}).get("summary"),
            "task_readiness": {
                task: item.get("status")
                for task, item in ((result.get("task_readiness") or {}).get("by_task") or {}).items()
            },
            "unresolved_calibration": (result.get("calibration_audit") or {}).get(
                "unresolved_scene_ids"
            ),
        }, indent=2))
        rejected = int(result["dataset"].get("rejected_scenes") or 0)
        return 1 if rejected and result["dataset"].get("validated_scenes", 0) == 0 else 0
    if args.command == "report":
        result = generate_dataset_report(config)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "candidates":
        result = preview_dataset_candidates(
            config,
            refresh_stac=args.refresh_stac,
            limit=args.limit,
        )
        print(json.dumps(result, indent=2))
        return 0
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
