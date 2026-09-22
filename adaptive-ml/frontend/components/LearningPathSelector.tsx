"use client";

import { useLanguage } from "@/components/LanguageProvider";
import { MathContent } from "@/components/math/MathContent";
import { catalogDisplayName } from "@/i18n";
import {
  AUTOMATIC_FAMILY,
  LOGICAL_REASONING_FAMILIES,
  exerciseStatementForDisplay,
  isLogicalReasoningTopic,
  readGeneratedFamily,
} from "@/lib/logicalReasoning";
import type {
  CatalogResponse,
  CatalogTopic,
  ProblemDetail,
  ProblemSummary,
} from "@/types/tutor";
import {
  comingSoonDomains,
  domainContentCount,
  domainsForSubject,
  problemsForTopic,
  runnableDomains,
  subjectContentCount,
  topicHasStaticProblems,
  topicSupportsGeneration,
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
  selectedFamily: string;
  loading: boolean;
  errorMessage: string | null;
  onSubjectChange: (subjectId: string) => void;
  onDomainChange: (domainId: string) => void;
  onTopicChange: (topicId: string) => void;
  onProblemChange: (problemId: string) => void;
  onDifficultyChange: (difficulty: number) => void;
  onFamilyChange: (family: string) => void;
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
  selectedFamily,
  loading,
  errorMessage,
  onSubjectChange,
  onDomainChange,
  onTopicChange,
  onProblemChange,
  onDifficultyChange,
  onFamilyChange,
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
  const canGenerate = topicSupportsGeneration(
    selectedTopicRecord,
  );
  const hasStaticProblems = topicHasStaticProblems(
    selectedTopicRecord,
  );
  const showProblemPicker =
    hasStaticProblems || filteredProblems.length > 0;
  const canStart = Boolean(
    selection.problemId && selectedProblem,
  );
  const generatedFamily = readGeneratedFamily(
    selectedProblem?.metadata,
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
            {subjects.map((subject) => {
              const runnableCount = subjectContentCount(
                subject,
              );

              return (
              <option
                disabled={runnableCount === 0}
                key={subject.id}
                value={subject.id}
              >
                {catalogDisplayName(
                  "subject",
                  subject.id,
                  subject.name,
                  locale,
                )}
                {runnableCount === 0
                  ? t("home.comingSoonSuffix")
                  : t("home.availableCount", {
                      count: runnableCount,
                    })}
              </option>
              );
            })}
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
                    count: domainContentCount(domain),
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
                    {topicHasStaticProblems(topic)
                      ? t("home.availableCount", {
                          count: topic.available_problem_count,
                        })
                      : topic.generation_available
                        ? t("path.generatedTopic")
                        : t("home.comingSoonSuffix")}
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

        {selection.topic && showProblemPicker ? (
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

        {canGenerate ? (
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
              {(
                selectedTopicRecord?.supported_difficulties
                ?? []
              ).map(
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

        {canGenerate &&
        isLogicalReasoningTopic(selection.topic) ? (
          <label>
            {t("path.family")}
            <select
              aria-label={t("path.family")}
              disabled={loading}
              onChange={(event) =>
                onFamilyChange(event.target.value)
              }
              value={selectedFamily}
            >
              <option value={AUTOMATIC_FAMILY}>
                {t("path.familyAutomatic")}
              </option>
              {LOGICAL_REASONING_FAMILIES.map((family) => (
                <option key={family} value={family}>
                  {t(`path.family.${family}`)}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      {canGenerate ? (
        <div className="generation-panel">
          <p>
            {isLogicalReasoningTopic(selection.topic)
              ? t("catalog.topic.logical_reasoning.description")
              : showProblemPicker
                ? t("path.generateHelp")
                : t("path.generateFirst")}
          </p>
          <button
            disabled={loading}
            onClick={onGenerateProblem}
            type="button"
          >
            {selectedProblem?.generated
              ? t("path.generateAgain")
              : t("path.generate")}
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
            text={exerciseStatementForDisplay(
              selectedProblem.problem_text,
              {
                topic: selectedProblem.topic,
                problemId: selectedProblem.problem_id,
              },
            )}
          />
          {generatedFamily ? (
            <span>
              {t(`path.family.${generatedFamily}`)}
            </span>
          ) : null}
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
