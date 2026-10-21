import { Card } from "@/components/common/Card";
import type { IntegrationFeatureDefinition, IntegrationObservation } from "@/types/integration";
import { formatMeasured } from "@/utils/format";
import { featureMeta } from "@/utils/integration";

interface Props {
  row: IntegrationObservation;
  catalog?: IntegrationFeatureDefinition[];
}

const GROUPS = [
  {
    title: "Water balance",
    items: [
      { id: "precip_prev_7d_mm", label: "Prior 7-day rainfall", unit: "mm" },
      { id: "precip_prev_14d_mm", label: "Prior 14-day rainfall", unit: "mm" },
      { id: "precip_prev_30d_mm", label: "Prior 30-day rainfall", unit: "mm" },
      { id: "evap_prev_7d_mm", label: "Prior 7-day evaporation", unit: "mm" },
      { id: "evap_prev_30d_mm", label: "Prior 30-day evaporation", unit: "mm" },
      { id: "dry_days_prev_30d", label: "Prior 30-day dry days", unit: "days" },
    ],
  },
  {
    title: "Atmospheric conditions",
    items: [
      { id: "temp_mean_prev_7d_c", label: "Prior 7-day mean temperature", unit: "°C" },
      { id: "temp_mean_prev_30d_c", label: "Prior 30-day mean temperature", unit: "°C" },
      { id: "rh_mean_prev_7d_pct", label: "Prior 7-day relative humidity", unit: "%" },
      { id: "wind_mean_prev_7d_ms", label: "Prior 7-day wind speed", unit: "m/s" },
    ],
  },
] as const;

export function FeatureDetails({ row, catalog }: Props) {
  return (
    <Card title="Historical weather features">
      <p className="mb-3 text-xs text-slate-500">
        Null feature values stay unavailable even when a precipitation window is marked complete.
        Evaporation is ERA5-Land water-balance context, not in-situ ET.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        {GROUPS.map((group) => (
          <div key={group.title}>
            <h3 className="mb-2 text-xs uppercase tracking-wide text-slate-500">{group.title}</h3>
            <table className="w-full text-sm">
              <tbody>
                {group.items.map((item) => {
                  const meta = featureMeta(catalog, item.id);
                  const raw = row[item.id as keyof IntegrationObservation];
                  const value = typeof raw === "number" ? raw : null;
                  return (
                    <tr key={item.id} data-testid={`feature-${item.id}`}>
                      <th className="py-1 pr-3 text-left font-normal text-slate-400" title={definitionTitle(meta)}>
                        {meta?.name ?? item.label}
                      </th>
                      <td className="py-1 font-mono text-slate-100" data-available={String(value !== null)}>
                        {formatMeasured(value, meta?.unit ?? item.unit)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </Card>
  );
}

function definitionTitle(meta: IntegrationFeatureDefinition | undefined): string {
  if (!meta) return "";
  return [meta.window_definition, meta.calculation, meta.minimum_coverage, meta.data_source]
    .filter(Boolean)
    .join(" ");
}
