"use client";

import { useLanguage } from "@/components/LanguageProvider";
import type { Locale } from "@/i18n";

export function LanguageSwitcher() {
  const { locale, setLocale, t } = useLanguage();

  function select(next: Locale) {
    if (next !== locale) {
      setLocale(next);
    }
  }

  return (
    <div
      aria-label={t("language.label")}
      className="language-switcher"
      role="group"
    >
      <button
        aria-pressed={locale === "en"}
        className={
          locale === "en"
            ? "language-option language-option-active"
            : "language-option"
        }
        onClick={() => select("en")}
        type="button"
      >
        {t("language.en")}
      </button>
      <span aria-hidden="true" className="language-divider">
        |
      </span>
      <button
        aria-pressed={locale === "bg"}
        className={
          locale === "bg"
            ? "language-option language-option-active"
            : "language-option"
        }
        onClick={() => select("bg")}
        type="button"
      >
        {t("language.bg")}
      </button>
    </div>
  );
}
