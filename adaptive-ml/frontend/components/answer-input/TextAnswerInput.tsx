"use client";

import type { HTMLAttributes } from "react";

import { useLanguage } from "@/components/LanguageProvider";
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
  const { t } = useLanguage();

  return (
    <form
      className="answer-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <label htmlFor="answer">
        {t("tutor.yourAnswer")}
      </label>
      <div className="answer-row">
        <input
          disabled={disabled}
          id="answer"
          inputMode={inputMode}
          onChange={(event) =>
            onChange(event.target.value)
          }
          placeholder={t("tutor.placeholderAnswer", {
            type: expectedInputType,
          })}
          type="text"
          value={value}
        />
        <button
          disabled={disabled || !value.trim()}
          type="submit"
        >
          {t("tutor.submit")}
        </button>
      </div>
      <p className="input-type-note">
        {t("tutor.expectedInput", { type: expectedInputType })}
      </p>
    </form>
  );
}
