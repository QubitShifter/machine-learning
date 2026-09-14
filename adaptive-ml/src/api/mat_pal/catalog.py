from src.api.mat_pal.schemas import (
    CatalogDomain,
    CatalogResponse,
    CatalogSubject,
    CatalogTopic,
    ProblemDetail,
    ProblemSummary,
)
from src.api.mat_pal.generated_problem_store import (
    add_generated_problem,
    get_generated_problem,
)
from src.api.mat_pal.problem_generation import (
    DEFAULT_PROBLEM_GENERATOR_REGISTRY,
)
from src.api.mat_pal.tutor_registry import (
    DEFAULT_TUTOR_REGISTRY,
    TutorRegistration,
)


MATHEMATICS_DOMAINS = [
    ("primary_school", "Primary School"),
    ("calculus", "Calculus"),
    ("ode", "ODE"),
    ("linear_algebra", "Linear Algebra"),
    ("geometry", "Geometry"),
    ("probability", "Probability"),
    ("statistics", "Statistics"),
]

PHYSICS_DOMAINS = [
    ("classical_mechanics", "Classical Mechanics"),
    ("electricity_and_magnetism", "Electricity and Magnetism"),
    ("waves", "Waves"),
    ("thermodynamics", "Thermodynamics"),
    ("optics", "Optics"),
    ("modern_physics", "Modern Physics"),
]


def _problem_summary(
    registration: TutorRegistration,
) -> ProblemSummary:
    metadata = registration.metadata or {}
    generated = bool(metadata.get("generated", False))
    supported_difficulties = (
        DEFAULT_PROBLEM_GENERATOR_REGISTRY
        .supported_difficulties(
            subject=registration.subject,
            domain=registration.domain,
            topic=registration.topic,
        )
    )

    return ProblemSummary(
        problem_id=registration.problem_id,
        title=registration.title,
        subject=registration.subject,
        domain=registration.domain,
        topic=registration.topic,
        problem_type=registration.problem_type,
        grade=registration.grade,
        total_steps=registration.total_steps,
        expected_input_type=(
            registration.expected_input_type
        ),
        generated=generated,
        generation_available=bool(
            supported_difficulties
        ),
        supported_difficulties=list(
            supported_difficulties
        ),
    )


def _problem_detail(
    registration: TutorRegistration,
) -> ProblemDetail:
    summary = _problem_summary(
        registration
    )

    return ProblemDetail(
        **summary.model_dump(),
        problem_text=registration.problem_statement,
        language=registration.language,
        skills=list(registration.skills),
        metadata=registration.metadata or {},
    )


def list_problems() -> list[ProblemSummary]:
    registrations = (
        DEFAULT_TUTOR_REGISTRY
        .list_registrations(
            catalog_visible=True
        )
    )

    return [
        _problem_summary(
            registration
        )
        for registration in registrations
    ]


def get_problem(
    problem_id: str,
) -> ProblemDetail:
    try:
        registration = DEFAULT_TUTOR_REGISTRY.get(
            problem_id
        )

        if not registration.catalog_visible:
            raise ValueError(
                "Problem is not catalog-visible: "
                f"{problem_id}"
            )

    except ValueError:
        registration = get_generated_problem(
            problem_id
        )

        if registration is None:
            raise ValueError(
                f"Unknown problem_id: {problem_id}"
            )

    return _problem_detail(
        registration
    )


def generate_problem(
    subject: str,
    domain: str,
    topic: str,
    difficulty: int,
    seed: int | None = None,
) -> ProblemDetail:
    registration = (
        DEFAULT_PROBLEM_GENERATOR_REGISTRY
        .generate(
            subject=subject,
            domain=domain,
            topic=topic,
            difficulty=difficulty,
            seed=seed,
        )
    )
    add_generated_problem(registration)

    return _problem_detail(registration)


def _topics_for_domain(
    registrations: list[TutorRegistration],
    subject: str,
    domain_id: str,
) -> list[CatalogTopic]:
    topic_records: dict[
        str,
        dict,
    ] = {}

    for registration in registrations:
        if registration.subject != subject:
            continue

        if registration.domain != domain_id:
            continue

        topic_record = topic_records.setdefault(
            registration.topic,
            {
                "name": registration.topic_name,
                "problem_ids": [],
            },
        )
        topic_record["problem_ids"].append(
            registration.problem_id
        )

    return [
        CatalogTopic(
            id=topic_id,
            name=topic_record["name"],
            available_problem_count=len(
                topic_record["problem_ids"]
            ),
            problem_ids=topic_record[
                "problem_ids"
            ],
            generation_available=(
                DEFAULT_PROBLEM_GENERATOR_REGISTRY
                .supports(
                    subject=subject,
                    domain=domain_id,
                    topic=topic_id,
                )
            ),
            supported_difficulties=list(
                DEFAULT_PROBLEM_GENERATOR_REGISTRY
                .supported_difficulties(
                    subject=subject,
                    domain=domain_id,
                    topic=topic_id,
                )
            ),
        )
        for topic_id, topic_record
        in topic_records.items()
    ]


def get_catalog() -> CatalogResponse:
    registrations = (
        DEFAULT_TUTOR_REGISTRY
        .list_registrations(
            catalog_visible=True
        )
    )

    mathematics_domains = _domains_for_subject(
        registrations,
        "mathematics",
        MATHEMATICS_DOMAINS,
    )
    physics_domains = _domains_for_subject(
        registrations,
        "physics",
        PHYSICS_DOMAINS,
    )

    return CatalogResponse(
        subjects=[
            CatalogSubject(
                id="mathematics",
                name="Mathematics",
                available_problem_count=sum(
                    domain.available_problem_count
                    for domain in mathematics_domains
                ),
                domains=mathematics_domains,
            ),
            CatalogSubject(
                id="physics",
                name="Physics",
                available_problem_count=sum(
                    domain.available_problem_count
                    for domain in physics_domains
                ),
                domains=physics_domains,
            ),
        ]
    )


def _domains_for_subject(
    registrations: list[TutorRegistration],
    subject: str,
    domain_pairs: list[tuple[str, str]],
) -> list[CatalogDomain]:
    domains = []

    for domain_id, domain_name in domain_pairs:
        topics = _topics_for_domain(
            registrations=registrations,
            subject=subject,
            domain_id=domain_id,
        )
        domains.append(
            CatalogDomain(
                id=domain_id,
                name=domain_name,
                available_problem_count=sum(
                    topic.available_problem_count
                    for topic in topics
                ),
                topics=topics,
            )
        )

    return domains
