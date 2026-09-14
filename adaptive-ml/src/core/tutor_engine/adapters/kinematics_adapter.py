from src.core.physics.kinematics.engine import (
    KinematicsTutorEngine,
)
from src.core.physics.kinematics.models import (
    KinematicsProblem,
)
from src.core.physics.kinematics.problems import (
    load_fixed_kinematics_problem,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
    TutorResponse,
)


class KinematicsTutorAdapter:
    def __init__(
        self,
        problem: KinematicsProblem | None = None,
    ):
        self.engine = KinematicsTutorEngine(
            problem or load_fixed_kinematics_problem()
        )

    def get_current_response(self) -> TutorResponse:
        return self.engine.get_current_response()

    def submit(
        self,
        submission: StudentSubmission,
    ) -> TutorResponse:
        return self.engine.submit(submission)

    def request_hint(self) -> TutorResponse:
        return self.engine.request_hint()
