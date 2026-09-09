import type { AnswerEditorProps } from "@/components/answer-input/types";

export function PlaceholderAnswerInput({
  expectedInputType,
}: AnswerEditorProps) {
  return (
    <section className="answer-form placeholder-input">
      <p className="placeholder-title">
        Input editor coming later
      </p>
      <p>
        MAT-PAL knows this step expects{" "}
        <strong>{expectedInputType}</strong> input, but
        that editor is not implemented in Phase 1.
      </p>
    </section>
  );
}
