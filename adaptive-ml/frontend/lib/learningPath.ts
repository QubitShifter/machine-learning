import type {
  CatalogDomain,
  CatalogResponse,
  CatalogSubject,
  CatalogTopic,
  ProblemDetail,
  ProblemSummary,
} from "@/types/tutor";

export const HOME_HREF = "/";
export const LEARN_HREF = "/#learn";
export const PROGRESS_HREF = "/?view=progress";
export const LOGIN_HREF = "/login";
export const AUTH_PLACEHOLDER_MESSAGE =
  "Authentication is not implemented yet.";

export interface LearningPathSelection {
  subject: string;
  domain: string;
  topic: string;
  problemId: string;
}

export function createEmptyLearningPath(): LearningPathSelection {
  return {
    subject: "",
    domain: "",
    topic: "",
    problemId: "",
  };
}

export function isProgressView(
  search: string | URLSearchParams | null,
) {
  if (!search) {
    return false;
  }

  const params =
    typeof search === "string"
      ? new URLSearchParams(
          search.startsWith("?")
            ? search.slice(1)
            : search,
        )
      : search;

  return params.get("view") === "progress";
}

export function catalogSubjects(
  catalog: CatalogResponse | null | undefined,
) {
  return catalog?.subjects ?? [];
}

export function findSubject(
  catalog: CatalogResponse | null | undefined,
  subjectId: string,
) {
  return (
    catalogSubjects(catalog).find(
      (subject) => subject.id === subjectId,
    ) ?? null
  );
}

export function isRunnableSubject(
  subject: CatalogSubject | null | undefined,
) {
  return (subject?.available_problem_count ?? 0) > 0;
}

export function isRunnableDomain(
  domain: CatalogDomain | null | undefined,
) {
  return (domain?.available_problem_count ?? 0) > 0;
}

export function firstRunnableSubject(
  catalog: CatalogResponse | null | undefined,
) {
  return (
    catalogSubjects(catalog).find(isRunnableSubject) ??
    null
  );
}

export function domainsForSubject(
  catalog: CatalogResponse | null | undefined,
  subjectId: string,
) {
  return findSubject(catalog, subjectId)?.domains ?? [];
}

export function runnableDomains(
  domains: CatalogDomain[],
) {
  return domains.filter(isRunnableDomain);
}

export function comingSoonDomains(
  domains: CatalogDomain[],
) {
  return domains.filter(
    (domain) => !isRunnableDomain(domain),
  );
}

export function findDomain(
  catalog: CatalogResponse | null | undefined,
  subjectId: string,
  domainId: string,
) {
  return (
    domainsForSubject(catalog, subjectId).find(
      (domain) => domain.id === domainId,
    ) ?? null
  );
}

export function topicsForDomain(
  catalog: CatalogResponse | null | undefined,
  subjectId: string,
  domainId: string,
) {
  if (!domainId) {
    return [];
  }

  return findDomain(catalog, subjectId, domainId)
    ?.topics ?? [];
}

export function findTopic(
  catalog: CatalogResponse | null | undefined,
  subjectId: string,
  domainId: string,
  topicId: string,
) {
  return (
    topicsForDomain(
      catalog,
      subjectId,
      domainId,
    ).find((topic) => topic.id === topicId) ?? null
  );
}

export function problemsForTopic(
  problems: ProblemSummary[],
  selection: LearningPathSelection,
) {
  if (
    !selection.subject ||
    !selection.domain ||
    !selection.topic
  ) {
    return [];
  }

  return problems.filter(
    (problem) =>
      problem.subject === selection.subject &&
      problem.domain === selection.domain &&
      problem.topic === selection.topic,
  );
}

export function selectSubject(
  subjectId: string,
): LearningPathSelection {
  return {
    subject: subjectId,
    domain: "",
    topic: "",
    problemId: "",
  };
}

export function selectDomain(
  selection: LearningPathSelection,
  domainId: string,
): LearningPathSelection {
  return {
    ...selection,
    domain: domainId,
    topic: "",
    problemId: "",
  };
}

export function selectTopic(
  selection: LearningPathSelection,
  topicId: string,
): LearningPathSelection {
  return {
    ...selection,
    topic: topicId,
    problemId: "",
  };
}

export function selectProblem(
  selection: LearningPathSelection,
  problemId: string,
): LearningPathSelection {
  return {
    ...selection,
    problemId,
  };
}

export function canStartSelectedProblem(
  selection: LearningPathSelection,
  problem: ProblemDetail | null | undefined,
) {
  return Boolean(
    selection.problemId &&
      problem &&
      problem.problem_id === selection.problemId,
  );
}

export function subjectCardDescription(
  subject: CatalogSubject,
) {
  const names = subject.domains
    .filter((domain) => domain.id !== "primary_school")
    .map((domain) => domain.name)
    .slice(0, 4);

  return names.join(" • ");
}

export function findPrimarySchoolDomain(
  catalog: CatalogResponse | null | undefined,
) {
  return findDomain(
    catalog,
    "mathematics",
    "primary_school",
  );
}

export function selectMathematicsEntry(
  catalog: CatalogResponse | null | undefined,
) {
  const mathematics = findSubject(
    catalog,
    "mathematics",
  );

  if (!mathematics) {
    return null;
  }

  return selectSubject(mathematics.id);
}

export function selectPrimarySchoolEntry(
  catalog: CatalogResponse | null | undefined,
) {
  const mathematics = findSubject(
    catalog,
    "mathematics",
  );
  const primarySchool = findPrimarySchoolDomain(catalog);

  if (!mathematics || !primarySchool) {
    return null;
  }

  return selectDomain(
    selectSubject(mathematics.id),
    primarySchool.id,
  );
}

export interface LandingEntry {
  key: string;
  title: string;
  eyebrow: string;
  description: string;
  ctaLabel: string;
  runnable: boolean;
  selection: LearningPathSelection;
}

export function landingEntries(
  catalog: CatalogResponse | null | undefined,
): LandingEntry[] {
  const mathematics = findSubject(
    catalog,
    "mathematics",
  );
  const physics = findSubject(catalog, "physics");
  const primarySchool = findPrimarySchoolDomain(catalog);
  const entries: LandingEntry[] = [];

  if (mathematics) {
    const selection = selectMathematicsEntry(catalog);

    if (selection) {
      entries.push({
        key: mathematics.id,
        title: mathematics.name,
        eyebrow: mathematics.name,
        description:
          subjectCardDescription(mathematics) ||
          "Available catalog topics",
        ctaLabel: "Explore Mathematics",
        runnable: isRunnableSubject(mathematics),
        selection,
      });
    }
  }

  if (mathematics && primarySchool) {
    const selection = selectPrimarySchoolEntry(catalog);

    if (selection) {
      const topicNames = primarySchool.topics
        .map((topic) => topic.name)
        .slice(0, 3)
        .join(" • ");

      entries.push({
        key: primarySchool.id,
        title: primarySchool.name,
        eyebrow: mathematics.name,
        description:
          topicNames || "Word problems and early reasoning",
        ctaLabel: "Explore Primary School",
        runnable: isRunnableDomain(primarySchool),
        selection,
      });
    }
  }

  if (physics) {
    entries.push({
      key: physics.id,
      title: physics.name,
      eyebrow: physics.name,
      description:
        subjectCardDescription(physics) ||
        "Curriculum in preparation",
      ctaLabel: "Explore Physics",
      runnable: isRunnableSubject(physics),
      selection: selectSubject(physics.id),
    });
  }

  return entries;
}

export function topicSupportsGeneration(
  topic: CatalogTopic | null | undefined,
) {
  return Boolean(topic?.generation_available);
}
