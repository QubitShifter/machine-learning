import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.core.imported_problem.contracts import (
    ConfirmedProblem,
    StructuredSolutionPlan,
)
from src.core.imported_problem.errors import (
    ImportedPlannerRequestError,
    ImportedPlannerTimeoutError,
    ImportedPlannerUnavailableError,
    ImportedPlanParseError,
)
from src.core.imported_problem.parse import parse_solution_plan
from src.core.imported_problem.prompt import (
    SYSTEM_PLAN_PROMPT,
    repair_plan_task,
    user_plan_task,
)
from src.core.openai_compatible_sampling import (
    completion_token_parameter,
    supports_custom_temperature,
)


logger = logging.getLogger(__name__)

DEFAULT_PLANNER_TIMEOUT_SECONDS = 45.0
MAX_OUTPUT_TOKENS = 1200
PLANNER_TEMPERATURE = 0


class OpenAICompatibleImportedProblemPlanner:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = (
            DEFAULT_PLANNER_TIMEOUT_SECONDS
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
            self._api_key and self._base_url and self._model
        )

    def plan(
        self,
        confirmed: ConfirmedProblem,
    ) -> StructuredSolutionPlan:
        if not self.is_available():
            raise ImportedPlannerUnavailableError(
                "Imported problem planner unavailable."
            )

        first = self._complete(confirmed, repair=False)
        try:
            return parse_solution_plan(first)
        except ImportedPlanParseError:
            logger.warning("imported plan parse failed")

        second = self._complete(confirmed, repair=True)
        try:
            return parse_solution_plan(second)
        except ImportedPlanParseError:
            logger.warning("imported plan parse failed")
            raise

    def _complete(
        self,
        confirmed: ConfirmedProblem,
        *,
        repair: bool,
    ) -> str:
        payload = build_plan_request_payload(
            model=self._model,
            confirmed=confirmed,
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
            ImportedPlannerTimeoutError,
            ImportedPlannerRequestError,
        ):
            raise
        except (
            HTTPError,
            URLError,
            TimeoutError,
            ValueError,
        ) as error:
            if _is_timeout_error(error):
                raise ImportedPlannerTimeoutError(
                    "Imported problem planner timed out."
                ) from error
            raise ImportedPlannerRequestError(
                "Imported problem planner request failed."
            ) from error

    def _urlopen_chat(self, payload: dict) -> str:
        request = Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )
        with urlopen(
            request,
            timeout=self._timeout_seconds,
        ) as response:
            body = json.loads(response.read().decode("utf-8"))
        try:
            return read_message_content(body)
        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as error:
            raise ImportedPlannerRequestError(
                "Imported problem planner returned an unexpected response."
            ) from error


def build_plan_request_payload(
    *,
    model: str,
    confirmed: ConfirmedProblem,
    repair: bool,
) -> dict:
    language = (
        confirmed.language
        if confirmed.language in {"en", "bg"}
        else "en"
    )
    task = (
        repair_plan_task(
            confirmed.transcription,
            language,
            confirmed.latex_expressions,
        )
        if repair
        else user_plan_task(
            confirmed.transcription,
            language,
            confirmed.latex_expressions,
        )
    )
    payload = {
        "model": model,
        completion_token_parameter(model): MAX_OUTPUT_TOKENS,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PLAN_PROMPT,
            },
            {
                "role": "user",
                "content": task,
            },
        ],
    }
    if supports_custom_temperature(model):
        payload["temperature"] = PLANNER_TEMPERATURE
    return payload


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
