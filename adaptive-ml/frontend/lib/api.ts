import type {
  AdaptiveRecommendation,
  AdaptiveRecommendationRequest,
  AnswerRequest,
  CatalogResponse,
  GenerateProblemRequest,
  ProblemDetail,
  ProblemSummary,
  StartSessionRequest,
  TutorSession,
} from "@/types/tutor";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_MAT_PAL_API_URL ??
  "http://localhost:8000";

async function requestJson<TResponse>(
  path: string,
  options?: RequestInit,
): Promise<TResponse> {
  const response = await fetch(
    `${API_BASE_URL}${path}`,
    {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    },
  );

  if (!response.ok) {
    const detail = await response
      .json()
      .catch(() => null);

    throw new Error(
      detail?.detail ??
        `MAT-PAL API request failed with ${response.status}`,
    );
  }

  return response.json();
}

export function getCatalog(): Promise<CatalogResponse> {
  return requestJson<CatalogResponse>("/catalog");
}

export function listProblems(): Promise<ProblemSummary[]> {
  return requestJson<ProblemSummary[]>("/problems");
}

export function getProblem(
  problemId: string,
): Promise<ProblemDetail> {
  return requestJson<ProblemDetail>(
    `/problems/${problemId}`,
  );
}

export function generateProblem(
  request: GenerateProblemRequest,
): Promise<ProblemDetail> {
  return requestJson<ProblemDetail>(
    "/problems/generate",
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}

export function getAdaptiveRecommendation(
  request: AdaptiveRecommendationRequest,
): Promise<AdaptiveRecommendation> {
  return requestJson<AdaptiveRecommendation>(
    "/adaptive/recommendation",
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}

export function startSession(
  request: StartSessionRequest,
): Promise<TutorSession> {
  return requestJson<TutorSession>(
    "/sessions/start",
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}

export function getSession(
  sessionId: string,
): Promise<TutorSession> {
  return requestJson<TutorSession>(
    `/sessions/${sessionId}`,
  );
}

export function submitAnswer(
  sessionId: string,
  request: AnswerRequest,
): Promise<TutorSession> {
  return requestJson<TutorSession>(
    `/sessions/${sessionId}/answer`,
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}

export function requestHint(
  sessionId: string,
): Promise<TutorSession> {
  return requestJson<TutorSession>(
    `/sessions/${sessionId}/hint`,
    {
      method: "POST",
    },
  );
}
