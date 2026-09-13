// Browser-only local profiles. studentId is a storage key,
// not authenticated identity.

export const GUEST_STUDENT_ID = "local_student";
export const GUEST_DISPLAY_NAME = "Guest";
export const PROFILES_STORAGE_KEY = "matpal_profiles";
export const SELECTED_STUDENT_STORAGE_KEY =
  "matpal_selected_student";

export interface StudentProfile {
  studentId: string;
  displayName: string;
  isGuest?: boolean;
}

export interface ProfileStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export const GUEST_PROFILE: StudentProfile = {
  studentId: GUEST_STUDENT_ID,
  displayName: GUEST_DISPLAY_NAME,
  isGuest: true,
};

export function createGuestProfile(): StudentProfile {
  return {
    ...GUEST_PROFILE,
  };
}

export function generateStudentId(
  now: () => number = Date.now,
  random: () => number = Math.random,
) {
  return `profile_${now().toString(36)}_${random()
    .toString(36)
    .slice(2, 8)}`;
}

function isProfile(value: unknown): value is StudentProfile {
  if (!value || typeof value !== "object") {
    return false;
  }

  const record = value as StudentProfile;

  return (
    typeof record.studentId === "string" &&
    record.studentId.trim().length > 0 &&
    typeof record.displayName === "string" &&
    record.displayName.trim().length > 0
  );
}

export function ensureGuestProfile(
  profiles: StudentProfile[],
): StudentProfile[] {
  const guest = createGuestProfile();
  const others = profiles.filter(
    (profile) => profile.studentId !== GUEST_STUDENT_ID,
  );

  return [guest, ...others];
}

export function parseStoredProfiles(
  raw: string | null,
): StudentProfile[] {
  if (!raw) {
    return [createGuestProfile()];
  }

  try {
    const parsed = JSON.parse(raw) as unknown;

    if (!Array.isArray(parsed)) {
      return [createGuestProfile()];
    }

    return ensureGuestProfile(
      parsed.filter(isProfile).map((profile) => ({
        studentId: profile.studentId.trim(),
        displayName: profile.displayName.trim(),
        isGuest: profile.studentId === GUEST_STUDENT_ID,
      })),
    );
  } catch {
    return [createGuestProfile()];
  }
}

export function parseSelectedStudentId(
  raw: string | null,
  profiles: StudentProfile[],
) {
  const selected = raw?.trim() ?? "";
  const known = profiles.some(
    (profile) => profile.studentId === selected,
  );

  if (!selected || !known) {
    return GUEST_STUDENT_ID;
  }

  return selected;
}

export function serializeProfiles(
  profiles: StudentProfile[],
) {
  return JSON.stringify(ensureGuestProfile(profiles));
}

export function addLocalProfile(
  profiles: StudentProfile[],
  displayName: string,
  studentId?: string,
) {
  const name = displayName.trim();

  if (!name) {
    return {
      profiles: ensureGuestProfile(profiles),
      profile: createGuestProfile(),
    };
  }

  const nextProfile: StudentProfile = {
    studentId: (studentId ?? generateStudentId()).trim(),
    displayName: name,
    isGuest: false,
  };
  const nextProfiles = ensureGuestProfile([
    ...profiles,
    nextProfile,
  ]);

  return {
    profiles: nextProfiles,
    profile: nextProfile,
  };
}

export function findProfile(
  profiles: StudentProfile[],
  studentId: string,
) {
  return (
    profiles.find(
      (profile) => profile.studentId === studentId,
    ) ?? createGuestProfile()
  );
}

export function loadProfileState(
  store: ProfileStore | null,
) {
  if (!store) {
    return {
      profiles: [createGuestProfile()],
      selectedStudentId: GUEST_STUDENT_ID,
    };
  }

  try {
    const profiles = parseStoredProfiles(
      store.getItem(PROFILES_STORAGE_KEY),
    );
    const selectedStudentId = parseSelectedStudentId(
      store.getItem(SELECTED_STUDENT_STORAGE_KEY),
      profiles,
    );

    return {
      profiles,
      selectedStudentId,
    };
  } catch {
    return {
      profiles: [createGuestProfile()],
      selectedStudentId: GUEST_STUDENT_ID,
    };
  }
}

export function persistProfileState(
  store: ProfileStore | null,
  profiles: StudentProfile[],
  selectedStudentId: string,
) {
  if (!store) {
    return;
  }

  const nextProfiles = ensureGuestProfile(profiles);
  const nextSelected = parseSelectedStudentId(
    selectedStudentId,
    nextProfiles,
  );

  store.setItem(
    PROFILES_STORAGE_KEY,
    serializeProfiles(nextProfiles),
  );
  store.setItem(
    SELECTED_STUDENT_STORAGE_KEY,
    nextSelected,
  );
}
