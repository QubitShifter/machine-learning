import {
  DEFAULT_LOCALE,
  LOCALE_STORAGE_KEY,
  catalogDisplayName,
  catalogProblemLookupId,
  interpolate,
  loadLocale,
  normalizeLocale,
  persistLocale,
  translate,
  trendDisplayLabel,
} from "../i18n/index.ts";
import {
  GUEST_STUDENT_ID,
  SELECTED_STUDENT_STORAGE_KEY,
  loadProfileState,
  persistProfileState,
} from "./studentProfiles.ts";

function assert(
  condition: boolean,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function createMemoryStore(
  initial: Record<string, string> = {},
) {
  const values = { ...initial };

  return {
    getItem(key: string) {
      return values[key] ?? null;
    },
    setItem(key: string, value: string) {
      values[key] = value;
    },
  };
}

assert(
  DEFAULT_LOCALE === "en",
  "Default locale must be en",
);
assert(
  normalizeLocale(undefined) === "en",
  "Missing locale must fall back to en",
);
assert(
  normalizeLocale("en") === "en",
  "en must load as en",
);
assert(
  normalizeLocale("bg") === "bg",
  "bg must load as bg",
);
assert(
  normalizeLocale("BG") === "bg",
  "Locale matching must be case-insensitive",
);
assert(
  normalizeLocale("de") === "en",
  "Unknown locale must fall back to en",
);
assert(
  normalizeLocale("") === "en",
  "Blank locale must fall back to en",
);

const store = createMemoryStore();

assert(
  loadLocale(store) === "en",
  "Missing storage must default to en",
);

persistLocale(store, "bg");
assert(
  store.getItem(LOCALE_STORAGE_KEY) === "bg",
  "Selected locale must persist under matpal_locale",
);
assert(
  loadLocale(store) === "bg",
  "Stored bg must load as bg",
);

store.setItem(LOCALE_STORAGE_KEY, "zz");
assert(
  loadLocale(store) === "en",
  "Malformed stored locale must load as en",
);

assert(
  translate("en", "tutor.sources") === "Sources",
  "English source heading",
);
assert(
  translate("bg", "tutor.sources") === "Източници",
  "Bulgarian source heading",
);
assert(
  translate("en", "tutor.externalSources") ===
    "Answer supported by external sources",
  "English external-source badge",
);
assert(
  translate("bg", "tutor.externalSources") ===
    "Отговор с помощта на външни източници",
  "Bulgarian external-source badge",
);
assert(
  translate("en", "tutor.findingExplanation") ===
    "Finding an explanation...",
  "English question loading text",
);
assert(
  translate("bg", "tutor.findingExplanation") ===
    "Подготвям обяснение...",
  "Bulgarian question loading text",
);
assert(
  translate("en", "tutor.explanation") === "Explanation",
  "English explanation heading",
);
assert(
  translate("bg", "tutor.explanation") === "Обяснение",
  "Bulgarian explanation heading",
);
assert(
  translate("en", "tutor.lastAnswer") === "Last answer",
  "English last-answer heading",
);
assert(
  translate("bg", "tutor.lastAnswer") ===
    "Последен отговор",
  "Bulgarian last-answer heading",
);
assert(
  translate("en", "status.concept") === "Explanation",
  "English concept status is an explanation, not Correct",
);
assert(
  translate("bg", "status.concept") === "Обяснение",
  "Bulgarian concept status is an explanation, not Правилно",
);
assert(
  translate("bg", "status.correct") === "Правилно",
  "Bulgarian correct status remains a graded-answer label",
);
assert(
  translate("bg", "nav.learn") === "Учебни теми",
  "Bulgarian known key must translate",
);
assert(
  translate("bg", "missing.translation.key") ===
    "missing.translation.key",
  "Missing translation must fall back to the key",
);
assert(
  interpolate("Progress — {name}", { name: "Student_B" }) ===
    "Progress — Student_B",
  "Interpolation must replace named placeholders",
);
assert(
  translate("bg", "progress.titleNamed", {
    name: "Student_B",
  }) === "Напредък — Student_B",
  "Bulgarian interpolation must keep profile names unchanged",
);

assert(
  catalogDisplayName(
    "subject",
    "mathematics",
    "Mathematics",
    "bg",
  ) === "Математика",
  "Catalog subject ids must map to Bulgarian display names",
);
assert(
  catalogDisplayName(
    "domain",
    "primary_school",
    "Primary School",
    "bg",
  ) === "Начален курс",
  "Catalog domain ids must map to Bulgarian display names",
);
assert(
  catalogDisplayName(
    "topic",
    "kinematics",
    "Kinematics",
    "bg",
  ) === "Кинематика",
  "Catalog topic ids must map to Bulgarian display names",
);
assert(
  catalogDisplayName(
    "problem",
    "unknown_generated_id",
    "Generated 1D kinematics",
    "bg",
  ) === "Generated 1D kinematics",
  "Unknown catalog ids must keep the provided fallback",
);

const LINEAR_ODE_FIXED_PROBLEM_ID =
  "linear_first_order_fixed_001";
const LINEAR_ODE_GENERATED_PROBLEM_ID =
  "linear_first_order_generated_a1b2c3d4e5f6";

assert(
  LINEAR_ODE_FIXED_PROBLEM_ID ===
    "linear_first_order_fixed_001",
  "Fixed Linear ODE catalog id must remain unchanged",
);
assert(
  catalogProblemLookupId(LINEAR_ODE_FIXED_PROBLEM_ID) ===
    LINEAR_ODE_FIXED_PROBLEM_ID,
  "Fixed Linear ODE ids must not be rewritten for lookup",
);
assert(
  catalogProblemLookupId(LINEAR_ODE_GENERATED_PROBLEM_ID) ===
    "linear_first_order_generated",
  "Generated Linear ODE ids must map to a stable catalog key",
);
assert(
  catalogProblemLookupId(LINEAR_ODE_GENERATED_PROBLEM_ID) !==
    LINEAR_ODE_GENERATED_PROBLEM_ID,
  "Generated Linear ODE display lookup must not use the raw id as a label",
);

const fixedBg = catalogDisplayName(
  "problem",
  LINEAR_ODE_FIXED_PROBLEM_ID,
  "First-Order Linear ODE",
  "bg",
);
const generatedBg = catalogDisplayName(
  "problem",
  LINEAR_ODE_GENERATED_PROBLEM_ID,
  "First-Order Linear ODE",
  "bg",
);
const fixedEn = catalogDisplayName(
  "problem",
  LINEAR_ODE_FIXED_PROBLEM_ID,
  "First-Order Linear ODE",
  "en",
);
const generatedEn = catalogDisplayName(
  "problem",
  LINEAR_ODE_GENERATED_PROBLEM_ID,
  "First-Order Linear ODE",
  "en",
);

assert(
  fixedBg ===
    "Линейно диференциално уравнение от първи ред",
  "Fixed Linear ODE must keep its Bulgarian catalog label",
);
assert(
  generatedBg ===
    "Генерирана задача — линейно ДУ от първи ред",
  "Generated Linear ODE must use a distinct Bulgarian catalog label",
);
assert(
  fixedEn === "First-order linear differential equation",
  "Fixed Linear ODE must use its English catalog label",
);
assert(
  generatedEn ===
    "Generated problem — first-order linear ODE",
  "Generated Linear ODE must use a distinct English catalog label",
);
assert(
  !fixedBg.includes(LINEAR_ODE_FIXED_PROBLEM_ID) &&
    !generatedBg.includes(LINEAR_ODE_GENERATED_PROBLEM_ID) &&
    !fixedEn.includes(LINEAR_ODE_FIXED_PROBLEM_ID) &&
    !generatedEn.includes(LINEAR_ODE_GENERATED_PROBLEM_ID),
  "Problem labels must not expose internal catalog ids",
);

assert(
  trendDisplayLabel("strong", "en") === "Strong",
  "English trend labels must stay language-neutral internally",
);
assert(
  trendDisplayLabel("strong", "bg") === "Силен напредък",
  "Bulgarian trend labels must localize presentation only",
);
assert(
  trendDisplayLabel("needs_support", "bg") ===
    "Нужда от подкрепа",
  "needs_support must localize",
);
assert(
  trendDisplayLabel("insufficient_history", "bg") ===
    "Недостатъчно данни",
  "insufficient_history must localize",
);

const sharedStore = createMemoryStore({
  [SELECTED_STUDENT_STORAGE_KEY]: "profile_keep",
});
const profiles = [
  {
    studentId: GUEST_STUDENT_ID,
    displayName: "Guest",
    isGuest: true as const,
  },
  {
    studentId: "profile_keep",
    displayName: "Student_B",
  },
];

persistProfileState(sharedStore, profiles, "profile_keep");
persistLocale(sharedStore, "bg");

const afterLanguageSwitch = loadProfileState(sharedStore);

assert(
  afterLanguageSwitch.selectedStudentId === "profile_keep",
  "Locale persistence must not change the selected student",
);
assert(
  afterLanguageSwitch.profiles.some(
    (profile) => profile.displayName === "Student_B",
  ),
  "Locale persistence must not mutate profile names",
);
assert(
  loadLocale(sharedStore) === "bg",
  "Language must remain independent of student profile state",
);

console.log("i18n helper tests passed");
