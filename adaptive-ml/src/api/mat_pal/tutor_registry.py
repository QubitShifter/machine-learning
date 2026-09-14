from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import sympy as sp

from src.core.physics.kinematics.problems import (
    KINEMATICS_FIXED_PROBLEM_ID,
    load_fixed_kinematics_problem,
)
from src.core.tutor_engine.adapters import (
    KinematicsTutorAdapter,
    LinearODETutorAdapter,
    SeparableODETutorAdapter,
)
from src.core.tutor_engine.contracts import (
    ExpectedInputType,
    StudentSubmission,
    TutorResponse,
)
from src.core.tutor_engine.math_input_probe_engine import (
    MathInputProbeEngine,
)
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.reverse_reasoning_solver import (
    load_reverse_reasoning_problem,
    load_reverse_reasoning_problems,
)


MATH_INPUT_PROBE_PROBLEM_ID = "math_input_probe_001"
LINEAR_ODE_FIXED_PROBLEM_ID = "linear_first_order_fixed_001"
SEPARABLE_ODE_FIXED_PROBLEM_ID = "separable_ode_fixed_001"


class TutorEngine(Protocol):
    def get_current_response(self) -> TutorResponse:
        ...

    def submit(
        self,
        submission: StudentSubmission,
    ) -> TutorResponse:
        ...

    def request_hint(self) -> TutorResponse:
        ...


@dataclass(frozen=True)
class TutorRegistration:
    problem_id: str
    title: str
    problem_statement: str
    subject: str
    domain: str
    topic: str
    topic_name: str
    problem_type: str
    total_steps: int
    expected_input_type: ExpectedInputType
    create_engine: Callable[[], TutorEngine]
    grade: int | None = None
    language: str = "en"
    skills: tuple[str, ...] = ()
    metadata: dict | None = None
    catalog_visible: bool = True


class TutorRegistry:
    def __init__(self):
        self._registrations: dict[
            str,
            TutorRegistration,
        ] = {}

    def register(
        self,
        registration: TutorRegistration,
    ) -> None:
        if (
            registration.problem_id
            in self._registrations
        ):
            raise ValueError(
                "Tutor problem already registered: "
                f"{registration.problem_id}"
            )

        self._registrations[
            registration.problem_id
        ] = registration

    def get(
        self,
        problem_id: str,
    ) -> TutorRegistration:
        try:
            return self._registrations[problem_id]

        except KeyError as error:
            raise ValueError(
                f"Unknown problem_id: {problem_id}"
            ) from error

    def create_engine(
        self,
        problem_id: str,
    ) -> TutorEngine:
        registration = self.get(
            problem_id
        )

        return registration.create_engine()

    def list_registrations(
        self,
        catalog_visible: bool | None = None,
    ) -> list[TutorRegistration]:
        registrations = list(
            self._registrations.values()
        )

        if catalog_visible is None:
            return registrations

        return [
            registration
            for registration in registrations
            if (
                registration.catalog_visible
                == catalog_visible
            )
        ]


def build_default_tutor_registry() -> TutorRegistry:
    registry = TutorRegistry()

    _register_primary_school_tutors(
        registry
    )
    _register_math_input_probe(
        registry
    )
    _register_linear_ode_tutors(
        registry
    )
    _register_separable_ode_tutors(
        registry
    )
    _register_kinematics_tutors(
        registry
    )

    return registry


def _register_primary_school_tutors(
    registry: TutorRegistry,
) -> None:
    for problem in load_reverse_reasoning_problems():
        problem_id = problem.problem_id

        registry.register(
            TutorRegistration(
                problem_id=problem_id,
                title=problem.title,
                problem_statement=problem.problem_text,
                subject="mathematics",
                domain="primary_school",
                topic=problem.topic,
                topic_name="Word Problems",
                problem_type=(
                    problem.problem_type.value
                ),
                grade=problem.grade,
                total_steps=(
                    problem.get_number_of_steps()
                ),
                expected_input_type="text",
                language=problem.language,
                skills=tuple(problem.skills),
                metadata={
                    "strategy": problem.strategy,
                    "known": problem.known,
                    "unknown": problem.unknown,
                },
                create_engine=(
                    lambda problem_id=problem_id:
                        PrimarySchoolTutorEngine(
                            problem=(
                                load_reverse_reasoning_problem(
                                    problem_id
                                )
                            )
                        )
                ),
            )
        )


def _register_math_input_probe(
    registry: TutorRegistry,
) -> None:
    registry.register(
        TutorRegistration(
            problem_id=MATH_INPUT_PROBE_PROBLEM_ID,
            title=MathInputProbeEngine.problem_title,
            problem_statement=(
                MathInputProbeEngine.problem_statement
            ),
            subject="mathematics",
            domain="developer_tools",
            topic="math_input",
            topic_name="Math Input",
            problem_type="math_input_probe",
            total_steps=1,
            expected_input_type="math",
            create_engine=MathInputProbeEngine,
            catalog_visible=False,
        )
    )


def _register_linear_ode_tutors(
    registry: TutorRegistry,
) -> None:
    x = sp.symbols("x")
    p_expression = 2 * x
    q_expression = x

    registry.register(
        TutorRegistration(
            problem_id=LINEAR_ODE_FIXED_PROBLEM_ID,
            title="First-Order Linear ODE",
            problem_statement=(
                "Solve dy/dx + (2*x)*y = x"
            ),
            subject="mathematics",
            domain="ode",
            topic="first_order_linear",
            topic_name="First-Order Linear ODEs",
            problem_type="linear_first_order_ode",
            total_steps=8,
            expected_input_type="text",
            create_engine=(
                lambda: LinearODETutorAdapter(
                    p_expression=p_expression,
                    q_expression=q_expression,
                    problem_id=(
                        LINEAR_ODE_FIXED_PROBLEM_ID
                    ),
                )
            ),
            catalog_visible=True,
        )
    )


def _register_separable_ode_tutors(
    registry: TutorRegistry,
) -> None:
    x, y = sp.symbols("x y")
    rhs_expression = 2 * x * y

    registry.register(
        TutorRegistration(
            problem_id=SEPARABLE_ODE_FIXED_PROBLEM_ID,
            title="Separable ODE",
            problem_statement=(
                "Solve dy/dx = 2*x*y"
            ),
            subject="mathematics",
            domain="ode",
            topic="separable_equations",
            topic_name="Separable Equations",
            problem_type="separable_ode",
            total_steps=4,
            expected_input_type="math",
            create_engine=(
                lambda: SeparableODETutorAdapter(
                    rhs_expression=rhs_expression,
                    problem_id=(
                        SEPARABLE_ODE_FIXED_PROBLEM_ID
                    ),
                )
            ),
            catalog_visible=True,
        )
    )


def _register_kinematics_tutors(
    registry: TutorRegistry,
) -> None:
    problem = load_fixed_kinematics_problem()
    registry.register(
        TutorRegistration(
            problem_id=KINEMATICS_FIXED_PROBLEM_ID,
            title=problem.title,
            problem_statement=problem.statement,
            subject="physics",
            domain="classical_mechanics",
            topic="kinematics",
            topic_name="Kinematics",
            problem_type="kinematics_1d",
            total_steps=problem.total_steps(),
            expected_input_type="units",
            skills=("kinematics",),
            language="en",
            metadata={
                "generated": False,
                "description": (
                    "One-dimensional motion with "
                    "constant velocity and constant "
                    "acceleration."
                ),
            },
            catalog_visible=True,
            create_engine=(
                lambda: KinematicsTutorAdapter(problem)
            ),
        )
    )


DEFAULT_TUTOR_REGISTRY = build_default_tutor_registry()
