"use client";

import { useState } from "react";

import { useLanguage } from "@/components/LanguageProvider";
import { MathContent } from "@/components/math/MathContent";
import {
  presentTutorFeedback,
  type GradedFeedback,
} from "@/components/feedbackPresentation";
import {
  canRestoreOriginalExplanation,
  guidedLocalExplanation,
  shouldShowElaborationFallback,
  shouldShowExplainDifferently,
} from "@/components/guidedQuestions";
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
  elaborationLoading?: boolean;
  lastGraded?: GradedFeedback | null;
  onElaborate?: () => void;
}

export function FeedbackPanel({
  feedback,
  suggestion,
  status,
  errorMessage,
  session,
  questionLoading = false,
  elaborationLoading = false,
  lastGraded = null,
  onElaborate,
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
  const explanationIdentity = [
    session?.session_id ?? "",
    String(session?.current_step ?? ""),
    session?.feedback ?? "",
  ].join(":");
  const [restoredIdentity, setRestoredIdentity] = useState(
    "",
  );
  const showOriginal = restoredIdentity === explanationIdentity;
  const originalExplanation = guidedLocalExplanation(session);

  function statusLabel(value: string) {
    const statusKey = `status.${value}`;
    const translated = t(statusKey);

    return translated === statusKey
      ? value.replaceAll("_", " ")
      : translated;
  }

  const explanationText =
    showOriginal && originalExplanation
      ? originalExplanation
      : view.explanation?.text;
  const showElaborate =
    shouldShowExplainDifferently(session) &&
    typeof onElaborate === "function";
  const showRestore =
    canRestoreOriginalExplanation(session) &&
    !showOriginal &&
    !elaborationLoading;
  const showFallbackNote =
    shouldShowElaborationFallback(session) &&
    !elaborationLoading;

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
          {explanationText ? (
            <MathContent text={explanationText} />
          ) : null}
          {view.explanation.suggestion ? (
            <div className="suggestion">
              <h2>{t("tutor.suggestion")}</h2>
              <MathContent
                text={view.explanation.suggestion}
              />
            </div>
          ) : null}
          {showElaborate || showRestore || showFallbackNote ? (
            <div className="explain-differently-row">
              {showElaborate ? (
                <button
                  aria-busy={elaborationLoading}
                  aria-label={t("tutor.explainDifferently")}
                  className="secondary-button explain-differently-button"
                  disabled={elaborationLoading}
                  onClick={onElaborate}
                  type="button"
                >
                  {elaborationLoading
                    ? t("tutor.explainDifferentlyLoading")
                    : t("tutor.explainDifferently")}
                </button>
              ) : null}
              {showRestore ? (
                <button
                  aria-label={t("tutor.showOriginalExplanation")}
                  className="secondary-button show-original-button"
                  onClick={() =>
                    setRestoredIdentity(explanationIdentity)
                  }
                  type="button"
                >
                  {t("tutor.showOriginalExplanation")}
                </button>
              ) : null}
              {showFallbackNote ? (
                <p className="elaboration-note" role="status">
                  {t("tutor.elaborationFallback")}
                </p>
              ) : null}
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
            <MathContent key={feedback} text={feedback} />
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
