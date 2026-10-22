from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services import ml_service
from ml.ingestion.manifest import write_json_atomic

client = TestClient(app)


def test_research_dataset_unavailable_without_outputs(monkeypatch, tmp_path: Path):
    config = tmp_path / "configs" / "agricultural_ml_dataset.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        Path("configs/agricultural_ml_dataset.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    monkeypatch.setattr(ml_service, "DEFAULT_CONFIG", config)
    monkeypatch.setattr(
        ml_service,
        "output_directory",
        lambda _config, root=None: tmp_path / "out",
    )
    response = client.get("/api/v1/ml/research-dataset")
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is False
    assert payload["label"] == "Research dataset — no trained model yet."
    assert payload["trained_model_present"] is False
    assert payload["suitable_for_modeling"] is False


def test_research_dataset_summary_from_artifacts(monkeypatch, tmp_path: Path):
    config = tmp_path / "configs" / "agricultural_ml_dataset.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        Path("configs/agricultural_ml_dataset.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    out = tmp_path / "ml-out"
    out.mkdir()
    write_json_atomic(out / "dataset_summary.json", {
        "dataset_id": "plovdiv_agricultural_ml_2023_2025",
        "label": "Research dataset — no trained model yet.",
        "period": {"start": "2023-01-01", "end": "2025-12-31"},
        "feature_row_count": 1096,
        "feature_catalog_count": 40,
        "target_row_count": 16440,
        "horizons_days": [1, 3, 7],
        "leakage_status": "passed",
        "eligible_satellite_scenes": 15,
        "research_readiness": {
            "historical_research_readiness": "limited",
            "operational_forecast_readiness": "not_ready",
            "independent_ground_truth_readiness": "not_ready",
        },
    })
    monkeypatch.setattr(ml_service, "DEFAULT_CONFIG", config)
    monkeypatch.setattr(ml_service, "output_directory", lambda _config, root=None: out)
    response = client.get("/api/v1/ml/datasets/plovdiv_agricultural_ml_2023_2025/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["feature_row_count"] == 1096
    assert payload["leakage_status"] == "passed"
    assert payload["trained_model_present"] is False
    unknown = client.get("/api/v1/ml/datasets/unknown_dataset/summary")
    assert unknown.status_code == 404


def test_experiment_list_metrics_and_no_path_escape(monkeypatch, tmp_path: Path):
    root = tmp_path / "experiments"
    exp = root / "plovdiv_soil_forecast_baselines_v1"
    exp.mkdir(parents=True)
    write_json_atomic(exp / "experiment_summary.json", {
        "experiment_id": "plovdiv_soil_forecast_baselines_v1",
        "label": "Research experiment on ERA5-Land modeled soil moisture. Not operational.",
        "frozen": True,
        "test_evaluated": True,
        "suitable_for_modeling": False,
        "validation_comparison": [{"model_id": "persistence", "mae": 0.02, "horizon_days": 1}],
    })
    (exp / "model_comparison.csv").write_text(
        "model_id,horizon_days,mae,skill_mae\npersistence,1,0.02,0.0\n",
        encoding="utf-8",
    )
    (exp / "final_test_predictions.csv").write_text(
        "issue_date_utc,horizon_days,prediction,observed_modeled_target\n2025-01-02,1,0.2,0.21\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ml_service, "EXPERIMENTS_ROOT", root)
    listing = client.get("/api/v1/ml/experiments")
    assert listing.status_code == 200
    assert listing.json()[0]["operational_forecast"] is False
    detail = client.get("/api/v1/ml/experiments/plovdiv_soil_forecast_baselines_v1")
    assert detail.status_code == 200
    assert detail.json()["is_ground_truth"] is False
    metrics = client.get("/api/v1/ml/experiments/plovdiv_soil_forecast_baselines_v1/metrics?partition=validation")
    assert metrics.status_code == 200
    assert metrics.json()["total"] == 1
    preds = client.get(
        "/api/v1/ml/experiments/plovdiv_soil_forecast_baselines_v1/predictions?partition=test&limit=10"
    )
    assert preds.status_code == 200
    assert preds.json()["total"] == 1
    assert "Not field measurements" in preds.json()["label"]
    assert client.get("/api/v1/ml/experiments/../secrets").status_code == 404
    assert client.get("/api/v1/ml/experiments/missing_experiment").status_code == 404


def test_experiment_dataset_training_provenance_and_filters(monkeypatch, tmp_path: Path):
    root = tmp_path / "experiments"
    exp = root / "plovdiv_soil_forecast_baselines_v1"
    exp.mkdir(parents=True)
    (exp / "experiment_config_snapshot.yaml").write_text(
        "\n".join([
            "experiment_id: plovdiv_soil_forecast_baselines_v1",
            "pipeline_version: '4.1.0'",
            "random_seed: 42",
            "satellite_features_enabled: false",
            "primary_feature_set: C",
            "source:",
            "  ml_dataset_id: plovdiv_agricultural_ml_2023_2025",
            "  ml_dataset_version: '4.0.0'",
            "  target_source_kind: modeled_reanalysis",
            "target:",
            "  variable: swvl1",
            "  depth_label: 0-7 cm",
            "  unit: m3 m-3",
            "  horizons_days: [1, 3, 7]",
            "feature_sets:",
            "  C:",
            "    name: soil_weather",
            "    columns: [swvl1_prev1, precip_prev_7d_mm]",
            "  D:",
            "    enabled: false",
            "    columns: []",
            "missing_data:",
            "  policy: complete_case",
            "splits:",
            "  respect_horizon_purge: true",
            "  final_training_policy: training_partition_only",
            "issue_time:",
            "  research_mode: research_reanalysis",
        ]),
        encoding="utf-8",
    )
    write_json_atomic(exp / "prepared_summary.json", {
        "n_joined_rows": 3288,
        "eligible_rows": 3255,
        "counts": [{"split": "training", "horizon_days": 1, "feature_set": "C", "n": 350, "purged_or_missing": 14}],
    })
    write_json_atomic(exp / "feature_selection.json", {
        "primary_feature_set": "C",
        "satellite_excluded": True,
        "satellite_reason": "synthesized midnight timestamps",
        "features": [
            {
                "feature_id": "soil.swvl1_prev1",
                "column_name": "swvl1_prev1",
                "formula": "swvl1_mean on D-1",
                "units": "m3 m-3",
                "input_source": "daily_soil.csv",
                "temporal_window": "D-1",
                "feature_set": "C",
            },
        ],
    })
    write_json_atomic(exp / "training_summary.json", {
        "fitted_on": "training",
        "validation_used_for_fitting": False,
        "test_used_for_fitting": False,
        "random_seed": 42,
        "trained": [{"model_id": "ridge"}],
        "versions": {"python": "3.14.4", "scikit-learn": "1.9.1"},
        "git": {"commit": "1d617c5", "dirty": True},
        "generated_at_utc": "2026-10-22T18:37:24Z",
    })
    write_json_atomic(exp / "frozen_experiment.json", {
        "pipeline_version": "4.1.0",
        "config_fingerprint": "abc123",
        "frozen_at_utc": "2026-10-22T18:38:09Z",
        "test_consulted": True,
        "selected": [{"model_id": "persistence", "horizon_days": 1, "feature_set": "C", "n": 365}],
    })
    write_json_atomic(exp / "data_fingerprint.json", {
        "config_fingerprint": "abc123",
        "features_daily_sha256": {"sha256": "e7f6f074"},
    })
    (exp / "selected_validation_predictions.csv").write_text(
        "model_id,feature_set,horizon_days,prediction\n"
        "persistence,C,1,0.2\nridge,C,1,0.21\nridge,C,3,0.22\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ml_service, "EXPERIMENTS_ROOT", root)
    dataset = client.get("/api/v1/ml/experiments/plovdiv_soil_forecast_baselines_v1/dataset")
    assert dataset.status_code == 200
    body = dataset.json()
    assert body["available"] is True
    assert body["counts"][0]["n"] == 350
    assert body["suitable_for_modeling"] is False
    assert any(item["id"] == "D" and item["enabled"] is False for item in body["feature_sets"])
    features = client.get("/api/v1/ml/experiments/plovdiv_soil_forecast_baselines_v1/features")
    assert features.status_code == 200
    assert features.json()["predictive_feature_count"] == 1
    training = client.get("/api/v1/ml/experiments/plovdiv_soil_forecast_baselines_v1/training")
    assert training.status_code == 200
    assert training.json()["live_training"] is False
    assert training.json()["telemetry"]["available"] is False
    assert "not per-iteration telemetry" in training.json()["telemetry"]["reason"]
    provenance = client.get("/api/v1/ml/experiments/plovdiv_soil_forecast_baselines_v1/provenance")
    assert provenance.status_code == 200
    assert provenance.json()["operational_forecast"] is False
    assert provenance.json()["is_ground_truth"] is False
    assert provenance.json()["suitable_for_modeling"] is False
    assert "source_dataset_dir" not in provenance.json()
    filtered = client.get(
        "/api/v1/ml/experiments/plovdiv_soil_forecast_baselines_v1/predictions"
        "?partition=validation&horizon_days=1&model_id=ridge"
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["selected_only"] is True
    assert client.get("/api/v1/ml/experiments/not/a/path/dataset").status_code == 404


def test_experiment_get_does_not_train_or_rewrite(monkeypatch, tmp_path: Path):
    root = tmp_path / "experiments"
    exp = root / "plovdiv_soil_forecast_baselines_v1"
    exp.mkdir(parents=True)
    write_json_atomic(exp / "experiment_summary.json", {
        "experiment_id": "plovdiv_soil_forecast_baselines_v1",
        "frozen": True,
        "test_evaluated": False,
        "suitable_for_modeling": False,
    })
    write_json_atomic(exp / "prepared_summary.json", {"counts": [], "n_joined_rows": 1, "eligible_rows": 1})
    write_json_atomic(exp / "training_summary.json", {"fitted_on": "training", "trained": []})
    before = {path.name: (path.stat().st_mtime_ns, path.read_bytes()) for path in exp.iterdir()}
    monkeypatch.setattr(ml_service, "EXPERIMENTS_ROOT", root)
    for suffix in ("", "/dataset", "/features", "/training", "/provenance", "/metrics?partition=validation"):
        response = client.get(f"/api/v1/ml/experiments/plovdiv_soil_forecast_baselines_v1{suffix}")
        assert response.status_code == 200
    after = {path.name: (path.stat().st_mtime_ns, path.read_bytes()) for path in exp.iterdir()}
    assert after == before
    assert not (exp / "training_events.jsonl").exists()
    assert client.get("/api/v1/ml/experiments/plovdiv_soil_forecast_baselines_v1/training").json()["live_training"] is False
