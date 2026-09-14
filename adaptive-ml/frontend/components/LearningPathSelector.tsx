"use client";

import { useLanguage } from "@/components/LanguageProvider";
import { MathContent } from "@/components/math/MathContent";
import { catalogDisplayName } from "@/i18n";
import type {
  CatalogResponse,
  CatalogTopic,
  ProblemDetail,
  ProblemSummary,
} from "@/types/tutor";
import {
  comingSoonDomains,
  domainsForSubject,
  problemsForTopic,
  runnableDomains,
  topicsForDomain,
} from "@/lib/learningPath";
import type { LearningPathSelection } from "@/lib/learningPath";

interface LearningPathSelectorProps {
  catalog: CatalogResponse | null;
  problems: ProblemSummary[];
  selection: LearningPathSelection;
  selectedProblem: ProblemDetail | null;
  selectedTopicRecord: CatalogTopic | null;
  selectedDifficulty: number;
  loading: boolean;
  errorMessage: string | null;
  onSubjectChange: (subjectId: string) => void;
  onDomainChange: (domainId: string) => void;
  onTopicChange: (topicId: string) => void;
  onProblemChange: (problemId: string) => void;
  onDifficultyChange: (difficulty: number) => void;
  onGenerateProblem: () => void;
  onStart: () => void;
}

export function LearningPathSelector({
  catalog,
  problems,
  selection,
  selectedProblem,
  selectedTopicRecord,
  selectedDifficulty,
  loading,
  errorMessage,
  onSubjectChange,
  onDomainChange,
  onTopicChange,
  onProblemChange,
  onDifficultyChange,
  onGenerateProblem,
  onStart,
}: LearningPathSelectorProps) {
  const { locale, t } = useLanguage();
  const subjects = catalog?.subjects ?? [];
  const domains = domainsForSubject(
    catalog,
    selection.subject,
  );
  const availableDomains = runnableDomains(domains);
  const unavailableDomains = comingSoonDomains(domains);
  const topics = topicsForDomain(
    catalog,
    selection.subject,
    selection.domain,
  );
  const filteredProblems = problemsForTopic(
    problems,
    selection,
  );
  const canStart = Boolean(
    selection.problemId && selectedProblem,
  );

  return (
    <section className="start-card" id="learn">
      <h2>{t("path.title")}</h2>
      <p>{t("path.description")}</p>

      <div className="selector-grid">
        <label>
          {t("path.subject")}
          <select
            disabled={loading}
            onChange={(event) =>
              onSubjectChange(event.target.value)
            }
            value={selection.subject}
          >
            <option value="">
              {t("path.chooseSubject")}
            </option>
            {subjects.map((subject) => (
              <option
                disabled={
                  subject.available_problem_count === 0
                }
                key={subject.id}
                value={subject.id}
              >
                {catalogDisplayName(
                  "subject",
                  subject.id,
                  subject.name,
                  locale,
                )}
                {subject.available_problem_count === 0
                  ? t("home.comingSoonSuffix")
                  : t("home.availableCount", {
                      count: subject.available_problem_count,
                    })}
              </option>
            ))}
          </select>
        </label>

        {selection.subject ? (
          <label>
            {t("path.domain")}
            <select
              disabled={
                loading || availableDomains.length === 0
              }
              onChange={(event) =>
                onDomainChange(event.target.value)
              }
              value={selection.domain}
            >
              <option value="">
                {t("path.chooseDomain")}
              </option>
              {availableDomains.map((domain) => (
                <option
                  key={domain.id}
                  value={domain.id}
                >
                  {catalogDisplayName(
                    "domain",
                    domain.id,
                    domain.name,
                    locale,
                  )}
                  {t("home.availableCount", {
                    count: domain.available_problem_count,
                  })}
                </option>
              ))}
              {unavailableDomains.map((domain) => (
                <option
                  disabled
                  key={domain.id}
                  value={domain.id}
                >
                  {catalogDisplayName(
                    "domain",
                    domain.id,
                    domain.name,
                    locale,
                  )}
                  {t("home.comingSoonSuffix")}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        {selection.domain ? (
          <label>
            {t("path.topic")}
            <select
              disabled={loading || topics.length === 0}
              onChange={(event) =>
                onTopicChange(event.target.value)
              }
              value={selection.topic}
            >
              <option value="">
                {t("path.chooseTopic")}
              </option>
              {topics.length > 0 ? (
                topics.map((topic) => (
                  <option
                    key={topic.id}
                    value={topic.id}
                  >
                    {catalogDisplayName(
                      "topic",
                      topic.id,
                      topic.name,
                      locale,
                    )}
                    {t("home.availableCount", {
                      count: topic.available_problem_count,
                    })}
                  </option>
                ))
              ) : (
                <option value="">
                  {t("path.noTopics")}
                </option>
              )}
            </select>
          </label>
        ) : null}

        {selection.topic ? (
          <label>
            {t("path.problem")}
            <select
              disabled={
                loading || filteredProblems.length === 0
              }
              onChange={(event) =>
                onProblemChange(event.target.value)
              }
              value={selection.problemId}
            >
              <option value="">
                {t("path.chooseProblem")}
              </option>
              {filteredProblems.length > 0 ? (
                filteredProblems.map((problem) => (
                  <option
                    key={problem.problem_id}
                    value={problem.problem_id}
                  >
                    {catalogDisplayName(
                      "problem",
                      problem.problem_id,
                      problem.title,
                      locale,
                    )}
                  </option>
                ))
              ) : (
                <option value="">
                  {t("path.noProblems")}
                </option>
              )}
            </select>
          </label>
        ) : null}

        {selectedTopicRecord?.generation_available ? (
          <label>
            {t("path.difficulty")}
            <select
              disabled={loading}
              onChange={(event) =>
                onDifficultyChange(
                  Number(event.target.value),
                )
              }
              value={selectedDifficulty}
            >
              {selectedTopicRecord.supported_difficulties.map(
                (difficulty) => (
                  <option
                    key={difficulty}
                    value={difficulty}
                  >
                    {difficulty}
                  </option>
                ),
              )}
            </select>
          </label>
        ) : null}
      </div>

      {selectedTopicRecord?.generation_available ? (
        <div className="generation-panel">
          <p>{t("path.generateHelp")}</p>
          <button
            disabled={loading}
            onClick={onGenerateProblem}
            type="button"
          >
            {t("path.generate")}
          </button>
        </div>
      ) : null}

      {selectedProblem ? (
        <div className="problem-preview">
          <p className="eyebrow">
            {catalogDisplayName(
              "subject",
              selectedProblem.subject,
              selectedProblem.subject,
              locale,
            )}{" "}
            /{" "}
            {catalogDisplayName(
              "domain",
              selectedProblem.domain,
              selectedProblem.domain,
              locale,
            )}{" "}
            /{" "}
            {catalogDisplayName(
              "topic",
              selectedProblem.topic,
              selectedProblem.topic,
              locale,
            )}
          </p>
          <h3>
            {catalogDisplayName(
              "problem",
              selectedProblem.problem_id,
              selectedProblem.title,
              locale,
            )}
          </h3>
          <MathContent
            text={selectedProblem.problem_text}
          />
          <span>
            {t("path.steps", {
              count: selectedProblem.total_steps,
            })}
          </span>
        </div>
      ) : null}

      <button
        disabled={loading || !canStart}
        onClick={onStart}
        type="button"
      >
        {loading ? t("path.loading") : t("path.start")}
      </button>
      {errorMessage ? (
        <p className="error-message">{errorMessage}</p>
      ) : null}
    </section>
  );
}
