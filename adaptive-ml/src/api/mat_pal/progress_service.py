from pathlib import Path

from src.api.mat_pal import adaptive_service
from src.api.mat_pal.schemas import (
    AdaptiveRecommendationResponse,
    StudentProgressResponse,
    TopicProgress,
)
from src.core.adaptive import (
    RuleBasedAdaptivePolicy,
)
from src.core.adaptive.policy import (
    HIGH_MASTERY_THRESHOLD,
    LOW_MASTERY_THRESHOLD,
)
from src.core.student_model.progress_store import (
    DEFAULT_PROGRESS_PATH,
)


def mastery_label(
    mastery: float,
) -> str:
    if mastery < LOW_MASTERY_THRESHOLD:
        return "Building"

    if mastery < HIGH_MASTERY_THRESHOLD:
        return "Developing"

    return "Strong"


def get_student_progress(
    subject: str | None = None,
    domain: str | None = None,
    path: Path = DEFAULT_PROGRESS_PATH,
) -> StudentProgressResponse:
    policy = RuleBasedAdaptivePolicy()
    topic_states = adaptive_service.list_topic_states(
        subject=subject,
        domain=domain,
        path=path,
    )
    sorted_topic_states = sorted(
        topic_states,
        key=lambda topic: (
            topic.subject,
            topic.domain,
            topic.topic_name,
        ),
    )
    recommendation = adaptive_service.recommend_next(
        subject=subject,
        domain=domain,
        path=path,
    )

    return StudentProgressResponse(
        student_id=adaptive_service.DEFAULT_STUDENT_ID,
        topics=[
            TopicProgress(
                subject=topic.subject,
                domain=topic.domain,
                topic=topic.topic,
                topic_name=topic.topic_name,
                mastery_key=topic.mastery_key,
                mastery=round(topic.mastery, 4),
                mastery_label=mastery_label(
                    topic.mastery
                ),
                questions_completed=(
                    topic.questions_completed
                ),
                first_attempt_streak=(
                    topic.first_attempt_streak
                ),
                last_total_attempts=(
                    topic.last_total_attempts
                ),
                last_incorrect_attempts=(
                    topic.last_incorrect_attempts
                ),
                last_hints_used=topic.last_hints_used,
                last_first_attempt_success=(
                    topic.last_first_attempt_success
                ),
                last_completed=topic.last_completed,
                generation_available=(
                    topic.generation_available
                ),
                supported_difficulties=(
                    list(topic.supported_difficulties)
                    if topic.generation_available
                    else []
                ),
                recommended_difficulty=(
                    policy.choose_difficulty(topic)
                    if topic.generation_available
                    else None
                ),
                problem_id=topic.problem_id,
                metadata={
                    "ordering": (
                        "subject, domain, topic_name"
                    ),
                },
            )
            for topic in sorted_topic_states
        ],
        recommendation=AdaptiveRecommendationResponse(
            recommendation_available=(
                recommendation.recommendation_available
            ),
            reason=recommendation.reason,
            subject=recommendation.subject,
            domain=recommendation.domain,
            topic=recommendation.topic,
            topic_name=recommendation.topic_name,
            difficulty=recommendation.difficulty,
            mastery=recommendation.mastery,
            mastery_key=recommendation.mastery_key,
            generation_available=(
                recommendation.generation_available
            ),
            problem_id=recommendation.problem_id,
            metadata=recommendation.metadata,
        ),
        metadata={
            "filters": {
                "subject": subject,
                "domain": domain,
            },
            "topic_grouping": "subject/domain/topic",
            "ordering": "subject, domain, topic_name",
        },
    )
