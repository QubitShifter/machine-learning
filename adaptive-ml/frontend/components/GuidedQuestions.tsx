"use client";

import { useLanguage } from "@/components/LanguageProvider";
import {
  shouldRenderGuidedQuestions,
  visibleGuidedQuestions,
} from "@/components/guidedQuestions";
import type { SuggestedQuestion } from "@/types/tutor";

interface GuidedQuestionsProps {
  questions: SuggestedQuestion[] | undefined;
  disabled?: boolean;
  onSelect: (questionId: string) => void;
}

export function GuidedQuestions({
  questions,
  disabled = false,
  onSelect,
}: GuidedQuestionsProps) {
  const { t } = useLanguage();
  const visible = visibleGuidedQuestions(questions);

  if (!shouldRenderGuidedQuestions(visible)) {
    return null;
  }

  return (
    <section
      aria-labelledby="guided-questions-heading"
      className="guided-questions"
    >
      <h2
        className="guided-questions-heading"
        id="guided-questions-heading"
      >
        {t("tutor.guidedHeading")}
      </h2>
      <div className="guided-question-list">
        {visible.map((question) => (
          <button
            aria-label={question.label}
            className="guided-question-button"
            disabled={disabled}
            key={question.question_id}
            onClick={() => onSelect(question.question_id)}
            type="button"
          >
            {question.label}
          </button>
        ))}
      </div>
    </section>
  );
}
