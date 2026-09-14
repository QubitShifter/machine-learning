"use client";

import { useLanguage } from "@/components/LanguageProvider";
import type { AnswerEditorProps } from "@/components/answer-input/types";

interface PlaceholderAnswerInputProps
  extends AnswerEditorProps {
  title?: string;
  description?: string;
}

export function PlaceholderAnswerInput({
  expectedInputType,
  title,
  description,
}: PlaceholderAnswerInputProps) {
  const { t } = useLanguage();

  return (
    <section className="answer-form placeholder-input">
      <p className="placeholder-title">
        {title ?? t("tutor.placeholderTitle")}
      </p>
      <p>
        {description ??
          t("tutor.placeholderBody", {
            type: expectedInputType,
          })}
      </p>
    </section>
  );
}
