import type {
  CatalogResponse,
  ProblemDetail,
  ProblemSummary,
} from "../types/tutor";
import {
  AUTH_PLACEHOLDER_MESSAGE,
  HOME_HREF,
  LEARN_HREF,
  LOGIN_HREF,
  PROGRESS_HREF,
  canStartSelectedProblem,
  catalogSubjects,
  comingSoonDomains,
  createEmptyLearningPath,
  domainsForSubject,
  firstRunnableSubject,
  isProgressView,
  landingEntries,
  selectMathematicsEntry,
  selectPrimarySchoolEntry,
  isRunnableDomain,
  isRunnableSubject,
  problemsForTopic,
  runnableDomains,
  selectDomain,
  selectProblem,
  selectSubject,
  selectTopic,
  topicsForDomain,
} from "./learningPath";

function assert(
  condition: boolean,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

const catalog: CatalogResponse = {
  subjects: [
    {
      id: "mathematics",
      name: "Mathematics",
      available_problem_count: 2,
      domains: [
        {
          id: "primary_school",
          name: "Primary School",
          available_problem_count: 1,
          topics: [
            {
              id: "word_problems",
              name: "Word Problems",
              available_problem_count: 1,
              problem_ids: ["hazelnuts"],
              generation_available: false,
              supported_difficulties: [],
            },
          ],
        },
        {
          id: "ode",
          name: "ODE",
          available_problem_count: 2,
          topics: [
            {
              id: "separable_equations",
              name: "Separable Equations",
              available_problem_count: 1,
              problem_ids: ["separable_1"],
              generation_available: false,
              supported_difficulties: [],
            },
            {
              id: "first_order_linear",
              name: "First-Order Linear ODE",
              available_problem_count: 1,
              problem_ids: ["linear_1"],
              generation_available: false,
              supported_difficulties: [],
            },
          ],
        },
        {
          id: "calculus",
          name: "Calculus",
          available_problem_count: 0,
          topics: [],
        },
      ],
    },
    {
      id: "physics",
      name: "Physics",
      available_problem_count: 0,
      domains: [
        {
          id: "classical_mechanics",
          name: "Classical Mechanics",
          available_problem_count: 0,
          topics: [],
        },
      ],
    },
  ],
};

const problems: ProblemSummary[] = [
  {
    problem_id: "separable_1",
    title: "Separable Equation",
    subject: "mathematics",
    domain: "ode",
    topic: "separable_equations",
    problem_type: "ode",
    available: true,
    grade: null,
    total_steps: 6,
    expected_input_type: "math",
    generated: false,
    generation_available: false,
    supported_difficulties: [],
  },
  {
    problem_id: "linear_1",
    title: "First-Order Linear ODE",
    subject: "mathematics",
    domain: "ode",
    topic: "first_order_linear",
    problem_type: "ode",
    available: true,
    grade: null,
    total_steps: 5,
    expected_input_type: "math",
    generated: false,
    generation_available: false,
    supported_difficulties: [],
  },
  {
    problem_id: "hazelnuts",
    title: "Hazelnuts in Three Hollows",
    subject: "mathematics",
    domain: "primary_school",
    topic: "word_problems",
    problem_type: "word_problem",
    available: true,
    grade: 4,
    total_steps: 4,
    expected_input_type: "text",
    generated: false,
    generation_available: false,
    supported_difficulties: [],
  },
];

const emptyPath = createEmptyLearningPath();

assert(
  emptyPath.subject === "" &&
    emptyPath.domain === "" &&
    emptyPath.topic === "" &&
    emptyPath.problemId === "",
  "Initial learning path must select nothing",
);
assert(
  problemsForTopic(problems, emptyPath).length === 0,
  "No default problem may be implied from an empty path",
);
assert(
  canStartSelectedProblem(emptyPath, null) === false,
  "Start must stay disabled until a problem exists",
);

const afterMathematics = selectSubject("mathematics");

assert(
  afterMathematics.subject === "mathematics",
  "Subject selection must keep the chosen subject",
);
assert(
  afterMathematics.domain === "" &&
    afterMathematics.topic === "" &&
    afterMathematics.problemId === "",
  "Subject selection must not auto-select domain, topic, or problem",
);
assert(
  domainsForSubject(catalog, afterMathematics.subject)
    .map((domain) => domain.id)
    .join(",") === "primary_school,ode,calculus",
  "Domain options must come from the catalog subject",
);
assert(
  topicsForDomain(
    catalog,
    afterMathematics.subject,
    afterMathematics.domain,
  ).length === 0,
  "Topics must stay hidden until a domain is chosen",
);

const afterOde = selectDomain(afterMathematics, "ode");

assert(
  afterOde.topic === "" && afterOde.problemId === "",
  "Domain selection must not auto-select a topic or problem",
);
assert(
  topicsForDomain(
    catalog,
    afterOde.subject,
    afterOde.domain,
  ).map((topic) => topic.id).join(",") ===
    "separable_equations,first_order_linear",
  "Topic options must come from the selected catalog domain",
);
assert(
  problemsForTopic(problems, afterOde).length === 0,
  "Problems must stay hidden until a topic is chosen",
);

const afterTopic = selectTopic(
  afterOde,
  "separable_equations",
);
const topicProblems = problemsForTopic(
  problems,
  afterTopic,
);

assert(
  afterTopic.problemId === "",
  "Topic selection must not auto-select a problem",
);
assert(
  topicProblems.map((problem) => problem.problem_id)
    .join(",") === "separable_1",
  "Problem options must be filtered from the backend problem list",
);
assert(
  topicProblems.some(
    (problem) => problem.problem_id === "hazelnuts",
  ) === false,
  "Unrelated catalog problems must not appear after topic filtering",
);

const afterProblem = selectProblem(
  afterTopic,
  "separable_1",
);
const selectedProblem = {
  ...topicProblems[0],
  problem_text: "Solve the separable equation.",
  language: "en",
  skills: [],
  metadata: {},
} satisfies ProblemDetail;

assert(
  canStartSelectedProblem(
    afterProblem,
    selectedProblem,
  ) === true,
  "Start becomes enabled only after a matching problem exists",
);
assert(
  canStartSelectedProblem(afterTopic, selectedProblem) ===
    false,
  "Start stays disabled before a problem id is chosen",
);

const physics = catalog.subjects[1];
const calculus = catalog.subjects[0].domains[1];

assert(
  isRunnableSubject(physics) === false,
  "A subject with zero available problems is coming soon",
);
assert(
  firstRunnableSubject(catalog)?.id === "mathematics",
  "Only backend-available subjects are runnable",
);
assert(
  isRunnableDomain(calculus) === false,
  "A domain with zero available problems is coming soon",
);
assert(
  runnableDomains(catalog.subjects[0].domains).map(
    (domain) => domain.id,
  ).join(",") === "ode",
  "Runnable domains must come from backend availability",
);
assert(
  comingSoonDomains(catalog.subjects[0].domains).map(
    (domain) => domain.id,
  ).join(",") === "calculus",
  "Unavailable catalog domains must be marked coming soon",
);
assert(
  catalogSubjects(catalog).map((subject) => subject.id)
    .join(",") === "mathematics,physics",
  "Displayed subjects must remain backend-driven",
);

assert(
  isProgressView("?view=progress") === true,
  "Header Progress must resolve to the progress view",
);
assert(
  isProgressView(new URLSearchParams("view=progress")) ===
    true,
  "Progress view detection must accept URLSearchParams",
);
assert(
  isProgressView("") === false,
  "Home must not open Progress unless requested",
);
assert(
  PROGRESS_HREF === "/?view=progress",
  "Header Progress route must be /?view=progress",
);
assert(
  LEARN_HREF === "/#learn",
  "Header Learn route must target the learning-path area",
);
assert(
  LOGIN_HREF === "/login",
  "Login route must be /login",
);
assert(
  HOME_HREF === "/",
  "Brand route must remain /",
);

const mathematicsEntry = selectMathematicsEntry(catalog);
const primarySchoolEntry = selectPrimarySchoolEntry(catalog);
const cards = landingEntries(catalog);

assert(
  mathematicsEntry?.subject === "mathematics" &&
    mathematicsEntry.domain === "" &&
    mathematicsEntry.topic === "" &&
    mathematicsEntry.problemId === "",
  "Mathematics landing entry must select only Mathematics",
);
assert(
  primarySchoolEntry?.subject === "mathematics" &&
    primarySchoolEntry.domain === "primary_school" &&
    primarySchoolEntry.topic === "" &&
    primarySchoolEntry.problemId === "",
  "Primary School landing entry must select Mathematics and Primary School only",
);
assert(
  problemsForTopic(problems, primarySchoolEntry!).length ===
    0,
  "Primary School landing entry must not auto-select a problem",
);
assert(
  cards.map((entry) => entry.key).join(",") ===
    "mathematics,primary_school,physics",
  "Landing cards must be Mathematics, Primary School, and Physics",
);
assert(
  cards.find((entry) => entry.key === "physics")
    ?.runnable === false,
  "Physics with zero available problems remains non-runnable",
);
assert(
  cards.find((entry) => entry.key === "mathematics")
    ?.eyebrow === "Mathematics",
  "Mathematics card eyebrow must be Mathematics",
);
assert(
  cards.find((entry) => entry.key === "primary_school")
    ?.eyebrow === "Mathematics",
  "Primary School card eyebrow must be Mathematics, not Subject",
);
assert(
  cards.find((entry) => entry.key === "physics")
    ?.eyebrow === "Physics",
  "Physics card eyebrow must be Physics",
);
assert(
  AUTH_PLACEHOLDER_MESSAGE ===
    "Authentication is not implemented yet.",
  "Login must not pretend authentication exists",
);

console.log("learning_path tests passed");
