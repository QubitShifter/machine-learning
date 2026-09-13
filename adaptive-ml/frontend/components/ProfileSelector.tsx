"use client";

import { FormEvent, useState } from "react";

import { useStudentProfile } from "@/components/StudentProfileProvider";

export function ProfileSelector() {
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

  return (
    <div className="profile-selector">
      <label className="profile-select-label">
        <span className="visually-hidden">
          Student profile
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
              {profile.displayName}
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
              Display name
            </span>
            <input
              autoFocus
              onChange={(event) =>
                setName(event.target.value)
              }
              placeholder="Display name"
              value={name}
            />
          </label>
          <button type="submit">Add</button>
          <button
            className="secondary-button"
            onClick={() => {
              setAdding(false);
              setName("");
            }}
            type="button"
          >
            Cancel
          </button>
        </form>
      ) : (
        <button
          className="secondary-button profile-add-button"
          onClick={() => setAdding(true)}
          type="button"
        >
          Add profile
        </button>
      )}
    </div>
  );
}
