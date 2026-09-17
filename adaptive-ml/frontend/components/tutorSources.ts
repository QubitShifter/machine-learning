import type { TutorSession, TutorSource } from "@/types/tutor";

export function isSafeHttpUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return (
      parsed.protocol === "http:" ||
      parsed.protocol === "https:"
    );
  } catch {
    return false;
  }
}

export function readTutorSources(
  session: Pick<TutorSession, "sources"> | null | undefined,
): TutorSource[] {
  const sources = session?.sources;

  if (!Array.isArray(sources)) {
    return [];
  }

  return sources.filter(
    (source): source is TutorSource =>
      typeof source?.title === "string" &&
      typeof source?.url === "string" &&
      isSafeHttpUrl(source.url),
  );
}

export function usedExternalSources(
  session: Pick<TutorSession, "metadata"> | null | undefined,
): boolean {
  return session?.metadata?.used_web === true;
}
