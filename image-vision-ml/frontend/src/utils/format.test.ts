import { describe, expect, it } from "vitest";
import { formatNumber, formatUtcTimestamp, isCompleteDay, lastUtcDayOfMonth, latestValidMonth } from "./format";

describe("format helpers", () => {
  it("does not invent numbers for missing values", () => {
    expect(formatNumber(null)).toBe("—");
    expect(formatNumber(undefined)).toBe("—");
  });

  it("formats UTC timestamps without converting to local time", () => {
    expect(formatUtcTimestamp("2023-03-26T09:18:47.322000Z")).toBe("2023-03-26 09:18:47 UTC");
    expect(formatUtcTimestamp("2025-07-18")).toBe("2025-07-18 UTC");
    expect(formatUtcTimestamp(null)).toBe("—");
  });

  it("selects the latest complete downloaded month", () => {
    const month = latestValidMonth([
      { month: "2023-01", availability: "downloaded", complete_days: 31 },
      { month: "2023-02", availability: "missing_source", complete_days: 0 },
      { month: "2025-04", availability: "downloaded", complete_days: 30 },
    ]);
    expect(month?.month).toBe("2025-04");
  });

  it("returns the UTC last day of a month", () => {
    expect(lastUtcDayOfMonth("2023-01")).toBe("31");
    expect(lastUtcDayOfMonth("2024-02")).toBe("29");
  });

  it("requires 24 hours and the next-day boundary for a complete day", () => {
    expect(isCompleteDay({
      hourly_records_available: 24,
      hourly_records_expected: 24,
      boundary_00utc_available: true,
    })).toBe(true);
    expect(isCompleteDay({
      hourly_records_available: 0,
      boundary_00utc_available: false,
    })).toBe(false);
  });
});
