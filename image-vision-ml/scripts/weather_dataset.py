"""ERA5-Land weather dataset commands."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from ml.ingestion.weather_pipeline import (
    check_weather_config,
    download_weather,
    integrate_weather_dataset,
    process_weather_dataset,
    report_weather_dataset,
    validate_weather_dataset,
    weather_status,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download and process ERA5-Land historical weather.",
    )
    parser.add_argument("--log-level", default="INFO", help="Python logging level")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Validate config and CDS authentication")
    check.add_argument("--config", required=True)

    status = sub.add_parser("status", help="Show downloaded, pending, and failed months")
    status.add_argument("--config", required=True)
    status.add_argument("--start-month", help="UTC month YYYY-MM")
    status.add_argument("--end-month", help="UTC month YYYY-MM")

    download = sub.add_parser("download", help="Download one month or a sequential range")
    download.add_argument("--config", required=True)
    download.add_argument("--month", help="Single UTC month as YYYY-MM")
    download.add_argument("--start-month", help="First UTC month YYYY-MM")
    download.add_argument("--end-month", help="Last UTC month YYYY-MM")
    download.add_argument("--dry-run", action="store_true")
    download.add_argument(
        "--resume",
        action="store_true",
        help="Download pending/failed months only; never overwrite complete files",
    )

    process = sub.add_parser("process", help="Aggregate downloaded hourly files")
    process.add_argument("--config", required=True)
    process.add_argument(
        "--full-period",
        action="store_true",
        help="Emit a row for every day in the configured period",
    )

    validate = sub.add_parser("validate", help="Read the weather quality report")
    validate.add_argument("--config", required=True)

    report = sub.add_parser("report", help="Refresh monthly summary and chart")
    report.add_argument("--config", required=True)

    integrate = sub.add_parser("integrate", help="Join weather with satellite NDVI")
    integrate.add_argument("--config", required=True)
    integrate.add_argument("--satellite-dataset", required=True)

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
    if args.command == "check":
        print(json.dumps(check_weather_config(config), indent=2))
        return 0
    if args.command == "status":
        print(json.dumps(weather_status(
            config,
            start_month=args.start_month,
            end_month=args.end_month,
        ), indent=2))
        return 0
    if args.command == "download":
        result = download_weather(
            config,
            month=args.month,
            start_month=args.start_month,
            end_month=args.end_month,
            dry_run=args.dry_run,
            resume=args.resume,
        )
        print(json.dumps(_jsonable(result), indent=2))
        return 0
    if args.command == "process":
        result = process_weather_dataset(config, full_period=args.full_period)
        print(json.dumps(_jsonable(result), indent=2))
        return 0
    if args.command == "validate":
        result = validate_weather_dataset(config)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "report":
        result = report_weather_dataset(config)
        print(json.dumps(_jsonable(result), indent=2))
        return 0
    if args.command == "integrate":
        result = integrate_weather_dataset(
            config,
            satellite_dataset_id=args.satellite_dataset,
        )
        printable = dict(result)
        printable.pop("rows", None)
        print(json.dumps(printable, indent=2))
        return 0
    parser.error(f"Unknown command: {args.command}")
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
