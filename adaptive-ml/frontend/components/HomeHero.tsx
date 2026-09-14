"use client";

import Link from "next/link";

import { EquationShowcase } from "@/components/EquationShowcase";
import { useLanguage } from "@/components/LanguageProvider";
import { PROGRESS_HREF } from "@/lib/learningPath";

interface HomeHeroProps {
  onStartLearning: () => void;
}

export function HomeHero({
  onStartLearning,
}: HomeHeroProps) {
  const { t } = useLanguage();

  return (
    <section className="landing-hero">
      <div className="home-hero-copy">
        <p className="eyebrow">{t("home.hero.eyebrow")}</p>
        <h1>{t("home.hero.title")}</h1>
        <p className="hero-tagline">
          {t("home.hero.tagline")}
        </p>
        <p className="hero-lead">
          {t("home.hero.description")}
        </p>
        <div className="hero-actions">
          <button
            onClick={onStartLearning}
            type="button"
          >
            {t("home.start")}
          </button>
          <Link
            className="secondary-button hero-progress-link"
            href={PROGRESS_HREF}
          >
            {t("home.viewProgress")}
          </Link>
        </div>
      </div>
      <EquationShowcase />
    </section>
  );
}
