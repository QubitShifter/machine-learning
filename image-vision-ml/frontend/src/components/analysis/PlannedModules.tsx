import { Card } from "@/components/common/Card";

const MODULES = [
  { name: "NDMI (B11)", reason: "SWIR B11 is not in the current Sentinel-2 ingestion set." },
  { name: "Soil temperature profiles", reason: "ERA5-Land stl1–4 are aliased but not processed into daily soil tables." },
  { name: "Vegetation temporal trends", reason: "Requires a longer validated NDVI series than exploratory charts." },
  { name: "Soil property comparisons", reason: "SoilGrids REST is paused; sand/clay/silt/FC/WP are not available." },
  { name: "Vegetation stress analysis", reason: "Needs NDMI or independently validated moisture, which are not present." },
  { name: "Actual versus predicted moisture", reason: "No trained soil-moisture model and no in-situ labels." },
  { name: "Forecast uncertainty", reason: "No ingested forecast archive with issue/valid times." },
  { name: "Agricultural drought indicators", reason: "Requires a defined drought index and complete weather/soil coverage." },
];

export function PlannedModules() {
  return (
    <Card title="Later analytical modules">
      <p className="mb-2 text-xs text-slate-400">
        These interfaces are reserved. They are not implemented and are not shown as available science.
      </p>
      <ul className="space-y-1 text-sm text-slate-300">
        {MODULES.map((item) => (
          <li key={item.name}>
            <span className="font-medium text-slate-200">{item.name}</span>
            <span className="text-slate-500"> — planned. {item.reason}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
