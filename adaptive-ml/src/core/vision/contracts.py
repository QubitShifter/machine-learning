from dataclasses import dataclass
from typing import Literal, Protocol


ExtractionLanguage = Literal["en", "bg", "unknown"]
ExtractionConfidence = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class DiagramFact:
    kind: str
    label: str | None = None
    value: str | None = None
    unit: str | None = None


@dataclass(frozen=True)
class Ambiguity:
    observation: str
    span: str | None = None
    candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractedProblem:
    transcription: str
    language: ExtractionLanguage
    problem_type_hint: str | None = None
    topic_hint: str | None = None
    latex_expressions: tuple[str, ...] = ()
    diagram_present: bool = False
    diagram_type: str | None = None
    diagram_facts: tuple[DiagramFact, ...] = ()
    ambiguities: tuple[Ambiguity, ...] = ()
    warnings: tuple[str, ...] = ()
    multiple_problems_detected: bool = False
    confidence: ExtractionConfidence | None = None


class VisionExtractor(Protocol):
    def is_available(self) -> bool:
        ...

    def extract(
        self,
        image_bytes: bytes,
        mime_type: str,
        locale_hint: str | None = None,
    ) -> ExtractedProblem:
        ...
