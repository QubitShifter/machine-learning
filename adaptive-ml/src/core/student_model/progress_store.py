import json
from pathlib import Path

from src.core.adaptive.features import (
    bound_recent_sessions,
    family_history_to_dict,
)


DEFAULT_PROGRESS_PATH = Path(
    "math/ode/data/student_progress.json"
)
DEFAULT_STUDENT_ID = "local_student"


def empty_skills_progress() -> dict:
    return {
        "skills": {},
    }


def normalize_student_id(
    student_id: str | None,
) -> str:
    if student_id is None:
        return DEFAULT_STUDENT_ID

    cleaned = student_id.strip()

    if not cleaned:
        return DEFAULT_STUDENT_ID

    return cleaned


def is_multi_student_progress(
    progress: dict,
) -> bool:
    return isinstance(
        progress.get("students"),
        dict,
    )


def load_progress(
    path: Path = DEFAULT_PROGRESS_PATH,
) -> dict:
    """
    Load persisted student progress.

    If the file does not exist yet,
    return an empty progress structure.
    """

    if not path.exists():
        return {
            "skills": {}
        }

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except (
        json.JSONDecodeError,
        OSError,
    ):
        return {
            "skills": {}
        }

    if "skills" not in data:
        data["skills"] = {}

    return data


def get_student_record(
    progress: dict,
    student_id: str | None = None,
) -> dict:
    """
    Return the skills-bearing record for one student.

    student_id is a local storage key, not authenticated
    identity. Unknown students receive an empty isolated
    record. Legacy files with root-level skills continue
    to belong to local_student.
    """

    resolved_id = normalize_student_id(student_id)

    if is_multi_student_progress(progress):
        students = progress["students"]
        record = students.get(resolved_id)

        if record is None:
            return empty_skills_progress()

        if "skills" not in record:
            record["skills"] = {}

        return record

    progress.setdefault("skills", {})

    if resolved_id == DEFAULT_STUDENT_ID:
        return progress

    return empty_skills_progress()


def complete_student_record(
    student_record: dict,
) -> dict:
    record = dict(student_record)
    record.setdefault("skills", {})
    return record


def save_student_record(
    progress: dict,
    student_id: str | None,
    student_record: dict,
    path: Path = DEFAULT_PROGRESS_PATH,
) -> None:
    resolved_id = normalize_student_id(student_id)
    record = complete_student_record(student_record)

    if (
        resolved_id == DEFAULT_STUDENT_ID
        and not is_multi_student_progress(progress)
    ):
        progress.clear()
        progress.update(record)
        save_progress(progress, path)
        return

    if not is_multi_student_progress(progress):
        legacy_record = complete_student_record(progress)
        progress.clear()
        progress["students"] = {
            DEFAULT_STUDENT_ID: legacy_record,
        }

    progress["students"][resolved_id] = record
    save_progress(progress, path)


def save_progress(
    progress: dict,
    path: Path = DEFAULT_PROGRESS_PATH,
) -> None:
    """
    Save student progress to disk.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            progress,
            file,
            indent=4,
        )


def get_skill_progress(
    progress: dict,
    skill: str,
    default_mastery: float = 0.50,
) -> dict:
    """
    Return stored state for one skill.
    """

    skills = progress.setdefault(
        "skills",
        {}
    )

    if skill not in skills:
        skills[skill] = {
            "mastery": default_mastery,
            "questions_completed": 0,
            "first_attempt_streak": 0,
            "last_total_attempts": 0,
            "last_incorrect_attempts": 0,
            "last_hints_used": 0,
            "last_first_attempt_success": False,
            "last_completed": False,
            "recent_sessions": [],
        }

    skills[skill].setdefault(
        "last_total_attempts",
        0,
    )
    skills[skill].setdefault(
        "last_incorrect_attempts",
        0,
    )
    skills[skill].setdefault(
        "last_hints_used",
        0,
    )
    skills[skill].setdefault(
        "last_first_attempt_success",
        False,
    )
    skills[skill].setdefault(
        "last_completed",
        False,
    )
    skills[skill]["recent_sessions"] = (
        bound_recent_sessions(
            skills[skill].get(
                "recent_sessions",
                [],
            )
            or []
        )
    )

    return skills[skill]


def update_skill_progress(
    progress: dict,
    skill: str,
    mastery: float,
    questions_completed: int,
    first_attempt_streak: int,
    last_total_attempts: int | None = None,
    last_incorrect_attempts: int | None = None,
    last_hints_used: int | None = None,
    last_first_attempt_success: bool | None = None,
    last_completed: bool | None = None,
    recent_session: dict | None = None,
    family_history: dict | None = None,
) -> None:
    """
    Update persisted state for one skill.

    family_history is an optional Logical Reasoning
    field only. When a replacement value is supplied,
    it is allowlisted, bounded to the last 3 outcomes
    per family, and written only if non-empty. When
    omitted (None), any previously stored
    family_history is preserved. Unknown extra skill
    keys are not copied.
    """

    skills = progress.setdefault(
        "skills",
        {}
    )

    previous = skills.get(
        skill,
        {},
    )
    updated = {
        "mastery": round(
            float(mastery),
            4,
        ),
        "questions_completed": int(
            questions_completed
        ),
        "first_attempt_streak": int(
            first_attempt_streak
        ),
    }

    updated["last_total_attempts"] = int(
        last_total_attempts
        if last_total_attempts is not None
        else previous.get("last_total_attempts", 0)
    )
    updated["last_incorrect_attempts"] = int(
        last_incorrect_attempts
        if last_incorrect_attempts is not None
        else previous.get("last_incorrect_attempts", 0)
    )
    updated["last_hints_used"] = int(
        last_hints_used
        if last_hints_used is not None
        else previous.get("last_hints_used", 0)
    )
    updated["last_first_attempt_success"] = bool(
        last_first_attempt_success
        if last_first_attempt_success is not None
        else previous.get(
            "last_first_attempt_success",
            False,
        )
    )
    updated["last_completed"] = bool(
        last_completed
        if last_completed is not None
        else previous.get("last_completed", False)
    )

    sessions = bound_recent_sessions(
        previous.get("recent_sessions", []) or []
    )
    if recent_session is not None:
        sessions = bound_recent_sessions(
            [*sessions, recent_session]
        )

    updated["recent_sessions"] = sessions

    if family_history is not None:
        normalized_history = family_history_to_dict(
            family_history
        )
    else:
        normalized_history = family_history_to_dict(
            previous.get("family_history")
        )
    if normalized_history:
        updated["family_history"] = normalized_history

    skills[skill] = updated