"use client";

import { useLanguage } from "@/components/LanguageProvider";
import {
  catalogDisplayName,
  localizeRecommendationReason,
  masteryDisplayLabel,
  trendDisplayLabel,
} from "@/i18n";
import type {
  AdaptiveRecommendation,
  StudentProgress,
  TopicProgress,
} from "@/types/tutor";

interface ProgressDashboardProps {
  progress: StudentProgress | null;
  loading: boolean;
  errorMessage?: string | null;
  studentName?: string;
  onBack: () => void;
  onPracticeRecommended: () => void;
  onRefresh: () => void;
}

function formatMasteryValue(
  mastery: number,
) {
  return mastery.toFixed(2);
}

function formatMasteryPercent(
  mastery: number,
) {
  return `${Math.round(mastery * 100)}%`;
}

function formatRate(
  rate: number,
) {
  return `${Math.round(rate * 100)}%`;
}

function readAdjustmentReason(
  recommendation: AdaptiveRecommendation | undefined,
) {
  const reason = recommendation?.metadata.adjustment_reason;

  return typeof reason === "string" ? reason : undefined;
}

function readSessionCount(
  recommendation: AdaptiveRecommendation | undefined,
) {
  const count = recommendation?.metadata.recent_session_count;

  return typeof count === "number" ? count : undefined;
}

function readFamilyReason(
  recommendation: AdaptiveRecommendation | undefined,
) {
  const reason = recommendation?.metadata.family_reason;

  return typeof reason === "string" ? reason : undefined;
}

function TopicProgressCard({
  topic,
}: {
  topic: TopicProgress;
}) {
  const { locale, t } = useLanguage();
  const topicName = catalogDisplayName(
    "topic",
    topic.topic,
    topic.topic_name,
    locale,
  );
  const masteryPercent = Math.round(
    topic.mastery * 100,
  );

  return (
    <article className="progress-topic-card">
      <div>
        <p className="eyebrow">
          {catalogDisplayName(
            "subject",
            topic.subject,
            topic.subject,
            locale,
          )}{" "}
          /{" "}
          {catalogDisplayName(
            "domain",
            topic.domain,
            topic.domain,
            locale,
          )}
        </p>
        <h3>{topicName}</h3>
        <p>
          {t("progress.mastery")}:{" "}
          {formatMasteryValue(topic.mastery)}{" "}
          ({formatMasteryPercent(topic.mastery)},{" "}
          {masteryDisplayLabel(topic.mastery_label, locale)})
        </p>
      </div>

      <div
        aria-label={t("progress.masteryAria", {
          topic: topicName,
          percent: masteryPercent,
        })}
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={masteryPercent}
        className="mastery-bar"
        role="progressbar"
      >
        <span
          style={{
            width: `${masteryPercent}%`,
          }}
        />
      </div>

      <dl className="progress-stats">
        <div>
          <dt>{t("progress.completed")}</dt>
          <dd>{topic.questions_completed}</dd>
        </div>
        <div>
          <dt>{t("progress.streak")}</dt>
          <dd>{topic.first_attempt_streak}</dd>
        </div>
        <div>
          <dt>{t("progress.lastAttempts")}</dt>
          <dd>{topic.last_total_attempts}</dd>
        </div>
        <div>
          <dt>{t("progress.lastIncorrect")}</dt>
          <dd>{topic.last_incorrect_attempts}</dd>
        </div>
        <div>
          <dt>{t("progress.lastHints")}</dt>
          <dd>{topic.last_hints_used}</dd>
        </div>
        <div>
          <dt>{t("progress.recommendedDifficulty")}</dt>
          <dd>
            {topic.recommended_difficulty ?? t("progress.na")}
          </dd>
        </div>
        <div>
          <dt>{t("progress.recentTrend")}</dt>
          <dd>{trendDisplayLabel(topic.recent_trend, locale)}</dd>
        </div>
        <div>
          <dt>{t("progress.recentSessions")}</dt>
          <dd>{topic.recent_session_count}</dd>
        </div>
        <div>
          <dt>{t("progress.recentFirstAttempt")}</dt>
          <dd>
            {formatRate(
              topic.recent_first_attempt_success_rate,
            )}
          </dd>
        </div>
        <div>
          <dt>{t("progress.recentHintRate")}</dt>
          <dd>{formatRate(topic.recent_hint_rate)}</dd>
        </div>
      </dl>

      <p className="progress-capability">
        {topic.generation_available
          ? t("progress.adaptiveGeneration", {
              levels: topic.supported_difficulties.join(", "),
            })
          : t("progress.staticOnly")}
      </p>
    </article>
  );
}

export function ProgressDashboard({
  progress,
  loading,
  errorMessage,
  studentName,
  onBack,
  onPracticeRecommended,
  onRefresh,
}: ProgressDashboardProps) {
  const { locale, t } = useLanguage();
  const recommendation = progress?.recommendation;
  const progressTitle = studentName
    ? t("progress.titleNamed", { name: studentName })
    : t("progress.title");
  const topicName = recommendation?.topic
    ? catalogDisplayName(
        "topic",
        recommendation.topic,
        recommendation.topic_name ?? recommendation.topic,
        locale,
      )
    : recommendation?.topic_name ?? "";
  const localizedReason = recommendation
    ? localizeRecommendationReason(
        locale,
        topicName,
        recommendation.mastery,
        readAdjustmentReason(recommendation),
        readSessionCount(recommendation),
        readFamilyReason(recommendation),
        recommendation.family,
      )
    : t("progress.noRecommendation");

  return (
    <section className="progress-dashboard">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">{t("progress.eyebrow")}</p>
          <h2>{progressTitle}</h2>
          <p>{t("progress.intro")}</p>
        </div>
        <div className="dashboard-actions">
          <button
            className="secondary-button"
            disabled={loading}
            onClick={onRefresh}
            type="button"
          >
            {t("progress.refresh")}
          </button>
          <button
            className="secondary-button"
            disabled={loading}
            onClick={onBack}
            type="button"
          >
            {t("progress.back")}
          </button>
        </div>
      </div>

      <section className="recommendation-card">
        <p className="eyebrow">
          {t("progress.recommended")}
        </p>
        {recommendation?.recommendation_available ? (
          <>
            <h3>{topicName}</h3>
            <p>
              {t("progress.mastery")}:{" "}
              {recommendation.mastery === null
                ? t("progress.na")
                : `${formatMasteryValue(recommendation.mastery)} (${formatMasteryPercent(recommendation.mastery)})`}
            </p>
            <p>
              {t("progress.recommendedDifficulty")}:{" "}
              {recommendation.difficulty ?? t("progress.na")}
            </p>
            <p>{localizedReason}</p>
            <button
              disabled={loading}
              onClick={onPracticeRecommended}
              type="button"
            >
              {t("progress.practiceRecommended")}
            </button>
          </>
        ) : (
          <p>
            {recommendation
              ? localizedReason
              : t("progress.noRecommendation")}
          </p>
        )}
      </section>

      <div className="progress-topic-grid">
        {progress?.topics.length ? (
          progress.topics.map((topic) => (
            <TopicProgressCard
              key={`${topic.subject}/${topic.domain}/${topic.topic}`}
              topic={topic}
            />
          ))
        ) : (
          <p>{t("progress.empty")}</p>
        )}
      </div>
      {errorMessage ? (
        <p className="error-message">
          {errorMessage}
        </p>
      ) : null}
    </section>
  );
}
