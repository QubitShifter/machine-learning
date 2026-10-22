import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";

const OverviewPage = lazy(() =>
  import("@/pages/OverviewPage").then((module) => ({ default: module.OverviewPage })),
);
const SatelliteExplorerPage = lazy(() =>
  import("@/pages/SatelliteExplorerPage").then((module) => ({ default: module.SatelliteExplorerPage })),
);
const IntegrationAnalyticsPage = lazy(() =>
  import("@/pages/IntegrationAnalyticsPage").then((module) => ({ default: module.IntegrationAnalyticsPage })),
);
const WeatherAnalyticsPage = lazy(() =>
  import("@/pages/WeatherAnalyticsPage").then((module) => ({ default: module.WeatherAnalyticsPage })),
);
const DataQualityPage = lazy(() =>
  import("@/pages/DataQualityPage").then((module) => ({ default: module.DataQualityPage })),
);
const SoilAnalysisPage = lazy(() =>
  import("@/pages/SoilAnalysisPage").then((module) => ({ default: module.SoilAnalysisPage })),
);
const AoiPage = lazy(() =>
  import("@/pages/AoiPage").then((module) => ({ default: module.AoiPage })),
);

export function App() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-slate-400">Loading workspace…</div>}>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/satellite" element={<SatelliteExplorerPage />} />
          <Route path="/integration" element={<IntegrationAnalyticsPage />} />
          <Route path="/weather" element={<WeatherAnalyticsPage />} />
          <Route path="/soil" element={<SoilAnalysisPage />} />
          <Route path="/quality" element={<DataQualityPage />} />
          <Route path="/aoi" element={<AoiPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
