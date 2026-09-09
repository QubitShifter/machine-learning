import type { HTMLAttributes } from "react";

import type { AnswerEditorProps } from "@/components/answer-input/types";

interface TextAnswerInputProps
  extends AnswerEditorProps {
  inputMode?: HTMLAttributes<HTMLInputElement>["inputMode"];
}

export function TextAnswerInput({
  value,
  expectedInputType,
  disabled,
  inputMode = "text",
  onChange,
  onSubmit,
}: TextAnswerInputProps) {
  return (
    <form
      className="answer-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <label htmlFor="answer">
        Your answer
      </label>
      <div className="answer-row">
        <input
          disabled={disabled}
          id="answer"
          inputMode={inputMode}
          onChange={(event) =>
            onChange(event.target.value)
          }
          placeholder={`Enter a ${expectedInputType} answer`}
          type="text"
          value={value}
        />
        <button
          disabled={disabled || !value.trim()}
          type="submit"
        >
          Submit Answer
        </button>
      </div>
      <p className="input-type-note">
        Expected input: {expectedInputType}
      </p>
    </form>
  );
}
