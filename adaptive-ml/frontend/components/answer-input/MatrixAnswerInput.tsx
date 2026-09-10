import { PlaceholderAnswerInput } from "@/components/answer-input/PlaceholderAnswerInput";
import type { AnswerEditorProps } from "@/components/answer-input/types";

export function MatrixAnswerInput(
  props: AnswerEditorProps,
) {
  return (
    <PlaceholderAnswerInput
      {...props}
      description={
        "A future matrix editor can capture rows and columns " +
        "and submit them through the shared answer payload."
      }
      title="Matrix input editor coming later"
    />
  );
}
