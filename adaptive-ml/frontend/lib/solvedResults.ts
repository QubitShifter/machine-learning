export interface SolvedStepResult {
  stepNumber: number;
  resultLatex: string;
}

export interface SolvedStepDisplay {
  history: SolvedStepResult[];
  finalResultLatex: string | null;
  showHistoryBeforeCurrentStep: boolean;
  showSolutionSummary: boolean;
}

function isRecord(
  value: unknown,
): value is Record<string, unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

function readLatex(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const text = value.trim();
  return text.length > 0 ? text : null;
}

function sameLatex(left: string, right: string) {
  return left.trim() === right.trim();
}

export function readSolvedResults(
  metadata: Record<string, unknown> | null | undefined,
): SolvedStepResult[] {
  const raw = metadata?.solved_results;
  if (!Array.isArray(raw)) {
    return [];
  }

  const results: SolvedStepResult[] = [];
  for (const item of raw) {
    if (!isRecord(item)) {
      continue;
    }

    const resultLatex = readLatex(item.result_latex);
    const stepNumber = item.step_number;
    if (
      resultLatex === null ||
      typeof stepNumber !== "number"
    ) {
      continue;
    }

    results.push({
      stepNumber,
      resultLatex,
    });
  }

  return results;
}

export function readCompletedResultLatex(
  metadata: Record<string, unknown> | null | undefined,
): string | null {
  return readLatex(metadata?.completed_result_latex);
}

export function readFinalResultLatex(
  metadata: Record<string, unknown> | null | undefined,
): string | null {
  const explicit = readLatex(metadata?.final_result_latex);
  if (explicit) {
    return explicit;
  }

  const solved = readSolvedResults(metadata);
  if (solved.length === 0) {
    return null;
  }

  return solved[solved.length - 1].resultLatex;
}

export function presentSolvedStepDisplay(input: {
  status: string;
  completed: boolean;
  metadata: Record<string, unknown> | null | undefined;
}): SolvedStepDisplay {
  const solved = readSolvedResults(input.metadata);
  const finalResultLatex = input.completed
    ? readFinalResultLatex(input.metadata)
    : null;
  const history =
    input.completed &&
    finalResultLatex &&
    solved.length > 0 &&
    sameLatex(
      solved[solved.length - 1].resultLatex,
      finalResultLatex,
    )
      ? solved.slice(0, -1)
      : solved;

  return {
    history,
    finalResultLatex,
    showHistoryBeforeCurrentStep:
      !input.completed && history.length > 0,
    showSolutionSummary: input.completed && history.length > 0,
  };
}
