import type {
  StudentProgress,
  TopicProgress,
} from "@/types/tutor";

interface ProgressDashboardProps {
  progress: StudentProgress | null;
  loading: boolean;
  errorMessage?: string | null;
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

function TopicProgressCard({
  topic,
}: {
  topic: TopicProgress;
}) {
  const masteryPercent = Math.round(
    topic.mastery * 100,
  );

  return (
    <article className="progress-topic-card">
      <div>
        <p className="eyebrow">
          {topic.subject} / {topic.domain}
        </p>
        <h3>{topic.topic_name}</h3>
        <p>
          Mastery: {formatMasteryValue(topic.mastery)}{" "}
          ({formatMasteryPercent(topic.mastery)},{" "}
          {topic.mastery_label})
        </p>
      </div>

      <div
        aria-label={`${topic.topic_name} mastery ${masteryPercent}%`}
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
          <dt>Completed</dt>
          <dd>{topic.questions_completed}</dd>
        </div>
        <div>
          <dt>First-attempt streak</dt>
          <dd>{topic.first_attempt_streak}</dd>
        </div>
        <div>
          <dt>Last attempts</dt>
          <dd>{topic.last_total_attempts}</dd>
        </div>
        <div>
          <dt>Last incorrect</dt>
          <dd>{topic.last_incorrect_attempts}</dd>
        </div>
        <div>
          <dt>Last hints</dt>
          <dd>{topic.last_hints_used}</dd>
        </div>
        <div>
          <dt>Recommended difficulty</dt>
          <dd>
            {topic.recommended_difficulty ?? "N/A"}
          </dd>
        </div>
      </dl>

      <p className="progress-capability">
        {topic.generation_available
          ? `Adaptive generation available: ${topic.supported_difficulties.join(", ")}`
          : "Static practice only"}
      </p>
    </article>
  );
}

export function ProgressDashboard({
  progress,
  loading,
  errorMessage,
  onBack,
  onPracticeRecommended,
  onRefresh,
}: ProgressDashboardProps) {
  const recommendation = progress?.recommendation;

  return (
    <section className="progress-dashboard">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">Student Progress</p>
          <h2>Progress Dashboard</h2>
          <p>
            Read-only mastery and adaptive practice
            state for runnable MAT-PAL topics.
            {progress?.student_id
              ? ` Profile: ${progress.student_id}.`
              : ""}
          </p>
        </div>
        <div className="dashboard-actions">
          <button
            className="secondary-button"
            disabled={loading}
            onClick={onRefresh}
            type="button"
          >
            Refresh
          </button>
          <button
            className="secondary-button"
            disabled={loading}
            onClick={onBack}
            type="button"
          >
            Back to Practice
          </button>
        </div>
      </div>

      <section className="recommendation-card">
        <p className="eyebrow">
          Recommended Next Practice
        </p>
        {recommendation?.recommendation_available ? (
          <>
            <h3>{recommendation.topic_name}</h3>
            <p>
              Mastery:{" "}
              {recommendation.mastery === null
                ? "N/A"
                : `${formatMasteryValue(recommendation.mastery)} (${formatMasteryPercent(recommendation.mastery)})`}
            </p>
            <p>
              Recommended difficulty:{" "}
              {recommendation.difficulty ?? "N/A"}
            </p>
            <p>{recommendation.reason}</p>
            <button
              disabled={loading}
              onClick={onPracticeRecommended}
              type="button"
            >
              Practice Recommended Topic
            </button>
          </>
        ) : (
          <p>
            {recommendation?.reason ??
              "No recommendation is available yet."}
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
          <p>No runnable topics are available yet.</p>
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
