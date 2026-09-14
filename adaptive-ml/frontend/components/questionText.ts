export function readQuestionFieldValue(
  value: string,
): string {
  return value;
}

export function prepareQuestionForSubmit(
  value: string,
): string {
  return value.trim();
}

export type QuestionInteractionState = {
  questionMode: boolean;
  questionText: string;
};

export const INITIAL_QUESTION_INTERACTION: QuestionInteractionState =
  {
    questionMode: false,
    questionText: "",
  };

export function isAnswerEditorEnabled(options: {
  questionMode: boolean;
  loading: boolean;
}): boolean {
  return !options.questionMode && !options.loading;
}

export function openQuestionMode(
  state: QuestionInteractionState,
): QuestionInteractionState {
  return {
    ...state,
    questionMode: true,
  };
}

export function closeQuestionMode(
  state: QuestionInteractionState,
): QuestionInteractionState {
  return {
    ...state,
    questionMode: false,
  };
}

export function toggleQuestionMode(
  state: QuestionInteractionState,
): QuestionInteractionState {
  return {
    ...state,
    questionMode: !state.questionMode,
  };
}

export function submitQuestionMode(
  state: QuestionInteractionState,
): {
  state: QuestionInteractionState;
  submittedQuestion: string | null;
} {
  const submittedQuestion = prepareQuestionForSubmit(
    state.questionText,
  );

  if (!submittedQuestion) {
    return {
      state,
      submittedQuestion: null,
    };
  }

  return {
    state: {
      questionMode: false,
      questionText: "",
    },
    submittedQuestion,
  };
}
