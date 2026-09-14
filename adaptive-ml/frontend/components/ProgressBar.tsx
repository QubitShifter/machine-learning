"use client";

import { useLanguage } from "@/components/LanguageProvider";

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
  const { t } = useLanguage();
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
          {t("tutor.stepOf", {
            current: currentStep,
            total: totalSteps,
          })}
        </span>
        <span>
          {t("tutor.percentComplete", { percent: progress })}
        </span>
      </div>
      <div
        aria-label={t("tutor.progressAria")}
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
