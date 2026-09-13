import Link from "next/link";

import { EquationShowcase } from "@/components/EquationShowcase";
import { PROGRESS_HREF } from "@/lib/learningPath";

interface HomeHeroProps {
  onStartLearning: () => void;
}

export function HomeHero({
  onStartLearning,
}: HomeHeroProps) {
  return (
    <section className="landing-hero">
      <div className="home-hero-copy">
        <p className="eyebrow">Adaptive STEM tutor</p>
        <h1>MAT-PAL</h1>
        <p className="hero-tagline">
          Math &amp; Physics Adaptive Learning
        </p>
        <p className="hero-lead">
          Learn mathematics and physics with
          adaptive, step-by-step guidance.
        </p>
        <div className="hero-actions">
          <button
            onClick={onStartLearning}
            type="button"
          >
            Start Learning
          </button>
          <Link
            className="secondary-button hero-progress-link"
            href={PROGRESS_HREF}
          >
            View Progress
          </Link>
        </div>
      </div>
      <EquationShowcase />
    </section>
  );
}
