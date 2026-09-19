export function isNumericAnswerField(
  expectedInputType: string,
): boolean {
  return expectedInputType === "number";
}

export function numericAnswerNoteKey(
  expectedInputType: string,
): "tutor.numberFieldHint" | "tutor.expectedInput" {
  if (isNumericAnswerField(expectedInputType)) {
    return "tutor.numberFieldHint";
  }

  return "tutor.expectedInput";
}

export function numericAnswerPlaceholderKey(
  expectedInputType: string,
): "tutor.placeholderNumber" | "tutor.placeholderAnswer" {
  if (isNumericAnswerField(expectedInputType)) {
    return "tutor.placeholderNumber";
  }

  return "tutor.placeholderAnswer";
}
