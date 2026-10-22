"""ERA5-Land soil-moisture and wetness-indicator commands."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from ml.ingestion.soil_pipeline import (
    check_soil_config,
    download_soil,
    generate_wetness_dataset,
    process_soil_dataset,
    report_soil_dataset,
    soil_status,
    validate_soil_dataset,
)
from ml.sources.registry import load_source_registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download and process ERA5-Land soil water and wetness indicators.",
    )
    parser.add_argument("--log-level", default="INFO", help="Python logging level")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Validate soil config and CDS authentication")
    check.add_argument("--config", default="configs/soil_era5_land.yaml")

    status = sub.add_parser("status", help="Show downloaded, pending, and failed months")
    status.add_argument("--config", default="configs/soil_era5_land.yaml")
    status.add_argument("--start-month", help="UTC month YYYY-MM")
    status.add_argument("--end-month", help="UTC month YYYY-MM")

    download = sub.add_parser("download", help="Download one month or a sequential range")
    download.add_argument("--config", default="configs/soil_era5_land.yaml")
    download.add_argument("--month", help="Single UTC month as YYYY-MM")
    download.add_argument("--start-month", help="First UTC month YYYY-MM")
    download.add_argument("--end-month", help="Last UTC month YYYY-MM")
    download.add_argument("--dry-run", action="store_true")
    download.add_argument(
        "--resume",
        action="store_true",
        help="Download pending/failed months only; never overwrite complete files",
    )

    process = sub.add_parser("process", help="Aggregate downloaded hourly soil-water files")
    process.add_argument("--config", default="configs/soil_era5_land.yaml")
    process.add_argument(
        "--full-period",
        action="store_true",
        help="Emit a row for every day in the configured period",
    )

    validate = sub.add_parser("validate", help="Read the soil quality report")
    validate.add_argument("--config", default="configs/soil_era5_land.yaml")

    report = sub.add_parser("report", help="Refresh monthly summary and chart")
    report.add_argument("--config", default="configs/soil_era5_land.yaml")

    wetness = sub.add_parser("wetness", help="Generate rainfall-derived wetness indicators")
    wetness.add_argument("--weather-config", default="configs/weather_era5_land.yaml")

    sources = sub.add_parser("sources", help="Print the agricultural source registry")

    diagnose = sub.add_parser("diagnose", help="Exploratory soil–weather correlations")
    diagnose.add_argument("--config", default="configs/soil_era5_land.yaml")
    diagnose.add_argument("--weather-config", default="configs/weather_era5_land.yaml")

    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    try:
        return _run_command(args, parser)
    except KeyboardInterrupt:
        logging.error("Interrupted.")
        return 130
    except Exception as exc:
        logging.error("%s", exc)
        return 1


def _run_command(args, parser: argparse.ArgumentParser) -> int:
    if args.command == "check":
        print(json.dumps(check_soil_config(Path(args.config)), indent=2))
        return 0
    if args.command == "status":
        print(json.dumps(soil_status(
            Path(args.config),
            start_month=args.start_month,
            end_month=args.end_month,
        ), indent=2))
        return 0
    if args.command == "download":
        result = download_soil(
            Path(args.config),
            month=args.month,
            start_month=args.start_month,
            end_month=args.end_month,
            dry_run=args.dry_run,
            resume=args.resume,
        )
        print(json.dumps(_jsonable(result), indent=2))
        return 0
    if args.command == "process":
        result = process_soil_dataset(Path(args.config), full_period=args.full_period)
        print(json.dumps(_jsonable(result), indent=2))
        return 0
    if args.command == "validate":
        print(json.dumps(validate_soil_dataset(Path(args.config)), indent=2))
        return 0
    if args.command == "report":
        print(json.dumps(_jsonable(report_soil_dataset(Path(args.config))), indent=2))
        return 0
    if args.command == "wetness":
        print(json.dumps(_jsonable(generate_wetness_dataset(Path(args.weather_config))), indent=2))
        return 0
    if args.command == "sources":
        print(json.dumps(_jsonable(load_source_registry()), indent=2))
        return 0
    if args.command == "diagnose":
        from ml.analysis.soil_timeseries import read_daily_soil
        from ml.analysis.soil_weather import exploratory_soil_weather_report
        from ml.analysis.weather_timeseries import read_daily_weather
        from ml.ingestion.soil_pipeline import soil_paths
        from ml.ingestion.weather_download import weather_paths
        from ml.ingestion.soil_config import load_soil_config
        from ml.ingestion.weather_config import load_weather_config
        from ml.preprocessing.errors import MissingProcessedOutputError

        soil_cfg = load_soil_config(Path(args.config))
        weather_cfg = load_weather_config(Path(args.weather_config))
        soil_csv = soil_paths(soil_cfg["dataset_id"])["daily_csv"]
        weather_csv = weather_paths(weather_cfg["dataset_id"])["daily_csv"]
        if not soil_csv.is_file() or not weather_csv.is_file():
            raise MissingProcessedOutputError(
                "Soil and weather daily tables are required for diagnostics."
            )
        report = exploratory_soil_weather_report(
            read_daily_soil(soil_csv),
            read_daily_weather(weather_csv),
        )
        print(json.dumps(_jsonable(report), indent=2))
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
