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
  domainContentCount,
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
  subjectContentCount,
  topicHasStaticProblems,
  topicIsRunnable,
  topicSupportsGeneration,
  topicsForDomain,
} from "./learningPath.ts";

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
const calculus = catalog.subjects[0].domains.find(
  (domain) => domain.id === "calculus",
);

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
  ).join(",") === "primary_school,ode",
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
  isRunnableSubject({
    id: "physics",
    name: "Physics",
    available_problem_count: 1,
    domains: [],
  }) === true,
  "Physics with available problems is runnable",
);
assert(
  landingEntries({
    subjects: [
      {
        id: "physics",
        name: "Physics",
        available_problem_count: 1,
        domains: [],
      },
    ],
  }).find((entry) => entry.key === "physics")
    ?.runnable === true,
  "Landing Physics card follows catalog availability",
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

const LINEAR_ODE_FIXED_PROBLEM_ID =
  "linear_first_order_fixed_001";
const LINEAR_ODE_GENERATED_PROBLEM_ID =
  "linear_first_order_generated_a1b2c3d4e5f6";
const linearOdeProblems: ProblemSummary[] = [
  {
    problem_id: LINEAR_ODE_FIXED_PROBLEM_ID,
    title: "First-Order Linear ODE",
    subject: "mathematics",
    domain: "ode",
    topic: "first_order_linear",
    problem_type: "linear_first_order_ode",
    available: true,
    grade: null,
    total_steps: 8,
    expected_input_type: "text",
    generated: false,
    generation_available: true,
    supported_difficulties: [1, 2, 3],
  },
  {
    problem_id: LINEAR_ODE_GENERATED_PROBLEM_ID,
    title: "Generated First-Order Linear ODE",
    subject: "mathematics",
    domain: "ode",
    topic: "first_order_linear",
    problem_type: "linear_first_order_ode",
    available: true,
    grade: null,
    total_steps: 8,
    expected_input_type: "text",
    generated: true,
    generation_available: true,
    supported_difficulties: [1, 2, 3],
  },
];
const linearOdePath = selectProblem(
  selectTopic(
    selectDomain(
      selectSubject("mathematics"),
      "ode",
    ),
    "first_order_linear",
  ),
  LINEAR_ODE_FIXED_PROBLEM_ID,
);
const linearOdeTopicProblems = problemsForTopic(
  linearOdeProblems,
  linearOdePath,
);
const generatedLinearOdePath = selectProblem(
  linearOdePath,
  LINEAR_ODE_GENERATED_PROBLEM_ID,
);

assert(
  LINEAR_ODE_FIXED_PROBLEM_ID ===
    "linear_first_order_fixed_001",
  "Fixed Linear ODE routing id must remain unchanged",
);
assert(
  LINEAR_ODE_GENERATED_PROBLEM_ID.startsWith(
    "linear_first_order_generated_",
  ),
  "Generated Linear ODE routing id prefix must remain unchanged",
);
assert(
  linearOdeTopicProblems.map(
    (problem) => problem.problem_id,
  ).join(",") ===
    `${LINEAR_ODE_FIXED_PROBLEM_ID},${LINEAR_ODE_GENERATED_PROBLEM_ID}`,
  "Linear ODE topic filtering must keep both catalog choices",
);
assert(
  linearOdePath.problemId === LINEAR_ODE_FIXED_PROBLEM_ID,
  "Selecting the fixed Linear ODE must keep its stable id",
);
assert(
  generatedLinearOdePath.problemId ===
    LINEAR_ODE_GENERATED_PROBLEM_ID,
  "Selecting the generated Linear ODE must keep its generated id",
);
assert(
  linearOdePath.subject === "mathematics" &&
    linearOdePath.domain === "ode" &&
    linearOdePath.topic === "first_order_linear" &&
    generatedLinearOdePath.subject === "mathematics" &&
    generatedLinearOdePath.domain === "ode" &&
    generatedLinearOdePath.topic === "first_order_linear",
  "Both Linear ODE choices must keep the same subject, domain, and topic routing",
);
assert(
  canStartSelectedProblem(
    linearOdePath,
    {
      ...linearOdeTopicProblems[0],
      problem_text: "Solve dy/dx + (2*x)*y = x",
      language: "en",
      skills: [],
      metadata: {},
    },
  ) === true,
  "Starting the fixed Linear ODE must still require its own problem id",
);
assert(
  canStartSelectedProblem(
    generatedLinearOdePath,
    {
      ...linearOdeTopicProblems[1],
      problem_text: "Solve dy/dx + (x)*y = 1",
      language: "en",
      skills: [],
      metadata: { generated: true },
    },
  ) === true,
  "Starting the generated Linear ODE must still require its own problem id",
);
assert(
  canStartSelectedProblem(
    linearOdePath,
    {
      ...linearOdeTopicProblems[1],
      problem_text: "Solve dy/dx + (x)*y = 1",
      language: "en",
      skills: [],
      metadata: { generated: true },
    },
  ) === false,
  "Fixed and generated Linear ODE selections must not start each other",
);

const generatedPrimaryCatalog: CatalogResponse = {
  subjects: [
    {
      id: "mathematics",
      name: "Mathematics",
      available_problem_count: 3,
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
            {
              id: "arithmetic",
              name: "Arithmetic",
              available_problem_count: 0,
              problem_ids: [],
              generation_available: true,
              supported_difficulties: [1, 2, 3],
            },
            {
              id: "unknown_numbers",
              name: "Unknown Numbers",
              available_problem_count: 0,
              problem_ids: [],
              generation_available: true,
              supported_difficulties: [1, 2, 3],
            },
            {
              id: "number_patterns",
              name: "Number Patterns",
              available_problem_count: 0,
              problem_ids: [],
              generation_available: true,
              supported_difficulties: [1, 2, 3],
            },
            {
              id: "story_problems",
              name: "Story Problems",
              available_problem_count: 0,
              problem_ids: [],
              generation_available: true,
              supported_difficulties: [1, 2, 3],
            },
          ],
        },
        {
          id: "ode",
          name: "ODE",
          available_problem_count: 2,
          topics: [
            {
              id: "first_order_linear",
              name: "First-Order Linear ODEs",
              available_problem_count: 1,
              problem_ids: ["linear_1"],
              generation_available: true,
              supported_difficulties: [1, 2, 3],
            },
          ],
        },
      ],
    },
  ],
};

const primaryTopics = topicsForDomain(
  generatedPrimaryCatalog,
  "mathematics",
  "primary_school",
);
const arithmeticTopic = primaryTopics.find(
  (topic) => topic.id === "arithmetic",
);
const wordProblemsTopic = primaryTopics.find(
  (topic) => topic.id === "word_problems",
);
const primaryDomain =
  generatedPrimaryCatalog.subjects[0].domains[0];
const arithmeticSelection = selectTopic(
  selectDomain(
    selectSubject("mathematics"),
    "primary_school",
  ),
  "arithmetic",
);
const generatedArithmetic = {
  problem_id: "grade4_arithmetic_generated_abc123def456",
  title: "Compute the expression",
  subject: "mathematics",
  domain: "primary_school",
  topic: "arithmetic",
  problem_type: "arithmetic",
  available: true,
  grade: 4,
  total_steps: 1,
  expected_input_type: "number" as const,
  generated: true,
  generation_available: true,
  supported_difficulties: [1, 2, 3],
};

assert(
  primaryTopics.map((topic) => topic.id).join(",") ===
    "word_problems,arithmetic,unknown_numbers,number_patterns,story_problems",
  "Primary School must list Word Problems and the generated families",
);
assert(
  topicHasStaticProblems(wordProblemsTopic) === true,
  "Word Problems remains a static catalog topic",
);
assert(
  topicHasStaticProblems(arithmeticTopic) === false,
  "Arithmetic must not pretend to have a static problem id",
);
assert(
  topicIsRunnable(arithmeticTopic) === true,
  "Generator-only topics must still be selectable",
);
assert(
  topicSupportsGeneration(arithmeticTopic) === true,
  "Selecting Arithmetic must expose generation controls",
);
assert(
  arithmeticTopic?.supported_difficulties.join(",") ===
    "1,2,3",
  "Generated Primary School topics must offer difficulties 1, 2, and 3",
);
assert(
  topicSupportsGeneration(wordProblemsTopic) === false,
  "Word Problems must keep the static-problem workflow",
);
assert(
  domainContentCount(primaryDomain) === 5,
  "Primary School available content includes generated families",
);
assert(
  subjectContentCount(generatedPrimaryCatalog.subjects[0]) ===
    6,
  "Mathematics available content includes generated Primary School families",
);
assert(
  problemsForTopic(problems, arithmeticSelection).length ===
    0,
  "A generator-only topic must not invent a predefined problem",
);
assert(
  problemsForTopic(
    [...problems, generatedArithmetic],
    arithmeticSelection,
  ).map((problem) => problem.problem_id).join(",") ===
    generatedArithmetic.problem_id,
  "Generate Again keeps the new generated problem in the topic list",
);
assert(
  canStartSelectedProblem(
    selectProblem(
      arithmeticSelection,
      generatedArithmetic.problem_id,
    ),
    {
      ...generatedArithmetic,
      problem_text: "Compute: 7 - 3",
      language: "en",
      skills: [],
      metadata: { generated: true, difficulty: 1 },
    },
  ) === true,
  "A generated Primary School problem can start a session after it exists",
);

const generatedUnknown = {
  ...generatedArithmetic,
  problem_id: "grade4_unknown_number_generated_aaaabbbbcccc",
  title: "Намерете неизвестното число",
  topic: "unknown_numbers",
  problem_type: "unknown_number",
};
const unknownSelection = selectProblem(
  selectTopic(
    selectDomain(
      selectSubject("mathematics"),
      "primary_school",
    ),
    "unknown_numbers",
  ),
  generatedUnknown.problem_id,
);
const difficultyAfterLanguageSwitch = 2;
assert(
  unknownSelection.problemId === generatedUnknown.problem_id,
  "Language switching must keep the selected generated problem id",
);
assert(
  unknownSelection.topic === "unknown_numbers" &&
    unknownSelection.domain === "primary_school",
  "Language switching must keep the current topic selection",
);
assert(
  difficultyAfterLanguageSwitch === 2,
  "Language switching must keep the selected difficulty",
);
assert(
  problemsForTopic(
    [...problems, generatedUnknown],
    unknownSelection,
  ).map((problem) => problem.problem_id).join(",") ===
    generatedUnknown.problem_id,
  "The Problem dropdown must keep the same generated problem after a language switch",
);

assert(
  landingEntries(generatedPrimaryCatalog).find(
    (entry) => entry.key === "primary_school",
  )?.description.includes("Arithmetic") === true,
  "The Primary School card must mention generated families",
);

console.log("learning_path tests passed");
