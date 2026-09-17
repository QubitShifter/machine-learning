from urllib.parse import urlparse

from src.core.question_engine.contracts import TutorSource


MAX_SEARCH_RESULTS = 5
DEFAULT_USEFUL_RESULTS = 3
MAX_SNIPPET_LENGTH = 280

_PREFERRED_DOMAIN_MARKERS = (
    ".edu",
    "openstax.org",
    "libretexts.org",
    "arxiv.org",
    "wikipedia.org",
    "khanacademy.org",
    "nist.gov",
    "nasa.gov",
)


def source_domain(url: str) -> str | None:
    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    host = (parsed.hostname or "").lower().strip()
    if host.startswith("www."):
        host = host[4:]

    return host or None


def clip_snippet(snippet: str | None) -> str | None:
    if snippet is None:
        return None

    text = " ".join(str(snippet).split())
    if len(text) <= MAX_SNIPPET_LENGTH:
        return text or None

    return text[: MAX_SNIPPET_LENGTH - 1].rstrip() + "…"


def rank_sources(
    sources: tuple[TutorSource, ...],
) -> tuple[TutorSource, ...]:
    def score(source: TutorSource) -> tuple[int, str]:
        domain = (source.domain or source_domain(source.url) or "")
        preferred = any(
            marker in domain
            for marker in _PREFERRED_DOMAIN_MARKERS
        )
        return (0 if preferred else 1, domain)

    ranked = sorted(sources, key=score)
    return tuple(ranked)


def bound_sources(
    sources: tuple[TutorSource, ...],
    *,
    limit: int = DEFAULT_USEFUL_RESULTS,
) -> tuple[TutorSource, ...]:
    ranked = rank_sources(sources)[:limit]
    bounded: list[TutorSource] = []

    for source in ranked:
        bounded.append(
            TutorSource(
                title=source.title.strip() or source.url,
                url=source.url,
                domain=source.domain or source_domain(source.url),
                snippet=clip_snippet(source.snippet),
            )
        )

    return tuple(bounded)


def public_sources(
    sources: tuple[TutorSource, ...],
) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []

    for source in sources:
        item = {
            "title": source.title,
            "url": source.url,
        }
        if source.domain:
            item["domain"] = source.domain
        payload.append(item)

    return payload
