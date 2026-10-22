export interface Point {
  x: number;
  y: number;
}

export interface LinearFit {
  slope: number;
  intercept: number;
  mse: number;
}

function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let next = Math.imul(state ^ (state >>> 15), 1 | state);
    next ^= next + Math.imul(next ^ (next >>> 7), 61 | next);
    return ((next ^ (next >>> 14)) >>> 0) / 4294967296;
  };
}

export function meanSquaredError(points: Point[], slope: number, intercept: number): number {
  if (!points.length) return 0;
  const total = points.reduce((sum, point) => {
    const residual = point.y - (slope * point.x + intercept);
    return sum + residual * residual;
  }, 0);
  return total / points.length;
}

export function ordinaryLeastSquares(points: Point[]): LinearFit {
  const n = points.length;
  if (n === 0) return { slope: 0, intercept: 0, mse: 0 };
  const meanX = points.reduce((sum, point) => sum + point.x, 0) / n;
  const meanY = points.reduce((sum, point) => sum + point.y, 0) / n;
  let xx = 0;
  let xy = 0;
  for (const point of points) {
    const dx = point.x - meanX;
    xx += dx * dx;
    xy += dx * (point.y - meanY);
  }
  const slope = xx === 0 ? 0 : xy / xx;
  const intercept = meanY - slope * meanX;
  return { slope, intercept, mse: meanSquaredError(points, slope, intercept) };
}

export function syntheticLinearRegression(options: {
  slope: number;
  intercept: number;
  noise: number;
  sampleSize: number;
  seed: number;
}): { points: Point[]; fit: LinearFit; trueLine: LinearFit } {
  const random = mulberry32(options.seed);
  const n = Math.max(2, Math.round(options.sampleSize));
  const points: Point[] = [];
  for (let index = 0; index < n; index += 1) {
    const x = -2 + (4 * index) / (n - 1);
    const noise = (random() * 2 - 1) * options.noise;
    points.push({ x, y: options.slope * x + options.intercept + noise });
  }
  const fit = ordinaryLeastSquares(points);
  return {
    points,
    fit,
    trueLine: {
      slope: options.slope,
      intercept: options.intercept,
      mse: meanSquaredError(points, options.slope, options.intercept),
    },
  };
}

export interface DescentStep {
  iteration: number;
  weight: number;
  gradient: number;
  loss: number;
}

/** Educational objective L(w)=(w-3)^2. Not the agricultural Ridge solver. */
export function quadraticGradientDescent(options: {
  start: number;
  learningRate: number;
  iterations: number;
}): DescentStep[] {
  const steps: DescentStep[] = [];
  let weight = options.start;
  const count = Math.max(0, Math.round(options.iterations));
  for (let iteration = 0; iteration <= count; iteration += 1) {
    const gradient = 2 * (weight - 3);
    const loss = (weight - 3) ** 2;
    steps.push({ iteration, weight, gradient, loss });
    weight -= options.learningRate * gradient;
  }
  return steps;
}

export function descentOutcome(steps: DescentStep[]): "converged" | "diverged" | "slow" {
  if (steps.length < 2) return "slow";
  const last = steps[steps.length - 1];
  const first = steps[0];
  if (last.loss < 1e-4) return "converged";
  if (last.loss > first.loss * 2 || !Number.isFinite(last.loss)) return "diverged";
  return "slow";
}

export interface RidgeDemoResult {
  alpha: number;
  intercept: number;
  coefficients: { name: string; value: number }[];
  mse: number;
}

function solveRidge(x: number[][], y: number[], alpha: number): number[] {
  const n = x.length;
  const p = x[0]?.length ?? 0;
  const xtx: number[][] = Array.from({ length: p }, () => Array(p).fill(0));
  const xty = Array(p).fill(0);
  for (let i = 0; i < n; i += 1) {
    for (let j = 0; j < p; j += 1) {
      xty[j] += x[i][j] * y[i];
      for (let k = 0; k < p; k += 1) {
        xtx[j][k] += x[i][j] * x[i][k];
      }
    }
  }
  for (let j = 1; j < p; j += 1) {
    xtx[j][j] += alpha;
  }
  return gaussian(xtx, xty);
}

function gaussian(matrix: number[][], vector: number[]): number[] {
  const n = vector.length;
  const a = matrix.map((row, index) => [...row, vector[index]]);
  for (let i = 0; i < n; i += 1) {
    let pivot = i;
    for (let r = i + 1; r < n; r += 1) {
      if (Math.abs(a[r][i]) > Math.abs(a[pivot][i])) pivot = r;
    }
    [a[i], a[pivot]] = [a[pivot], a[i]];
    const denom = a[i][i] || 1e-12;
    for (let c = i; c <= n; c += 1) a[i][c] /= denom;
    for (let r = 0; r < n; r += 1) {
      if (r === i) continue;
      const factor = a[r][i];
      for (let c = i; c <= n; c += 1) a[r][c] -= factor * a[i][c];
    }
  }
  return a.map((row) => row[n]);
}

export function syntheticRidgeRegularization(options: {
  alpha: number;
  seed: number;
}): RidgeDemoResult {
  const random = mulberry32(options.seed);
  const n = 40;
  const x: number[][] = [];
  const y: number[] = [];
  for (let i = 0; i < n; i += 1) {
    const x1 = random() * 2 - 1;
    const x2 = x1 * 0.85 + (random() * 0.3 - 0.15);
    const intercept = 1;
    const noise = (random() * 2 - 1) * 0.15;
    x.push([1, x1, x2]);
    y.push(intercept + 1.5 * x1 + 0.2 * x2 + noise);
  }
  const beta = solveRidge(x, y, Math.max(0, options.alpha));
  let mse = 0;
  for (let i = 0; i < n; i += 1) {
    const pred = beta[0] + beta[1] * x[i][1] + beta[2] * x[i][2];
    mse += (y[i] - pred) ** 2;
  }
  return {
    alpha: options.alpha,
    intercept: beta[0],
    coefficients: [
      { name: "x1", value: beta[1] },
      { name: "x2 (correlated)", value: beta[2] },
    ],
    mse: mse / n,
  };
}

export interface BoostingStage {
  stage: number;
  prediction: number[];
  residual: number[];
  stump: number;
  mse: number;
}

export function syntheticBoosting(options: {
  stages: number;
  learningRate: number;
  seed: number;
}): { x: number[]; y: number[]; stages: BoostingStage[] } {
  const random = mulberry32(options.seed);
  const x = Array.from({ length: 16 }, (_, index) => index);
  const y = x.map((value) => (value < 8 ? 0.2 : 0.8) + (random() * 0.1 - 0.05));
  const stages: BoostingStage[] = [];
  let prediction = y.map(() => y.reduce((sum, item) => sum + item, 0) / y.length);
  const count = Math.max(1, Math.round(options.stages));
  for (let stage = 0; stage < count; stage += 1) {
    const residual = y.map((value, index) => value - prediction[index]);
    const left = residual.filter((_, index) => x[index] < 8);
    const right = residual.filter((_, index) => x[index] >= 8);
    const leftMean = left.reduce((sum, item) => sum + item, 0) / left.length;
    const rightMean = right.reduce((sum, item) => sum + item, 0) / right.length;
    prediction = prediction.map((value, index) => (
      value + options.learningRate * (x[index] < 8 ? leftMean : rightMean)
    ));
    const mse = y.reduce((sum, value, index) => sum + (value - prediction[index]) ** 2, 0) / y.length;
    stages.push({
      stage: stage + 1,
      prediction: [...prediction],
      residual,
      stump: x[8] ?? 8,
      mse,
    });
  }
  return { x, y, stages };
}
