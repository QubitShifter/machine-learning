"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useStudentProfile } from "@/components/StudentProfileProvider";

import { HomeHero } from "@/components/HomeHero";
import { LearningPathSelector } from "@/components/LearningPathSelector";
import { useLanguage } from "@/components/LanguageProvider";
import { ProgressDashboard } from "@/components/ProgressDashboard";
import { SubjectCard } from "@/components/SubjectCard";
import { TutorCard } from "@/components/TutorCard";
import {
  snapshotGradedFeedback,
  type GradedFeedback,
} from "@/components/feedbackPresentation";
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
  submitQuestion,
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
import {
  DEFAULT_LOCALE,
  catalogDisplayName,
  localizeRecommendationReason,
  translate,
} from "@/i18n";
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
  const { locale, t } = useLanguage();
  const studentId = selectedStudent.studentId;
  const previousStudentId = useRef(studentId);
  const previousLocale = useRef(locale);

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
  const [questionLoading, setQuestionLoading] =
    useState(false);
  const [lastGraded, setLastGraded] =
    useState<GradedFeedback | null>(null);
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
    setLastGraded(null);
  }, [studentId]);

  useEffect(() => {
    if (previousLocale.current === locale) {
      return;
    }

    previousLocale.current = locale;
    setSession(null);
    setCurrentPrompt("");
    setAnswer("");
    setAdaptiveMessage(null);
    setErrorMessage(null);
    setLastGraded(null);
  }, [locale]);

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
              : translate(DEFAULT_LOCALE, "error.catalog"),
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
          locale,
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
              : translate(locale, "error.problem"),
          );
        }
      }
    }

    void loadProblem();

    return () => {
      ignore = true;
    };
  }, [selection.problemId, locale]);

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
          : t("error.generic"),
      );
    } finally {
      setLoading(false);
    }
  }

  function handleStart() {
    if (!selection.problemId || !visibleProblem) {
      setErrorMessage(
        t("path.chooseProblemFirst"),
      );
      return;
    }

    void runRequest(
      () =>
        startSession({
          problem_id: selection.problemId,
          student_id: studentId,
          language: locale,
        }),
      (nextSession) => {
        setCurrentPrompt(nextSession.feedback);
        setAnswer("");
        setLastGraded(null);
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
    setLastGraded(null);
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
        t("path.noGeneration"),
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
        language: locale,
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
      setLastGraded(null);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : t("error.generate"),
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
        const graded = snapshotGradedFeedback(
          nextSession,
        );
        if (graded) {
          setLastGraded(graded);
        }

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

    setQuestionLoading(true);
    setErrorMessage(null);

    void (async () => {
      try {
        const nextSession = await submitQuestion(
          session.session_id,
          {
            question,
          },
        );
        setSession(nextSession);
      } catch (error) {
        setErrorMessage(
          error instanceof Error
            ? error.message
            : t("error.generic"),
        );
      } finally {
        setQuestionLoading(false);
      }
    })();
  }

  function handleRequestHint() {
    if (!session) {
      return;
    }

    void runRequest(
      () => requestHint(session.session_id),
      (nextSession) => {
        const graded = snapshotGradedFeedback(
          nextSession,
        );
        if (graded) {
          setLastGraded(graded);
        }
      },
    );
  }

  async function startRecommendedPractice(
    recommendation: AdaptiveRecommendation,
  ) {
    const topicName = recommendation.topic
      ? catalogDisplayName(
          "topic",
          recommendation.topic,
          recommendation.topic_name ?? recommendation.topic,
          locale,
        )
      : recommendation.topic_name ?? "";
    const adjustmentReason =
      typeof recommendation.metadata.adjustment_reason ===
      "string"
        ? recommendation.metadata.adjustment_reason
        : undefined;
    const sessionCount =
      typeof recommendation.metadata.recent_session_count ===
      "number"
        ? recommendation.metadata.recent_session_count
        : undefined;

    setAdaptiveMessage(
      localizeRecommendationReason(
        locale,
        topicName,
        recommendation.mastery,
        adjustmentReason,
        sessionCount,
      ),
    );

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
        language: locale,
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
        language: locale,
      });
      setSession(nextSession);
      setCurrentPrompt(nextSession.feedback);
      setAnswer("");
      return;
    }

    if (recommendation.problem_id) {
      const problem = await getProblem(
        recommendation.problem_id,
        locale,
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
        language: locale,
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
          : t("adaptive.practiceError"),
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
          : t("progress.loadError"),
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
              : translate(locale, "progress.loadError"),
          );
        }
      }
    }

    void fetchProgress();

    return () => {
      ignore = true;
    };
  }, [progressRequested, studentId, locale]);

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
          : t("progress.practiceError"),
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
          studentName={
            selectedStudent.isGuest
              ? t("profile.guest")
              : selectedStudent.displayName
          }
        />
      ) : session ? (
        <TutorCard
          adaptiveMessage={adaptiveMessage}
          answer={answer}
          currentPrompt={currentPrompt}
          errorMessage={errorMessage}
          lastGraded={lastGraded}
          loading={loading}
          questionLoading={questionLoading}
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
            <h2>{t("home.chooseBegin")}</h2>
            {catalog ? (
              <div className="subject-grid">
                {landingEntries(catalog).map((entry) => (
                  <SubjectCard
                    catalog={catalog}
                    entry={entry}
                    key={entry.key}
                    onExplore={enterLearningPath}
                  />
                ))}
              </div>
            ) : (
              <p>{t("home.loadingCatalog")}</p>
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
