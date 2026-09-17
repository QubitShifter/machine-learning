from src.core.question_engine.contracts import QuestionRoute


_WEB_PHRASES = (
    "find sources",
    "find source",
    "look this up",
    "look up",
    "search the web",
    "search for",
    "external reference",
    "external source",
    "latest",
    "recent",
    "today",
    "newest",
    "current applications",
    "current research",
    "current developments",
    "who introduced",
    "who discovered",
    "who invented",
    "намери",
    "източник",
    "източници",
    "потърси",
    "търсене",
    "външен източник",
    "последни",
    "най-нови",
    "актуалн",
    "днес",
    "текущи приложения",
)


def wants_web_retrieval(question: str) -> bool:
    message = " ".join(question.strip().lower().split())
    return any(phrase in message for phrase in _WEB_PHRASES)


def route_question(
    *,
    local_match: bool,
    question: str,
) -> QuestionRoute:
    if local_match:
        return QuestionRoute.LOCAL_ONLY

    if wants_web_retrieval(question):
        return QuestionRoute.MODEL_WITH_WEB

    return QuestionRoute.MODEL_ONLY


def build_search_query(
    question: str,
    *,
    subject: str = "",
    domain: str = "",
    topic: str = "",
) -> str:
    parts = [
        topic.replace("_", " ").strip(),
        domain.replace("_", " ").strip(),
        subject.replace("_", " ").strip(),
        " ".join(question.split()),
    ]
    return " ".join(part for part in parts if part)
