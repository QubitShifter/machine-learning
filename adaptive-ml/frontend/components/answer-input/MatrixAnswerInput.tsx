"use client";

import { PlaceholderAnswerInput } from "@/components/answer-input/PlaceholderAnswerInput";
import { useLanguage } from "@/components/LanguageProvider";
import type { AnswerEditorProps } from "@/components/answer-input/types";

export function MatrixAnswerInput(
  props: AnswerEditorProps,
) {
  const { t } = useLanguage();

  return (
    <PlaceholderAnswerInput
      {...props}
      description={t("tutor.matrixBody")}
      title={t("tutor.matrixTitle")}
    />
  );
}
