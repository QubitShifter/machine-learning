import { MathContent } from "@/components/math/MathContent";
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
      <h2>Choose your learning path</h2>
      <p>
        Select a subject, then a domain, topic, and
        problem from the MAT-PAL catalog.
      </p>

      <div className="selector-grid">
        <label>
          Subject
          <select
            disabled={loading}
            onChange={(event) =>
              onSubjectChange(event.target.value)
            }
            value={selection.subject}
          >
            <option value="">
              Choose a subject
            </option>
            {subjects.map((subject) => (
              <option
                disabled={
                  subject.available_problem_count === 0
                }
                key={subject.id}
                value={subject.id}
              >
                {subject.name}
                {subject.available_problem_count === 0
                  ? " — Coming soon"
                  : ` (${subject.available_problem_count} available)`}
              </option>
            ))}
          </select>
        </label>

        {selection.subject ? (
          <label>
            Domain
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
                Choose a domain
              </option>
              {availableDomains.map((domain) => (
                <option
                  key={domain.id}
                  value={domain.id}
                >
                  {domain.name} (
                  {domain.available_problem_count}{" "}
                  available)
                </option>
              ))}
              {unavailableDomains.map((domain) => (
                <option
                  disabled
                  key={domain.id}
                  value={domain.id}
                >
                  {domain.name} — Coming soon
                </option>
              ))}
            </select>
          </label>
        ) : null}

        {selection.domain ? (
          <label>
            Topic
            <select
              disabled={loading || topics.length === 0}
              onChange={(event) =>
                onTopicChange(event.target.value)
              }
              value={selection.topic}
            >
              <option value="">
                Choose a topic
              </option>
              {topics.length > 0 ? (
                topics.map((topic) => (
                  <option
                    key={topic.id}
                    value={topic.id}
                  >
                    {topic.name} (
                    {topic.available_problem_count}{" "}
                    available)
                  </option>
                ))
              ) : (
                <option value="">
                  No topics available yet
                </option>
              )}
            </select>
          </label>
        ) : null}

        {selection.topic ? (
          <label>
            Problem
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
                Choose a problem
              </option>
              {filteredProblems.length > 0 ? (
                filteredProblems.map((problem) => (
                  <option
                    key={problem.problem_id}
                    value={problem.problem_id}
                  >
                    {problem.title}
                  </option>
                ))
              ) : (
                <option value="">
                  No problems available yet
                </option>
              )}
            </select>
          </label>
        ) : null}

        {selectedTopicRecord?.generation_available ? (
          <label>
            Difficulty
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
          <p>
            This topic can generate new practice
            problems at the selected difficulty.
          </p>
          <button
            disabled={loading}
            onClick={onGenerateProblem}
            type="button"
          >
            Generate Problem
          </button>
        </div>
      ) : null}

      {selectedProblem ? (
        <div className="problem-preview">
          <p className="eyebrow">
            {selectedProblem.subject} /{" "}
            {selectedProblem.domain} /{" "}
            {selectedProblem.topic}
          </p>
          <h3>{selectedProblem.title}</h3>
          <MathContent
            text={selectedProblem.problem_text}
          />
          <span>
            {selectedProblem.total_steps} tutor
            steps
          </span>
        </div>
      ) : null}

      <button
        disabled={loading || !canStart}
        onClick={onStart}
        type="button"
      >
        {loading
          ? "Loading..."
          : "Start Selected Problem"}
      </button>
      {errorMessage ? (
        <p className="error-message">{errorMessage}</p>
      ) : null}
    </section>
  );
}
