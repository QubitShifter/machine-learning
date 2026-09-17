from dataclasses import replace
import logging

from src.core.i18n.question import (
    question_continue_message,
    question_fallback_message,
    question_web_unavailable_message,
)
from src.core.question_engine.context import (
    build_model_prompt,
    sanitize_tutor_metadata,
)
from src.core.question_engine.contracts import (
    QuestionRoute,
    TutorModelProvider,
    TutorQuestionContext,
    TutorQuestionRequest,
    TutorQuestionResult,
    WebSearchProvider,
)
from src.core.question_engine.local_guidance import match_local_concept
from src.core.question_engine.providers import (
    ModelProviderError,
    NullTutorModelProvider,
    NullWebSearchProvider,
    WebSearchProviderError,
)
from src.core.question_engine.grounding import enrich_question_context
from src.core.question_engine.routing import (
    build_search_query,
    route_question,
    wants_web_retrieval,
)
from src.core.question_engine.sources import (
    DEFAULT_USEFUL_RESULTS,
    MAX_SEARCH_RESULTS,
    bound_sources,
)


logger = logging.getLogger(__name__)


class GeneralTutorQuestionEngine:
    def __init__(
        self,
        *,
        model_provider: TutorModelProvider | None = None,
        web_search_provider: WebSearchProvider | None = None,
    ):
        self.model_provider = (
            model_provider or NullTutorModelProvider()
        )
        self.web_search_provider = (
            web_search_provider or NullWebSearchProvider()
        )

    def answer(
        self,
        request: TutorQuestionRequest,
        context: TutorQuestionContext,
    ) -> TutorQuestionResult:
        question = " ".join(request.question.split()).strip()
        context = enrich_question_context(context)
        wants_web = wants_web_retrieval(question)
        local = (
            None
            if wants_web
            else match_local_concept(question, context)
        )
        route = route_question(
            local_match=local is not None,
            question=question,
        )

        if route == QuestionRoute.LOCAL_ONLY and local:
            return TutorQuestionResult(
                answer=local,
                answer_source="local",
                sources=(),
                used_web=False,
                route=route,
                metadata={"matched_local_concept": True},
            )

        sources = ()
        used_web = False
        web_failed = False

        if route == QuestionRoute.MODEL_WITH_WEB:
            query = build_search_query(
                question,
                subject=context.subject,
                domain=context.domain,
                topic=context.topic,
            )

            try:
                raw_sources = self.web_search_provider.search(
                    query,
                    max_results=MAX_SEARCH_RESULTS,
                )
                sources = bound_sources(
                    raw_sources,
                    limit=DEFAULT_USEFUL_RESULTS,
                )
                used_web = len(sources) > 0
            except WebSearchProviderError:
                logger.warning(
                    "Question engine web search failed; "
                    "continuing without retrieved sources."
                )
                web_failed = True

        if not self.model_provider.is_available():
            return TutorQuestionResult(
                answer=question_fallback_message(
                    context.language,
                ),
                answer_source="fallback",
                sources=(),
                used_web=False,
                route=route,
                metadata={"model_unavailable": True},
            )

        prompt = build_model_prompt(
            question=question,
            context=context,
            sources=sources,
        )
        external_context = replace(
            context,
            session_id=None,
            student_id=None,
            tutor_metadata=sanitize_tutor_metadata(
                context.tutor_metadata,
            ),
        )

        try:
            model_answer = self.model_provider.answer(
                question=question,
                context=external_context,
                sources=sources,
                prompt=prompt,
            )
        except ModelProviderError:
            logger.warning(
                "Question engine model provider failed."
            )
            return TutorQuestionResult(
                answer=question_fallback_message(
                    context.language,
                ),
                answer_source="fallback",
                sources=(),
                used_web=False,
                route=route,
                metadata={"model_failed": True},
            )

        answer = model_answer.text.strip()

        if web_failed and answer:
            notice = question_web_unavailable_message(
                context.language,
            )
            answer = f"{notice}\n\n{answer}"

        return TutorQuestionResult(
            answer=answer,
            answer_source="web" if used_web else "model",
            sources=sources if used_web else (),
            used_web=used_web,
            route=route,
            metadata={
                "suggestion": question_continue_message(
                    context.language,
                ),
            },
        )
