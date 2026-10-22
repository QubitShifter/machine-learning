import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { MonthlySoilRow } from "@/types/api";
import { utcDaysInMonth } from "@/utils/soilYearComparison";
import { YearOverYearSoilChart } from "./YearOverYearSoilChart";

function row(month: string, extras: Partial<MonthlySoilRow> = {}): MonthlySoilRow {
  const [year, monthPart] = month.split("-");
  const days = utcDaysInMonth(year, Number(monthPart));
  return {
    month,
    day_count: days,
    complete_days: days,
    missing_days: 0,
    availability: "complete",
    swvl1_mean: 0.354,
    swvl2_mean: 0.346,
    swvl3_mean: 0.286,
    swvl4_mean: 0.312,
    theta_root_zone_0_100_mean: 0.303,
    theta_root_zone_0_100_min: 0.281,
    theta_root_zone_0_100_max: 0.331,
    aggregation: "monthly_mean_of_complete_days",
    unit: "m3 m-3",
    observation_kind: "modeled_volumetric_soil_moisture",
    ...extras,
  };
}

function completeYear(year: string, january: number): MonthlySoilRow[] {
  return Array.from({ length: 12 }, (_, index) => row(`${year}-${String(index + 1).padStart(2, "0")}`, {
    theta_root_zone_0_100_mean: index === 0 ? january : 0.31,
    swvl1_mean: index === 0 ? 0.11 : 0.20,
  }));
}

const months = [
  ...completeYear("2023", 0.3029981553682717),
  ...completeYear("2024", 0.3123924058483493),
  ...completeYear("2025", 0.3734779265619093),
];

describe("YearOverYearSoilChart", () => {
  it("renders year lines, depth selector, provenance, and exact January delta", () => {
    render(
      <YearOverYearSoilChart
        months={months}
        spatial={{ source_latitude: 42.1, source_longitude: 24.7, distance_km: 4.846579998487036 }}
      />,
    );
    expect(screen.getByTestId("soil-yoy-chart")).toBeInTheDocument();
    expect(screen.getByLabelText("2023")).toBeChecked();
    expect(screen.getByLabelText("2024")).toBeChecked();
    expect(screen.getByLabelText("2025")).toBeChecked();
    expect(screen.getByTestId("soil-yoy-delta-value").textContent).toMatch(/0\.0705 m³\/m³/);
    expect(screen.getByTestId("soil-yoy-provenance").textContent).toMatch(/ERA5-Land modeled volumetric soil water/);
    expect(screen.getByTestId("soil-yoy-provenance").textContent).toMatch(/42\.1° N/);
    expect(screen.getByTestId("soil-yoy-provenance").textContent).toMatch(/24\.7° E/);
    expect(screen.getByTestId("soil-yoy-provenance").textContent).toMatch(/4\.85 km/);
    expect(screen.getByTestId("soil-yoy-provenance").textContent).toMatch(/not a robust long-term climatology/);
    expect(screen.getByText(/not that crop health is better/)).toBeInTheDocument();
  });

  it("toggles years and changes depth without fabricating missing months", () => {
    const withGap = months.map((item) => (
      item.month === "2024-06"
        ? {
          ...item,
          availability: "missing",
          complete_days: 0,
          theta_root_zone_0_100_mean: null,
          swvl1_mean: null,
        }
        : item
    ));
    render(<YearOverYearSoilChart months={withGap} />);
    expect(screen.getByLabelText("2024")).not.toBeChecked();
    fireEvent.click(screen.getByLabelText("2024"));
    expect(screen.getByLabelText("2024")).toBeChecked();
    fireEvent.click(screen.getByLabelText("2023"));
    expect(screen.getByLabelText("2023")).not.toBeChecked();
    fireEvent.change(screen.getByLabelText("Comparison soil depth"), {
      target: { value: "swvl1_mean" },
    });
    expect((screen.getByLabelText("Comparison soil depth") as HTMLSelectElement).value).toBe("swvl1_mean");
    expect(screen.getByText(/Single ERA5-Land TESSEL layer/)).toBeInTheDocument();
    expect(screen.getByTestId("soil-yoy-seasons").textContent).toMatch(/Winter DJF/);
  });

  it("offers Explore this year without changing comparison year toggles", () => {
    const onExploreYear = vi.fn();
    render(<YearOverYearSoilChart months={months} onExploreYear={onExploreYear} />);
    fireEvent.click(screen.getByLabelText("2024"));
    expect(screen.getByLabelText("2024")).not.toBeChecked();
    expect(onExploreYear).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Explore this year 2024" }));
    expect(onExploreYear).toHaveBeenCalledWith("2024");
    expect(screen.getByLabelText("2024")).not.toBeChecked();
    expect(screen.getByLabelText("2023")).toBeChecked();
    expect(screen.getByTestId("soil-yoy-delta-value").textContent).toMatch(/0\.0705 m³\/m³/);
  });
});
