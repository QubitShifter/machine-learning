from dataclasses import replace

from src.core.vision.contracts import (
    Ambiguity,
    DiagramFact,
    ExtractedProblem,
    VisionExtractor,
)


class VisionExtractorError(RuntimeError):
    pass


class VisionProviderUnavailableError(VisionExtractorError):
    pass


class VisionProviderTimeoutError(VisionExtractorError):
    pass


class VisionProviderRequestError(VisionExtractorError):
    pass


class VisionResponseParseError(VisionExtractorError):
    pass


class NullVisionExtractor:
    def is_available(self) -> bool:
        return False

    def extract(
        self,
        image_bytes: bytes,
        mime_type: str,
        locale_hint: str | None = None,
    ) -> ExtractedProblem:
        raise VisionExtractorError(
            "No vision extractor is configured."
        )


class FakeVisionExtractor:
    def __init__(
        self,
        result: ExtractedProblem | None = None,
        *,
        available: bool = True,
    ):
        self.result = result
        self.available = available
        self.calls: list[dict] = []

    def is_available(self) -> bool:
        return self.available

    def extract(
        self,
        image_bytes: bytes,
        mime_type: str,
        locale_hint: str | None = None,
    ) -> ExtractedProblem:
        self.calls.append(
            {
                "byte_size": len(image_bytes),
                "mime_type": mime_type,
                "locale_hint": locale_hint,
            }
        )
        payload = self.result
        if payload is None:
            payload = default_fake_extracted_problem()
        return payload


def default_fake_extracted_problem() -> ExtractedProblem:
    return ExtractedProblem(
        transcription="2x + 5 = 17",
        language="en",
        problem_type_hint="equation",
        topic_hint="arithmetic",
        latex_expressions=("2x + 5 = 17",),
        diagram_present=False,
        diagram_type=None,
        diagram_facts=(),
        ambiguities=(),
        warnings=(),
        multiple_problems_detected=False,
        confidence="high",
    )


def make_fake_extracted_problem(
    **overrides,
) -> ExtractedProblem:
    payload = default_fake_extracted_problem()
    return replace(payload, **overrides)


def fake_en_arithmetic_problem(
    **overrides,
) -> ExtractedProblem:
    return make_fake_extracted_problem(
        **overrides,
    )


def fake_bg_word_problem(
    **overrides,
) -> ExtractedProblem:
    return make_fake_extracted_problem(
        transcription=(
            "Мария има 3 пъти повече ябълки от Иван..."
        ),
        language="bg",
        problem_type_hint="word_problem",
        topic_hint="arithmetic",
        latex_expressions=(),
        confidence="medium",
        **overrides,
    )


def fake_ambiguous_problem(
    **overrides,
) -> ExtractedProblem:
    return make_fake_extracted_problem(
        transcription="a / ? = 4",
        language="en",
        problem_type_hint="equation",
        confidence="low",
        ambiguities=(
            Ambiguity(
                observation=(
                    "denominator may be 3 or 5"
                ),
                span=None,
                candidates=("3", "5"),
            ),
        ),
        **overrides,
    )


def fake_diagram_problem(
    **overrides,
) -> ExtractedProblem:
    return make_fake_extracted_problem(
        transcription="Find the perimeter.",
        language="en",
        problem_type_hint="geometry",
        topic_hint="geometry",
        diagram_present=True,
        diagram_type="triangle",
        diagram_facts=(
            DiagramFact(
                kind="side",
                label="AB",
                value="5",
                unit=None,
            ),
        ),
        confidence="medium",
        **overrides,
    )


def fake_unreadable_problem(
    **overrides,
) -> ExtractedProblem:
    return make_fake_extracted_problem(
        transcription="",
        language="unknown",
        problem_type_hint=None,
        topic_hint=None,
        latex_expressions=(),
        confidence="low",
        warnings=("unreadable",),
        **overrides,
    )


def fake_multiple_problems(
    **overrides,
) -> ExtractedProblem:
    return make_fake_extracted_problem(
        transcription="2x + 5 = 17",
        language="en",
        multiple_problems_detected=True,
        warnings=("multiple_problems_detected",),
        confidence="medium",
        **overrides,
    )


_vision_extractor: VisionExtractor | None = None


def get_vision_extractor() -> VisionExtractor:
    global _vision_extractor

    if _vision_extractor is None:
        from src.core.vision.config import (
            build_vision_extractor_from_env,
        )

        _vision_extractor = (
            build_vision_extractor_from_env()
        )

    return _vision_extractor


def set_vision_extractor(
    extractor: VisionExtractor | None,
) -> None:
    global _vision_extractor
    _vision_extractor = extractor
