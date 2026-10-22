import { Link, useOutletContext, useNavigate } from "react-router-dom";
import { Card } from "@/components/common/Card";
import { Metric } from "@/components/common/Metric";
import { QueryState } from "@/components/common/QueryState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { CoverageMatrix } from "@/components/quality/CoverageMatrix";
import { TaskReadiness } from "@/components/quality/TaskReadiness";
import { useAgriculturalMlSummary } from "@/hooks/useMl";
import { useSatelliteQuality } from "@/hooks/useSatellite";
import { useSoilDatasets, useSoilQuality } from "@/hooks/useSoil";
import { useWeatherQuality } from "@/hooks/useWeather";
import { formatNumber, formatPercent, formatStatus, preferredSoilDataset } from "@/utils/format";

interface Outlet {
  satelliteId?: string;
  weatherId?: string;
}

export function DataQualityPage() {
  const { satelliteId, weatherId } = useOutletContext<Outlet>();
  const weather = useWeatherQuality(weatherId);
  const satellite = useSatelliteQuality(satelliteId);
  const soilList = useSoilDatasets();
  const soilId = preferredSoilDataset(soilList.data ?? []);
  const soil = useSoilQuality(soilId);
  const research = useAgriculturalMlSummary();
  const navigate = useNavigate();
  const hourly = weather.data?.hourly ?? {};
  const daily = weather.data?.daily ?? {};
  const accumulation = weather.data?.accumulation ?? hourly.accumulation ?? {};
  const coverage = weather.data?.coverage;
  const satelliteMonths = Object.fromEntries(
    (satellite.data?.coverage?.months ?? []).map((row) => [row.month, row.coverage_status]),
  );
  const unresolved = satellite.data?.calibration_audit?.unresolved_scene_ids ?? [];

  return (
    <div className="space-y-4">
      <Card title="Quality dimensions">
        <QueryState
          isLoading={weather.isLoading}
          error={weather.error}
          onRetry={() => void weather.refetch()}
        >
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <Dimension
              title="Source integrity"
              value={weather.data?.source_integrity}
              note="Hourly file consistency after expected month-boundary overlaps are reconciled."
            />
            <Dimension
              title="Observation validity"
              value={weather.data?.observation_validity}
              note="Validity of days that have observations. Missing days are coverage, not corruption."
            />
            <Dimension
              title="Period completeness"
              value={weather.data?.period_completeness}
              note={`${formatNumber(daily.complete_days, 0)} complete of ${formatNumber(daily.day_count ?? coverage?.expected_days, 0)} processed days.`}
            />
            <Dimension
              title="Integration readiness"
              value={weather.data?.integration_readiness}
              note="Ready only for unrestricted three-year modelling when the archive is complete and valid."
            />
          </div>
          <p className="mt-3 text-sm text-sand-300">
            Overall API status is <StatusBadge value={weather.data?.status} />. That does not mean the
            three-year archive is ready for model training.
          </p>
        </QueryState>
      </Card>

      <Card title="Weather monthly coverage">
        <CoverageMatrix
          availability={coverage?.month_availability}
          onSelect={(month) => navigate(`/weather?year=${month.slice(0, 4)}&month=${month}`)}
        />
      </Card>

      <Card title="Satellite monthly coverage">
        <QueryState
          isLoading={satellite.isLoading}
          error={satellite.error}
          onRetry={() => void satellite.refetch()}
        >
          {Object.keys(satelliteMonths).length ? (
            <CoverageMatrix
              satelliteStatuses={satelliteMonths}
              onSelect={(month) => navigate(`/satellite?month=${month}`)}
            />
          ) : (
            <p className="text-sm text-slate-400">
              Satellite monthly coverage is written by validate. Unknown discovery evidence is not shown as zero.
            </p>
          )}
          {unresolved.length ? (
            <p className="mt-2 text-xs text-sand-200">
              Calibration review: {unresolved.join(", ")}
            </p>
          ) : null}
        </QueryState>
      </Card>

      <Card
        title="Modeled soil moisture"
        actions={(
          <Link className="text-xs text-moss-300 hover:underline" to="/soil">
            Soil analysis
          </Link>
        )}
      >
        {!soilId ? (
          <p className="text-sm text-slate-400">
            ERA5-Land volumetric soil water has not been processed. When present it is a modeled
            regional state, not an in-situ ground measurement, and does not set suitable_for_modeling.
          </p>
        ) : (
          <QueryState
            isLoading={soil.isLoading}
            error={soil.error}
            onRetry={() => void soil.refetch()}
          >
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <Metric label="Dataset" value={soilId} />
              <Metric label="Complete days" value={formatNumber(soil.data?.daily.complete_days, 0)} />
              <Metric label="Kind" value={soil.data?.observation_kind ?? "modeled"} />
              <Metric label="Ground truth" value={soil.data?.is_ground_truth ? "yes" : "no"} />
            </div>
            <p className="mt-3 text-sm text-sand-300">
              Quality {formatStatus(soil.data?.status)}. Modeled readiness{" "}
              {formatStatus(soil.data?.modeled_soil_readiness)}. suitable_for_modeling remains false
              for ERA5-Land soil water.
            </p>
          </QueryState>
        )}
      </Card>

      <Card title="Agricultural ML research dataset">
        <QueryState
          isLoading={research.isLoading}
          error={research.error}
          onRetry={() => void research.refetch()}
        >
          <p className="mb-3 text-sm font-medium text-sand-100">
            {research.data?.label ?? "Research dataset — no trained model yet."}
          </p>
          {!research.data?.available ? (
            <p className="text-sm text-slate-400">
              Features and targets have not been generated. Run the agricultural ML dataset
              pipeline locally. No trained forecast is shown here.
            </p>
          ) : (
            <>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <Metric label="Dataset" value={research.data.dataset_id ?? "—"} />
                <Metric label="Feature rows" value={formatNumber(research.data.feature_row_count, 0)} />
                <Metric label="Target rows" value={formatNumber(research.data.target_row_count, 0)} />
                <Metric
                  label="Horizons"
                  value={(research.data.horizons_days ?? []).map((item) => `${item}d`).join(", ") || "—"}
                />
                <Metric label="Leakage" value={formatStatus(research.data.leakage_status)} />
                <Metric label="Research readiness" value={formatStatus(research.data.historical_research_readiness)} />
                <Metric label="Operational readiness" value={formatStatus(research.data.operational_forecast_readiness)} />
                <Metric label="Ground truth" value={formatStatus(research.data.independent_ground_truth_readiness)} />
              </div>
              <p className="mt-3 text-sm text-sand-300">
                Coverage {research.data.period_start ?? "—"} through {research.data.period_end ?? "—"}.
                suitable_for_modeling remains false. Operational replay is not verified.
                {" "}
                <Link className="text-moss-300 hover:underline" to="/ml/training">
                  Open ML Training Lab
                </Link>
              </p>
            </>
          )}
        </QueryState>
      </Card>

      <Card title="Modeling readiness by task">
        <TaskReadiness report={satellite.data?.task_readiness} />
      </Card>

      <Card title="Validation details">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Metric label="Unique hourly timestamps" value={formatNumber(asNumber(hourly.unique_timestamps), 0)} />
          <Metric label="Expected boundary overlaps" value={formatNumber(asNumber(hourly.expected_boundary_overlaps), 0)} />
          <Metric label="Unexpected accumulation resets" value={formatNumber(asNumber(accumulation.unexpected_resets), 0)} />
          <Metric label="Negative accumulation steps" value={formatNumber(asNumber(accumulation.negative_steps), 0)} />
          <Metric label="Complete daily records" value={formatNumber(daily.complete_days, 0)} />
          <Metric label="Missing daily records" value={formatNumber(daily.missing_days, 0)} />
          <Metric label="Expected total days" value={formatNumber(coverage?.expected_days ?? daily.day_count, 0)} />
          <Metric label="Completeness" value={formatPercent(daily.completeness_pct)} />
          <Metric label="Forecast-cycle resets" value={formatNumber(asNumber(accumulation.forecast_cycle_resets), 0)} />
        </div>
        <p className="mt-3 text-sm text-slate-400">
          01:00 UTC decreases are expected ERA5-Land forecast-cycle starts. They are not treated as data corruption.
          Daily totals continue to use the next-day 00:00 UTC accumulated value.
        </p>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card title="Available for inspection">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
            <li>{formatNumber(daily.complete_days, 0)} complete UTC weather days can be inspected now.</li>
            <li>{formatNumber(satellite.data?.dataset.validated_scenes, 0)} validated Sentinel-2 observations are available.</li>
            <li>Source integrity is {formatStatus(weather.data?.source_integrity)}.</li>
          </ul>
        </Card>
        <Card title="Not ready for unrestricted modelling">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
            <li>Weather integration readiness: {formatStatus(weather.data?.integration_readiness)}.</li>
            <li>Satellite soil-forecasting readiness: {formatStatus(satellite.data?.training_readiness?.supervised_soil_forecasting)}.</li>
            <li>Observation-level suitable_for_modeling uses that soil-forecasting gate, not exploratory NDVI.</li>
            <li>ERA5-Land soil water is modeled, not independently measured field moisture.</li>
            <li>Soil-moisture production forecasts are not trained in this phase.</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}

function Dimension({ title, value, note }: { title: string; value?: string | null; note: string }) {
  return (
    <div className="rounded-lg border border-ink-600 bg-ink-800/50 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-400">{title}</p>
      <div className="mt-2"><StatusBadge value={value} /></div>
      <p className="mt-2 text-xs text-slate-400">{note}</p>
    </div>
  );
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}
