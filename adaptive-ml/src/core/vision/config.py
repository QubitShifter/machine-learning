import logging
import math

from src.core.question_engine.providers import env_flag
from src.core.vision.extractor import (
    NullVisionExtractor,
    VisionExtractor,
)
from src.core.vision.openai_compatible import (
    OpenAICompatibleVisionExtractor,
)


logger = logging.getLogger(__name__)

DEFAULT_VISION_TIMEOUT_SECONDS = 45.0
MIN_VISION_TIMEOUT_SECONDS = 1.0
MAX_VISION_TIMEOUT_SECONDS = 600.0
DEFAULT_VISION_BASE_URL = "https://api.openai.com/v1"


def build_vision_extractor_from_env() -> VisionExtractor:
    provider_name = env_flag(
        "MATPAL_VISION_PROVIDER",
        "none",
    ).lower()

    if provider_name not in {
        "openai",
        "openai_compatible",
    }:
        return NullVisionExtractor()

    api_key = env_flag("MATPAL_MODEL_API_KEY")
    base_url = env_flag(
        "MATPAL_MODEL_BASE_URL",
        DEFAULT_VISION_BASE_URL,
    )
    model = env_flag("MATPAL_VISION_MODEL_NAME")
    timeout_seconds = coerce_vision_timeout_seconds(
        env_flag("MATPAL_VISION_TIMEOUT_SECONDS")
    )

    if not api_key or not model or not base_url:
        return NullVisionExtractor()

    return OpenAICompatibleVisionExtractor(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
    )


def coerce_vision_timeout_seconds(
    value: object,
) -> float:
    if value is None:
        return DEFAULT_VISION_TIMEOUT_SECONDS

    if isinstance(value, bool):
        logger.warning(
            "Invalid MATPAL_VISION_TIMEOUT_SECONDS; "
            "using default %ss.",
            int(DEFAULT_VISION_TIMEOUT_SECONDS),
        )
        return DEFAULT_VISION_TIMEOUT_SECONDS

    if isinstance(value, str) and not value.strip():
        return DEFAULT_VISION_TIMEOUT_SECONDS

    try:
        timeout = float(value)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid MATPAL_VISION_TIMEOUT_SECONDS; "
            "using default %ss.",
            int(DEFAULT_VISION_TIMEOUT_SECONDS),
        )
        return DEFAULT_VISION_TIMEOUT_SECONDS

    if (
        not math.isfinite(timeout)
        or timeout < MIN_VISION_TIMEOUT_SECONDS
        or timeout > MAX_VISION_TIMEOUT_SECONDS
    ):
        logger.warning(
            "Unreasonable MATPAL_VISION_TIMEOUT_SECONDS; "
            "using default %ss.",
            int(DEFAULT_VISION_TIMEOUT_SECONDS),
        )
        return DEFAULT_VISION_TIMEOUT_SECONDS

    return timeout
