import { MathAnswerInput } from "@/components/answer-input/MathAnswerInput";
import { MatrixAnswerInput } from "@/components/answer-input/MatrixAnswerInput";
import { PlaceholderAnswerInput } from "@/components/answer-input/PlaceholderAnswerInput";
import { TextAnswerInput } from "@/components/answer-input/TextAnswerInput";
import type { AnswerEditorProps } from "@/components/answer-input/types";
import { UnitsAnswerInput } from "@/components/answer-input/UnitsAnswerInput";
import { VectorAnswerInput } from "@/components/answer-input/VectorAnswerInput";

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
      return (
        <PlaceholderAnswerInput {...props} />
      );

    case "units":
      return <UnitsAnswerInput {...props} />;

    case "vector":
      return <VectorAnswerInput {...props} />;

    case "matrix":
      return <MatrixAnswerInput {...props} />;

    default:
      return (
        <TextAnswerInput
          {...props}
          inputMode="text"
        />
      );
  }
}
