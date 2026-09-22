import type { GenerateProblemRequest } from "@/types/tutor";

export const LOGICAL_REASONING_TOPIC = "logical_reasoning";

export const LOGICAL_REASONING_FAMILIES = [
  "number_detective",
  "distribution_puzzles",
  "logic_detective",
] as const;

export type LogicalReasoningFamily =
  (typeof LOGICAL_REASONING_FAMILIES)[number];

export const AUTOMATIC_FAMILY = "";

const CLUE_SENTENCE_SPLIT = /(?<=[.!?])\s+(?=[A-ZА-ЯЁІЇЄҐ])/u;

export function isLogicalReasoningTopic(topicId: string) {
  return topicId === LOGICAL_REASONING_TOPIC;
}

export function isLogicalReasoningFamily(
  value: string | null | undefined,
): value is LogicalReasoningFamily {
  return (
    typeof value === "string" &&
    (LOGICAL_REASONING_FAMILIES as readonly string[]).includes(
      value,
    )
  );
}

export function isLogicalReasoningProblemId(problemId: string) {
  return problemId.startsWith("grade4_logical_reasoning");
}

export function familySelectionForTopic(
  topicId: string,
  currentFamily: string,
) {
  if (!isLogicalReasoningTopic(topicId)) {
    return AUTOMATIC_FAMILY;
  }

  return currentFamily;
}

export function buildGenerateProblemRequest(input: {
  subject: string;
  domain: string;
  topic: string;
  difficulty: number;
  language: "en" | "bg";
  family?: string | null;
}): GenerateProblemRequest {
  const request: GenerateProblemRequest = {
    subject: input.subject,
    domain: input.domain,
    topic: input.topic,
    difficulty: input.difficulty,
    language: input.language,
  };

  if (
    isLogicalReasoningTopic(input.topic) &&
    isLogicalReasoningFamily(input.family)
  ) {
    request.family = input.family;
  }

  return request;
}

export function formatLogicalReasoningStatement(text: string) {
  const trimmed = text.trim();

  if (!trimmed) {
    return text;
  }

  const parts = trimmed
    .split(CLUE_SENTENCE_SPLIT)
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length < 2) {
    return text;
  }

  return parts.join("\n");
}

export function exerciseStatementForDisplay(
  text: string,
  options: {
    topic?: string | null;
    problemId?: string | null;
  } = {},
) {
  if (
    isLogicalReasoningTopic(options.topic ?? "") ||
    isLogicalReasoningProblemId(options.problemId ?? "")
  ) {
    return formatLogicalReasoningStatement(text);
  }

  return text;
}

export function readGeneratedFamily(
  metadata: Record<string, unknown> | null | undefined,
) {
  const family = metadata?.family;

  return isLogicalReasoningFamily(
    typeof family === "string" ? family : null,
  )
    ? family
    : null;
}

export type CatalogPanelState = "loading" | "ready" | "error";

export function catalogPanelState(
  catalog: unknown,
  loading: boolean,
) {
  if (catalog) {
    return "ready" satisfies CatalogPanelState;
  }

  if (loading) {
    return "loading" satisfies CatalogPanelState;
  }

  return "error" satisfies CatalogPanelState;
}
