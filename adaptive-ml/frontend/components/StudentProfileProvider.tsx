"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import type { StudentProfile } from "@/lib/studentProfiles";
import {
  GUEST_STUDENT_ID,
  addLocalProfile,
  createGuestProfile,
  findProfile,
  loadProfileState,
  persistProfileState,
} from "@/lib/studentProfiles";

// Local profiles separate learning state on this device.
// They are not authenticated identity.

interface StudentProfileContextValue {
  profiles: StudentProfile[];
  selectedStudent: StudentProfile;
  selectStudent: (studentId: string) => void;
  addProfile: (displayName: string) => StudentProfile;
}

const StudentProfileContext =
  createContext<StudentProfileContextValue | null>(
    null,
  );

function browserStore() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage;
}

export function StudentProfileProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [profiles, setProfiles] = useState<
    StudentProfile[]
  >([createGuestProfile()]);
  const [selectedStudentId, setSelectedStudentId] =
    useState(GUEST_STUDENT_ID);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let ignore = false;
    const loaded = loadProfileState(browserStore());

    void Promise.resolve().then(() => {
      if (ignore) {
        return;
      }

      setProfiles(loaded.profiles);
      setSelectedStudentId(loaded.selectedStudentId);
      setReady(true);
    });

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (!ready) {
      return;
    }

    persistProfileState(
      browserStore(),
      profiles,
      selectedStudentId,
    );
  }, [profiles, ready, selectedStudentId]);

  const value = useMemo(
    () => ({
      profiles,
      selectedStudent: findProfile(
        profiles,
        selectedStudentId,
      ),
      selectStudent(studentId: string) {
        setSelectedStudentId(
          findProfile(profiles, studentId).studentId,
        );
      },
      addProfile(displayName: string) {
        const added = addLocalProfile(
          profiles,
          displayName,
        );
        setProfiles(added.profiles);
        setSelectedStudentId(added.profile.studentId);
        return added.profile;
      },
    }),
    [profiles, selectedStudentId],
  );

  return (
    <StudentProfileContext.Provider value={value}>
      {children}
    </StudentProfileContext.Provider>
  );
}

export function useStudentProfile() {
  const value = useContext(StudentProfileContext);

  if (!value) {
    throw new Error(
      "useStudentProfile must be used inside StudentProfileProvider.",
    );
  }

  return value;
}
