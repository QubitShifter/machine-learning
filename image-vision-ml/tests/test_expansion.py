from pathlib import Path

from ml.ingestion.config import validate_dataset_config
from ml.ingestion.expansion import ACTION_CANDIDATE_DOWNLOAD, preview_expansion_candidates
from ml.ingestion.manifest import empty_manifest, save_manifest, upsert_scene
from ml.ingestion.pipeline import preview_dataset_candidates
from ml.validation.coverage import build_monthly_coverage


def test_preview_prefers_missing_months_and_skips_ingested():
    config = validate_dataset_config({
        "dataset_id": "plovdiv_2023_2025",
        "source": {"collection": "sentinel-2-l2a"},
        "area": {"bbox": [24.65, 42.05, 24.68, 42.08]},
        "period": {"start": "2023-01-01", "end": "2023-03-31"},
    })
    catalog = [
        {
            "scene_id": "S2B_35TLG_20230110_0_L2A",
            "acquisition_date": "2023-01-10",
            "status": "processed",
            "mgrs_tile": "MGRS-35TLG",
            "cloud_cover": 4.0,
            "aoi_overlap_pct": 100.0,
        },
        {
            "scene_id": "S2A_35TLG_20230215_0_L2A",
            "acquisition_date": "2023-02-15",
            "status": "discovered",
            "mgrs_tile": "MGRS-35TLG",
            "cloud_cover": 8.0,
            "aoi_overlap_pct": 100.0,
        },
        {
            "scene_id": "S2B_34TGM_20230301_0_L2A",
            "acquisition_date": "2023-03-01",
            "status": "discovered",
            "mgrs_tile": "MGRS-34TGM",
            "cloud_cover": 2.0,
            "aoi_overlap_pct": 96.0,
        },
        {
            "scene_id": "S2A_35TLG_20230312_0_L2A",
            "acquisition_date": "2023-03-12",
            "status": "discovered",
            "mgrs_tile": "MGRS-35TLG",
            "cloud_cover": 12.0,
            "aoi_overlap_pct": 100.0,
        },
    ]
    quality = [
        {
            "scene_id": "S2B_35TLG_20230110_0_L2A",
            "acquisition_date": "2023-01-10",
            "quality_status": "valid",
        }
    ]
    coverage = build_monthly_coverage(
        period=config["period"],
        catalog_records=catalog,
        quality_scenes=quality,
        catalog_known=True,
    )
    preview = preview_expansion_candidates(
        config=config,
        catalog_records=catalog,
        catalog_known=True,
        quality_scenes=quality,
        coverage=coverage,
        limit=5,
        refresh_stac=False,
    )
    assert preview["dry_run"] is True
    assert preview["refresh_stac"] is False
    ids = [item["scene_id"] for item in preview["candidates"]]
    assert "S2B_35TLG_20230110_0_L2A" not in ids
    assert "S2A_35TLG_20230215_0_L2A" in ids
    march = next(item for item in preview["candidates"] if item["month"] == "2023-03")
    assert march["scene_id"] == "S2A_35TLG_20230312_0_L2A"
    assert march["expected_action"] == ACTION_CANDIDATE_DOWNLOAD
    assert "live_stac_item_metadata" in preview["unverified_without_network"]


def test_unknown_catalog_does_not_fabricate_candidates():
    config = validate_dataset_config({
        "dataset_id": "plovdiv_2023_2025",
        "source": {"collection": "sentinel-2-l2a"},
        "area": {"bbox": [24.65, 42.05, 24.68, 42.08]},
        "period": {"start": "2023-01-01", "end": "2023-02-28"},
    })
    coverage = build_monthly_coverage(
        period=config["period"],
        catalog_records=None,
        quality_scenes=[],
        catalog_known=False,
    )
    preview = preview_expansion_candidates(
        config=config,
        catalog_records=None,
        catalog_known=False,
        quality_scenes=[],
        coverage=coverage,
        limit=4,
    )
    assert preview["candidates"] == []
    assert preview["month_assessments"][0]["scene_id"] is None
    assert preview["month_assessments"][0]["selection_reason"] == "unknown_discovery_evidence"


def test_preview_cli_is_non_destructive(tmp_path: Path):
    config = validate_dataset_config({
        "dataset_id": "plovdiv_2023_2025",
        "source": {"collection": "sentinel-2-l2a"},
        "area": {"bbox": [24.65, 42.05, 24.68, 42.08]},
        "period": {"start": "2023-01-01", "end": "2023-01-31"},
    })
    raw = tmp_path / "raw" / "plovdiv_2023_2025"
    processed = tmp_path / "processed" / "plovdiv_2023_2025"
    manifest = empty_manifest(config)
    upsert_scene(
        manifest,
        "S2A_35TLG_20230110_0_L2A",
        status="discovered",
        acquisition_date="2023-01-10",
        mgrs_tile="35TLG",
        cloud_cover=5.0,
        aoi_overlap_pct=100.0,
        footprint_overlap_pct=100.0,
    )
    save_manifest(raw / "manifest.json", manifest)
    (raw / "discovered.json").write_text('{"records": []}', encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "dataset_id: plovdiv_2023_2025\n"
        "source:\n  collection: sentinel-2-l2a\n"
        "area:\n  bbox: [24.65, 42.05, 24.68, 42.08]\n"
        "period:\n  start: 2023-01-01\n  end: 2023-01-31\n",
        encoding="utf-8",
    )
    before = list(raw.rglob("*"))
    preview = preview_dataset_candidates(
        config_path,
        raw_root=tmp_path / "raw",
        processed_root=tmp_path / "processed",
    )
    after = list(raw.rglob("*"))
    assert preview["dry_run"] is True
    assert not any(path.suffix == ".tif" for path in after)
    assert set(before) <= set(after)
    assert (processed / "quality" / "expansion_preview.json").is_file()
