import type { AnswerEditorProps } from "@/components/answer-input/types";

interface UnitsParts {
  value: string;
  unit: string;
}

function splitUnitsAnswer(answer: string): UnitsParts {
  const trimmed = answer.trim();

  if (!trimmed) {
    return {
      value: "",
      unit: "",
    };
  }

  const [value, ...unitParts] = trimmed.split(/\s+/);

  return {
    value,
    unit: unitParts.join(" "),
  };
}

function joinUnitsAnswer({
  value,
  unit,
}: UnitsParts) {
  return [value.trim(), unit.trim()]
    .filter(Boolean)
    .join(" ");
}

export function UnitsAnswerInput({
  value,
  expectedInputType,
  disabled,
  onChange,
  onSubmit,
}: AnswerEditorProps) {
  const parts = splitUnitsAnswer(value);
  const canSubmit = Boolean(
    parts.value.trim() && parts.unit.trim(),
  );

  return (
    <form
      className="answer-form"
      onSubmit={(event) => {
        event.preventDefault();

        if (!disabled && canSubmit) {
          onSubmit();
        }
      }}
    >
      <p className="answer-label">Your answer</p>
      <div className="units-answer-row">
        <label>
          Value
          <input
            disabled={disabled}
            inputMode="decimal"
            onChange={(event) =>
              onChange(
                joinUnitsAnswer({
                  value: event.target.value,
                  unit: parts.unit,
                }),
              )
            }
            placeholder="9.81"
            type="text"
            value={parts.value}
          />
        </label>

        <label>
          Unit
          <input
            disabled={disabled}
            onChange={(event) =>
              onChange(
                joinUnitsAnswer({
                  value: parts.value,
                  unit: event.target.value,
                }),
              )
            }
            placeholder="m/s^2"
            type="text"
            value={parts.unit}
          />
        </label>

        <button
          disabled={disabled || !canSubmit}
          type="submit"
        >
          Submit Answer
        </button>
      </div>
      <p className="input-type-note">
        Expected input: {expectedInputType}. Enter a
        numerical value with its physical unit.
      </p>
    </form>
  );
}
