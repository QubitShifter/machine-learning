from src.core.imported_problem.openai_compatible import (
    DEFAULT_PLANNER_TIMEOUT_SECONDS,
    OpenAICompatibleImportedProblemPlanner,
)
from src.core.imported_problem.planner import (
    NullImportedProblemPlanner,
)
from src.core.question_engine.providers import (
    coerce_model_timeout_seconds,
    env_flag,
)


DEFAULT_PLANNER_BASE_URL = "https://api.openai.com/v1"


def build_imported_planner_from_env():
    provider_name = env_flag(
        "MATPAL_MODEL_PROVIDER",
        "none",
    ).lower()

    if provider_name not in {"openai", "openai_compatible"}:
        return NullImportedProblemPlanner()

    api_key = env_flag("MATPAL_MODEL_API_KEY")
    base_url = env_flag(
        "MATPAL_MODEL_BASE_URL",
        DEFAULT_PLANNER_BASE_URL,
    )
    model = env_flag(
        "MATPAL_IMPORTED_PROBLEM_MODEL_NAME",
        env_flag("MATPAL_MODEL_NAME"),
    )
    timeout_raw = env_flag("MATPAL_MODEL_TIMEOUT_SECONDS")
    timeout_seconds = (
        coerce_model_timeout_seconds(timeout_raw)
        if timeout_raw
        else DEFAULT_PLANNER_TIMEOUT_SECONDS
    )

    if not api_key or not model or not base_url:
        return NullImportedProblemPlanner()

    return OpenAICompatibleImportedProblemPlanner(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
    )
