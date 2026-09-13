# Student Profiles

Phase 20 adds an explicit local student identity so learning
state is scoped per profile.

This is **not authentication**. `student_id` is a local storage
key, not a trusted or verified identity. MAT-PAL does not
provide secure accounts, authorization, or identity proof.

## Purpose

Keep tutor sessions, progress, mastery, recent history, and
adaptive recommendations isolated per selected profile while
remaining ready for a later real-auth phase.

## Default Profile

If no profile is selected, MAT-PAL uses:

- `student_id`: `local_student`
- `display_name`: `Guest`

Existing progress stored under `local_student` continues to
load. First-time users are not forced through setup.

## Profile Model

Minimum fields:

- `student_id` / `studentId`
- `display_name` / `displayName`

Optional frontend metadata: `isGuest`.

Local profiles may be created from the header with a display
name only. Generated ids use `profile_<time>_<rand>`.

## Browser Persistence

Frontend stores:

- `matpal_profiles` — local profile list
- `matpal_selected_student` — selected `student_id`

Malformed localStorage data fails safe and falls back to
Guest / `local_student`. No passwords, tokens, or personal
account data are stored.

## Backend Student Scoping

Student-specific APIs accept `student_id` and default it to
`local_student` so older callers keep working.

Scoped today:

- `GET /progress?student_id=`
- `POST /adaptive/recommendation` (`student_id` in body)
- `POST /sessions/start` (`student_id` in body)
- session completion / mastery updates

Catalog and problem endpoints stay identity-free.

## Progress Storage

Legacy files keep a root `skills` object. That record belongs
to `local_student`.

Writing a non-guest student migrates the file to:

```text
{
  "students": {
    "local_student": { "skills": { ... } },
    "student_alice": { "skills": { ... } }
  }
}
```

Unknown student ids receive empty isolated progress. Students
are never merged. Reads do not discard legacy mastery or
history.

## Session Ownership

Started sessions store `student_id` on the session and in
response metadata. Completion updates that session's owner
only. `local_student` remains the explicit fallback when no
id is supplied.

Switching the selected profile while a tutor session is
active clears the tutor UI and returns to the learning/home
state. Active sessions are not transferred between profiles.

## Adaptive Recommendation

`RuleBasedAdaptivePolicy` and feature math are unchanged.
Only the selected student's progress is supplied to the
existing policy.

## Login Page

`/login` remains a placeholder. Local profiles are managed
from the header, not as real sign-in.

## Future Authentication

A later phase can map a verified account onto a stable
`student_id` and keep the same progress-scoping boundary.
Until then, anyone who can call the API can supply any
`student_id`.
