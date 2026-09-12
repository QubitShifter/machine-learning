import type { FormEvent } from "react";
import { useState } from "react";

import { AnswerInput } from "@/components/answer-input/AnswerInput";
import { FeedbackPanel } from "@/components/FeedbackPanel";
import { MathContent } from "@/components/math/MathContent";
import { ProgressBar } from "@/components/ProgressBar";
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
      "Comparison",
    ),
    leftLabel: readString(
      comparison,
      "left_label",
      "Left-hand side",
    ),
    left,
    rightLabel: readString(
      comparison,
      "right_label",
      "Right-hand side",
    ),
    right,
    question: readString(
      comparison,
      "question",
      "Do they match?",
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
  const [showQuestionInput, setShowQuestionInput] =
    useState(false);
  const [question, setQuestion] = useState("");
  const comparison = readComparisonMetadata(
    session.metadata,
  );

  function handleQuestionSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) {
      return;
    }

    onSubmitQuestion(trimmedQuestion);
    setQuestion("");
  }

  return (
    <article className="tutor-card">
      <section className="problem-context-card">
        <p className="eyebrow">Problem</p>
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
          <p className="eyebrow">Adaptive recommendation</p>
          <p>{adaptiveMessage}</p>
        </section>
      ) : null}

      {session.completed ? (
        <section className="completion-card">
          <p className="eyebrow">Session complete</p>
          <h1>Great work. You finished this problem.</h1>
          <MathContent text={session.feedback} />
          <button
            disabled={loading}
            onClick={onRestart}
            type="button"
          >
            Start Again
          </button>
          {onPracticeNext ? (
            <button
              disabled={loading}
              onClick={onPracticeNext}
              type="button"
            >
              Practice Next
            </button>
          ) : null}
        </section>
      ) : (
        <>
          <section className="prompt-card">
            <p className="eyebrow">
              Current step
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
            disabled={loading}
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
              Hint
            </button>
            <button
              className="secondary-button"
              disabled={loading}
              onClick={() =>
                setShowQuestionInput(
                  (isVisible) => !isVisible,
                )
              }
              type="button"
            >
              Ask a question
            </button>
          </div>

          {showQuestionInput ? (
            <form
              className="question-form"
              onSubmit={handleQuestionSubmit}
            >
              <label htmlFor="concept-question">
                Ask about this step
              </label>
              <div className="question-row">
                <input
                  disabled={loading}
                  id="concept-question"
                  onChange={(event) =>
                    setQuestion(
                      event.target.value,
                    )
                  }
                  placeholder="Ask about this step..."
                  type="text"
                  value={question}
                />
                <button
                  disabled={
                    loading ||
                    question.trim().length === 0
                  }
                  type="submit"
                >
                  Send Question
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
