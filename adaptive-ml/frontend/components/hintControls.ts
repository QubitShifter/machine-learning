import type { TutorSession } from "@/types/tutor";

export function hintButtonDisabled(
  session: TutorSession,
  extraDisabled = false,
): boolean {
  if (extraDisabled) {
    return true;
  }
  if (session.metadata?.hint_exhausted === true) {
    return true;
  }
  return !session.hint_available;
}

export function hintButtonLabelKey(
  session: TutorSession,
): "tutor.hint" | "tutor.moreHelp" {
  const used = session.metadata?.hints_used_on_step;
  if (
    typeof used === "number" &&
    used >= 1 &&
    session.hint_available &&
    session.metadata?.hint_exhausted !== true
  ) {
    return "tutor.moreHelp";
  }
  return "tutor.hint";
}

export function feedbackPanelKey(session: TutorSession): string {
  const level = session.metadata?.hint_level;
  return [
    session.session_id,
    session.status,
    String(session.current_step),
    String(typeof level === "number" ? level : ""),
    session.feedback,
  ].join(":");
}

export function answerPreservedAfterHint(
  answerBefore: string,
  answerAfter: string,
): boolean {
  return answerBefore === answerAfter;
}
