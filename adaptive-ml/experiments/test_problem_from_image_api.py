import os
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.mat_pal.app import app
from src.api.mat_pal.generated_problem_store import (
    _generated_registrations,
)
from src.api.mat_pal.image_extraction import (
    DETAIL_EMPTY,
    DETAIL_MIME_MAGIC_MISMATCH,
    DETAIL_TOO_LARGE,
    DETAIL_UNAVAILABLE,
    DETAIL_UNSUPPORTED_MIME,
    MAX_IMAGE_BYTES,
    UNAVAILABLE_REASON,
)
from src.api.mat_pal.schemas import ExtractedProblem
from src.api.mat_pal.session_store import (
    _sessions,
    set_question_engine,
)
from src.core.student_model.progress_store import (
    DEFAULT_PROGRESS_PATH,
)
from src.core.vision import (
    FakeVisionExtractor,
    NullVisionExtractor,
    fake_ambiguous_problem,
    fake_bg_word_problem,
    fake_diagram_problem,
    fake_en_arithmetic_problem,
    fake_multiple_problems,
    fake_unreadable_problem,
    set_vision_extractor,
)


os.environ.setdefault("MATPAL_MODEL_PROVIDER", "none")

client = TestClient(app)

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    + b"\x00\x00\x00\rIHDR"
    + b"\x00\x00\x00\x01"
    + b"\x00\x00\x00\x01"
    + b"\x08\x02\x00\x00\x00"
    + b"\x90wS\xde"
)
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 24
WEBP_BYTES = (
    b"RIFF"
    + (12).to_bytes(4, "little")
    + b"WEBP"
)
PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
SVG_BYTES = (
    b'<svg xmlns="http://www.w3.org/2000/svg">'
    b"</svg>"
)

EXTRACTED_FIELDS = {
    "transcription",
    "language",
    "problem_type_hint",
    "topic_hint",
    "latex_expressions",
    "diagram_present",
    "diagram_type",
    "diagram_facts",
    "ambiguities",
    "warnings",
    "multiple_problems_detected",
    "confidence",
    "source",
}

SOLUTION_FIELDS = {
    "final_answer",
    "solution",
    "steps",
    "expected_answer",
    "hints",
}

REPO_ROOT = Path(__file__).resolve().parents[1]


def post_image(
    contents: bytes,
    filename: str,
    content_type: str,
    locale_hint: str | None = None,
):
    params = {}
    if locale_hint is not None:
        params["locale_hint"] = locale_hint
    return client.post(
        "/problems/from-image",
        files={
            "file": (filename, contents, content_type),
        },
        params=params,
    )


def use_fake(result=None):
    extractor = FakeVisionExtractor(result)
    set_vision_extractor(extractor)
    return extractor


def use_null():
    set_vision_extractor(NullVisionExtractor())


def assert_status_unavailable_with_null():
    use_null()
    response = client.get(
        "/problems/from-image/status"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is False
    assert payload["reason"] == UNAVAILABLE_REASON


def assert_post_returns_503_with_null():
    use_null()
    response = post_image(
        PNG_BYTES,
        "problem.png",
        "image/png",
    )
    assert response.status_code == 503
    assert response.json()["detail"] == (
        DETAIL_UNAVAILABLE
    )


def assert_status_available_with_fake():
    use_fake(fake_en_arithmetic_problem())
    response = client.get(
        "/problems/from-image/status"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["reason"] is None


def assert_valid_png_upload_succeeds():
    use_fake(fake_en_arithmetic_problem())
    response = post_image(
        PNG_BYTES,
        "problem.png",
        "image/png",
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["transcription"] == "2x + 5 = 17"
    assert payload["source"]["content_type"] == (
        "image/png"
    )
    assert payload["source"]["byte_size"] == len(
        PNG_BYTES
    )


def assert_valid_jpeg_upload_succeeds():
    use_fake(fake_en_arithmetic_problem())
    response = post_image(
        JPEG_BYTES,
        "problem.jpg",
        "image/jpeg",
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source"]["content_type"] == (
        "image/jpeg"
    )
    assert payload["source"]["byte_size"] == len(
        JPEG_BYTES
    )


def assert_extracted_problem_structure():
    use_fake(fake_en_arithmetic_problem())
    response = post_image(
        PNG_BYTES,
        "problem.png",
        "image/png",
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == EXTRACTED_FIELDS
    for field in SOLUTION_FIELDS:
        assert field not in payload
    ExtractedProblem.model_validate(payload)
    assert payload["language"] in {
        "en",
        "bg",
        "unknown",
    }
    assert isinstance(payload["latex_expressions"], list)
    assert isinstance(payload["diagram_facts"], list)
    assert isinstance(payload["ambiguities"], list)
    assert isinstance(payload["warnings"], list)
    assert isinstance(
        payload["diagram_present"],
        bool,
    )
    assert isinstance(
        payload["multiple_problems_detected"],
        bool,
    )
    source = payload["source"]
    assert set(source) == {
        "content_type",
        "byte_size",
    }
    assert "filename" not in source
    assert "path" not in source


def assert_bg_extraction_preserved():
    use_fake(fake_bg_word_problem())
    response = post_image(
        PNG_BYTES,
        "problem.png",
        "image/png",
        locale_hint="bg",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["language"] == "bg"
    assert payload["transcription"] == (
        "Мария има 3 пъти повече ябълки от Иван..."
    )


def assert_ambiguity_structure_preserved():
    use_fake(fake_ambiguous_problem())
    response = post_image(
        PNG_BYTES,
        "problem.png",
        "image/png",
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["ambiguities"]) == 1
    item = payload["ambiguities"][0]
    assert item["observation"] == (
        "denominator may be 3 or 5"
    )
    assert item["candidates"] == ["3", "5"]


def assert_diagram_facts_preserved():
    use_fake(fake_diagram_problem())
    response = post_image(
        PNG_BYTES,
        "problem.png",
        "image/png",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["diagram_present"] is True
    assert payload["diagram_type"] == "triangle"
    assert payload["diagram_facts"] == [
        {
            "kind": "side",
            "label": "AB",
            "value": "5",
            "unit": None,
        }
    ]


def assert_multiple_problems_preserved():
    use_fake(fake_multiple_problems())
    response = post_image(
        PNG_BYTES,
        "problem.png",
        "image/png",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["multiple_problems_detected"] is True
    assert "multiple_problems_detected" in (
        payload["warnings"]
    )
    assert payload["transcription"] == "2x + 5 = 17"


def assert_unreadable_without_invented_text():
    use_fake(fake_unreadable_problem())
    response = post_image(
        PNG_BYTES,
        "problem.png",
        "image/png",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["transcription"] == ""
    assert "unreadable" in payload["warnings"]
    assert payload["language"] == "unknown"


def assert_unsupported_mime_rejected():
    use_fake(fake_en_arithmetic_problem())
    response = post_image(
        PNG_BYTES,
        "problem.txt",
        "text/plain",
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        DETAIL_UNSUPPORTED_MIME
    )


def assert_png_mime_with_jpeg_magic_rejected():
    use_fake(fake_en_arithmetic_problem())
    response = post_image(
        JPEG_BYTES,
        "problem.png",
        "image/png",
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        DETAIL_MIME_MAGIC_MISMATCH
    )


def assert_jpeg_mime_with_png_magic_rejected():
    use_fake(fake_en_arithmetic_problem())
    response = post_image(
        PNG_BYTES,
        "problem.jpg",
        "image/jpeg",
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        DETAIL_MIME_MAGIC_MISMATCH
    )


def assert_pdf_rejected():
    use_fake(fake_en_arithmetic_problem())
    response = post_image(
        PDF_BYTES,
        "problem.pdf",
        "application/pdf",
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        DETAIL_UNSUPPORTED_MIME
    )


def assert_svg_rejected():
    use_fake(fake_en_arithmetic_problem())
    response = post_image(
        SVG_BYTES,
        "problem.svg",
        "image/svg+xml",
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        DETAIL_UNSUPPORTED_MIME
    )


def assert_webp_rejected():
    use_fake(fake_en_arithmetic_problem())
    response = post_image(
        WEBP_BYTES,
        "problem.webp",
        "image/webp",
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        DETAIL_UNSUPPORTED_MIME
    )


def assert_empty_file_rejected():
    use_fake(fake_en_arithmetic_problem())
    response = post_image(
        b"",
        "problem.png",
        "image/png",
    )
    assert response.status_code == 400
    assert response.json()["detail"] == DETAIL_EMPTY


def assert_oversized_upload_rejected():
    use_fake(fake_en_arithmetic_problem())
    oversized = JPEG_BYTES + (
        b"\x00" * (MAX_IMAGE_BYTES - len(JPEG_BYTES) + 1)
    )
    assert len(oversized) > MAX_IMAGE_BYTES
    response = post_image(
        oversized,
        "problem.jpg",
        "image/jpeg",
    )
    assert response.status_code == 400
    assert response.json()["detail"] == (
        DETAIL_TOO_LARGE
    )


def assert_image_bytes_are_not_persisted():
    marker = b"MATPAL29B_NO_STORE_" + os.urandom(8)
    png = PNG_BYTES + marker
    before_generated = list(
        _generated_registrations.keys()
    )
    before_sessions = set(_sessions)
    uploads = [
        REPO_ROOT / "uploads",
        REPO_ROOT / "src" / "api" / "mat_pal" / "uploads",
        REPO_ROOT / "math" / "ode" / "data" / "uploads",
    ]
    use_fake(fake_en_arithmetic_problem())
    response = post_image(
        png,
        "problem.png",
        "image/png",
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "path" not in payload
    assert "path" not in payload["source"]
    assert list(_generated_registrations.keys()) == (
        before_generated
    )
    assert set(_sessions) == before_sessions
    for path in uploads:
        assert not path.exists()
    progress_path = DEFAULT_PROGRESS_PATH
    if progress_path.exists():
        contents = progress_path.read_bytes()
        assert marker not in contents


def assert_catalog_still_works():
    response = client.get("/catalog")
    assert response.status_code == 200
    payload = response.json()
    assert "subjects" in payload
    assert payload["subjects"]


def assert_generate_still_works():
    response = client.post(
        "/problems/generate",
        json={
            "subject": "mathematics",
            "domain": "primary_school",
            "topic": "unknown_numbers",
            "difficulty": 1,
            "seed": 2,
            "language": "en",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["generated"] is True
    assert payload["problem_id"]
    assert payload["problem_text"]


def assert_tutoring_with_null_model_still_works():
    assert os.environ["MATPAL_MODEL_PROVIDER"] == "none"
    set_question_engine(None)
    use_null()
    start = client.post(
        "/sessions/start",
        json={
            "problem_id": (
                "grade4_reverse_reasoning_001"
            ),
            "student_id": "local_student",
            "language": "en",
        },
    )
    assert start.status_code == 200, start.text
    session_id = start.json()["session_id"]
    question = client.post(
        f"/sessions/{session_id}/question",
        json={
            "question": "What should I do first?",
        },
    )
    assert question.status_code == 200, question.text
    payload = question.json()
    assert payload["session_id"] == session_id
    assert payload["status"]
    assert question.status_code != 503


def main():
    previous_keys = list(
        _generated_registrations.keys()
    )
    try:
        assert_status_unavailable_with_null()
        assert_post_returns_503_with_null()
        assert_status_available_with_fake()
        assert_valid_png_upload_succeeds()
        assert_valid_jpeg_upload_succeeds()
        assert_extracted_problem_structure()
        assert_bg_extraction_preserved()
        assert_ambiguity_structure_preserved()
        assert_diagram_facts_preserved()
        assert_multiple_problems_preserved()
        assert_unreadable_without_invented_text()
        assert_unsupported_mime_rejected()
        assert_png_mime_with_jpeg_magic_rejected()
        assert_jpeg_mime_with_png_magic_rejected()
        assert_pdf_rejected()
        assert_svg_rejected()
        assert_webp_rejected()
        assert_empty_file_rejected()
        assert_oversized_upload_rejected()
        assert_image_bytes_are_not_persisted()
        assert_catalog_still_works()
        assert_generate_still_works()
        assert_tutoring_with_null_model_still_works()
        print("problem_from_image_api tests passed")
    finally:
        set_vision_extractor(None)
        set_question_engine(None)
        extra = [
            key
            for key in list(_generated_registrations)
            if key not in previous_keys
        ]
        for key in extra:
            _generated_registrations.pop(key, None)


if __name__ == "__main__":
    main()
