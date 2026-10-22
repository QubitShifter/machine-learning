import { StatusBadge } from "@/components/common/StatusBadge";
import type { TaskReadinessAssessment, TaskReadinessReport } from "@/types/api";

const LABELS: Record<string, string> = {
  exploratory_ndvi_analysis: "Exploratory NDVI analysis",
  weather_ndvi_relationship_analysis: "Weather–NDVI relationship",
  vegetation_forecasting: "Vegetation forecasting",
  soil_moisture_historical_analysis: "Soil-moisture historical analysis",
  rainfall_derived_wetness_analysis: "Rainfall-derived wetness analysis",
  modeled_soil_moisture_forecasting_research: "Modeled soil-moisture forecasting research",
  independently_validated_field_soil_moisture_forecasting: "Independent field soil-moisture forecasting",
  supervised_soil_forecasting: "Supervised soil forecasting",
};

interface Props {
  report?: TaskReadinessReport | {
    tasks?: TaskReadinessAssessment[];
    by_task?: Record<string, TaskReadinessAssessment>;
    suitable_for_modeling_meaning?: string;
  } | null;
  meaning?: string | null;
}

export function TaskReadiness({ report, meaning }: Props) {
  const tasks = report?.tasks ?? Object.values(report?.by_task ?? {});
  if (!tasks.length) {
    return (
      <p className="text-sm text-slate-400">
        Task-specific readiness has not been written yet. Run satellite validate, then weather integrate.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">
        {meaning
          ?? report?.suitable_for_modeling_meaning
          ?? "suitable_for_modeling remains supervised soil-forecasting eligibility and is not a general ML gate."}
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        {tasks.map((item) => (
          <TaskCard key={item.task} item={item} />
        ))}
      </div>
    </div>
  );
}

function TaskCard({ item }: { item: TaskReadinessAssessment }) {
  return (
    <div className="rounded-lg border border-ink-600 bg-ink-800/50 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-slate-200">{LABELS[item.task] ?? item.task}</p>
        <StatusBadge value={item.status} />
      </div>
      {item.explanation ? (
        <p className="mt-2 text-xs text-slate-400">{item.explanation}</p>
      ) : null}
      {item.reasons?.length ? (
        <ul className="mt-2 list-disc pl-4 text-xs text-sand-200">
          {item.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      ) : null}
      {item.warnings?.length ? (
        <ul className="mt-2 list-disc pl-4 text-xs text-slate-400">
          {item.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
