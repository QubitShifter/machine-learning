"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useStudentProfile } from "@/components/StudentProfileProvider";

import { HomeHero } from "@/components/HomeHero";
import { LearningPathSelector } from "@/components/LearningPathSelector";
import { ProgressDashboard } from "@/components/ProgressDashboard";
import { SubjectCard } from "@/components/SubjectCard";
import { TutorCard } from "@/components/TutorCard";
import {
  generateProblem,
  getAdaptiveRecommendation,
  getCatalog,
  getProblem,
  getStudentProgress,
  listProblems,
  requestHint,
  startSession,
  submitAnswer,
} from "@/lib/api";
import {
  HOME_HREF,
  LEARN_HREF,
  catalogSubjects,
  createEmptyLearningPath,
  findTopic,
  firstRunnableSubject,
  isProgressView,
  landingEntries,
  isRunnableSubject,
  selectDomain,
  selectProblem,
  selectSubject,
  selectTopic,
} from "@/lib/learningPath";
import type {
  LandingEntry,
  LearningPathSelection,
} from "@/lib/learningPath";
import type {
  AdaptiveRecommendation,
  CatalogResponse,
  ProblemDetail,
  ProblemSummary,
  StudentProgress,
  TutorSession,
} from "@/types/tutor";

function readNextPrompt(session: TutorSession) {
  const nextPrompt = session.metadata.next_prompt;

  return typeof nextPrompt === "string"
    ? nextPrompt
    : session.feedback;
}

function scrollToLearn() {
  document
    .getElementById("learn")
    ?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
}

export function HomePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const progressRequested = isProgressView(searchParams);
  const { selectedStudent } = useStudentProfile();
  const studentId = selectedStudent.studentId;
  const previousStudentId = useRef(studentId);

  const [catalog, setCatalog] =
    useState<CatalogResponse | null>(null);
  const [problems, setProblems] = useState<
    ProblemSummary[]
  >([]);
  const [selection, setSelection] =
    useState<LearningPathSelection>(
      createEmptyLearningPath,
    );
  const [selectedDifficulty, setSelectedDifficulty] =
    useState(1);
  const [selectedProblem, setSelectedProblem] =
    useState<ProblemDetail | null>(null);
  const [session, setSession] =
    useState<TutorSession | null>(null);
  const [progress, setProgress] =
    useState<StudentProgress | null>(null);
  const [currentPrompt, setCurrentPrompt] =
    useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] =
    useState<string | null>(null);
  const [adaptiveMessage, setAdaptiveMessage] =
    useState<string | null>(null);

  useEffect(() => {
    if (previousStudentId.current === studentId) {
      return;
    }

    previousStudentId.current = studentId;
    setSession(null);
    setCurrentPrompt("");
    setAnswer("");
    setAdaptiveMessage(null);
    setProgress(null);
    setErrorMessage(null);
  }, [studentId]);

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
    if (!selection.problemId) {
      return;
    }

    let ignore = false;

    async function loadProblem() {
      try {
        const problem = await getProblem(
          selection.problemId,
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
  }, [selection.problemId]);

  const visibleProblem =
    selection.problemId &&
    selectedProblem?.problem_id === selection.problemId
      ? selectedProblem
      : null;

  const selectedTopicRecord = useMemo(
    () =>
      findTopic(
        catalog,
        selection.subject,
        selection.domain,
        selection.topic,
      ),
    [catalog, selection],
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
    if (!selection.problemId || !visibleProblem) {
      setErrorMessage(
        "Choose an available problem before starting.",
      );
      return;
    }

    void runRequest(
      () =>
        startSession({
          problem_id: selection.problemId,
          student_id: studentId,
        }),
      (nextSession) => {
        setCurrentPrompt(nextSession.feedback);
        setAnswer("");
      },
    );
  }

  function handleSubjectChange(value: string) {
    const subject = catalogSubjects(catalog).find(
      (item) => item.id === value,
    );

    if (value && subject && !isRunnableSubject(subject)) {
      return;
    }

    setSelection(selectSubject(value));
    setSelectedDifficulty(1);
    setSelectedProblem(null);
    setSession(null);
    setAdaptiveMessage(null);
  }

  function handleDomainChange(value: string) {
    setSelection((current) =>
      selectDomain(current, value),
    );
    setSelectedDifficulty(1);
    setSelectedProblem(null);
  }

  function handleTopicChange(value: string) {
    const topic = findTopic(
      catalog,
      selection.subject,
      selection.domain,
      value,
    );

    setSelection((current) =>
      selectTopic(current, value),
    );
    setSelectedDifficulty(
      topic?.supported_difficulties[0] ?? 1,
    );
    setSelectedProblem(null);
  }

  function handleProblemChange(value: string) {
    setSelection((current) =>
      selectProblem(current, value),
    );
    setSelectedProblem(null);
  }

  function applyLearningSelection(
    nextSelection: LearningPathSelection,
  ) {
    setSelection(nextSelection);
    setSelectedDifficulty(1);
    setSelectedProblem(null);
    setSession(null);
    setAdaptiveMessage(null);
    router.replace(LEARN_HREF);
    window.requestAnimationFrame(scrollToLearn);
  }

  function enterLearningPath(entry?: LandingEntry) {
    if (entry) {
      if (!entry.runnable) {
        return;
      }

      applyLearningSelection(entry.selection);
      return;
    }

    const nextSubject = firstRunnableSubject(catalog);

    if (nextSubject) {
      applyLearningSelection(selectSubject(nextSubject.id));
    } else {
      router.replace(LEARN_HREF);
      window.requestAnimationFrame(scrollToLearn);
    }
  }

  async function handleGenerateProblem() {
    if (!selectedTopicRecord?.generation_available) {
      setErrorMessage(
        "This topic does not support generated problems yet.",
      );
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      const generated = await generateProblem({
        subject: selection.subject,
        domain: selection.domain,
        topic: selection.topic,
        difficulty: selectedDifficulty,
      });

      setProblems((currentProblems) => [
        ...currentProblems,
        generated,
      ]);
      setSelection((current) =>
        selectProblem(current, generated.problem_id),
      );
      setSelectedProblem(generated);
      setSession(null);
      setCurrentPrompt("");
      setAnswer("");
      setAdaptiveMessage(null);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Could not generate a new problem.",
      );
    } finally {
      setLoading(false);
    }
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

        if (nextSession.completed) {
          setAdaptiveMessage(null);
        }

        if (
          nextSession.status === "correct" ||
          nextSession.status === "waiting_for_answer"
        ) {
          setCurrentPrompt(readNextPrompt(nextSession));
        }
      },
    );
  }

  function handleSubmitQuestion(question: string) {
    if (!session) {
      return;
    }

    void runRequest(
      () =>
        submitAnswer(session.session_id, {
          answer: question,
          input_type: "text",
        }),
      (nextSession) => {
        if (
          nextSession.status === "correct" ||
          nextSession.status === "waiting_for_answer"
        ) {
          setCurrentPrompt(readNextPrompt(nextSession));
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

  async function startRecommendedPractice(
    recommendation: AdaptiveRecommendation,
  ) {
    setAdaptiveMessage(recommendation.reason);

    if (!recommendation.recommendation_available) {
      return;
    }

    if (
      recommendation.generation_available &&
      recommendation.subject &&
      recommendation.domain &&
      recommendation.topic &&
      recommendation.difficulty !== null
    ) {
      const generated = await generateProblem({
        subject: recommendation.subject,
        domain: recommendation.domain,
        topic: recommendation.topic,
        difficulty: recommendation.difficulty,
      });
      setProblems((currentProblems) => [
        ...currentProblems,
        generated,
      ]);
      setSelection({
        subject: generated.subject,
        domain: generated.domain,
        topic: generated.topic,
        problemId: generated.problem_id,
      });
      setSelectedProblem(generated);
      setSelectedDifficulty(
        typeof generated.metadata.difficulty === "number"
          ? generated.metadata.difficulty
          : generated.supported_difficulties[0] ?? 1,
      );

      const nextSession = await startSession({
        problem_id: generated.problem_id,
        student_id: studentId,
      });
      setSession(nextSession);
      setCurrentPrompt(nextSession.feedback);
      setAnswer("");
      return;
    }

    if (recommendation.problem_id) {
      const problem = await getProblem(
        recommendation.problem_id,
      );
      setSelection({
        subject: problem.subject,
        domain: problem.domain,
        topic: problem.topic,
        problemId: problem.problem_id,
      });
      setSelectedProblem(problem);

      const nextSession = await startSession({
        problem_id: problem.problem_id,
        student_id: studentId,
      });
      setSession(nextSession);
      setCurrentPrompt(nextSession.feedback);
      setAnswer("");
    }
  }

  async function handlePracticeNext() {
    if (!session) {
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      const recommendation =
        await getAdaptiveRecommendation({
          subject: selection.subject || undefined,
          domain: selection.domain || undefined,
          student_id: studentId,
        });

      await startRecommendedPractice(recommendation);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Could not start adaptive practice.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadProgress() {
    setLoading(true);
    setErrorMessage(null);

    try {
      const nextProgress = await getStudentProgress(studentId);
      setProgress(nextProgress);
      setSession(null);
      setAdaptiveMessage(null);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Could not load progress.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!progressRequested) {
      return;
    }

    let ignore = false;

    async function fetchProgress() {
      try {
        const nextProgress = await getStudentProgress(
          studentId,
        );

        if (!ignore) {
          setProgress(nextProgress);
          setSession(null);
          setAdaptiveMessage(null);
        }
      } catch (error) {
        if (!ignore) {
          setErrorMessage(
            error instanceof Error
              ? error.message
              : "Could not load progress.",
          );
        }
      }
    }

    void fetchProgress();

    return () => {
      ignore = true;
    };
  }, [progressRequested, studentId]);

  async function handlePracticeRecommendedFromDashboard() {
    if (!progress) {
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      await startRecommendedPractice(
        progress.recommendation,
      );
      router.replace(HOME_HREF);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Could not start recommended practice.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page-shell">
      {progressRequested ? (
        <ProgressDashboard
          errorMessage={errorMessage}
          loading={loading}
          onBack={() => router.replace(LEARN_HREF)}
          onPracticeRecommended={
            handlePracticeRecommendedFromDashboard
          }
          onRefresh={() => {
            void loadProgress();
          }}
          progress={progress}
          studentName={selectedStudent.displayName}
        />
      ) : session ? (
        <TutorCard
          adaptiveMessage={adaptiveMessage}
          answer={answer}
          currentPrompt={currentPrompt}
          errorMessage={errorMessage}
          loading={loading}
          onAnswerChange={setAnswer}
          onPracticeNext={handlePracticeNext}
          onRequestHint={handleRequestHint}
          onRestart={handleStart}
          onSubmitAnswer={handleSubmitAnswer}
          onSubmitQuestion={handleSubmitQuestion}
          session={session}
        />
      ) : (
        <>
          <HomeHero
            onStartLearning={() => enterLearningPath()}
          />

          <section className="subject-section">
            <h2>Choose where to begin</h2>
            {catalog ? (
              <div className="subject-grid">
                {landingEntries(catalog).map((entry) => (
                  <SubjectCard
                    entry={entry}
                    key={entry.key}
                    onExplore={enterLearningPath}
                  />
                ))}
              </div>
            ) : (
              <p>Loading available subjects from the catalog…</p>
            )}
          </section>

          <LearningPathSelector
            catalog={catalog}
            errorMessage={errorMessage}
            loading={loading}
            onDifficultyChange={setSelectedDifficulty}
            onDomainChange={handleDomainChange}
            onGenerateProblem={handleGenerateProblem}
            onProblemChange={handleProblemChange}
            onStart={handleStart}
            onSubjectChange={handleSubjectChange}
            onTopicChange={handleTopicChange}
            problems={problems}
            selectedDifficulty={selectedDifficulty}
            selectedProblem={visibleProblem}
            selectedTopicRecord={selectedTopicRecord}
            selection={selection}
          />
        </>
      )}
    </main>
  );
}
