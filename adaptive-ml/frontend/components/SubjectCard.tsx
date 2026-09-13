import type { LandingEntry } from "@/lib/learningPath";

interface SubjectCardProps {
  entry: LandingEntry;
  onExplore: (entry: LandingEntry) => void;
}

export function SubjectCard({
  entry,
  onExplore,
}: SubjectCardProps) {
  return (
    <article
      className={
        entry.runnable
          ? "subject-card"
          : "subject-card subject-card-soon"
      }
    >
      <p className="eyebrow">{entry.eyebrow}</p>
      <h3>{entry.title}</h3>
      <p>{entry.description}</p>
      {entry.runnable ? (
        <button
          onClick={() => onExplore(entry)}
          type="button"
        >
          {entry.ctaLabel}
        </button>
      ) : (
        <button
          className="coming-soon-cta"
          disabled
          type="button"
        >
          Coming soon
        </button>
      )}
    </article>
  );
}
