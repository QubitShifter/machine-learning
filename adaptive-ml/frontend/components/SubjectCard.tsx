"use client";

import { useLanguage } from "@/components/LanguageProvider";
import { catalogDisplayName } from "@/i18n";
import {
  findPrimarySchoolDomain,
  findSubject,
} from "@/lib/learningPath";
import type { LandingEntry } from "@/lib/learningPath";
import type { CatalogResponse } from "@/types/tutor";

interface SubjectCardProps {
  catalog: CatalogResponse | null;
  entry: LandingEntry;
  onExplore: (entry: LandingEntry) => void;
}

function cardDescription(
  entry: LandingEntry,
  catalog: CatalogResponse | null,
  locale: "en" | "bg",
  t: (key: string) => string,
) {
  if (entry.key === "primary_school") {
    const primary = findPrimarySchoolDomain(catalog);
    const names = primary?.topics
      .map((topic) =>
        catalogDisplayName(
          "topic",
          topic.id,
          topic.name,
          locale,
        ),
      )
      .join(" • ");

    return names || t("home.primaryFallback");
  }

  const subject = findSubject(catalog, entry.key);

  if (subject) {
    const names = subject.domains
      .filter((domain) => domain.id !== "primary_school")
      .slice(0, 4)
      .map((domain) =>
        catalogDisplayName(
          "domain",
          domain.id,
          domain.name,
          locale,
        ),
      )
      .join(" • ");

    return (
      names ||
      (entry.key === "physics"
        ? t("home.physicsFallback")
        : t("home.catalogFallback"))
    );
  }

  return entry.description;
}

export function SubjectCard({
  catalog,
  entry,
  onExplore,
}: SubjectCardProps) {
  const { locale, t } = useLanguage();
  const title = catalogDisplayName(
    entry.key === "primary_school" ? "domain" : "subject",
    entry.key,
    entry.title,
    locale,
  );
  const eyebrow = catalogDisplayName(
    "subject",
    entry.key === "primary_school" ? "mathematics" : entry.key,
    entry.eyebrow,
    locale,
  );
  const ctaKey = `home.explore.${entry.key}`;
  const cta = t(ctaKey) === ctaKey ? entry.ctaLabel : t(ctaKey);

  return (
    <article
      className={
        entry.runnable
          ? "subject-card"
          : "subject-card subject-card-soon"
      }
    >
      <p className="eyebrow">{eyebrow}</p>
      <h3>{title}</h3>
      <p>{cardDescription(entry, catalog, locale, t)}</p>
      {entry.runnable ? (
        <button
          onClick={() => onExplore(entry)}
          type="button"
        >
          {cta}
        </button>
      ) : (
        <button
          className="coming-soon-cta"
          disabled
          type="button"
        >
          {t("home.comingSoon")}
        </button>
      )}
    </article>
  );
}
