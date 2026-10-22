import { describe, expect, it } from "vitest";
import { deriveInterpretation, displayValue, metricRow, sampleCount } from "./mlLab";

describe("ml laboratory helpers", () => {
  it("reads horizon-specific sample counts", () => {
    const counts = [
      { split: "training", horizon_days: 1, feature_set: "C", n: 350, purged_or_missing: 14 },
      { split: "validation", horizon_days: 1, feature_set: "C", n: 365, purged_or_missing: 0 },
    ];
    expect(sampleCount(counts, "training", 1, "C")).toBe(350);
    expect(sampleCount(counts, "test", 1, "C")).toBeNull();
  });

  it("does not display zero for missing metrics", () => {
    expect(displayValue(null)).toBe("Unavailable");
    expect(displayValue(undefined)).toBe("Unavailable");
  });

  it("interprets held-out winners from actual metric rows", () => {
    const records = [
      { model_id: "persistence", horizon_days: "1", feature_set: "C", mae: "0.0196", skill_mae: "0", n: "364" },
      { model_id: "ridge", horizon_days: "1", feature_set: "C", mae: "0.0202", skill_mae: "-0.03", n: "364" },
      { model_id: "seasonal", horizon_days: "1", feature_set: "C", mae: "0.0516", skill_mae: "-1.6", n: "364" },
      { model_id: "gradient_boosting", horizon_days: "1", feature_set: "C", mae: "0.0214", skill_mae: "-0.09", n: "364" },
    ];
    const lines = deriveInterpretation(records, 1, "C");
    expect(lines[0]).toMatch(/Persistence has the lowest MAE/);
    expect(lines.some((line) => line.includes("worse than persistence"))).toBe(true);
    expect(metricRow(records, "ridge", 1, "C")?.mae).toBe("0.0202");
  });
});
