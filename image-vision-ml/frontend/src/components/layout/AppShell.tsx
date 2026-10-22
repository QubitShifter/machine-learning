import { Suspense, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { ChartNoAxesCombined, CloudSun, FlaskConical, LayoutDashboard, Layers, MapPinned, Satellite, ShieldCheck, Sparkles } from "lucide-react";
import { useSatelliteDatasets } from "@/hooks/useSatellite";
import { useSoilDatasets } from "@/hooks/useSoil";
import { useWeatherDatasets, useWeatherQuality } from "@/hooks/useWeather";
import { preferredSatelliteDataset, preferredSoilDataset, preferredWeatherDataset, formatStatus } from "@/utils/format";
import { StatusBadge } from "@/components/common/StatusBadge";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/satellite", label: "Satellite Explorer", icon: Satellite },
  { to: "/integration", label: "Combined Analytics", icon: ChartNoAxesCombined },
  { to: "/weather", label: "Weather Analytics", icon: CloudSun },
  { to: "/soil", label: "Soil Analysis", icon: Layers },
  { to: "/quality", label: "Data Quality", icon: ShieldCheck },
  { to: "/ml/training", label: "ML Training Lab", icon: FlaskConical },
  { to: "/aoi", label: "Study Areas", icon: MapPinned },
];

const TITLES: Record<string, string> = {
  "/": "Overview",
  "/satellite": "Satellite Explorer",
  "/integration": "Combined Analytics",
  "/weather": "Weather Analytics",
  "/soil": "Soil Analysis",
  "/quality": "Data Quality",
  "/ml/training": "ML Training Lab",
  "/aoi": "Study Areas",
};

export function AppShell() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const satellite = useSatelliteDatasets();
  const weather = useWeatherDatasets();
  const soil = useSoilDatasets();
  const satelliteId = preferredSatelliteDataset(satellite.data ?? []);
  const weatherId = preferredWeatherDataset(weather.data ?? []);
  const soilId = preferredSoilDataset(soil.data ?? []);
  const quality = useWeatherQuality(weatherId);

  return (
    <div className="flex min-h-screen bg-ink-950">
      <aside
        className={`fixed inset-y-0 z-20 w-64 border-r border-ink-700 bg-ink-900 transition-transform lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center gap-2 border-b border-ink-700 px-4">
          <div className="h-8 w-8 rounded bg-moss-600/30 text-center text-lg leading-8 text-moss-400">◈</div>
          <div>
            <p className="text-sm font-semibold">Image Vision ML</p>
            <p className="text-[11px] text-slate-400">Geospatial research</p>
          </div>
        </div>
        <nav className="flex flex-col gap-1 p-3" aria-label="Primary">
          {NAV.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
                    isActive
                      ? "bg-ink-700 text-moss-400"
                      : "text-slate-300 hover:bg-ink-800"
                  }`
                }
              >
                <Icon size={16} />
                {item.label}
              </NavLink>
            );
          })}
          <span
            aria-disabled="true"
            title="Soil-moisture predictions are not implemented yet."
            className="mt-2 flex cursor-not-allowed items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-500"
          >
            <Sparkles size={16} />
            Predictions
            <span className="ml-auto text-[10px] uppercase tracking-wide">Coming later</span>
          </span>
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between gap-3 border-b border-ink-700 bg-ink-900/90 px-4">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              className="rounded border border-ink-600 px-2 py-1 text-xs lg:hidden"
              onClick={() => setOpen((value) => !value)}
              aria-label="Toggle navigation"
            >
              Menu
            </button>
            <div className="min-w-0">
              <h1 className="truncate text-base font-semibold">{TITLES[location.pathname] ?? "Image Vision ML"}</h1>
              <p className="truncate text-xs text-slate-400">
                {satelliteId ?? "No satellite dataset"} · {weatherId ?? "No weather dataset"} · {soilId ?? "No soil dataset"} · UTC
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <StatusBadge
              value={quality.data?.period_completeness}
              label={formatStatus(quality.data?.period_completeness ?? "unknown")}
            />
            <StatusBadge value={quality.data?.integration_readiness} />
          </div>
        </header>
        <main className="min-w-0 flex-1 overflow-x-hidden p-4 lg:p-6">
          {satellite.error || weather.error ? (
            <div className="mb-4 rounded-lg border border-rust-500/40 bg-rust-500/10 p-3 text-sm" role="alert">
              <p>{satellite.error?.message || weather.error?.message}</p>
              <button
                type="button"
                className="mt-2 rounded border border-sand-400/50 px-2 py-1 text-xs"
                onClick={() => {
                  void satellite.refetch();
                  void weather.refetch();
                }}
              >
                Retry
              </button>
            </div>
          ) : null}
          <Suspense fallback={<div className="p-6 text-sm text-slate-400">Loading workspace…</div>}>
            <Outlet context={{ satelliteId, weatherId, soilId }} />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
