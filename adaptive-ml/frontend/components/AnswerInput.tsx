import type { InputType } from "@/types/tutor";

interface AnswerInputProps {
  value: string;
  expectedInputType: InputType;
  disabled: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

function getInputMode(
  expectedInputType: InputType,
) {
  if (expectedInputType === "number") {
    return "decimal";
  }

  return "text";
}

export function AnswerInput({
  value,
  expectedInputType,
  disabled,
  onChange,
  onSubmit,
}: AnswerInputProps) {
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
          inputMode={getInputMode(
            expectedInputType,
          )}
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
