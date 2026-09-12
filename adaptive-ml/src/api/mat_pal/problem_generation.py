from collections.abc import Callable
from dataclasses import dataclass
import random
from uuid import uuid4

import sympy as sp

from src.api.mat_pal.tutor_registry import (
    TutorRegistration,
)
from src.core.question_generation.linear_first_order import (
    generate_linear_first_order_question,
)
from src.core.question_generation.separable import (
    generate_separable_question,
)
from src.core.tutor_engine.adapters import (
    LinearODETutorAdapter,
    SeparableODETutorAdapter,
)


GeneratorKey = tuple[str, str, str]


@dataclass(frozen=True)
class GeneratorRegistration:
    subject: str
    domain: str
    topic: str
    topic_name: str
    generator_name: str
    supported_difficulties: tuple[int, ...]
    create_problem: Callable[
        [int, int | None],
        TutorRegistration,
    ]


class ProblemGeneratorRegistry:
    def __init__(self) -> None:
        self._generators: dict[
            GeneratorKey,
            GeneratorRegistration,
        ] = {}

    def register(
        self,
        registration: GeneratorRegistration,
    ) -> None:
        key = (
            registration.subject,
            registration.domain,
            registration.topic,
        )

        if key in self._generators:
            raise ValueError(
                "Problem generator already registered: "
                f"{key}"
            )

        self._generators[key] = registration

    def get(
        self,
        subject: str,
        domain: str,
        topic: str,
    ) -> GeneratorRegistration:
        key = (subject, domain, topic)

        try:
            return self._generators[key]

        except KeyError as error:
            raise ValueError(
                "No generator is registered for "
                f"{subject}/{domain}/{topic}."
            ) from error

    def supports(
        self,
        subject: str,
        domain: str,
        topic: str,
    ) -> bool:
        return (
            subject,
            domain,
            topic,
        ) in self._generators

    def supported_difficulties(
        self,
        subject: str,
        domain: str,
        topic: str,
    ) -> tuple[int, ...]:
        if not self.supports(
            subject,
            domain,
            topic,
        ):
            return ()

        return self.get(
            subject,
            domain,
            topic,
        ).supported_difficulties

    def generate(
        self,
        subject: str,
        domain: str,
        topic: str,
        difficulty: int,
        seed: int | None = None,
    ) -> TutorRegistration:
        registration = self.get(
            subject=subject,
            domain=domain,
            topic=topic,
        )

        if difficulty not in registration.supported_difficulties:
            raise ValueError(
                "Unsupported difficulty "
                f"{difficulty} for {subject}/{domain}/{topic}. "
                "Supported difficulties: "
                f"{list(registration.supported_difficulties)}"
            )

        return registration.create_problem(
            difficulty,
            seed,
        )


def build_default_problem_generator_registry() -> (
    ProblemGeneratorRegistry
):
    registry = ProblemGeneratorRegistry()

    registry.register(
        GeneratorRegistration(
            subject="mathematics",
            domain="ode",
            topic="first_order_linear",
            topic_name="First-Order Linear ODEs",
            generator_name="linear_first_order",
            supported_difficulties=(1, 2, 3),
            create_problem=_create_linear_problem,
        )
    )
    registry.register(
        GeneratorRegistration(
            subject="mathematics",
            domain="ode",
            topic="separable_equations",
            topic_name="Separable Equations",
            generator_name="separable_equations",
            supported_difficulties=(1, 2, 3),
            create_problem=_create_separable_problem,
        )
    )

    return registry


def _rng_from_seed(
    seed: int | None,
) -> random.Random | None:
    if seed is None:
        return None

    return random.Random(seed)


def _generated_problem_id(
    prefix: str,
) -> str:
    return f"{prefix}_generated_{uuid4().hex[:12]}"


def _create_linear_problem(
    difficulty: int,
    seed: int | None,
) -> TutorRegistration:
    generated = generate_linear_first_order_question(
        difficulty=difficulty,
        rng=_rng_from_seed(seed),
    )
    p_expression = sp.sympify(
        generated["p_expression"]
    )
    q_expression = sp.sympify(
        generated["q_expression"]
    )
    problem_id = _generated_problem_id(
        "linear_first_order"
    )

    metadata = {
        "generated": True,
        "difficulty": difficulty,
        "generator_name": "linear_first_order",
        "seed": seed,
        "P": sp.sstr(p_expression),
        "Q": sp.sstr(q_expression),
    }

    return TutorRegistration(
        problem_id=problem_id,
        title="Generated First-Order Linear ODE",
        problem_statement=generated["question"],
        subject="mathematics",
        domain="ode",
        topic="first_order_linear",
        topic_name="First-Order Linear ODEs",
        problem_type="linear_first_order_ode",
        total_steps=8,
        expected_input_type="text",
        skills=("linear_ode", "integrating_factor"),
        metadata=metadata,
        catalog_visible=False,
        create_engine=(
            lambda: LinearODETutorAdapter(
                p_expression=p_expression,
                q_expression=q_expression,
                problem_id=problem_id,
            )
        ),
    )


def _create_separable_problem(
    difficulty: int,
    seed: int | None,
) -> TutorRegistration:
    generated = generate_separable_question(
        difficulty=difficulty,
        rng=_rng_from_seed(seed),
    )
    rhs_expression = sp.sympify(
        generated["rhs_expression"]
    )
    problem_id = _generated_problem_id(
        "separable_ode"
    )

    metadata = {
        "generated": True,
        "difficulty": difficulty,
        "generator_name": "separable_equations",
        "seed": seed,
        "rhs_expression": sp.sstr(rhs_expression),
    }

    return TutorRegistration(
        problem_id=problem_id,
        title="Generated Separable ODE",
        problem_statement=generated["question"],
        subject="mathematics",
        domain="ode",
        topic="separable_equations",
        topic_name="Separable Equations",
        problem_type="separable_ode",
        total_steps=4,
        expected_input_type="math",
        skills=tuple(generated.get("skills", ())),
        metadata=metadata,
        catalog_visible=False,
        create_engine=(
            lambda: SeparableODETutorAdapter(
                rhs_expression=rhs_expression,
                problem_id=problem_id,
            )
        ),
    )


DEFAULT_PROBLEM_GENERATOR_REGISTRY = (
    build_default_problem_generator_registry()
)
