"use client";

import { FormEvent, useState } from "react";

import { useLanguage } from "@/components/LanguageProvider";
import { useStudentProfile } from "@/components/StudentProfileProvider";

export function ProfileSelector() {
  const { t } = useLanguage();
  const {
    profiles,
    selectedStudent,
    selectStudent,
    addProfile,
  } = useStudentProfile();
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");

  function handleAdd(event: FormEvent) {
    event.preventDefault();
    const added = addProfile(name);

    if (added.displayName === name.trim() && name.trim()) {
      setName("");
      setAdding(false);
    }
  }

  function profileLabel(
    displayName: string,
    isGuest?: boolean,
  ) {
    return isGuest ? t("profile.guest") : displayName;
  }

  return (
    <div className="profile-selector">
      <label className="profile-select-label">
        <span className="visually-hidden">
          {t("profile.select")}
        </span>
        <select
          onChange={(event) =>
            selectStudent(event.target.value)
          }
          value={selectedStudent.studentId}
        >
          {profiles.map((profile) => (
            <option
              key={profile.studentId}
              value={profile.studentId}
            >
              {profileLabel(
                profile.displayName,
                profile.isGuest,
              )}
            </option>
          ))}
        </select>
      </label>
      {adding ? (
        <form
          className="profile-add-form"
          onSubmit={handleAdd}
        >
          <label>
            <span className="visually-hidden">
              {t("profile.displayName")}
            </span>
            <input
              autoFocus
              onChange={(event) =>
                setName(event.target.value)
              }
              placeholder={t("profile.displayName")}
              value={name}
            />
          </label>
          <button type="submit">
            {t("profile.addSubmit")}
          </button>
          <button
            className="secondary-button"
            onClick={() => {
              setAdding(false);
              setName("");
            }}
            type="button"
          >
            {t("profile.cancel")}
          </button>
        </form>
      ) : (
        <button
          className="secondary-button profile-add-button"
          onClick={() => setAdding(true)}
          type="button"
        >
          {t("profile.add")}
        </button>
      )}
    </div>
  );
}
