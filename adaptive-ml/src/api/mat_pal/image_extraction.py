from pathlib import Path

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from src.api.mat_pal.schemas import (
    Ambiguity,
    DiagramFact,
    ExtractedProblem,
    ImageExtractionStatusResponse,
    SourceImageMetadata,
)
from src.core.vision.contracts import (
    ExtractedProblem as CoreExtractedProblem,
)
from src.core.vision.extractor import (
    VisionExtractorError,
    VisionProviderTimeoutError,
    VisionResponseParseError,
    get_vision_extractor,
)


MAX_IMAGE_BYTES = 5 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024
JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
ALLOWED_MIME_TYPES = {
    "image/jpeg": JPEG_MAGIC,
    "image/png": PNG_MAGIC,
}
ALLOWED_EXTENSIONS = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}

UNAVAILABLE_REASON = "vision_provider_unavailable"
DETAIL_UNSUPPORTED_MIME = "Unsupported image type."
DETAIL_MIME_MAGIC_MISMATCH = (
    "Image content does not match the declared type."
)
DETAIL_TOO_LARGE = "Upload exceeds the 5 MiB limit."
DETAIL_EMPTY = "Empty upload."
DETAIL_UNAVAILABLE = "Vision provider unavailable."
DETAIL_TIMEOUT = "Vision provider timed out."
DETAIL_PARSE = (
    "Vision extraction could not be parsed."
)
DETAIL_INVALID_RESULT = (
    "Vision extractor returned an invalid result."
)


def get_status() -> ImageExtractionStatusResponse:
    extractor = get_vision_extractor()
    available = extractor.is_available()
    return ImageExtractionStatusResponse(
        available=available,
        reason=(
            None if available else UNAVAILABLE_REASON
        ),
    )


async def extract_from_upload(
    upload: UploadFile,
    locale_hint: str | None = None,
) -> ExtractedProblem:
    image_bytes = await read_upload_bytes(upload)
    mime_type = normalize_content_type(
        upload.content_type
    )
    validate_image(image_bytes, mime_type, upload)
    extractor = get_vision_extractor()

    if not extractor.is_available():
        raise HTTPException(
            status_code=503,
            detail=DETAIL_UNAVAILABLE,
        )

    try:
        extracted = extractor.extract(
            image_bytes,
            mime_type,
            locale_hint,
        )
        return to_api_extracted_problem(
            extracted,
            mime_type=mime_type,
            byte_size=len(image_bytes),
        )
    except VisionProviderTimeoutError as error:
        raise HTTPException(
            status_code=504,
            detail=DETAIL_TIMEOUT,
        ) from error
    except VisionResponseParseError as error:
        raise HTTPException(
            status_code=422,
            detail=DETAIL_PARSE,
        ) from error
    except VisionExtractorError as error:
        raise HTTPException(
            status_code=503,
            detail=DETAIL_UNAVAILABLE,
        ) from error
    except (
        ValidationError,
        TypeError,
        AttributeError,
        ValueError,
    ) as error:
        raise HTTPException(
            status_code=422,
            detail=DETAIL_INVALID_RESULT,
        ) from error


def to_api_extracted_problem(
    extracted: CoreExtractedProblem,
    *,
    mime_type: str,
    byte_size: int,
) -> ExtractedProblem:
    return ExtractedProblem(
        transcription=extracted.transcription,
        language=extracted.language,
        problem_type_hint=extracted.problem_type_hint,
        topic_hint=extracted.topic_hint,
        latex_expressions=list(
            extracted.latex_expressions
        ),
        diagram_present=extracted.diagram_present,
        diagram_type=extracted.diagram_type,
        diagram_facts=[
            DiagramFact(
                kind=fact.kind,
                label=fact.label,
                value=fact.value,
                unit=fact.unit,
            )
            for fact in extracted.diagram_facts
        ],
        ambiguities=[
            Ambiguity(
                observation=item.observation,
                span=item.span,
                candidates=list(item.candidates),
            )
            for item in extracted.ambiguities
        ],
        warnings=list(extracted.warnings),
        multiple_problems_detected=(
            extracted.multiple_problems_detected
        ),
        confidence=extracted.confidence,
        source=SourceImageMetadata(
            content_type=mime_type,
            byte_size=byte_size,
        ),
    )


async def read_upload_bytes(
    upload: UploadFile,
) -> bytes:
    chunks: list[bytes] = []
    total = 0

    try:
        while True:
            chunk = await upload.read(READ_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_IMAGE_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=DETAIL_TOO_LARGE,
                )
            chunks.append(chunk)
    finally:
        await upload.close()

    if total == 0:
        raise HTTPException(
            status_code=400,
            detail=DETAIL_EMPTY,
        )

    return b"".join(chunks)


def validate_image(
    image_bytes: bytes,
    mime_type: str,
    upload: UploadFile,
) -> None:
    expected_magic = ALLOWED_MIME_TYPES.get(mime_type)
    if expected_magic is None:
        raise HTTPException(
            status_code=400,
            detail=DETAIL_UNSUPPORTED_MIME,
        )

    if not image_bytes.startswith(expected_magic):
        raise HTTPException(
            status_code=400,
            detail=DETAIL_MIME_MAGIC_MISMATCH,
        )

    suffix = upload_suffix(upload)
    if suffix is None:
        return

    allowed = ALLOWED_EXTENSIONS[mime_type]
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=DETAIL_UNSUPPORTED_MIME,
        )


def normalize_content_type(
    value: str | None,
) -> str:
    if not value:
        return ""
    return value.split(";", 1)[0].strip().lower()


def upload_suffix(
    upload: UploadFile,
) -> str | None:
    raw = upload.filename
    if not raw:
        return None
    name = Path(
        str(raw).replace("\\", "/")
    ).name
    suffix = Path(name).suffix.lower()
    if not suffix:
        return None
    return suffix
