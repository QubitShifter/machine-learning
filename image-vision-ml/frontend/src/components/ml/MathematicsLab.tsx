import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "@/components/common/Card";
import {
  descentOutcome,
  quadraticGradientDescent,
  syntheticBoosting,
  syntheticLinearRegression,
  syntheticRidgeRegularization,
} from "@/utils/mlDemos";

const DEMO_BANNER = "Educational simulation — not training telemetry from the agricultural model.";

export function MathematicsLab() {
  return (
    <div className="space-y-4">
      <p
        className="rounded border border-sand-400/40 bg-sand-400/10 px-3 py-2 text-sm text-sand-200"
        data-testid="educational-simulation-banner"
      >
        {DEMO_BANNER} Synthetic points use a fixed seed. They are not ERA5-Land observations.
        Real Ridge coefficients, boosting iteration counts, and validation MAE belong on the Training Runs tab.
      </p>
      <LinearRegressionDemo />
      <GradientDescentDemo />
      <RidgeRegularizationDemo />
      <GradientBoostingDemo />
      <Card title="Loss functions used in evaluation">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>MAE = mean |y − ŷ|. Reported for scientific comparison.</li>
          <li>RMSE = sqrt(mean (y − ŷ)²).</li>
          <li>Ridge optimizes squared error plus α‖β‖², which is not MAE.</li>
          <li>Boosting here used sklearn’s squared-error objective, not a logged per-iteration curve.</li>
        </ul>
      </Card>
    </div>
  );
}

function LinearRegressionDemo() {
  const [slope, setSlope] = useState(1.2);
  const [intercept, setIntercept] = useState(0.4);
  const [noise, setNoise] = useState(0.35);
  const [sampleSize, setSampleSize] = useState(24);
  const result = useMemo(
    () => syntheticLinearRegression({ slope, intercept, noise, sampleSize, seed: 21 }),
    [slope, intercept, noise, sampleSize],
  );
  const line = result.points.map((point) => ({
    ...point,
    fitted: result.fit.slope * point.x + result.fit.intercept,
  }));
  return (
    <Card title="Linear regression (synthetic)">
      <Controls>
        <Slider label="Slope" value={slope} min={-2} max={2} step={0.1} onChange={setSlope} />
        <Slider label="Intercept" value={intercept} min={-2} max={2} step={0.1} onChange={setIntercept} />
        <Slider label="Noise" value={noise} min={0} max={1.5} step={0.05} onChange={setNoise} />
        <Slider label="Sample size" value={sampleSize} min={5} max={60} step={1} onChange={setSampleSize} />
      </Controls>
      <div className="h-56">
        <ResponsiveContainer>
          <ComposedChart data={line}>
            <CartesianGrid stroke="#1a3144" />
            <XAxis dataKey="x" type="number" tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#122230", border: "1px solid #27445c" }} />
            <Scatter data={result.points} fill="#7dce9a" name="synthetic y" />
            <Line dataKey="fitted" stroke="#60a5fa" dot={false} name="OLS fit" isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-slate-400">
        OLS slope {result.fit.slope.toFixed(3)}, intercept {result.fit.intercept.toFixed(3)}, MSE {result.fit.mse.toFixed(4)}. Seed 21.
      </p>
    </Card>
  );
}

function GradientDescentDemo() {
  const [learningRate, setLearningRate] = useState(0.2);
  const [start, setStart] = useState(0);
  const [iterations, setIterations] = useState(25);
  const steps = useMemo(
    () => quadraticGradientDescent({ start, learningRate, iterations }),
    [start, learningRate, iterations],
  );
  const outcome = descentOutcome(steps);
  return (
    <Card title="Gradient descent on L(w)=(w−3)²">
      <p className="text-xs text-sand-200">{DEMO_BANNER} Ridge in Phase 4.1 did not train this way.</p>
      <Controls>
        <Slider label="Learning rate" value={learningRate} min={0.01} max={1.4} step={0.01} onChange={setLearningRate} />
        <Slider label="Start w" value={start} min={-4} max={8} step={0.1} onChange={setStart} />
        <Slider label="Iterations" value={iterations} min={5} max={80} step={1} onChange={setIterations} />
      </Controls>
      <div className="h-56">
        <ResponsiveContainer>
          <LineChart data={steps}>
            <CartesianGrid stroke="#1a3144" />
            <XAxis dataKey="iteration" tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <Legend />
            <Line dataKey="loss" stroke="#fb7185" dot={false} isAnimationActive={false} />
            <Line dataKey="weight" stroke="#7dce9a" dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-sm text-slate-300" data-testid="descent-outcome">
        Outcome: {outcome}. Last w={steps[steps.length - 1]?.weight.toFixed(3)}, gradient={steps[steps.length - 1]?.gradient.toFixed(3)}.
        Too small a rate crawls; rates above 1 diverge on this quadratic.
      </p>
    </Card>
  );
}

function RidgeRegularizationDemo() {
  const [alpha, setAlpha] = useState(1);
  const result = useMemo(() => syntheticRidgeRegularization({ alpha, seed: 5 }), [alpha]);
  return (
    <Card title="Ridge regularization (synthetic correlated features)">
      <Slider label="Alpha" value={alpha} min={0} max={40} step={0.5} onChange={setAlpha} />
      <ul className="mt-2 text-sm text-slate-300">
        <li>Intercept {result.intercept.toFixed(3)}</li>
        {result.coefficients.map((item) => (
          <li key={item.name}>{item.name}: {item.value.toFixed(3)}</li>
        ))}
        <li>MSE {result.mse.toFixed(4)}</li>
      </ul>
    </Card>
  );
}

function GradientBoostingDemo() {
  const [stages, setStages] = useState(3);
  const result = useMemo(() => syntheticBoosting({ stages, learningRate: 0.5, seed: 9 }), [stages]);
  const last = result.stages[result.stages.length - 1];
  const chart = result.x.map((x, index) => ({
    x,
    y: result.y[index],
    ensemble: last?.prediction[index],
  }));
  return (
    <Card title="Sequential weak learners (synthetic stumps)">
      <p className="text-xs text-sand-200">These stumps are not the fitted scikit-learn trees.</p>
      <Slider label="Stages" value={stages} min={1} max={6} step={1} onChange={setStages} />
      <div className="h-56">
        <ResponsiveContainer>
          <LineChart data={chart}>
            <CartesianGrid stroke="#1a3144" />
            <XAxis dataKey="x" tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <Line dataKey="y" name="synthetic y" stroke="#e2e8f0" dot isAnimationActive={false} />
            <Line dataKey="ensemble" name="ensemble" stroke="#60a5fa" dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-slate-400">Stage {last?.stage} MSE {last?.mse.toFixed(4)}.</p>
    </Card>
  );
}

function Controls({ children }: { children: ReactNode }) {
  return <div className="mb-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">{children}</div>;
}

function Slider({
  label, value, min, max, step, onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="text-xs text-slate-400">
      {label}: {value}
      <input
        className="mt-1 w-full"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        aria-label={label}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
