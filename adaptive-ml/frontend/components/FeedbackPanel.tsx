"use client";

import { useLanguage } from "@/components/LanguageProvider";
import { MathContent } from "@/components/math/MathContent";
import {
  presentTutorFeedback,
  type GradedFeedback,
} from "@/components/feedbackPresentation";
import {
  readTutorSources,
  usedExternalSources,
} from "@/components/tutorSources";
import type { TutorSession } from "@/types/tutor";

interface FeedbackPanelProps {
  feedback: string;
  suggestion: string | null;
  status: string;
  errorMessage?: string | null;
  session?: TutorSession | null;
  questionLoading?: boolean;
  lastGraded?: GradedFeedback | null;
}

export function FeedbackPanel({
  feedback,
  suggestion,
  status,
  errorMessage,
  session,
  questionLoading = false,
  lastGraded = null,
}: FeedbackPanelProps) {
  const { t } = useLanguage();
  const sources = readTutorSources(session);
  const showExternalBadge = usedExternalSources(session);
  const view = presentTutorFeedback({
    questionLoading,
    status,
    feedback,
    suggestion,
    lastGraded,
  });

  function statusLabel(value: string) {
    const statusKey = `status.${value}`;
    const translated = t(statusKey);

    return translated === statusKey
      ? value.replaceAll("_", " ")
      : translated;
  }

  return (
    <section className="feedback-panel">
      {errorMessage ? (
        <p className="error-message">{errorMessage}</p>
      ) : null}

      {view.loadingExplanation ? (
        <div className="explanation-block">
          <div className="status-pill status-concept">
            {t("tutor.findingExplanation")}
          </div>
        </div>
      ) : null}

      {view.explanation ? (
        <div className="explanation-block">
          <div className="status-pill status-concept">
            {statusLabel("concept")}
          </div>
          <MathContent text={view.explanation.text} />
          {view.explanation.suggestion ? (
            <div className="suggestion">
              <h2>{t("tutor.suggestion")}</h2>
              <MathContent
                text={view.explanation.suggestion}
              />
            </div>
          ) : null}
        </div>
      ) : null}

      {view.showGradedAsLastAnswer && view.graded ? (
        <div className="graded-answer-block">
          <div
            className={`status-pill status-${view.graded.status}`}
          >
            {statusLabel(view.graded.status)}
          </div>
          <div>
            <h2>{t("tutor.lastAnswer")}</h2>
            <MathContent text={view.graded.feedback} />
          </div>
        </div>
      ) : null}

      {view.useDefaultPanel ? (
        <>
          <div className={`status-pill status-${status}`}>
            {statusLabel(status)}
          </div>
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
        </>
      ) : null}

      {showExternalBadge ? (
        <p className="external-source-note">
          {t("tutor.externalSources")}
        </p>
      ) : null}

      {sources.length > 0 ? (
        <div className="source-list">
          <h2>{t("tutor.sources")}</h2>
          <ul>
            {sources.map((source) => (
              <li key={source.url}>
                <a
                  href={source.url}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  {source.title}
                </a>
                {source.domain ? (
                  <span className="source-domain">
                    {source.domain}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
