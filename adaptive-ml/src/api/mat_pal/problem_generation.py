from collections.abc import Callable
from dataclasses import dataclass
import random
from uuid import uuid4

import sympy as sp

from src.core.i18n.locale import normalize_locale
from src.core.i18n.ode import ot
from src.api.mat_pal.tutor_registry import (
    TutorRegistration,
)
from src.core.question_generation.linear_first_order import (
    generate_linear_first_order_question,
)
from src.core.question_generation.separable import (
    generate_separable_question,
)
from src.core.physics.kinematics.generator import (
    assign_problem_id,
    generate_kinematics_problem,
)
from src.core.tutor_engine.adapters import (
    KinematicsTutorAdapter,
    LinearODETutorAdapter,
    SeparableODETutorAdapter,
)
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.generation import (
    generate_arithmetic_problem,
    generate_sequence_or_chain_problem,
    generate_unknown_number_problem,
    localize_generated_primary_school,
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
        [int, int | None, str],
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

    def list_registrations(
        self,
    ) -> list[GeneratorRegistration]:
        return list(self._generators.values())

    def generate(
        self,
        subject: str,
        domain: str,
        topic: str,
        difficulty: int,
        seed: int | None = None,
        language: str = "en",
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

        locale = normalize_locale(language)
        return registration.create_problem(
            difficulty,
            seed,
            locale,
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
    registry.register(
        GeneratorRegistration(
            subject="physics",
            domain="classical_mechanics",
            topic="kinematics",
            topic_name="Kinematics",
            generator_name="kinematics_1d",
            supported_difficulties=(1, 2, 3),
            create_problem=_create_kinematics_problem,
        )
    )
    registry.register(
        GeneratorRegistration(
            subject="mathematics",
            domain="primary_school",
            topic="arithmetic",
            topic_name="Arithmetic",
            generator_name="grade4_arithmetic",
            supported_difficulties=(1, 2, 3),
            create_problem=_create_arithmetic_problem,
        )
    )
    registry.register(
        GeneratorRegistration(
            subject="mathematics",
            domain="primary_school",
            topic="unknown_numbers",
            topic_name="Unknown Numbers",
            generator_name="grade4_unknown_number",
            supported_difficulties=(1, 2, 3),
            create_problem=_create_unknown_number_problem,
        )
    )
    registry.register(
        GeneratorRegistration(
            subject="mathematics",
            domain="primary_school",
            topic="number_patterns",
            topic_name="Number Patterns",
            generator_name="grade4_number_patterns",
            supported_difficulties=(1, 2, 3),
            create_problem=_create_number_patterns_problem,
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
    language: str = "en",
) -> TutorRegistration:
    locale = normalize_locale(language)
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
        language=locale,
        title=ot(locale, "linear.title.generated"),
        problem_statement=ot(
            locale,
            "linear.statement",
            equation=(
                "dy/dx + "
                f"({sp.sstr(p_expression)})*y "
                f"= {sp.sstr(q_expression)}"
            ),
        ),
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
            lambda language="en": LinearODETutorAdapter(
                p_expression=p_expression,
                q_expression=q_expression,
                problem_id=problem_id,
                language=language,
            )
        ),
    )


def _create_separable_problem(
    difficulty: int,
    seed: int | None,
    language: str = "en",
) -> TutorRegistration:
    locale = normalize_locale(language)
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
        language=locale,
        title=ot(locale, "separable.title.generated"),
        problem_statement=ot(
            locale,
            "separable.statement",
            equation=(
                "dy/dx = "
                f"{sp.sstr(rhs_expression)}"
            ),
        ),
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
            lambda language="en": SeparableODETutorAdapter(
                rhs_expression=rhs_expression,
                problem_id=problem_id,
                language=language,
            )
        ),
    )


def _create_kinematics_problem(
    difficulty: int,
    seed: int | None,
    language: str = "en",
) -> TutorRegistration:
    locale = normalize_locale(language)
    generated = generate_kinematics_problem(
        difficulty=difficulty,
        seed=seed,
        rng=_rng_from_seed(seed),
        language=locale,
    )
    problem_id = _generated_problem_id("kinematics")
    problem = assign_problem_id(generated, problem_id)
    metadata = {
        **problem.metadata,
        "generated": True,
        "difficulty": difficulty,
        "generator_name": "kinematics_1d",
        "seed": seed,
    }

    return TutorRegistration(
        problem_id=problem_id,
        title=problem.title,
        problem_statement=problem.statement,
        subject="physics",
        domain="classical_mechanics",
        topic="kinematics",
        topic_name="Kinematics",
        problem_type="kinematics_1d",
        total_steps=problem.total_steps(),
        expected_input_type=problem.steps[0].input_type,
        skills=("kinematics",),
        metadata=metadata,
        catalog_visible=False,
        language=locale,
        create_engine=(
            lambda language="en", current=problem:
                KinematicsTutorAdapter(
                    current,
                    language=language,
                )
        ),
    )


def _create_primary_school_registration(
    problem,
    *,
    prefix: str,
    topic: str,
    topic_name: str,
    generator_name: str,
    difficulty: int,
    seed: int | None,
    language: str,
) -> TutorRegistration:
    locale = normalize_locale(language)
    problem_id = _generated_problem_id(prefix)
    problem.problem_id = problem_id
    source_metadata = dict(problem.metadata or {})
    known = getattr(problem, "known", None) or {}
    public_metadata = {
        "generated": True,
        "difficulty": difficulty,
        "generator_name": generator_name,
        "seed": seed,
        "family": source_metadata.get("family"),
        "variant": source_metadata.get("variant"),
        "shape": source_metadata.get("shape"),
        "form": source_metadata.get("form"),
        "direction": source_metadata.get("direction"),
        "answer_format": source_metadata.get("answer_format"),
    }
    equation = known.get("equation")
    if isinstance(equation, str) and equation:
        public_metadata["equation"] = equation
    problem.metadata = {
        **source_metadata,
        **public_metadata,
    }
    first_step = problem.solution_steps[0]
    return TutorRegistration(
        problem_id=problem_id,
        title=problem.title,
        problem_statement=problem.problem_text,
        subject="mathematics",
        domain="primary_school",
        topic=topic,
        topic_name=topic_name,
        problem_type=problem.problem_type.value,
        total_steps=problem.get_number_of_steps(),
        expected_input_type=(
            first_step.input_type or "number"
        ),
        skills=tuple(problem.skills),
        metadata=public_metadata,
        catalog_visible=False,
        language=locale,
        grade=problem.grade,
        create_engine=(
            lambda language="en", current=problem:
                PrimarySchoolTutorEngine(
                    problem=localize_generated_primary_school(
                        current,
                        language,
                    )
                )
        ),
    )


def _create_arithmetic_problem(
    difficulty: int,
    seed: int | None,
    language: str = "en",
) -> TutorRegistration:
    locale = normalize_locale(language)
    problem = generate_arithmetic_problem(
        difficulty=difficulty,
        seed=seed,
        rng=_rng_from_seed(seed),
        language=locale,
    )
    return _create_primary_school_registration(
        problem,
        prefix="grade4_arithmetic",
        topic="arithmetic",
        topic_name="Arithmetic",
        generator_name="grade4_arithmetic",
        difficulty=difficulty,
        seed=seed,
        language=locale,
    )


def _create_unknown_number_problem(
    difficulty: int,
    seed: int | None,
    language: str = "en",
) -> TutorRegistration:
    locale = normalize_locale(language)
    problem = generate_unknown_number_problem(
        difficulty=difficulty,
        seed=seed,
        rng=_rng_from_seed(seed),
        language=locale,
    )
    return _create_primary_school_registration(
        problem,
        prefix="grade4_unknown_number",
        topic="unknown_numbers",
        topic_name="Unknown Numbers",
        generator_name="grade4_unknown_number",
        difficulty=difficulty,
        seed=seed,
        language=locale,
    )


def _create_number_patterns_problem(
    difficulty: int,
    seed: int | None,
    language: str = "en",
) -> TutorRegistration:
    locale = normalize_locale(language)
    problem = generate_sequence_or_chain_problem(
        difficulty=difficulty,
        seed=seed,
        rng=_rng_from_seed(seed),
        language=locale,
    )
    return _create_primary_school_registration(
        problem,
        prefix="grade4_number_patterns",
        topic="number_patterns",
        topic_name="Number Patterns",
        generator_name="grade4_number_patterns",
        difficulty=difficulty,
        seed=seed,
        language=locale,
    )


DEFAULT_PROBLEM_GENERATOR_REGISTRY = (
    build_default_problem_generator_registry()
)
