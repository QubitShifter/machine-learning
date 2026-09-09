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
        <p>{feedback}</p>
      </div>

      {suggestion ? (
        <div className="suggestion">
          <h2>Suggestion</h2>
          <p>{suggestion}</p>
        </div>
      ) : null}
    </section>
  );
}
