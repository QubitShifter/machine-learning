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
        }

    return skills[skill]


def update_skill_progress(
    progress: dict,
    skill: str,
    mastery: float,
    questions_completed: int,
    first_attempt_streak: int,
) -> None:
    """
    Update persisted state for one skill.
    """

    skills = progress.setdefault(
        "skills",
        {}
    )

    skills[skill] = {
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