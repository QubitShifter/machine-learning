import { describe, expect, it } from "vitest";
import {
  descentOutcome,
  meanSquaredError,
  ordinaryLeastSquares,
  quadraticGradientDescent,
  syntheticBoosting,
  syntheticLinearRegression,
  syntheticRidgeRegularization,
} from "./mlDemos";

describe("educational ML demonstrations", () => {
  it("fits ordinary least squares on a noiseless line", () => {
    const points = [
      { x: 0, y: 1 },
      { x: 1, y: 3 },
      { x: 2, y: 5 },
    ];
    const fit = ordinaryLeastSquares(points);
    expect(fit.slope).toBeCloseTo(2, 8);
    expect(fit.intercept).toBeCloseTo(1, 8);
    expect(fit.mse).toBeCloseTo(0, 8);
  });

  it("repeats synthetic linear data for a fixed seed", () => {
    const first = syntheticLinearRegression({
      slope: 1.5, intercept: 0.2, noise: 0.4, sampleSize: 20, seed: 7,
    });
    const second = syntheticLinearRegression({
      slope: 1.5, intercept: 0.2, noise: 0.4, sampleSize: 20, seed: 7,
    });
    expect(first.points).toEqual(second.points);
    expect(meanSquaredError(first.points, first.fit.slope, first.fit.intercept)).toBeCloseTo(first.fit.mse, 10);
  });

  it("converges quadratic gradient descent at a moderate learning rate", () => {
    const steps = quadraticGradientDescent({ start: 0, learningRate: 0.2, iterations: 40 });
    expect(descentOutcome(steps)).toBe("converged");
    expect(steps[steps.length - 1].weight).toBeCloseTo(3, 3);
  });

  it("diverges when the learning rate is too large", () => {
    const steps = quadraticGradientDescent({ start: 0, learningRate: 1.2, iterations: 12 });
    expect(descentOutcome(steps)).toBe("diverged");
  });

  it("shrinks the correlated ridge coefficient as alpha increases", () => {
    const light = syntheticRidgeRegularization({ alpha: 0.01, seed: 3 });
    const heavy = syntheticRidgeRegularization({ alpha: 25, seed: 3 });
    const l2 = (result: { coefficients: { value: number }[] }) => (
      result.coefficients.reduce((sum, item) => sum + item.value * item.value, 0)
    );
    expect(l2(heavy)).toBeLessThan(l2(light));
  });

  it("reduces boosting demonstration MSE across stages", () => {
    const result = syntheticBoosting({ stages: 4, learningRate: 0.5, seed: 11 });
    expect(result.stages[result.stages.length - 1].mse).toBeLessThan(result.stages[0].mse);
  });
});
