import { MathAnswerInput } from "@/components/answer-input/MathAnswerInput";
import { PlaceholderAnswerInput } from "@/components/answer-input/PlaceholderAnswerInput";
import { TextAnswerInput } from "@/components/answer-input/TextAnswerInput";
import type { AnswerEditorProps } from "@/components/answer-input/types";

export function AnswerInput(
  props: AnswerEditorProps,
) {
  switch (props.expectedInputType) {
    case "number":
      return (
        <TextAnswerInput
          {...props}
          inputMode="decimal"
        />
      );

    case "text":
      return (
        <TextAnswerInput
          {...props}
          inputMode="text"
        />
      );

    case "math":
    case "latex":
      return <MathAnswerInput {...props} />;

    case "multiple_choice":
    case "vector":
    case "matrix":
    case "units":
      return (
        <PlaceholderAnswerInput {...props} />
      );

    default:
      return (
        <TextAnswerInput
          {...props}
          inputMode="text"
        />
      );
  }
}
