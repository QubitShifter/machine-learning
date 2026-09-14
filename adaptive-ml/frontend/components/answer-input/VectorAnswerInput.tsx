"use client";

import { PlaceholderAnswerInput } from "@/components/answer-input/PlaceholderAnswerInput";
import { useLanguage } from "@/components/LanguageProvider";
import type { AnswerEditorProps } from "@/components/answer-input/types";

export function VectorAnswerInput(
  props: AnswerEditorProps,
) {
  const { t } = useLanguage();

  return (
    <PlaceholderAnswerInput
      {...props}
      description={t("tutor.vectorBody")}
      title={t("tutor.vectorTitle")}
    />
  );
}
