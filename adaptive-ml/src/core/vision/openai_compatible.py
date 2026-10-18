import base64
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.core.vision.contracts import ExtractedProblem
from src.core.vision.extractor import (
    VisionProviderRequestError,
    VisionProviderTimeoutError,
    VisionProviderUnavailableError,
    VisionResponseParseError,
)
from src.core.openai_compatible_sampling import (
    completion_token_parameter,
    supports_custom_temperature,
)
from src.core.vision.parse import parse_extracted_problem
from src.core.vision.prompt import (
    SYSTEM_EXTRACTION_PROMPT,
    repair_extraction_task,
    user_extraction_task,
)


logger = logging.getLogger(__name__)

DEFAULT_VISION_TIMEOUT_SECONDS = 45.0
MAX_OUTPUT_TOKENS = 800
VISION_TEMPERATURE = 0


class OpenAICompatibleVisionExtractor:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = (
            DEFAULT_VISION_TIMEOUT_SECONDS
        ),
        transport=None,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def is_available(self) -> bool:
        return bool(
            self._api_key
            and self._base_url
            and self._model
        )

    def extract(
        self,
        image_bytes: bytes,
        mime_type: str,
        locale_hint: str | None = None,
    ) -> ExtractedProblem:
        if not self.is_available():
            logger.warning(
                "vision provider unavailable"
            )
            raise VisionProviderUnavailableError(
                "Vision provider unavailable."
            )

        first = self._complete(
            image_bytes,
            mime_type,
            locale_hint,
            repair=False,
        )
        try:
            return parse_extracted_problem(first)
        except VisionResponseParseError:
            logger.warning(
                "vision extraction parse failed"
            )

        second = self._complete(
            image_bytes,
            mime_type,
            locale_hint,
            repair=True,
        )
        try:
            return parse_extracted_problem(second)
        except VisionResponseParseError:
            logger.warning(
                "vision extraction parse failed"
            )
            raise

    def _complete(
        self,
        image_bytes: bytes,
        mime_type: str,
        locale_hint: str | None,
        *,
        repair: bool,
    ) -> str:
        payload = build_vision_request_payload(
            model=self._model,
            image_bytes=image_bytes,
            mime_type=mime_type,
            locale_hint=locale_hint,
            repair=repair,
        )
        return self._post_chat(payload)

    def _post_chat(self, payload: dict) -> str:
        try:
            if self._transport is not None:
                return self._transport(
                    payload,
                    self._timeout_seconds,
                )
            return self._urlopen_chat(payload)
        except (
            VisionProviderTimeoutError,
            VisionProviderRequestError,
        ):
            raise
        except (
            HTTPError,
            URLError,
            TimeoutError,
            ValueError,
        ) as error:
            if _is_timeout_error(error):
                logger.warning(
                    "vision provider timeout"
                )
                raise VisionProviderTimeoutError(
                    "Vision provider timed out."
                ) from error
            logger.warning(
                "vision provider request failed"
            )
            raise VisionProviderRequestError(
                "Vision provider request failed."
            ) from error

    def _urlopen_chat(self, payload: dict) -> str:
        request = Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": (
                    f"Bearer {self._api_key}"
                ),
            },
        )
        with urlopen(
            request,
            timeout=self._timeout_seconds,
        ) as response:
            body = json.loads(
                response.read().decode("utf-8")
            )
        try:
            return read_message_content(body)
        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as error:
            raise VisionProviderRequestError(
                "Vision provider returned an unexpected response."
            ) from error


def build_vision_request_payload(
    *,
    model: str,
    image_bytes: bytes,
    mime_type: str,
    locale_hint: str | None,
    repair: bool,
) -> dict:
    if repair:
        task = repair_extraction_task(locale_hint)
    else:
        task = user_extraction_task(locale_hint)
    data_url = encode_image_data_url(
        image_bytes,
        mime_type,
    )
    payload = {
        "model": model,
        completion_token_parameter(model): MAX_OUTPUT_TOKENS,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_EXTRACTION_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": task,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_url,
                        },
                    },
                ],
            },
        ],
    }
    if supports_custom_temperature(model):
        payload["temperature"] = VISION_TEMPERATURE
    return payload


def encode_image_data_url(
    image_bytes: bytes,
    mime_type: str,
) -> str:
    encoded = base64.b64encode(image_bytes).decode(
        "ascii"
    )
    return f"data:{mime_type};base64,{encoded}"


def read_message_content(body: object) -> str:
    if not isinstance(body, dict):
        raise TypeError("response is not an object")
    content = body["choices"][0]["message"]["content"]
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif (
                isinstance(part, dict)
                and part.get("type") == "text"
            ):
                parts.append(str(part.get("text") or ""))
        return "".join(parts)
    raise TypeError("unsupported message content")


def _is_timeout_error(error: BaseException) -> bool:
    if isinstance(error, TimeoutError):
        return True
    if isinstance(error, URLError):
        reason = error.reason
        if isinstance(reason, TimeoutError):
            return True
        text = str(reason).lower()
        return "timed out" in text or "timeout" in text
    return False
