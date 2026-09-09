import type { InputType } from "@/types/tutor";

export interface AnswerEditorProps {
  value: string;
  expectedInputType: InputType;
  disabled: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}
