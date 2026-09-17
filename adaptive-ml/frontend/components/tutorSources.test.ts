import {
  isSafeHttpUrl,
  readTutorSources,
  usedExternalSources,
} from "./tutorSources.ts";

function assert(
  condition: boolean,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

assert(
  isSafeHttpUrl("https://openstax.org/ode") === true,
  "https URLs must be allowed",
);
assert(
  isSafeHttpUrl("http://libretexts.org/ode") === true,
  "http URLs must be allowed",
);
assert(
  isSafeHttpUrl("javascript:alert(1)") === false,
  "javascript URLs must be rejected",
);

const localSession = {
  sources: [],
  metadata: { answer_source: "local", used_web: false },
};
assert(
  readTutorSources(localSession).length === 0,
  "Local-only responses must have no sources",
);
assert(
  usedExternalSources(localSession) === false,
  "Local-only responses must not show the external-source badge",
);

const webSession = {
  sources: [
    {
      title: "Source A",
      url: "https://openstax.org/a",
      domain: "openstax.org",
    },
    {
      title: "Bad",
      url: "javascript:alert(1)",
    },
  ],
  metadata: { used_web: true, answer_source: "web" },
};
const sources = readTutorSources(webSession);
assert(sources.length === 1, "Only safe http(s) sources are shown");
assert(sources[0].title === "Source A", "Source titles are retained");
assert(
  usedExternalSources(webSession) === true,
  "used_web must enable the external-source badge",
);

console.log("tutor_sources tests passed");
