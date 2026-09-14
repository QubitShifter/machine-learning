"use client";

import type { FormEvent, KeyboardEvent } from "react";
import { useEffect, useRef, useState } from "react";

import { AnswerInput } from "@/components/answer-input/AnswerInput";
import { FeedbackPanel } from "@/components/FeedbackPanel";
import { useLanguage } from "@/components/LanguageProvider";
import { MathContent } from "@/components/math/MathContent";
import { ProgressBar } from "@/components/ProgressBar";
import {
  isAnswerEditorEnabled,
  prepareQuestionForSubmit,
  readQuestionFieldValue,
  submitQuestionMode,
  toggleQuestionMode,
} from "@/components/questionText";
import type { TutorSession } from "@/types/tutor";

interface TutorCardProps {
  session: TutorSession;
  currentPrompt: string;
  answer: string;
  loading: boolean;
  errorMessage: string | null;
  onAnswerChange: (value: string) => void;
  onSubmitAnswer: () => void;
  onSubmitQuestion: (question: string) => void;
  onRequestHint: () => void;
  onRestart: () => void;
  onPracticeNext?: () => void;
  adaptiveMessage?: string | null;
}

interface ComparisonMetadata {
  title: string;
  leftLabel: string;
  left: string;
  rightLabel: string;
  right: string;
  question: string;
}

function isRecord(
  value: unknown,
): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

function readString(
  record: Record<string, unknown>,
  key: string,
  fallback: string,
) {
  const value = record[key];

  return typeof value === "string"
    ? value
    : fallback;
}

function readComparisonMetadata(
  metadata: Record<string, unknown>,
  fallbacks: {
    title: string;
    leftLabel: string;
    rightLabel: string;
    question: string;
  },
): ComparisonMetadata | null {
  const comparison = metadata.comparison;

  if (!isRecord(comparison)) {
    return null;
  }

  const left = comparison.left;
  const right = comparison.right;

  if (
    typeof left !== "string" ||
    typeof right !== "string"
  ) {
    return null;
  }

  return {
    title: readString(
      comparison,
      "title",
      fallbacks.title,
    ),
    leftLabel: readString(
      comparison,
      "left_label",
      fallbacks.leftLabel,
    ),
    left,
    rightLabel: readString(
      comparison,
      "right_label",
      fallbacks.rightLabel,
    ),
    right,
    question: readString(
      comparison,
      "question",
      fallbacks.question,
    ),
  };
}

export function TutorCard({
  session,
  currentPrompt,
  answer,
  loading,
  errorMessage,
  onAnswerChange,
  onSubmitAnswer,
  onSubmitQuestion,
  onRequestHint,
  onRestart,
  onPracticeNext,
  adaptiveMessage,
}: TutorCardProps) {
  const { t } = useLanguage();
  const questionInputRef =
    useRef<HTMLInputElement | null>(null);
  const [showQuestionInput, setShowQuestionInput] =
    useState(false);
  const [question, setQuestion] = useState("");
  const comparison = readComparisonMetadata(
    session.metadata,
    {
      title: t("tutor.comparison"),
      leftLabel: t("tutor.comparisonLeft"),
      rightLabel: t("tutor.comparisonRight"),
      question: t("tutor.comparisonQuestion"),
    },
  );

  function handleQuestionSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const { state: nextState, submittedQuestion } =
      submitQuestionMode({
        questionMode: showQuestionInput,
        questionText: question,
      });

    if (!submittedQuestion) {
      return;
    }

    onSubmitQuestion(submittedQuestion);
    setQuestion(nextState.questionText);
    setShowQuestionInput(nextState.questionMode);
  }

  function keepQuestionKeysInField(
    event: KeyboardEvent<HTMLInputElement>,
  ) {
    event.stopPropagation();
  }

  useEffect(() => {
    if (!showQuestionInput) {
      return;
    }

    const mathFields = document.querySelectorAll(
      "math-field",
    );

    mathFields.forEach((field) => {
      if (field instanceof HTMLElement) {
        field.blur();
      }
    });

    questionInputRef.current?.focus();
  }, [showQuestionInput]);

  return (
    <article className="tutor-card">
      <section className="problem-context-card">
        <p className="eyebrow">{t("tutor.problem")}</p>
        <h1>{session.problem_title}</h1>
        <MathContent text={session.problem_statement} />
      </section>

      <ProgressBar
        completed={session.completed}
        currentStep={session.current_step}
        totalSteps={session.total_steps}
      />

      {adaptiveMessage ? (
        <section className="adaptive-message">
          <p className="eyebrow">{t("adaptive.eyebrow")}</p>
          <p>{adaptiveMessage}</p>
        </section>
      ) : null}

      {session.completed ? (
        <section className="completion-card">
          <p className="eyebrow">{t("tutor.completeEyebrow")}</p>
          <h1>{t("tutor.completeTitle")}</h1>
          <MathContent text={session.feedback} />
          <button
            disabled={loading}
            onClick={onRestart}
            type="button"
          >
            {t("tutor.startAgain")}
          </button>
          {onPracticeNext ? (
            <button
              disabled={loading}
              onClick={onPracticeNext}
              type="button"
            >
              {t("tutor.practiceNext")}
            </button>
          ) : null}
        </section>
      ) : (
        <>
          <section className="prompt-card">
            <p className="eyebrow">
              {t("tutor.currentStep")}
            </p>
            <MathContent
              className="prompt-content"
              text={currentPrompt}
            />
          </section>

          {comparison ? (
            <section className="comparison-card">
              <p className="eyebrow">
                {comparison.title}
              </p>
              <div className="comparison-grid">
                <div>
                  <h2>
                    {comparison.leftLabel}
                  </h2>
                  <MathContent
                    className="comparison-expression"
                    forceMath
                    text={comparison.left}
                  />
                </div>
                <div>
                  <h2>
                    {comparison.rightLabel}
                  </h2>
                  <MathContent
                    className="comparison-expression"
                    forceMath
                    text={comparison.right}
                  />
                </div>
              </div>
              <MathContent text={comparison.question} />
            </section>
          ) : null}

          <AnswerInput
            disabled={
              !isAnswerEditorEnabled({
                loading,
                questionMode: showQuestionInput,
              })
            }
            expectedInputType={
              session.expected_input_type
            }
            onChange={onAnswerChange}
            onSubmit={onSubmitAnswer}
            value={answer}
          />

          <div className="action-row">
            <button
              className="secondary-button"
              disabled={
                loading ||
                !session.hint_available
              }
              onClick={onRequestHint}
              type="button"
            >
              {t("tutor.hint")}
            </button>
            <button
              className="secondary-button"
              disabled={loading}
              onClick={() =>
                setShowQuestionInput((isVisible) =>
                  toggleQuestionMode({
                    questionMode: isVisible,
                    questionText: question,
                  }).questionMode,
                )
              }
              type="button"
            >
              {t("tutor.ask")}
            </button>
          </div>

          {showQuestionInput ? (
            <form
              className="question-form"
              onSubmit={handleQuestionSubmit}
            >
              <label htmlFor="concept-question">
                {t("tutor.askLabel")}
              </label>
              <div className="question-row">
                <input
                  autoComplete="off"
                  autoCorrect="off"
                  disabled={loading}
                  id="concept-question"
                  inputMode="text"
                  onChange={(event) =>
                    setQuestion(
                      readQuestionFieldValue(
                        event.target.value,
                      ),
                    )
                  }
                  onKeyDown={keepQuestionKeysInField}
                  onKeyUp={keepQuestionKeysInField}
                  placeholder={t("tutor.askPlaceholder")}
                  ref={questionInputRef}
                  spellCheck={false}
                  type="text"
                  value={question}
                />
                <button
                  disabled={
                    loading ||
                    prepareQuestionForSubmit(
                      question,
                    ).length === 0
                  }
                  type="submit"
                >
                  {t("tutor.sendQuestion")}
                </button>
              </div>
            </form>
          ) : null}
        </>
      )}

      <FeedbackPanel
        errorMessage={errorMessage}
        feedback={session.feedback}
        status={session.status}
        suggestion={session.suggestion}
      />
    </article>
  );
}
