from pydantic import BaseModel, Field


class ExperimentListItem(BaseModel):
    experiment_id: str
    label: str
    frozen: bool = False
    test_evaluated: bool = False
    operational_forecast: bool = False
    suitable_for_modeling: bool = False


class ExperimentDetailResponse(BaseModel):
    experiment_id: str
    label: str
    frozen: bool = False
    test_evaluated: bool = False
    suitable_for_modeling: bool = False
    trained_model_present: bool = False
    operational_forecast: bool = False
    target_source_kind: str = "modeled_reanalysis"
    is_ground_truth: bool = False
    dataset_id: str | None = None
    dataset_version: str | None = None
    pipeline_version: str | None = None
    target_variable: str | None = None
    depth_label: str | None = None
    unit: str | None = None
    horizons_days: list[int] = Field(default_factory=list)
    feature_sets: list[str] = Field(default_factory=list)
    primary_feature_set: str | None = None
    config_fingerprint: str | None = None
    frozen_at_utc: str | None = None
    random_seed: int | None = None
    research_mode: str = "research_reanalysis"
    validation_comparison: list[dict] = Field(default_factory=list)
    final_test_metrics: list[dict] | None = None


class ExperimentMetricsResponse(BaseModel):
    experiment_id: str
    partition: str
    total: int
    records: list[dict]


class ExperimentPredictionsResponse(BaseModel):
    experiment_id: str
    partition: str
    total: int
    offset: int
    limit: int
    records: list[dict]
    selected_only: bool = False
    label: str = "ERA5-Land modeled soil-moisture research predictions. Not field measurements."


class ExperimentDatasetResponse(BaseModel):
    experiment_id: str
    available: bool
    label: str = "Research experiment dataset statistics."
    dataset_id: str | None = None
    dataset_version: str | None = None
    pipeline_version: str | None = None
    target_variable: str | None = None
    depth_label: str | None = None
    unit: str | None = None
    horizons_days: list[int] = Field(default_factory=list)
    feature_sets: list[dict] = Field(default_factory=list)
    n_joined_rows: int | None = None
    eligible_rows: int | None = None
    counts: list[dict] = Field(default_factory=list)
    missing_data_policy: str | None = None
    satellite_features_enabled: bool = False
    chronological_splits: dict = Field(default_factory=dict)
    suitable_for_modeling: bool = False
    is_ground_truth: bool = False
    target_source_kind: str = "modeled_reanalysis"


class ExperimentFeatureRecord(BaseModel):
    feature_id: str | None = None
    column_name: str
    scientific_meaning: str | None = None
    input_source: str | None = None
    source_variable: str | None = None
    units: str | None = None
    temporal_window: str | None = None
    formula: str | None = None
    missing_data_policy: str | None = None
    feature_sets: list[str] = Field(default_factory=list)
    used_by_primary: bool = False
    satellite: bool = False


class ExperimentFeaturesResponse(BaseModel):
    experiment_id: str
    available: bool
    primary_feature_set: str | None = None
    satellite_excluded: bool = True
    satellite_reason: str | None = None
    predictive_feature_count: int | None = None
    records: list[ExperimentFeatureRecord] = Field(default_factory=list)
    note: str = "Feature metadata from the experiment catalog. Not fitted coefficients."


class TrainingLifecycleStage(BaseModel):
    stage: str
    label: str
    status: str
    artifact: str | None = None


class ExperimentTrainingResponse(BaseModel):
    experiment_id: str
    available: bool
    live_training: bool = False
    fitted_on: str | None = None
    validation_used_for_fitting: bool = False
    test_used_for_fitting: bool = False
    random_seed: int | None = None
    generated_at_utc: str | None = None
    selected: list[dict] = Field(default_factory=list)
    trained_candidate_count: int | None = None
    telemetry: dict = Field(default_factory=dict)
    lifecycle: list[TrainingLifecycleStage] = Field(default_factory=list)
    coefficients: list[dict] = Field(default_factory=list)
    seasonal_monthly_means: dict | None = None
    suitable_for_modeling: bool = False
    note: str = "Read-only training artifacts. GET does not train models."


class ExperimentProvenanceResponse(BaseModel):
    experiment_id: str
    available: bool
    pipeline_version: str | None = None
    dataset_id: str | None = None
    dataset_version: str | None = None
    config_fingerprint: str | None = None
    features_daily_sha256: str | None = None
    frozen: bool = False
    frozen_at_utc: str | None = None
    test_consulted: bool = False
    test_evaluated_at_utc: str | None = None
    test_repeat: bool | None = None
    git_revision: str | None = None
    git_dirty: bool | None = None
    python_version: str | None = None
    package_versions: dict = Field(default_factory=dict)
    random_seed: int | None = None
    research_mode: str = "research_reanalysis"
    operational_forecast: bool = False
    operational_availability_verified: bool = False
    is_ground_truth: bool = False
    is_measured_soil_moisture: bool = False
    suitable_for_modeling: bool = False
    target_source_kind: str = "modeled_reanalysis"
    training_events_format: str = "training_events.jsonl"
    training_events_present: bool = False
    label: str = "Research experiment on ERA5-Land modeled soil moisture. Not operational."


class AgriculturalMlSummaryResponse(BaseModel):
    available: bool
    label: str = "Research dataset — no trained model yet."
    dataset_id: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    feature_row_count: int | None = None
    feature_catalog_count: int | None = None
    target_row_count: int | None = None
    horizons_days: list[int] = Field(default_factory=list)
    leakage_status: str | None = None
    historical_research_readiness: str | None = None
    operational_forecast_readiness: str | None = None
    independent_ground_truth_readiness: str | None = None
    suitable_for_modeling: bool = False
    trained_model_present: bool = False
    eligible_satellite_scenes: int | None = None
