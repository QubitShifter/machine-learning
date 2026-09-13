import {
  GUEST_DISPLAY_NAME,
  GUEST_STUDENT_ID,
  addLocalProfile,
  createGuestProfile,
  ensureGuestProfile,
  findProfile,
  generateStudentId,
  loadProfileState,
  parseSelectedStudentId,
  parseStoredProfiles,
  persistProfileState,
  serializeProfiles,
} from "./studentProfiles.ts";

function assert(
  condition: boolean,
  message: string,
): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

const guest = createGuestProfile();

assert(
  guest.studentId === GUEST_STUDENT_ID,
  "Default Guest must use local_student",
);
assert(
  guest.displayName === GUEST_DISPLAY_NAME,
  "Default profile display name must be Guest",
);
assert(guest.isGuest === true, "Guest must be marked isGuest");

assert(
  parseStoredProfiles(null)[0].studentId ===
    GUEST_STUDENT_ID,
  "Missing storage must fall back to local_student",
);
assert(
  parseStoredProfiles("{not-json")[0].studentId ===
    GUEST_STUDENT_ID,
  "Malformed localStorage payload must fall back to Guest",
);
assert(
  parseStoredProfiles("[]")[0].studentId ===
    GUEST_STUDENT_ID,
  "Profile list must always contain local_student / Guest",
);

const serialized = serializeProfiles([
  {
    studentId: "profile_a",
    displayName: "Student A",
  },
]);
const restored = parseStoredProfiles(serialized);

assert(
  restored[0].studentId === GUEST_STUDENT_ID,
  "Serialization must keep Guest first",
);
assert(
  restored.some(
    (profile) => profile.displayName === "Student A",
  ),
  "Serialization must restore added profiles",
);

const added = addLocalProfile(
  [createGuestProfile()],
  "  Joro  ",
  "profile_joro",
);

assert(
  added.profile.studentId === "profile_joro",
  "Injected student ids must be preserved",
);
assert(
  added.profile.displayName === "Joro",
  "Added profile names must be trimmed",
);
assert(
  added.profiles.map((profile) => profile.studentId)
    .join(",") === "local_student,profile_joro",
  "Adding a profile must keep Guest and append the new profile",
);

const generated = generateStudentId(
  () => 1000,
  () => 0.123456,
);

assert(
  generated.startsWith("profile_"),
  "Generated ids must use the profile_ prefix",
);
assert(
  generated !== generateStudentId(() => 2000, () => 0.99),
  "Generated ids must change when time/random change",
);

const profiles = ensureGuestProfile(added.profiles);

assert(
  parseSelectedStudentId("profile_joro", profiles) ===
    "profile_joro",
  "Selected profile restoration must keep a known id",
);
assert(
  parseSelectedStudentId("missing", profiles) ===
    GUEST_STUDENT_ID,
  "Unknown selected profile must fall back to Guest",
);
assert(
  findProfile(profiles, "missing").studentId ===
    GUEST_STUDENT_ID,
  "Unknown lookup must return Guest",
);

const store: Record<string, string> = {};
const memoryStore = {
  getItem(key: string) {
    return store[key] ?? null;
  },
  setItem(key: string, value: string) {
    store[key] = value;
  },
};

persistProfileState(
  memoryStore,
  profiles,
  "profile_joro",
);
const loaded = loadProfileState(memoryStore);

assert(
  loaded.selectedStudentId === "profile_joro",
  "Persisted selection must restore",
);
assert(
  loaded.profiles.some(
    (profile) => profile.studentId === "profile_joro",
  ),
  "Persisted profiles must restore",
);

const beforeSwitch = JSON.stringify(profiles);
findProfile(profiles, "profile_joro");
parseSelectedStudentId("local_student", profiles);

assert(
  JSON.stringify(profiles) === beforeSwitch,
  "Switching profiles must not mutate profile records",
);

console.log("student_profiles tests passed");
