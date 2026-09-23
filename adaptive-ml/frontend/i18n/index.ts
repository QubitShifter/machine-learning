import { bg } from "./bg.ts";
import { en } from "./en.ts";
import type {
  Locale,
  LocaleStore,
  TranslationParams,
} from "./types.ts";

export type { Locale, LocaleStore, TranslationParams };

export const DEFAULT_LOCALE: Locale = "en";
export const SUPPORTED_LOCALES = ["en", "bg"] as const;
export const LOCALE_STORAGE_KEY = "matpal_locale";

const dictionaries: Record<Locale, Record<string, string>> = {
  en,
  bg,
};

export function normalizeLocale(value: unknown): Locale {
  if (typeof value !== "string") {
    return DEFAULT_LOCALE;
  }

  const locale = value.trim().toLowerCase();

  if (locale === "en" || locale === "bg") {
    return locale;
  }

  return DEFAULT_LOCALE;
}

export function loadLocale(store: LocaleStore | null): Locale {
  if (!store) {
    return DEFAULT_LOCALE;
  }

  try {
    return normalizeLocale(store.getItem(LOCALE_STORAGE_KEY));
  } catch {
    return DEFAULT_LOCALE;
  }
}

export function persistLocale(
  store: LocaleStore | null,
  locale: Locale,
): Locale {
  const normalized = normalizeLocale(locale);

  if (!store) {
    return normalized;
  }

  try {
    store.setItem(LOCALE_STORAGE_KEY, normalized);
  } catch {
    return normalized;
  }

  return normalized;
}

export function interpolate(
  text: string,
  params?: TranslationParams,
): string {
  if (!params) {
    return text;
  }

  let result = text;

  for (const [key, value] of Object.entries(params)) {
    result = result.replaceAll(`{${key}}`, String(value));
  }

  return result;
}

export function translate(
  locale: Locale,
  key: string,
  params?: TranslationParams,
): string {
  const table = dictionaries[normalizeLocale(locale)];
  const fallback = dictionaries[DEFAULT_LOCALE];
  const text = table[key] ?? fallback[key] ?? key;

  return interpolate(text, params);
}

const GENERATED_PROBLEM_ID =
  /^(.+)_generated_[0-9a-f]+$/i;

export function catalogProblemLookupId(problemId: string): string {
  const match = GENERATED_PROBLEM_ID.exec(problemId);

  if (!match) {
    return problemId;
  }

  return `${match[1]}_generated`;
}

export function catalogDisplayName(
  kind: "subject" | "domain" | "topic" | "problem",
  id: string,
  fallback: string,
  locale: Locale = DEFAULT_LOCALE,
): string {
  if (!id) {
    return fallback;
  }

  const exactKey = `catalog.${kind}.${id}`;
  const exact = translate(locale, exactKey);

  if (exact !== exactKey) {
    return exact;
  }

  if (kind === "problem") {
    const lookupId = catalogProblemLookupId(id);

    if (lookupId !== id) {
      const generatedKey = `catalog.${kind}.${lookupId}`;
      const generated = translate(locale, generatedKey);

      if (generated !== generatedKey) {
        return generated;
      }
    }
  }

  return fallback;
}

export function masteryDisplayLabel(
  label: string,
  locale: Locale = DEFAULT_LOCALE,
): string {
  const normalized = label.trim().toLowerCase();

  if (normalized === "building" || normalized === "beginning") {
    return translate(locale, "mastery.building");
  }

  if (normalized === "developing") {
    return translate(locale, "mastery.developing");
  }

  if (normalized === "strong") {
    return translate(locale, "mastery.strong");
  }

  return label;
}

export function trendDisplayLabel(
  trend: string,
  locale: Locale = DEFAULT_LOCALE,
): string {
  if (
    trend === "strong" ||
    trend === "stable" ||
    trend === "needs_support" ||
    trend === "insufficient_history"
  ) {
    return translate(locale, `trend.${trend}`);
  }

  return translate(locale, "trend.insufficient_history");
}

export function localizedFamilyName(
  locale: Locale,
  family: string | null | undefined,
): string {
  if (
    family === "number_detective" ||
    family === "distribution_puzzles" ||
    family === "logic_detective"
  ) {
    return translate(locale, `path.family.${family}`);
  }

  return "";
}

export function localizeFamilyReason(
  locale: Locale,
  familyReason: string | undefined,
  family: string | null | undefined,
): string {
  const familyName = localizedFamilyName(locale, family);
  if (!familyReason || !familyName) {
    return "";
  }

  const key = `adaptive.familyReason.${familyReason}`;
  const text = translate(locale, key, { family: familyName });
  return text === key ? "" : text;
}

export function localizeRecommendationReason(
  locale: Locale,
  topicName: string,
  mastery: number | null | undefined,
  adjustmentReason: string | undefined,
  recentSessionCount?: number,
  familyReason?: string,
  family?: string | null,
): string {
  const base = translate(locale, "adaptive.reason.base", {
    topic: topicName,
    mastery:
      typeof mastery === "number" ? mastery.toFixed(2) : "—",
  });

  let text = base;
  if (adjustmentReason && adjustmentReason !== "static_topic") {
    const suffixKey = `adaptive.reason.${adjustmentReason}`;
    const suffix = translate(locale, suffixKey, {
      sessions: recentSessionCount ?? 0,
    });

    if (suffix !== suffixKey) {
      text = `${base}${suffix}`;
    }
  }

  return `${text}${localizeFamilyReason(locale, familyReason, family)}`;
}
