import { describe, expect, it } from "vitest";
import type { MonthlySoilRow } from "@/types/api";
import {
  MONTH_LABELS,
  MONTH_SHORT,
  buildYearOverYearRows,
  completeYearsFromMonthly,
  formatYearOverYearTooltip,
  interannualDelta,
  seasonalMean,
  utcDaysInMonth,
  yearsFromMonthly,
} from "./soilYearComparison";

function row(month: string, extras: Partial<MonthlySoilRow> = {}): MonthlySoilRow {
  const [year, monthPart] = month.split("-");
  const days = utcDaysInMonth(year, Number(monthPart));
  return {
    month,
    day_count: days,
    complete_days: days,
    missing_days: 0,
    availability: "complete",
    swvl1_mean: 0.35,
    swvl2_mean: 0.34,
    swvl3_mean: 0.29,
    swvl4_mean: 0.31,
    theta_root_zone_0_100_mean: 0.30,
    theta_root_zone_0_100_min: 0.28,
    theta_root_zone_0_100_max: 0.33,
    aggregation: "monthly_mean_of_complete_days",
    unit: "m3 m-3",
    observation_kind: "modeled_volumetric_soil_moisture",
    ...extras,
  };
}

function yearMonths(year: string, extras: Record<string, Partial<MonthlySoilRow>> = {}): MonthlySoilRow[] {
  return Array.from({ length: 12 }, (_, index) => {
    const month = `${year}-${String(index + 1).padStart(2, "0")}`;
    return row(month, extras[month]);
  });
}

const JAN_2023 = 0.3029981553682717;
const JAN_2025 = 0.3734779265619093;

describe("soil year-over-year grouping", () => {
  it("orders January through December and groups by year", () => {
    const rows = [...yearMonths("2025"), ...yearMonths("2023")];
    const chart = buildYearOverYearRows(rows, "theta_root_zone_0_100_mean", ["2023", "2025"]);
    expect(chart.map((item) => item.monthLabel)).toEqual([...MONTH_LABELS]);
    expect(MONTH_SHORT).toHaveLength(12);
    expect(chart[0]?.monthIndex).toBe(1);
    expect(chart[11]?.monthIndex).toBe(12);
    expect(yearsFromMonthly(rows)).toEqual(["2023", "2025"]);
    expect(completeYearsFromMonthly(rows)).toEqual(["2023", "2025"]);
  });

  it("keeps leap-year February complete-day counts", () => {
    const rows = [row("2023-02"), row("2024-02")];
    expect(utcDaysInMonth("2023", 2)).toBe(28);
    expect(utcDaysInMonth("2024", 2)).toBe(29);
    expect(rows[0]?.complete_days).toBe(28);
    expect(rows[1]?.complete_days).toBe(29);
    const chart = buildYearOverYearRows(rows, "theta_root_zone_0_100_mean", ["2023", "2024"]);
    expect(chart[1]?.points["2023"]?.completeDays).toBe(28);
    expect(chart[1]?.points["2024"]?.completeDays).toBe(29);
  });

  it("leaves missing months as null gaps, not zero", () => {
    const rows = yearMonths("2023", {
      "2023-06": {
        complete_days: 0,
        availability: "missing",
        swvl1_mean: null,
        swvl2_mean: null,
        swvl3_mean: null,
        swvl4_mean: null,
        theta_root_zone_0_100_mean: null,
        theta_root_zone_0_100_min: null,
        theta_root_zone_0_100_max: null,
      },
    });
    const chart = buildYearOverYearRows(rows, "theta_root_zone_0_100_mean", ["2023"]);
    expect(chart[5]?.values["2023"]).toBeNull();
    expect(chart[5]?.points["2023"]?.availability).toBe("missing");
    expect(chart[4]?.values["2023"]).toBe(0.30);
    expect(completeYearsFromMonthly(rows)).toEqual([]);
  });

  it("does not treat a later year as a complete year when months are absent", () => {
    expect(completeYearsFromMonthly([row("2026-01")])).toEqual([]);
    expect(yearsFromMonthly([row("2026-01")])).toEqual(["2026"]);
  });

  it("selects the requested soil depth for every year", () => {
    const rows = [
      row("2023-01", { swvl1_mean: 0.11, theta_root_zone_0_100_mean: 0.22 }),
      row("2024-01", { swvl1_mean: 0.12, theta_root_zone_0_100_mean: 0.23 }),
    ];
    const surface = buildYearOverYearRows(rows, "swvl1_mean", ["2023", "2024"]);
    const profile = buildYearOverYearRows(rows, "theta_root_zone_0_100_mean", ["2023", "2024"]);
    expect(surface[0]?.values["2023"]).toBe(0.11);
    expect(profile[0]?.values["2023"]).toBe(0.22);
    expect(profile[0]?.points["2023"]?.min).toBe(0.28);
  });

  it("computes exact year-to-year differences from processed monthly means", () => {
    const rows = [
      row("2023-01", { theta_root_zone_0_100_mean: JAN_2023 }),
      row("2025-01", { theta_root_zone_0_100_mean: JAN_2025 }),
    ];
    const result = interannualDelta(rows, "theta_root_zone_0_100_mean", 1, "2023", "2025");
    expect(result.thetaA).toBe(JAN_2023);
    expect(result.thetaB).toBe(JAN_2025);
    expect(result.delta).toBeCloseTo(JAN_2025 - JAN_2023, 12);
    expect(result.delta).toBeCloseTo(0.0704797711936376, 12);
    expect(result.relativePct).toBeCloseTo(((JAN_2025 - JAN_2023) / JAN_2023) * 100, 10);
  });

  it("does not invent a relative change when the denominator is near zero", () => {
    const rows = [
      row("2023-01", { theta_root_zone_0_100_mean: 0 }),
      row("2025-01", { theta_root_zone_0_100_mean: 0.1 }),
    ];
    const result = interannualDelta(rows, "theta_root_zone_0_100_mean", 1, "2023", "2025");
    expect(result.delta).toBe(0.1);
    expect(result.relativePct).toBeNull();
    expect(result.relativeUndefinedReason).toMatch(/near zero/);
  });

  it("formats scientific tooltips without fabricating missing values", () => {
    const chart = buildYearOverYearRows(
      [row("2023-01", { theta_root_zone_0_100_mean: JAN_2023, complete_days: 31 })],
      "theta_root_zone_0_100_mean",
      ["2023"],
    );
    const lines = formatYearOverYearTooltip(chart[0]!.points["2023"]!, "theta_root_zone_0_100_mean");
    expect(lines.join("\n")).toMatch(/Year 2023/);
    expect(lines.join("\n")).toMatch(/Month January/);
    expect(lines.join("\n")).toMatch(/Weighted profile 0–100 cm/);
    expect(lines.join("\n")).toMatch(/0\.3030 m³\/m³/);
    expect(lines.join("\n")).toMatch(/Complete days 31/);
    expect(lines.join("\n")).toMatch(/ERA5-Land/);
    expect(lines.join("\n")).toMatch(/modeled reanalysis/);
    expect(lines.join("\n")).toMatch(/not a confidence interval/);
    const missing = formatYearOverYearTooltip(
      buildYearOverYearRows([], "swvl4_mean", ["2023"])[0]!.points["2023"]!,
      "swvl4_mean",
    );
    expect(missing.join("\n")).toMatch(/Monthly mean null/);
    expect(missing.join("\n")).not.toMatch(/ 0 m³/);
  });

  it("uses meteorological winter spanning December of Y and Jan–Feb of Y+1", () => {
    const rows = [
      row("2023-12", { theta_root_zone_0_100_mean: 0.30 }),
      row("2024-01", { theta_root_zone_0_100_mean: 0.33 }),
      row("2024-02", { theta_root_zone_0_100_mean: 0.36 }),
    ];
    const winter = seasonalMean(rows, "theta_root_zone_0_100_mean", "winter", "2023");
    expect(winter.label).toBe("Winter DJF 2023–2024");
    expect(winter.value).toBeCloseTo(0.33, 12);
    expect(winter.complete).toBe(true);
    const incomplete = seasonalMean(rows, "theta_root_zone_0_100_mean", "winter", "2024");
    expect(incomplete.value).toBeNull();
    expect(incomplete.complete).toBe(false);
  });
});
