from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.ml import (
    AgriculturalMlSummaryResponse,
    ExperimentDatasetResponse,
    ExperimentDetailResponse,
    ExperimentFeaturesResponse,
    ExperimentListItem,
    ExperimentMetricsResponse,
    ExperimentPredictionsResponse,
    ExperimentProvenanceResponse,
    ExperimentTrainingResponse,
    TrainingRunArtifactsResponse,
    TrainingRunDetailResponse,
    TrainingRunEventsResponse,
    TrainingRunListResponse,
    TrainingRunMetricsResponse,
)
from backend.app.services import ml_service
from ml.preprocessing.errors import DatasetNotFoundError, MissingProcessedOutputError, SoilForecastingError

router = APIRouter()


def _summary(dataset_id: str | None = None) -> AgriculturalMlSummaryResponse:
    try:
        return ml_service.research_summary(dataset_id)
    except DatasetNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MissingProcessedOutputError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/research-dataset", response_model=AgriculturalMlSummaryResponse)
def get_default_summary() -> AgriculturalMlSummaryResponse:
    return _summary()


@router.get("/datasets/{dataset_id}/summary", response_model=AgriculturalMlSummaryResponse)
def get_summary(dataset_id: str) -> AgriculturalMlSummaryResponse:
    return _summary(dataset_id)


@router.get("/experiments", response_model=list[ExperimentListItem])
def list_experiments() -> list[ExperimentListItem]:
    return ml_service.list_experiments()


@router.get("/experiments/{experiment_id}", response_model=ExperimentDetailResponse)
def get_experiment(experiment_id: str) -> ExperimentDetailResponse:
    try:
        return ml_service.experiment_detail(experiment_id)
    except (DatasetNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}/metrics", response_model=ExperimentMetricsResponse)
def get_experiment_metrics(
    experiment_id: str,
    partition: str = Query(default="validation"),
) -> ExperimentMetricsResponse:
    if partition not in {"validation", "test"}:
        raise HTTPException(status_code=400, detail="partition must be validation or test.")
    try:
        return ml_service.experiment_metrics(experiment_id, partition=partition)
    except (DatasetNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}/predictions", response_model=ExperimentPredictionsResponse)
def get_experiment_predictions(
    experiment_id: str,
    partition: str = Query(default="validation"),
    horizon_days: int | None = Query(default=None),
    model_id: str | None = Query(default=None),
    feature_set: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=400, ge=1, le=2000),
) -> ExperimentPredictionsResponse:
    if partition not in {"validation", "test"}:
        raise HTTPException(status_code=400, detail="partition must be validation or test.")
    try:
        return ml_service.experiment_predictions(
            experiment_id,
            partition=partition,
            horizon_days=horizon_days,
            model_id=model_id,
            feature_set=feature_set,
            offset=offset,
            limit=limit,
        )
    except (DatasetNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}/dataset", response_model=ExperimentDatasetResponse)
def get_experiment_dataset(experiment_id: str) -> ExperimentDatasetResponse:
    try:
        return ml_service.experiment_dataset(experiment_id)
    except (DatasetNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}/features", response_model=ExperimentFeaturesResponse)
def get_experiment_features(experiment_id: str) -> ExperimentFeaturesResponse:
    try:
        return ml_service.experiment_features(experiment_id)
    except (DatasetNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}/training", response_model=ExperimentTrainingResponse)
def get_experiment_training(experiment_id: str) -> ExperimentTrainingResponse:
    try:
        return ml_service.experiment_training(experiment_id)
    except (DatasetNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}/provenance", response_model=ExperimentProvenanceResponse)
def get_experiment_provenance(experiment_id: str) -> ExperimentProvenanceResponse:
    try:
        return ml_service.experiment_provenance(experiment_id)
    except (DatasetNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}/runs", response_model=TrainingRunListResponse)
def list_experiment_runs(
    experiment_id: str,
    model: str | None = Query(default=None),
    horizon_days: int | None = Query(default=None),
    feature_set: str | None = Query(default=None),
    status: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> TrainingRunListResponse:
    try:
        return ml_service.list_training_runs(
            experiment_id,
            model=model,
            horizon_days=horizon_days,
            feature_set=feature_set,
            status=status,
            start_date=start_date,
            limit=limit,
        )
    except (DatasetNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SoilForecastingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}/runs/{run_id}", response_model=TrainingRunDetailResponse)
def get_experiment_run(experiment_id: str, run_id: str) -> TrainingRunDetailResponse:
    try:
        return ml_service.training_run_detail(experiment_id, run_id)
    except (DatasetNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SoilForecastingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}/runs/{run_id}/events", response_model=TrainingRunEventsResponse)
def get_experiment_run_events(
    experiment_id: str,
    run_id: str,
    event_type: str | None = Query(default=None),
    phase: str | None = Query(default=None),
    sequence_after: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=2000),
) -> TrainingRunEventsResponse:
    try:
        return ml_service.training_run_events(
            experiment_id,
            run_id,
            event_type=event_type,
            phase=phase,
            sequence_after=sequence_after,
            limit=limit,
        )
    except (DatasetNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SoilForecastingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}/runs/{run_id}/metrics", response_model=TrainingRunMetricsResponse)
def get_experiment_run_metrics(experiment_id: str, run_id: str) -> TrainingRunMetricsResponse:
    try:
        return ml_service.training_run_metrics(experiment_id, run_id)
    except (DatasetNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SoilForecastingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/experiments/{experiment_id}/runs/{run_id}/artifacts", response_model=TrainingRunArtifactsResponse)
def get_experiment_run_artifacts(experiment_id: str, run_id: str) -> TrainingRunArtifactsResponse:
    try:
        return ml_service.training_run_artifacts(experiment_id, run_id)
    except (DatasetNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SoilForecastingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
