import { AnswerInput } from "@/components/AnswerInput";
import { FeedbackPanel } from "@/components/FeedbackPanel";
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
  onRequestHint: () => void;
  onRestart: () => void;
}

export function TutorCard({
  session,
  currentPrompt,
  answer,
  loading,
  errorMessage,
  onAnswerChange,
  onSubmitAnswer,
  onRequestHint,
  onRestart,
}: TutorCardProps) {
  return (
    <article className="tutor-card">
      <ProgressBar
        completed={session.completed}
        currentStep={session.current_step}
        totalSteps={session.total_steps}
      />

      {session.completed ? (
        <section className="completion-card">
          <p className="eyebrow">Session complete</p>
          <h1>Great work. You finished this problem.</h1>
          <p>{session.feedback}</p>
          <button
            disabled={loading}
            onClick={onRestart}
            type="button"
          >
            Start Again
          </button>
        </section>
      ) : (
        <>
          <section className="prompt-card">
            <p className="eyebrow">
              Problem {session.problem_id}
            </p>
            <h1>{currentPrompt}</h1>
          </section>

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
          </div>
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
