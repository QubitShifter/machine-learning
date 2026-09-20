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
  translate("en", "tutor.numberFieldHint").includes(
    "Ask a question",
  ),
  "English number field must point questions to Ask a question",
);
assert(
  translate("bg", "tutor.numberFieldHint").includes(
    "Задай въпрос",
  ),
  "Bulgarian number field must point questions to Задай въпрос",
);
assert(
  translate("en", "tutor.placeholderNumber") ===
    "Enter a number",
  "English number placeholder",
);
assert(
  translate("bg", "tutor.placeholderNumber") ===
    "Въведете число",
  "Bulgarian number placeholder",
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
    "topic",
    "arithmetic",
    "Arithmetic",
    "en",
  ) === "Arithmetic",
  "Arithmetic catalog topic must keep its English label",
);
assert(
  catalogDisplayName(
    "topic",
    "unknown_numbers",
    "Unknown Numbers",
    "bg",
  ) === "Неизвестни числа",
  "Unknown-number catalog topic must have a Bulgarian label",
);
assert(
  catalogDisplayName(
    "topic",
    "number_patterns",
    "Number Patterns",
    "bg",
  ) === "Числови редици",
  "Number-pattern catalog topic must have a Bulgarian label",
);
assert(
  translate("en", "path.generateAgain") ===
    "Generate Another Problem",
  "Generate Again must have an English label",
);
assert(
  translate("bg", "path.generatedTopic") ===
    " (генерирана)",
  "Generated-topic suffix must be localized",
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

const UNKNOWN_GENERATED_ID =
  "grade4_unknown_number_generated_aaaabbbbcccc";
const ARITHMETIC_GENERATED_ID =
  "grade4_arithmetic_generated_111122223333";
const PATTERNS_GENERATED_ID =
  "grade4_number_patterns_generated_abcd1234ef56";
const STORY_GENERATED_ID =
  "grade4_word_problems_generated_feedface0123";
const REVERSE_REASONING_ID =
  "grade4_reverse_reasoning_001";
const KINEMATICS_FIXED_ID = "kinematics_fixed_001";

assert(
  catalogProblemLookupId(UNKNOWN_GENERATED_ID) ===
    "grade4_unknown_number_generated",
  "Generated Unknown Numbers ids must map to a stable catalog key",
);
assert(
  catalogProblemLookupId(ARITHMETIC_GENERATED_ID) ===
    "grade4_arithmetic_generated",
  "Generated Arithmetic ids must map to a stable catalog key",
);
assert(
  catalogProblemLookupId(PATTERNS_GENERATED_ID) ===
    "grade4_number_patterns_generated",
  "Generated Number Patterns ids must map to a stable catalog key",
);
assert(
  catalogProblemLookupId(STORY_GENERATED_ID) ===
    "grade4_word_problems_generated",
  "Generated story-problem ids must map to a stable catalog key",
);
assert(
  catalogProblemLookupId(REVERSE_REASONING_ID) ===
    REVERSE_REASONING_ID,
  "Static reverse-reasoning ids must not be rewritten",
);

const unknownBgStored = "Намерете неизвестното число";
const unknownEnStored = "Find the unknown number";
const arithmeticBgStored = "Пресметнете израза";
const arithmeticEnStored = "Compute the expression";
const patternsBgStored = "Числови редици";
const patternsEnStored = "Number patterns";
const storyBgStored = "Текстова задача за 4. клас";
const storyEnStored = "Grade 4 story problem";

const unknownDropdownAfterBgToEn = catalogDisplayName(
  "problem",
  UNKNOWN_GENERATED_ID,
  unknownBgStored,
  "en",
);
const unknownPreviewAfterBgToEn = catalogDisplayName(
  "problem",
  UNKNOWN_GENERATED_ID,
  unknownEnStored,
  "en",
);
assert(
  unknownDropdownAfterBgToEn === unknownEnStored,
  "Unknown Numbers dropdown must switch BG stored title to English",
);
assert(
  unknownPreviewAfterBgToEn === unknownEnStored,
  "Unknown Numbers preview must show the English title",
);
assert(
  unknownDropdownAfterBgToEn === unknownPreviewAfterBgToEn,
  "Unknown Numbers dropdown and preview must share the English title",
);

const unknownDropdownAfterEnToBg = catalogDisplayName(
  "problem",
  UNKNOWN_GENERATED_ID,
  unknownEnStored,
  "bg",
);
const unknownPreviewAfterEnToBg = catalogDisplayName(
  "problem",
  UNKNOWN_GENERATED_ID,
  unknownBgStored,
  "bg",
);
assert(
  unknownDropdownAfterEnToBg === unknownBgStored,
  "Unknown Numbers dropdown must switch EN stored title to Bulgarian",
);
assert(
  unknownPreviewAfterEnToBg === unknownBgStored,
  "Unknown Numbers preview must show the Bulgarian title",
);
assert(
  unknownDropdownAfterEnToBg === unknownPreviewAfterEnToBg,
  "Unknown Numbers dropdown and preview must share the Bulgarian title",
);

assert(
  catalogDisplayName(
    "problem",
    ARITHMETIC_GENERATED_ID,
    arithmeticBgStored,
    "en",
  ) === arithmeticEnStored,
  "Arithmetic dropdown must localize BG → EN",
);
assert(
  catalogDisplayName(
    "problem",
    ARITHMETIC_GENERATED_ID,
    arithmeticEnStored,
    "bg",
  ) === arithmeticBgStored,
  "Arithmetic dropdown must localize EN → BG",
);
assert(
  catalogDisplayName(
    "problem",
    PATTERNS_GENERATED_ID,
    patternsBgStored,
    "en",
  ) === patternsEnStored,
  "Number Patterns dropdown must localize BG → EN",
);
assert(
  catalogDisplayName(
    "problem",
    PATTERNS_GENERATED_ID,
    patternsEnStored,
    "bg",
  ) === patternsBgStored,
  "Number Patterns dropdown must localize EN → BG",
);
assert(
  catalogDisplayName(
    "topic",
    "story_problems",
    "Story Problems",
    "bg",
  ) === "Сюжетни задачи",
  "Story Problems topic must localize EN → BG",
);
assert(
  catalogDisplayName(
    "problem",
    STORY_GENERATED_ID,
    storyBgStored,
    "en",
  ) === storyEnStored,
  "Story problem dropdown must localize BG → EN",
);
assert(
  catalogDisplayName(
    "problem",
    STORY_GENERATED_ID,
    storyEnStored,
    "bg",
  ) === storyBgStored,
  "Story problem dropdown must localize EN → BG",
);
assert(
  catalogDisplayName(
    "problem",
    STORY_GENERATED_ID,
    storyBgStored,
    "en",
  ) ===
    catalogDisplayName(
      "problem",
      STORY_GENERATED_ID,
      storyEnStored,
      "en",
    ),
  "Story problem dropdown and preview must share the English title",
);

assert(
  catalogDisplayName(
    "problem",
    REVERSE_REASONING_ID,
    "Hazelnuts in Three Hollows",
    "bg",
  ) === "Лешници в три хралупи",
  "Static reverse-reasoning title must stay localized",
);
assert(
  catalogDisplayName(
    "problem",
    REVERSE_REASONING_ID,
    "Лешници в три хралупи",
    "en",
  ) === "Hazelnuts in Three Hollows",
  "Static reverse-reasoning title must switch EN ← BG",
);
assert(
  catalogDisplayName(
    "problem",
    KINEMATICS_FIXED_ID,
    "Car accelerating from rest",
    "bg",
  ) === "Автомобил, ускоряващ от покой",
  "Kinematics titles must keep their existing Bulgarian label",
);
assert(
  catalogDisplayName(
    "problem",
    LINEAR_ODE_FIXED_PROBLEM_ID,
    "First-Order Linear ODE",
    "en",
  ) === "First-order linear differential equation",
  "Fixed Linear ODE English title must remain unchanged",
);

assert(
  UNKNOWN_GENERATED_ID ===
    "grade4_unknown_number_generated_aaaabbbbcccc",
  "Language switching must not rewrite the generated problem id",
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
