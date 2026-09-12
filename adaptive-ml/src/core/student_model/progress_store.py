import json
from pathlib import Path


DEFAULT_PROGRESS_PATH = Path(
    "math/ode/data/student_progress.json"
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
) -> None:
    """
    Update persisted state for one skill.
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

    skills[skill] = updated