import { PlaceholderAnswerInput } from "@/components/answer-input/PlaceholderAnswerInput";
import type { AnswerEditorProps } from "@/components/answer-input/types";

export function VectorAnswerInput(
  props: AnswerEditorProps,
) {
  return (
    <PlaceholderAnswerInput
      {...props}
      description={
        "A future vector editor can capture ordered entries " +
        "and submit them through the shared answer payload."
      }
      title="Vector input editor coming later"
    />
  );
}
