from src.api.mat_pal.schemas import (
    CatalogDomain,
    CatalogResponse,
    CatalogSubject,
    CatalogTopic,
    ProblemDetail,
    ProblemSummary,
)
from src.core.tutor_engine.primary_school.problem_types import (
    PrimarySchoolProblem,
)
from src.core.tutor_engine.primary_school.reverse_reasoning_solver import (
    load_reverse_reasoning_problem,
    load_reverse_reasoning_problems,
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
    problem: PrimarySchoolProblem,
) -> ProblemSummary:
    return ProblemSummary(
        problem_id=problem.problem_id,
        title=problem.title,
        subject="mathematics",
        domain="primary_school",
        topic=problem.topic,
        problem_type=problem.problem_type.value,
        grade=problem.grade,
        total_steps=problem.get_number_of_steps(),
        expected_input_type="text",
    )


def _problem_detail(
    problem: PrimarySchoolProblem,
) -> ProblemDetail:
    summary = _problem_summary(
        problem
    )

    return ProblemDetail(
        **summary.model_dump(),
        problem_text=problem.problem_text,
        language=problem.language,
        skills=problem.skills,
        metadata={
            "strategy": problem.strategy,
            "known": problem.known,
            "unknown": problem.unknown,
        },
    )


def list_problems() -> list[ProblemSummary]:
    problems = load_reverse_reasoning_problems()

    return [
        _problem_summary(
            problem
        )
        for problem in problems
    ]


def get_problem(
    problem_id: str,
) -> ProblemDetail:
    problem = load_reverse_reasoning_problem(
        problem_id
    )

    return _problem_detail(
        problem
    )


def get_catalog() -> CatalogResponse:
    available_problems = list_problems()
    primary_school_topics = [
        CatalogTopic(
            id="word_problems",
            name="Word Problems",
            available_problem_count=len(
                available_problems
            ),
            problem_ids=[
                problem.problem_id
                for problem in available_problems
            ],
        )
    ]

    mathematics_domains = []

    for domain_id, domain_name in MATHEMATICS_DOMAINS:
        topics = (
            primary_school_topics
            if domain_id == "primary_school"
            else []
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
