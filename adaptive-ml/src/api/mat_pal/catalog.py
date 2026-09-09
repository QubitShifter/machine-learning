from src.api.mat_pal.schemas import (
    CatalogDomain,
    CatalogResponse,
    CatalogSubject,
    CatalogTopic,
    ProblemDetail,
    ProblemSummary,
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
    registration = DEFAULT_TUTOR_REGISTRY.get(
        problem_id
    )

    if not registration.catalog_visible:
        raise ValueError(
            f"Problem is not catalog-visible: {problem_id}"
        )

    return _problem_detail(
        registration
    )


def _topics_for_domain(
    registrations: list[TutorRegistration],
    domain_id: str,
) -> list[CatalogTopic]:
    topic_records: dict[
        str,
        dict,
    ] = {}

    for registration in registrations:
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

    mathematics_domains = []

    for domain_id, domain_name in MATHEMATICS_DOMAINS:
        topics = _topics_for_domain(
            registrations=registrations,
            domain_id=domain_id,
        )
        available_problem_count = sum(
            topic.available_problem_count
            for topic in topics
        )

        mathematics_domains.append(
            CatalogDomain(
                id=domain_id,
                name=domain_name,
                available_problem_count=(
                    available_problem_count
                ),
                topics=topics,
            )
        )

    physics_domains = [
        CatalogDomain(
            id=domain_id,
            name=domain_name,
            available_problem_count=0,
            topics=[],
        )
        for domain_id, domain_name in PHYSICS_DOMAINS
    ]

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
                available_problem_count=0,
                domains=physics_domains,
            ),
        ]
    )
