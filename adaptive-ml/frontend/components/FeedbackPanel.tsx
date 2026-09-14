"use client";

import { useLanguage } from "@/components/LanguageProvider";
import { MathContent } from "@/components/math/MathContent";

interface FeedbackPanelProps {
  feedback: string;
  suggestion: string | null;
  status: string;
  errorMessage?: string | null;
}

export function FeedbackPanel({
  feedback,
  suggestion,
  status,
  errorMessage,
}: FeedbackPanelProps) {
  const { t } = useLanguage();
  const statusKey = `status.${status}`;
  const statusLabel = t(statusKey);

  return (
    <section className="feedback-panel">
      <div className={`status-pill status-${status}`}>
        {statusLabel === statusKey
          ? status.replaceAll("_", " ")
          : statusLabel}
      </div>

      {errorMessage ? (
        <p className="error-message">{errorMessage}</p>
      ) : null}

      <div>
        <h2>{t("tutor.feedback")}</h2>
        <MathContent text={feedback} />
      </div>

      {suggestion ? (
        <div className="suggestion">
          <h2>{t("tutor.suggestion")}</h2>
          <MathContent text={suggestion} />
        </div>
      ) : null}
    </section>
  );
}
