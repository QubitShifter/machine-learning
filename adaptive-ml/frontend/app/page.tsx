"use client";

import { useEffect, useMemo, useState } from "react";

import { TutorCard } from "@/components/TutorCard";
import {
  getCatalog,
  getProblem,
  listProblems,
  requestHint,
  startSession,
  submitAnswer,
} from "@/lib/api";
import type {
  CatalogResponse,
  ProblemDetail,
  ProblemSummary,
  TutorSession,
} from "@/types/tutor";

function readNextPrompt(
  session: TutorSession,
) {
  const nextPrompt = session.metadata.next_prompt;

  return typeof nextPrompt === "string"
    ? nextPrompt
    : session.feedback;
}

export default function Home() {
  const [catalog, setCatalog] =
    useState<CatalogResponse | null>(null);
  const [problems, setProblems] = useState<
    ProblemSummary[]
  >([]);
  const [selectedSubject, setSelectedSubject] =
    useState("");
  const [selectedDomain, setSelectedDomain] =
    useState("");
  const [selectedTopic, setSelectedTopic] =
    useState("");
  const [selectedProblemId, setSelectedProblemId] =
    useState("");
  const [selectedProblem, setSelectedProblem] =
    useState<ProblemDetail | null>(null);
  const [session, setSession] =
    useState<TutorSession | null>(null);
  const [currentPrompt, setCurrentPrompt] =
    useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] =
    useState<string | null>(null);

  useEffect(() => {
    async function loadCatalog() {
      setLoading(true);
      setErrorMessage(null);

      try {
        const [nextCatalog, nextProblems] =
          await Promise.all([
            getCatalog(),
            listProblems(),
          ]);

        setCatalog(nextCatalog);
        setProblems(nextProblems);

        const firstProblem = nextProblems[0];

        if (firstProblem) {
          setSelectedSubject(firstProblem.subject);
          setSelectedDomain(firstProblem.domain);
          setSelectedTopic(firstProblem.topic);
          setSelectedProblemId(
            firstProblem.problem_id,
          );
        }
      } catch (error) {
        setErrorMessage(
          error instanceof Error
            ? error.message
            : "Could not load the MAT-PAL catalog.",
        );
      } finally {
        setLoading(false);
      }
    }

    void loadCatalog();
  }, []);

  useEffect(() => {
    if (!selectedProblemId) {
      return;
    }

    let ignore = false;

    async function loadProblem() {
      try {
        const problem = await getProblem(
          selectedProblemId,
        );

        if (!ignore) {
          setSelectedProblem(problem);
        }
      } catch (error) {
        if (!ignore) {
          setSelectedProblem(null);
          setErrorMessage(
            error instanceof Error
              ? error.message
              : "Could not load the selected problem.",
          );
        }
      }
    }

    void loadProblem();

    return () => {
      ignore = true;
    };
  }, [selectedProblemId]);

  const subjects = useMemo(
    () => catalog?.subjects ?? [],
    [catalog],
  );
  const domains = useMemo(
    () =>
      subjects.find(
        (subject) =>
          subject.id === selectedSubject,
      )?.domains ?? [],
    [selectedSubject, subjects],
  );
  const topics = useMemo(
    () =>
      domains.find(
        (domain) =>
          domain.id === selectedDomain,
      )?.topics ?? [],
    [selectedDomain, domains],
  );
  const filteredProblems = useMemo(
    () =>
      problems.filter(
        (problem) =>
          problem.subject === selectedSubject &&
          problem.domain === selectedDomain &&
          problem.topic === selectedTopic,
      ),
    [
      problems,
      selectedDomain,
      selectedSubject,
      selectedTopic,
    ],
  );

  async function runRequest(
    action: () => Promise<TutorSession>,
    onSuccess?: (nextSession: TutorSession) => void,
  ) {
    setLoading(true);
    setErrorMessage(null);

    try {
      const nextSession = await action();
      setSession(nextSession);
      onSuccess?.(nextSession);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Something went wrong while contacting MAT-PAL.",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleStart() {
    if (!selectedProblemId || !selectedProblem) {
      setErrorMessage(
        "Choose an available problem before starting.",
      );
      return;
    }

    void runRequest(
      () =>
        startSession({
          problem_id: selectedProblemId,
        }),
      (nextSession) => {
        setCurrentPrompt(nextSession.feedback);
        setAnswer("");
      },
    );
  }

  function handleSubjectChange(value: string) {
    const subject = subjects.find(
      (item) => item.id === value,
    );
    const domain = subject?.domains[0];
    const topic = domain?.topics[0];
    const problem = problems.find(
      (item) =>
        item.subject === value &&
        item.domain === domain?.id &&
        item.topic === topic?.id,
    );

    setSelectedSubject(value);
    setSelectedDomain(domain?.id ?? "");
    setSelectedTopic(topic?.id ?? "");
    setSelectedProblemId(
      problem?.problem_id ?? "",
    );
    setSelectedProblem(null);
  }

  function handleDomainChange(value: string) {
    const topic = domains.find(
      (item) => item.id === value,
    )?.topics[0];
    const problem = problems.find(
      (item) =>
        item.subject === selectedSubject &&
        item.domain === value &&
        item.topic === topic?.id,
    );

    setSelectedDomain(value);
    setSelectedTopic(topic?.id ?? "");
    setSelectedProblemId(
      problem?.problem_id ?? "",
    );
    setSelectedProblem(null);
  }

  function handleTopicChange(value: string) {
    const problem = problems.find(
      (item) =>
        item.subject === selectedSubject &&
        item.domain === selectedDomain &&
        item.topic === value,
    );

    setSelectedTopic(value);
    setSelectedProblemId(
      problem?.problem_id ?? "",
    );
    setSelectedProblem(null);
  }

  function handleSubmitAnswer() {
    if (!session) {
      return;
    }

    void runRequest(
      () =>
        submitAnswer(session.session_id, {
          answer,
          input_type: session.expected_input_type,
        }),
      (nextSession) => {
        setAnswer("");

        if (
          nextSession.status === "correct" ||
          nextSession.status === "waiting_for_answer"
        ) {
          setCurrentPrompt(
            readNextPrompt(nextSession),
          );
        }
      },
    );
  }

  function handleRequestHint() {
    if (!session) {
      return;
    }

    void runRequest(() =>
      requestHint(session.session_id),
    );
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">Adaptive STEM tutor</p>
        <h1>MAT-PAL</h1>
        <p>
          Math And Physics Adaptive Learning
        </p>
      </section>

      {!session ? (
        <section className="start-card">
          <h2>Choose a learning path</h2>
          <p>
            Select a subject, domain, topic, and
            available problem from the MAT-PAL backend.
          </p>

          <div className="selector-grid">
            <label>
              Subject
              <select
                disabled={loading}
                onChange={(event) =>
                  handleSubjectChange(
                    event.target.value,
                  )
                }
                value={selectedSubject}
              >
                {subjects.map((subject) => (
                  <option
                    key={subject.id}
                    value={subject.id}
                  >
                    {subject.name} (
                    {
                      subject.available_problem_count
                    }{" "}
                    available)
                  </option>
                ))}
              </select>
            </label>

            <label>
              Domain
              <select
                disabled={loading || !selectedSubject}
                onChange={(event) =>
                  handleDomainChange(
                    event.target.value,
                  )
                }
                value={selectedDomain}
              >
                {domains.map((domain) => (
                  <option
                    key={domain.id}
                    value={domain.id}
                  >
                    {domain.name} (
                    {
                      domain.available_problem_count
                    }{" "}
                    available)
                  </option>
                ))}
              </select>
            </label>

            <label>
              Topic
              <select
                disabled={loading || !selectedDomain}
                onChange={(event) =>
                  handleTopicChange(
                    event.target.value,
                  )
                }
                value={selectedTopic}
              >
                {topics.length > 0 ? (
                  topics.map((topic) => (
                    <option
                      key={topic.id}
                      value={topic.id}
                    >
                      {topic.name} (
                      {
                        topic.available_problem_count
                      }{" "}
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

            <label>
              Problem
              <select
                disabled={
                  loading ||
                  filteredProblems.length === 0
                }
                onChange={(event) => {
                  setSelectedProblemId(
                    event.target.value,
                  );
                  setSelectedProblem(null);
                }}
                value={selectedProblemId}
              >
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
          </div>

          {selectedProblem ? (
            <div className="problem-preview">
              <p className="eyebrow">
                {selectedProblem.subject} /{" "}
                {selectedProblem.domain} /{" "}
                {selectedProblem.topic}
              </p>
              <h3>{selectedProblem.title}</h3>
              <p>{selectedProblem.problem_text}</p>
              <span>
                {selectedProblem.total_steps} tutor
                steps
              </span>
            </div>
          ) : null}

          <button
            disabled={
              loading ||
              !selectedProblemId ||
              !selectedProblem
            }
            onClick={handleStart}
            type="button"
          >
            {loading
              ? "Loading..."
              : "Start Selected Problem"}
          </button>
          {errorMessage ? (
            <p className="error-message">
              {errorMessage}
            </p>
          ) : null}
        </section>
      ) : (
        <TutorCard
          answer={answer}
          currentPrompt={currentPrompt}
          errorMessage={errorMessage}
          loading={loading}
          onAnswerChange={setAnswer}
          onRequestHint={handleRequestHint}
          onRestart={handleStart}
          onSubmitAnswer={handleSubmitAnswer}
          session={session}
        />
      )}
    </main>
  );
}
