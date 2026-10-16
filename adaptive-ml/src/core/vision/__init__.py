from src.core.vision.config import (
    build_vision_extractor_from_env,
)
from src.core.vision.contracts import (
    Ambiguity,
    DiagramFact,
    ExtractedProblem,
    VisionExtractor,
)
from src.core.vision.extractor import (
    FakeVisionExtractor,
    NullVisionExtractor,
    VisionExtractorError,
    VisionProviderRequestError,
    VisionProviderTimeoutError,
    VisionProviderUnavailableError,
    VisionResponseParseError,
    fake_ambiguous_problem,
    fake_bg_word_problem,
    fake_diagram_problem,
    fake_en_arithmetic_problem,
    fake_multiple_problems,
    fake_unreadable_problem,
    get_vision_extractor,
    make_fake_extracted_problem,
    set_vision_extractor,
)
from src.core.vision.openai_compatible import (
    OpenAICompatibleVisionExtractor,
)
from src.core.vision.parse import parse_extracted_problem
from src.core.vision.prompt import (
    EXTRACTION_SCHEMA_ID,
    SYSTEM_EXTRACTION_PROMPT,
)

__all__ = [
    "Ambiguity",
    "DiagramFact",
    "EXTRACTION_SCHEMA_ID",
    "ExtractedProblem",
    "FakeVisionExtractor",
    "NullVisionExtractor",
    "OpenAICompatibleVisionExtractor",
    "SYSTEM_EXTRACTION_PROMPT",
    "VisionExtractor",
    "VisionExtractorError",
    "VisionProviderRequestError",
    "VisionProviderTimeoutError",
    "VisionProviderUnavailableError",
    "VisionResponseParseError",
    "build_vision_extractor_from_env",
    "fake_ambiguous_problem",
    "fake_bg_word_problem",
    "fake_diagram_problem",
    "fake_en_arithmetic_problem",
    "fake_multiple_problems",
    "fake_unreadable_problem",
    "get_vision_extractor",
    "make_fake_extracted_problem",
    "parse_extracted_problem",
    "set_vision_extractor",
]
