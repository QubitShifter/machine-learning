interface ProgressBarProps {
  currentStep: number;
  totalSteps: number;
  completed: boolean;
}

export function ProgressBar({
  currentStep,
  totalSteps,
  completed,
}: ProgressBarProps) {
  const completedSteps = completed
    ? totalSteps
    : Math.max(0, currentStep - 1);
  const progress =
    totalSteps > 0
      ? Math.round((completedSteps / totalSteps) * 100)
      : 0;

  return (
    <div className="progress">
      <div className="progress-label">
        <span>
          Step {currentStep} of {totalSteps}
        </span>
        <span>{progress}% complete</span>
      </div>
      <div
        aria-label="Tutor progress"
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={progress}
        className="progress-track"
        role="progressbar"
      >
        <div
          className="progress-fill"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
