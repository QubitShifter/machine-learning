import { MathContent } from "@/components/math/MathContent";

interface FeedbackPanelProps {
  feedback: string;
  suggestion: string | null;
  status: string;
  errorMessage?: string | null;
}

export function FeedbackPanel({
  feedback,
  suggestion,
  status,
  errorMessage,
}: FeedbackPanelProps) {
  return (
    <section className="feedback-panel">
      <div className={`status-pill status-${status}`}>
        {status.replaceAll("_", " ")}
      </div>

      {errorMessage ? (
        <p className="error-message">{errorMessage}</p>
      ) : null}

      <div>
        <h2>Feedback</h2>
        <MathContent text={feedback} />
      </div>

      {suggestion ? (
        <div className="suggestion">
          <h2>Suggestion</h2>
          <MathContent text={suggestion} />
        </div>
      ) : null}
    </section>
  );
}
