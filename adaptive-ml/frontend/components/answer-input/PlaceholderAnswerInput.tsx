import type { AnswerEditorProps } from "@/components/answer-input/types";

interface PlaceholderAnswerInputProps
  extends AnswerEditorProps {
  title?: string;
  description?: string;
}

export function PlaceholderAnswerInput({
  expectedInputType,
  title = "Input editor coming later",
  description,
}: PlaceholderAnswerInputProps) {
  return (
    <section className="answer-form placeholder-input">
      <p className="placeholder-title">
        {title}
      </p>
      <p>
        {description ??
          `MAT-PAL knows this step expects ${expectedInputType} input, ` +
            "but that editor is not implemented yet."}
      </p>
    </section>
  );
}
