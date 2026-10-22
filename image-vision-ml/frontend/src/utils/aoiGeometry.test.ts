import { describe, expect, it } from "vitest";
import { bboxAreaKm2, validateBbox } from "./aoiGeometry";

describe("multi-AOI geometry", () => {
  it("accepts the operational Plovdiv bbox", () => {
    expect(validateBbox([24.65, 42.05, 24.68, 42.08])).toBeNull();
    expect(bboxAreaKm2(24.65, 42.05, 24.68, 42.08)).toBeGreaterThan(0.01);
  });

  it("rejects inverted or oversized boxes", () => {
    expect(validateBbox([24.68, 42.05, 24.65, 42.08])).toMatch(/west/i);
    expect(validateBbox([24.65, 42.08, 24.68, 42.05])).toMatch(/south/i);
    expect(validateBbox([20, 40, 25, 45])).toMatch(/2 degrees/i);
  });
});
