from src.core.i18n.locale import normalize_locale
from src.core.physics.kinematics.engine import (
    KinematicsTutorEngine,
)
from src.core.physics.kinematics.models import (
    KinematicsProblem,
)
from src.core.physics.kinematics.problems import (
    load_fixed_kinematics_problem,
    localize_kinematics_problem,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
    TutorResponse,
)


class KinematicsTutorAdapter:
    def __init__(
        self,
        problem: KinematicsProblem | None = None,
        language: str | None = None,
    ):
        locale = normalize_locale(language)
        loaded = problem or load_fixed_kinematics_problem(
            locale
        )
        self.engine = KinematicsTutorEngine(
            localize_kinematics_problem(loaded, locale)
        )

    @property
    def problem_title(self) -> str:
        return self.engine.problem.title

    @property
    def problem_statement(self) -> str:
        return self.engine.problem.statement

    def get_current_response(self) -> TutorResponse:
        return self.engine.get_current_response()

    def submit(
        self,
        submission: StudentSubmission,
    ) -> TutorResponse:
        return self.engine.submit(submission)

    def request_hint(self) -> TutorResponse:
        return self.engine.request_hint()
