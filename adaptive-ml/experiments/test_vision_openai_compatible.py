import io
import json
import logging
import os
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from fastapi.testclient import TestClient

from src.api.mat_pal.app import app
from src.api.mat_pal.image_extraction import (
    DETAIL_PARSE,
    DETAIL_TIMEOUT,
    UNAVAILABLE_REASON,
)
from src.core.vision import (
    EXTRACTION_SCHEMA_ID,
    FakeVisionExtractor,
    NullVisionExtractor,
    OpenAICompatibleVisionExtractor,
    SYSTEM_EXTRACTION_PROMPT,
    VisionProviderRequestError,
    VisionProviderTimeoutError,
    VisionProviderUnavailableError,
    VisionResponseParseError,
    build_vision_extractor_from_env,
    get_vision_extractor,
    parse_extracted_problem,
    set_vision_extractor,
)
from src.core.vision.config import (
    DEFAULT_VISION_TIMEOUT_SECONDS,
)
from src.core.vision.openai_compatible import (
    MAX_OUTPUT_TOKENS,
    VISION_TEMPERATURE,
)
from src.core.vision.prompt import (
    REPAIR_EXTRACTION_PROMPT,
)


os.environ.setdefault("MATPAL_MODEL_PROVIDER", "none")
os.environ.setdefault("MATPAL_VISION_PROVIDER", "none")

client = TestClient(app)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 16


class ScriptedTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, payload, timeout):
        self.requests.append(
            {
                "payload": payload,
                "timeout": timeout,
            }
        )
        if not self.responses:
            raise AssertionError(
                "unexpected extra request"
            )
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def explode_urlopen(*args, **kwargs):
    raise AssertionError("real network call")


def valid_payload(**overrides):
    payload = {
        "schema": EXTRACTION_SCHEMA_ID,
        "transcription": "2x + 5 = 17",
        "language": "en",
        "problem_type_hint": "equation",
        "topic_hint": "arithmetic",
        "latex_expressions": ["2x + 5 = 17"],
        "diagram_present": False,
        "diagram_type": None,
        "diagram_facts": [],
        "ambiguities": [],
        "warnings": [],
        "multiple_problems_detected": False,
        "confidence": "high",
    }
    payload.update(overrides)
    return payload


def valid_json(**overrides):
    return json.dumps(valid_payload(**overrides))


def make_provider(responses, **overrides):
    transport = ScriptedTransport(responses)
    values = {
        "api_key": "test-not-a-secret",
        "base_url": "https://example.invalid/v1",
        "model": "test-vision",
        "timeout_seconds": 45,
        "transport": transport,
    }
    values.update(overrides)
    return (
        OpenAICompatibleVisionExtractor(**values),
        transport,
    )


def patched_env(**overrides):
    values = {
        "MATPAL_MODEL_PROVIDER": "none",
        "MATPAL_VISION_PROVIDER": "none",
        "MATPAL_MODEL_API_KEY": "",
        "MATPAL_MODEL_BASE_URL": "",
        "MATPAL_VISION_MODEL_NAME": "",
        "MATPAL_VISION_TIMEOUT_SECONDS": "",
    }
    values.update(overrides)
    cleaned = {
        key: str(value)
        for key, value in values.items()
        if value is not None
    }
    return patch.dict(os.environ, cleaned, clear=True)


def configured_vision_env(**overrides):
    values = {
        "MATPAL_VISION_PROVIDER": "openai_compatible",
        "MATPAL_MODEL_API_KEY": "test-not-a-secret",
        "MATPAL_MODEL_BASE_URL": (
            "https://example.invalid/v1"
        ),
        "MATPAL_VISION_MODEL_NAME": "test-vision",
    }
    values.update(overrides)
    return patched_env(**values)


def extract_with(responses, locale_hint=None, **kwargs):
    provider, transport = make_provider(
        responses,
        **kwargs,
    )
    result = provider.extract(
        PNG_BYTES,
        "image/png",
        locale_hint,
    )
    return result, transport


def assert_valid_en_arithmetic():
    result, _ = extract_with([valid_json()])
    assert result.transcription == "2x + 5 = 17"
    assert result.language == "en"
    assert "x = 4" not in result.transcription
    assert "x = 4" not in result.latex_expressions


def assert_valid_bg_word_problem():
    text = (
        "Мария има 3 пъти повече ябълки от Иван..."
    )
    result, _ = extract_with(
        [
            valid_json(
                transcription=text,
                language="bg",
                problem_type_hint="word_problem",
                latex_expressions=[],
                confidence="medium",
            )
        ]
    )
    assert result.language == "bg"
    assert result.transcription == text


def assert_language_unknown_accepted():
    result, _ = extract_with(
        [valid_json(language="unknown")]
    )
    assert result.language == "unknown"


def assert_latex_expressions_preserved():
    result, _ = extract_with(
        [
            valid_json(
                latex_expressions=["2x + 5 = 17"],
            )
        ]
    )
    assert result.latex_expressions == (
        "2x + 5 = 17",
    )


def assert_diagram_facts_parsed():
    result, _ = extract_with(
        [
            valid_json(
                diagram_present=True,
                diagram_type="triangle",
                diagram_facts=[
                    {
                        "kind": "side",
                        "label": "AB",
                        "value": "5",
                        "unit": None,
                    }
                ],
            )
        ]
    )
    assert result.diagram_present is True
    assert result.diagram_type == "triangle"
    assert result.diagram_facts[0].kind == "side"
    assert result.diagram_facts[0].label == "AB"
    assert result.diagram_facts[0].value == "5"
    assert result.diagram_facts[0].unit is None


def assert_ambiguity_parsed():
    result, _ = extract_with(
        [
            valid_json(
                ambiguities=[
                    {
                        "observation": (
                            "denominator may be 3 or 5"
                        ),
                        "span": None,
                        "candidates": ["3", "5"],
                    }
                ]
            )
        ]
    )
    assert result.ambiguities[0].observation == (
        "denominator may be 3 or 5"
    )
    assert result.ambiguities[0].candidates == (
        "3",
        "5",
    )


def assert_unreadable_warning_parsed():
    result, _ = extract_with(
        [
            valid_json(
                transcription="",
                language="unknown",
                latex_expressions=[],
                warnings=["unreadable"],
                confidence="low",
            )
        ]
    )
    assert result.transcription == ""
    assert "unreadable" in result.warnings


def assert_multiple_problems_parsed():
    result, _ = extract_with(
        [
            valid_json(
                multiple_problems_detected=True,
                warnings=[
                    "multiple_problems_detected"
                ],
            )
        ]
    )
    assert result.multiple_problems_detected is True


def assert_confidence_values():
    for value in ("low", "medium", "high", None):
        parsed = parse_extracted_problem(
            valid_json(confidence=value)
        )
        assert parsed.confidence == value


def assert_unknown_schema_rejected():
    try:
        parse_extracted_problem(
            valid_json(
                schema="matpal.extracted_problem.v2"
            )
        )
    except VisionResponseParseError as error:
        assert "Unknown" in str(error)
        return
    raise AssertionError("expected parse error")


def assert_missing_schema_rejected():
    payload = valid_payload()
    del payload["schema"]
    try:
        parse_extracted_problem(json.dumps(payload))
    except VisionResponseParseError as error:
        assert "Missing" in str(error)
        return
    raise AssertionError("expected parse error")


def assert_repair_retry_succeeds():
    result, transport = extract_with(
        ["not-json", valid_json()]
    )
    assert result.transcription == "2x + 5 = 17"
    assert len(transport.requests) == 2
    repair_text = transport.requests[1]["payload"][
        "messages"
    ][1]["content"][0]["text"]
    assert "not valid" in repair_text
    assert "ONLY valid JSON" in repair_text
    assert "Do not solve" in repair_text
    assert REPAIR_EXTRACTION_PROMPT in repair_text


def assert_both_attempts_fail():
    provider, transport = make_provider(
        ["not-json", "{bad"]
    )
    try:
        provider.extract(PNG_BYTES, "image/png")
    except VisionResponseParseError:
        assert len(transport.requests) == 2
        return
    raise AssertionError("expected parse error")


def assert_prose_around_json_rejected():
    raw = "Here is the JSON:\n" + valid_json()
    try:
        parse_extracted_problem(raw)
    except VisionResponseParseError:
        return
    raise AssertionError("expected parse error")


def assert_markdown_fenced_json_rejected():
    raw = "```json\n" + valid_json() + "\n```"
    try:
        parse_extracted_problem(raw)
    except VisionResponseParseError:
        return
    raise AssertionError("expected parse error")


def assert_final_answer_field_rejected():
    payload = valid_payload(final_answer="x = 4")
    try:
        parse_extracted_problem(json.dumps(payload))
    except VisionResponseParseError as error:
        assert "final_answer" in str(error)
        return
    raise AssertionError("expected parse error")


def assert_solution_field_rejected():
    payload = valid_payload(solution="subtract 5")
    try:
        parse_extracted_problem(json.dumps(payload))
    except VisionResponseParseError as error:
        assert "solution" in str(error)
        return
    raise AssertionError("expected parse error")


def assert_invalid_language_rejected():
    try:
        parse_extracted_problem(
            valid_json(language="fr")
        )
    except VisionResponseParseError:
        return
    raise AssertionError("expected parse error")


def assert_invalid_confidence_rejected():
    try:
        parse_extracted_problem(
            valid_json(confidence="0.9")
        )
    except VisionResponseParseError:
        return
    raise AssertionError("expected parse error")


def assert_wrong_diagram_fact_rejected():
    try:
        parse_extracted_problem(
            valid_json(
                diagram_facts=[{"label": "AB"}]
            )
        )
    except VisionResponseParseError:
        return
    raise AssertionError("expected parse error")


def assert_wrong_ambiguity_rejected():
    try:
        parse_extracted_problem(
            valid_json(
                ambiguities=[{"candidates": ["3"]}]
            )
        )
    except VisionResponseParseError:
        return
    raise AssertionError("expected parse error")


def assert_timeout_maps_to_provider_error():
    provider, _ = make_provider([TimeoutError()])
    try:
        provider.extract(PNG_BYTES, "image/png")
    except VisionProviderTimeoutError:
        return
    raise AssertionError("expected timeout error")


def assert_http_error_maps_to_provider_error():
    error = HTTPError(
        "https://example.invalid/v1/chat/completions",
        502,
        "Bad Gateway",
        hdrs=None,
        fp=io.BytesIO(),
    )
    provider, _ = make_provider([error])
    try:
        provider.extract(PNG_BYTES, "image/png")
    except VisionProviderRequestError:
        return
    raise AssertionError("expected request error")


def assert_missing_api_key_is_unavailable():
    provider = OpenAICompatibleVisionExtractor(
        api_key="",
        base_url="https://example.invalid/v1",
        model="test-vision",
    )
    assert provider.is_available() is False
    try:
        provider.extract(PNG_BYTES, "image/png")
    except VisionProviderUnavailableError:
        return
    raise AssertionError("expected unavailable")


def assert_env_none_builds_null():
    with patched_env():
        extractor = build_vision_extractor_from_env()
    assert isinstance(
        extractor,
        NullVisionExtractor,
    )
    assert extractor.is_available() is False

    with patched_env(MATPAL_VISION_PROVIDER="none"):
        named = build_vision_extractor_from_env()
    assert isinstance(named, NullVisionExtractor)


def assert_env_builds_real_extractor():
    with configured_vision_env():
        extractor = build_vision_extractor_from_env()
    assert isinstance(
        extractor,
        OpenAICompatibleVisionExtractor,
    )
    assert extractor.is_available() is True
    assert extractor._model == "test-vision"
    assert extractor._base_url == (
        "https://example.invalid/v1"
    )
    assert extractor._timeout_seconds == (
        DEFAULT_VISION_TIMEOUT_SECONDS
    )

    with configured_vision_env(
        MATPAL_VISION_PROVIDER="openai",
    ):
        openai = build_vision_extractor_from_env()
    assert isinstance(
        openai,
        OpenAICompatibleVisionExtractor,
    )


def assert_missing_config_is_unavailable():
    with configured_vision_env(
        MATPAL_MODEL_API_KEY="",
    ):
        missing_key = build_vision_extractor_from_env()
    assert isinstance(
        missing_key,
        NullVisionExtractor,
    )

    with configured_vision_env(
        MATPAL_VISION_MODEL_NAME="",
    ):
        missing_model = (
            build_vision_extractor_from_env()
        )
    assert isinstance(
        missing_model,
        NullVisionExtractor,
    )

    with patched_env(
        MATPAL_VISION_PROVIDER="bogus",
        MATPAL_MODEL_API_KEY="test-not-a-secret",
        MATPAL_VISION_MODEL_NAME="test-vision",
    ):
        invalid = build_vision_extractor_from_env()
    assert isinstance(invalid, NullVisionExtractor)


def assert_test_injection_overrides_env():
    with configured_vision_env():
        set_vision_extractor(None)
        built = get_vision_extractor()
        assert isinstance(
            built,
            OpenAICompatibleVisionExtractor,
        )
        fake = FakeVisionExtractor()
        set_vision_extractor(fake)
        assert get_vision_extractor() is fake
        set_vision_extractor(None)


def assert_no_real_network_call():
    with patch(
        "src.core.vision.openai_compatible.urlopen",
        explode_urlopen,
    ):
        extract_with([valid_json()])


def assert_prompt_contains_contract_markers():
    text = SYSTEM_EXTRACTION_PROMPT.lower()
    assert "do not solve" in text
    assert "visibly present" in text
    assert "strict json" in text
    assert "ambiguity" in text
    assert "multiple_problems_detected" in text
    assert "final_answer" in text
    assert "solution" in text
    assert "steps" in text
    assert EXTRACTION_SCHEMA_ID in (
        SYSTEM_EXTRACTION_PROMPT
    )


def assert_request_shape():
    _, transport = extract_with(
        [valid_json()],
    )
    provider, transport_jpeg = make_provider(
        [valid_json()]
    )
    provider.extract(
        JPEG_BYTES,
        "image/jpeg",
        "bg",
    )
    payload = transport.requests[0]["payload"]
    jpeg_payload = transport_jpeg.requests[0][
        "payload"
    ]
    assert payload["model"] == "test-vision"
    assert payload["temperature"] == (
        VISION_TEMPERATURE
    )
    assert payload["max_tokens"] == MAX_OUTPUT_TOKENS
    assert transport.requests[0]["timeout"] == 45
    messages = payload["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == (
        SYSTEM_EXTRACTION_PROMPT
    )
    user = messages[1]["content"]
    assert user[0]["type"] == "text"
    assert "hint only" in user[0]["text"]
    assert "Do not solve" in user[0]["text"]
    assert user[1]["type"] == "image_url"
    data_url = user[1]["image_url"]["url"]
    assert data_url.startswith(
        "data:image/png;base64,"
    )
    jpeg_url = jpeg_payload["messages"][1][
        "content"
    ][1]["image_url"]["url"]
    assert jpeg_url.startswith(
        "data:image/jpeg;base64,"
    )
    assert "UI locale hint: bg" in (
        jpeg_payload["messages"][1]["content"][0][
            "text"
        ]
    )
    user_text = user[0]["text"]
    assert "Do not solve" in user_text
    assert "x = 4" not in user_text
    assert "final_answer" not in user_text


def assert_urlopen_path_uses_chat_completions():
    captured = {}

    class FakeResponse:
        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": valid_json()
                            }
                        }
                    ]
                }
            ).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["method"] = request.get_method()
        captured["has_auth"] = bool(
            request.get_header("Authorization")
        )
        return FakeResponse()

    provider = OpenAICompatibleVisionExtractor(
        api_key="test-not-a-secret",
        base_url="https://example.invalid/v1",
        model="test-vision",
        timeout_seconds=45,
    )
    with patch(
        "src.core.vision.openai_compatible.urlopen",
        fake_urlopen,
    ):
        result = provider.extract(
            PNG_BYTES,
            "image/png",
        )
    assert result.transcription == "2x + 5 = 17"
    assert captured["url"] == (
        "https://example.invalid/v1/chat/completions"
    )
    assert captured["method"] == "POST"
    assert captured["timeout"] == 45
    assert captured["has_auth"] is True


def assert_urlopen_timeout_and_http_error():
    provider = OpenAICompatibleVisionExtractor(
        api_key="test-not-a-secret",
        base_url="https://example.invalid/v1",
        model="test-vision",
    )

    def timeout_urlopen(*args, **kwargs):
        raise URLError(TimeoutError("timed out"))

    with patch(
        "src.core.vision.openai_compatible.urlopen",
        timeout_urlopen,
    ):
        try:
            provider.extract(PNG_BYTES, "image/png")
            raise AssertionError("expected timeout")
        except VisionProviderTimeoutError:
            pass

    def http_urlopen(*args, **kwargs):
        raise HTTPError(
            "https://example.invalid/v1/chat/completions",
            401,
            "Unauthorized",
            hdrs=None,
            fp=io.BytesIO(),
        )

    with patch(
        "src.core.vision.openai_compatible.urlopen",
        http_urlopen,
    ):
        try:
            provider.extract(PNG_BYTES, "image/png")
            raise AssertionError("expected request error")
        except VisionProviderRequestError:
            pass


def assert_status_does_not_probe_network():
    class BoomTransport:
        def __call__(self, *args, **kwargs):
            raise AssertionError(
                "status probed network"
            )

    previous = get_vision_extractor()
    try:
        set_vision_extractor(NullVisionExtractor())
        none_status = client.get(
            "/problems/from-image/status"
        )
        assert none_status.status_code == 200
        assert none_status.json() == {
            "available": False,
            "reason": UNAVAILABLE_REASON,
        }

        set_vision_extractor(
            OpenAICompatibleVisionExtractor(
                api_key="test-not-a-secret",
                base_url="https://example.invalid/v1",
                model="test-vision",
                transport=BoomTransport(),
            )
        )
        ready = client.get(
            "/problems/from-image/status"
        )
        assert ready.status_code == 200
        assert ready.json() == {
            "available": True,
            "reason": None,
        }
    finally:
        set_vision_extractor(previous)


def assert_api_maps_timeout_and_parse():
    class TimeoutExtractor:
        def is_available(self):
            return True

        def extract(self, *args, **kwargs):
            raise VisionProviderTimeoutError(
                "Vision provider timed out."
            )

    class ParseExtractor:
        def is_available(self):
            return True

        def extract(self, *args, **kwargs):
            raise VisionResponseParseError(
                "Extraction response is not valid JSON."
            )

    previous = get_vision_extractor()
    try:
        set_vision_extractor(TimeoutExtractor())
        timeout = client.post(
            "/problems/from-image",
            files={
                "file": (
                    "problem.png",
                    PNG_BYTES,
                    "image/png",
                )
            },
        )
        assert timeout.status_code == 504
        assert timeout.json()["detail"] == (
            DETAIL_TIMEOUT
        )

        set_vision_extractor(ParseExtractor())
        parsed = client.post(
            "/problems/from-image",
            files={
                "file": (
                    "problem.png",
                    PNG_BYTES,
                    "image/png",
                )
            },
        )
        assert parsed.status_code == 422
        assert parsed.json()["detail"] == DETAIL_PARSE
    finally:
        set_vision_extractor(previous)


def assert_logs_do_not_leak_secrets():
    provider, _ = make_provider(["not-json", "{bad"])
    logger = logging.getLogger(
        "src.core.vision.openai_compatible"
    )
    with patch.object(logger, "warning") as warning:
        try:
            provider.extract(PNG_BYTES, "image/png")
        except VisionResponseParseError:
            pass
    messages = [
        str(call.args[0])
        for call in warning.call_args_list
    ]
    joined = " ".join(messages)
    assert "test-not-a-secret" not in joined
    assert "Authorization" not in joined
    assert "base64" not in joined
    assert PNG_BYTES.decode("latin1") not in joined
    assert "2x + 5 = 17" not in joined
    assert "vision extraction parse failed" in (
        joined
    )


def main():
    previous = get_vision_extractor()
    try:
        with patch(
            "src.core.vision.openai_compatible.urlopen",
            explode_urlopen,
        ):
            assert_valid_en_arithmetic()
            assert_valid_bg_word_problem()
            assert_language_unknown_accepted()
            assert_latex_expressions_preserved()
            assert_diagram_facts_parsed()
            assert_ambiguity_parsed()
            assert_unreadable_warning_parsed()
            assert_multiple_problems_parsed()
            assert_confidence_values()
            assert_unknown_schema_rejected()
            assert_missing_schema_rejected()
            assert_repair_retry_succeeds()
            assert_both_attempts_fail()
            assert_prose_around_json_rejected()
            assert_markdown_fenced_json_rejected()
            assert_final_answer_field_rejected()
            assert_solution_field_rejected()
            assert_invalid_language_rejected()
            assert_invalid_confidence_rejected()
            assert_wrong_diagram_fact_rejected()
            assert_wrong_ambiguity_rejected()
            assert_timeout_maps_to_provider_error()
            assert_http_error_maps_to_provider_error()
            assert_missing_api_key_is_unavailable()
            assert_env_none_builds_null()
            assert_env_builds_real_extractor()
            assert_missing_config_is_unavailable()
            assert_test_injection_overrides_env()
            assert_no_real_network_call()
            assert_prompt_contains_contract_markers()
            assert_request_shape()
            assert_status_does_not_probe_network()
            assert_api_maps_timeout_and_parse()
            assert_logs_do_not_leak_secrets()
        assert_urlopen_path_uses_chat_completions()
        assert_urlopen_timeout_and_http_error()
        print("vision_openai_compatible tests passed")
    finally:
        set_vision_extractor(previous)


if __name__ == "__main__":
    main()
