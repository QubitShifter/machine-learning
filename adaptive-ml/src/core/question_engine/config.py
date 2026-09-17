from src.core.question_engine.engine import (
    GeneralTutorQuestionEngine,
)
from src.core.question_engine.providers import (
    HttpWebSearchProvider,
    NullTutorModelProvider,
    NullWebSearchProvider,
    OpenAICompatibleTutorModelProvider,
    coerce_model_timeout_seconds,
    env_flag,
)


def build_question_engine_from_env() -> GeneralTutorQuestionEngine:
    model_name = env_flag(
        "MATPAL_MODEL_PROVIDER",
        "none",
    ).lower()
    search_name = env_flag(
        "MATPAL_WEB_SEARCH_PROVIDER",
        "none",
    ).lower()

    model_provider: NullTutorModelProvider | OpenAICompatibleTutorModelProvider
    web_provider: NullWebSearchProvider | HttpWebSearchProvider

    if model_name in {"openai", "openai_compatible"}:
        api_key = env_flag("MATPAL_MODEL_API_KEY")
        base_url = env_flag(
            "MATPAL_MODEL_BASE_URL",
            "https://api.openai.com/v1",
        )
        model = env_flag(
            "MATPAL_MODEL_NAME",
            "gpt-4.1-mini",
        )
        timeout_seconds = coerce_model_timeout_seconds(
            env_flag("MATPAL_MODEL_TIMEOUT_SECONDS"),
        )

        if api_key:
            model_provider = OpenAICompatibleTutorModelProvider(
                api_key=api_key,
                base_url=base_url,
                model=model,
                timeout_seconds=timeout_seconds,
            )
        else:
            model_provider = NullTutorModelProvider()
    else:
        model_provider = NullTutorModelProvider()

    if search_name in {"http", "web"}:
        search_url = env_flag("MATPAL_WEB_SEARCH_URL")

        if search_url:
            web_provider = HttpWebSearchProvider(
                url=search_url,
                api_key=env_flag("MATPAL_WEB_SEARCH_API_KEY")
                or None,
            )
        else:
            web_provider = NullWebSearchProvider()
    else:
        web_provider = NullWebSearchProvider()

    return GeneralTutorQuestionEngine(
        model_provider=model_provider,
        web_search_provider=web_provider,
    )
