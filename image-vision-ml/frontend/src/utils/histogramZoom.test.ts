import { describe, expect, it } from "vitest";
import {
  autoZoomUpper,
  binsOverlappingDomain,
  samplesOutsideViewport,
} from "./histogramZoom";

describe("histogram auto-zoom", () => {
  it("uses the highest enabled-channel P99 with padding and caps at 1", () => {
    expect(autoZoomUpper([0.2, 0.16, 0.12])).toBeCloseTo(0.23, 8);
    expect(autoZoomUpper([0.96])).toBe(1);
    expect(autoZoomUpper([0.01])).toBe(0.05);
    expect(autoZoomUpper([null, undefined])).toBe(1);
  });

  it("counts samples whose bins lie entirely outside the zoom window", () => {
    const bins = [
      { index: 0, edge_left: 0, edge_right: 0.1, center: 0.05, count: 80, percent_of_valid: 80, percent_of_total: 80 },
      { index: 1, edge_left: 0.1, edge_right: 0.2, center: 0.15, count: 15, percent_of_valid: 15, percent_of_total: 15 },
      { index: 2, edge_left: 0.4, edge_right: 0.5, center: 0.45, count: 5, percent_of_valid: 5, percent_of_total: 5 },
    ];
    const result = samplesOutsideViewport(bins, 0.23, 100);
    expect(result.outsideCount).toBe(5);
    expect(result.percent).toBe(5);
  });

  it("does not merge bins when filtering to the zoomed domain", () => {
    const bins = [
      { index: 0, edge_left: 0, edge_right: 0.1, center: 0.05, count: 8, percent_of_valid: 80, percent_of_total: 80 },
      { index: 1, edge_left: 0.9, edge_right: 1, center: 0.95, count: 2, percent_of_valid: 20, percent_of_total: 20 },
    ];
    const visible = binsOverlappingDomain(bins, [0, 0.23]);
    expect(visible).toHaveLength(1);
    expect(visible[0].count).toBe(8);
    expect(bins[1].count).toBe(2);
  });
});
