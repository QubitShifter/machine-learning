import json
import os
from unittest.mock import patch
from urllib.error import URLError

os.environ.setdefault("MATPAL_MODEL_PROVIDER", "none")
os.environ.setdefault("MATPAL_VISION_PROVIDER", "none")

from src.core.imported_problem.compiler import (
    compile_imported_problem,
)
from src.core.imported_problem.contracts import (
    PLAN_SCHEMA_ID,
    ConfirmedProblem,
    PlannedStep,
    StructuredSolutionPlan,
    SUPPORTED_TOPICS,
)
from src.core.imported_problem.errors import (
    ImportedPlanParseError,
    ImportedPlannerRequestError,
    ImportedPlannerTimeoutError,
    UnsupportedImportedProblem,
)
from src.core.imported_problem.openai_compatible import (
    MAX_OUTPUT_TOKENS,
    PLANNER_TEMPERATURE,
    OpenAICompatibleImportedProblemPlanner,
    build_plan_request_payload,
)
from src.core.imported_problem.parse import parse_solution_plan
from src.core.imported_problem.planner import (
    FakeImportedProblemPlanner,
    NullImportedProblemPlanner,
    default_plan_for_confirmed,
)
from src.core.imported_problem.prompt import SYSTEM_PLAN_PROMPT


def dump_plan(**overrides) -> str:
    payload = {
        "schema": PLAN_SCHEMA_ID,
        "supported": True,
        "normalized_topic": "arithmetic",
        "title": "Arithmetic problem",
        "statement": "12 + 7",
        "final_answer": 19,
        "steps": [
            {
                "instruction": "What is 12 + 7?",
                "expected_answer": 19,
                "hints": ["Add 12 and 7."],
            }
        ],
        "unsupported_reason": None,
    }
    payload.update(overrides)
    return json.dumps(payload)


class ScriptedTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, payload, timeout):
        self.requests.append(
            {"payload": payload, "timeout": timeout}
        )
        if not self.responses:
            raise AssertionError("unexpected extra request")
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def explode_urlopen(*args, **kwargs):
    raise AssertionError("real network call")


def assert_prompt_contract():
    text = SYSTEM_PLAN_PROMPT
    for topic in SUPPORTED_TOPICS:
        assert topic in text
    assert "JSON" in text
    assert "Markdown" in text
    assert "expected_answer" in text
    assert "hints" in text
    assert "result_latex" in text
    assert "2x = 12" in text
    assert "x = 6" in text
    assert "unsupported" in text.lower()
    assert "chain-of-thought" in text
    assert "reasoning trace" in text
    assert "hidden thoughts" in text


def assert_parse_rejects_unknown_schema():
    raw = dump_plan(schema="other.schema.v1")
    try:
        parse_solution_plan(raw)
    except ImportedPlanParseError:
        return
    raise AssertionError("unknown schema must be rejected")


def assert_parse_rejects_extra_field():
    payload = json.loads(dump_plan())
    payload["commentary"] = "nope"
    try:
        parse_solution_plan(json.dumps(payload))
    except ImportedPlanParseError:
        return
    raise AssertionError("extra field must be rejected")


def assert_parse_rejects_empty_steps():
    try:
        parse_solution_plan(dump_plan(steps=[]))
    except ImportedPlanParseError:
        return
    raise AssertionError("empty steps must be rejected")


def assert_parse_rejects_missing_expected_answer():
    payload = json.loads(dump_plan())
    del payload["steps"][0]["expected_answer"]
    try:
        parse_solution_plan(json.dumps(payload))
    except ImportedPlanParseError:
        return
    raise AssertionError("missing expected answer must be rejected")


def assert_parse_rejects_prose_and_fences():
    try:
        parse_solution_plan("Here is JSON:\n" + dump_plan())
    except ImportedPlanParseError:
        pass
    else:
        raise AssertionError("prose wrapping must be rejected")
    fenced = "```json\n" + dump_plan() + "\n```"
    try:
        parse_solution_plan(fenced)
    except ImportedPlanParseError:
        return
    raise AssertionError("markdown fences must be rejected")


def assert_parse_result_latex_optional_and_carried():
    plan = parse_solution_plan(
        dump_plan(
            steps=[
                {
                    "instruction": "What is 12 + 7?",
                    "expected_answer": 19,
                    "hints": ["Add 12 and 7."],
                    "result_latex": "  12 + 7 = 19  ",
                }
            ]
        )
    )
    assert plan.steps[0].result_latex == "12 + 7 = 19"

    without = parse_solution_plan(dump_plan())
    assert without.steps[0].result_latex is None


def assert_parse_rejects_malformed_result_latex():
    payload = json.loads(dump_plan())
    payload["steps"][0]["result_latex"] = 12
    try:
        parse_solution_plan(json.dumps(payload))
    except ImportedPlanParseError:
        pass
    else:
        raise AssertionError("numeric result_latex must be rejected")

    payload["steps"][0]["result_latex"] = ["2x = 12"]
    try:
        parse_solution_plan(json.dumps(payload))
    except ImportedPlanParseError:
        return
    raise AssertionError("list result_latex must be rejected")


def assert_equation_fixture_has_step_results():
    plan = default_plan_for_confirmed(
        ConfirmedProblem("2x + 5 = 17", "en")
    )
    assert plan.normalized_topic == "unknown_numbers"
    assert plan.final_answer == 6
    assert plan.steps[0].expected_answer == 12
    assert plan.steps[0].result_latex == "2x = 12"
    assert plan.steps[1].expected_answer == 6
    assert plan.steps[1].result_latex == "x = 6"


def assert_compile_carries_result_latex():
    confirmed = ConfirmedProblem("2x + 5 = 17", "en")
    plan = default_plan_for_confirmed(confirmed)
    problem = compile_imported_problem(confirmed, plan)
    assert problem.solution_steps[0].result_latex == "2x = 12"
    assert problem.solution_steps[1].result_latex == "x = 6"
    assert problem.final_answer == 6


def assert_compile_without_result_latex_still_works():
    confirmed = ConfirmedProblem("12 + 7", "en")
    plan = default_plan_for_confirmed(confirmed)
    assert plan.steps[0].result_latex is None
    problem = compile_imported_problem(confirmed, plan)
    assert problem.solution_steps[0].result_latex is None
    assert problem.final_answer == 19


def assert_compile_uses_confirmed_statement():
    confirmed = ConfirmedProblem(
        transcription="12 + 7",
        language="en",
        topic_hint="geometry",
    )
    plan = default_plan_for_confirmed(confirmed)
    problem = compile_imported_problem(confirmed, plan)
    assert problem.problem_text == "12 + 7"
    assert problem.topic == "arithmetic"
    assert problem.metadata["imported"] is True
    assert problem.metadata["source"] == "image"


def assert_unsupported_topic_does_not_compile():
    plan = StructuredSolutionPlan(
        supported=True,
        normalized_topic="geometry",
        title="Triangle",
        statement="Find the perimeter.",
        final_answer=12,
        steps=(
            PlannedStep("What is the perimeter?", 12, ("Add the sides.",)),
        ),
    )
    confirmed = ConfirmedProblem(
        transcription="Find the perimeter.",
        language="en",
    )
    try:
        compile_imported_problem(confirmed, plan)
    except UnsupportedImportedProblem:
        return
    raise AssertionError("geometry must not compile")


def assert_request_payload_is_text_only():
    confirmed = ConfirmedProblem(
        transcription="12 + 7",
        language="en",
        latex_expressions=(),
        topic_hint="geometry",
        problem_type_hint="triangle",
    )
    payload = build_plan_request_payload(
        model="test-model",
        confirmed=confirmed,
        repair=False,
    )
    assert payload["temperature"] == PLANNER_TEMPERATURE
    user = payload["messages"][1]["content"]
    assert isinstance(user, str)
    encoded = json.dumps(payload)
    assert "image_url" not in encoded
    assert "topic_hint" not in user
    assert "triangle" not in user
    assert payload["model"] == "test-model"
    assert payload["max_tokens"] == MAX_OUTPUT_TOKENS
    assert "max_completion_tokens" not in payload
    assert "top_p" not in payload
    assert "reasoning" not in payload
    assert "reasoning_effort" not in payload


def assert_gpt6_astra_request_compatibility():
    confirmed = ConfirmedProblem("12 + 7", "en")
    for model in (
        "gpt-6-astra",
        "GPT-6-Astra",
        "gpt-6-astra-preview",
        "openai/gpt-6-astra",
    ):
        payload = build_plan_request_payload(
            model=model,
            confirmed=confirmed,
            repair=False,
        )
        assert "temperature" not in payload
        assert "max_tokens" not in payload
        assert payload["max_completion_tokens"] == (
            MAX_OUTPUT_TOKENS
        )
        assert payload["model"] == model
        assert payload["messages"][0]["role"] == "system"
        user = payload["messages"][1]["content"]
        assert isinstance(user, str)
        assert "image_url" not in json.dumps(payload)

    compatible = build_plan_request_payload(
        model="gpt-4o-mini",
        confirmed=confirmed,
        repair=False,
    )
    assert compatible["temperature"] == PLANNER_TEMPERATURE
    assert compatible["max_tokens"] == MAX_OUTPUT_TOKENS
    assert "max_completion_tokens" not in compatible


def assert_repair_then_success():
    transport = ScriptedTransport(
        ["not-json", dump_plan()]
    )
    planner = OpenAICompatibleImportedProblemPlanner(
        api_key="test-not-a-secret",
        base_url="https://example.invalid/v1",
        model="test-model",
        transport=transport,
    )
    with patch(
        "src.core.imported_problem.openai_compatible.urlopen",
        explode_urlopen,
    ):
        plan = planner.plan(
            ConfirmedProblem("12 + 7", "en")
        )
    assert plan.supported is True
    assert len(transport.requests) == 2
    assert "previous JSON was invalid" in (
        transport.requests[1]["payload"]["messages"][1]["content"]
    )


def assert_repair_exhausted():
    transport = ScriptedTransport(["bad", "still-bad"])
    planner = OpenAICompatibleImportedProblemPlanner(
        api_key="test-not-a-secret",
        base_url="https://example.invalid/v1",
        model="test-model",
        transport=transport,
    )
    with patch(
        "src.core.imported_problem.openai_compatible.urlopen",
        explode_urlopen,
    ):
        try:
            planner.plan(ConfirmedProblem("12 + 7", "en"))
        except ImportedPlanParseError:
            assert len(transport.requests) == 2
            return
    raise AssertionError("two invalid outputs must fail")


def assert_timeout_and_http_error():
    timeout_planner = OpenAICompatibleImportedProblemPlanner(
        api_key="test-not-a-secret",
        base_url="https://example.invalid/v1",
        model="test-model",
        transport=ScriptedTransport(
            [TimeoutError("timed out")]
        ),
    )
    try:
        timeout_planner.plan(ConfirmedProblem("12 + 7", "en"))
    except ImportedPlannerTimeoutError:
        pass
    else:
        raise AssertionError("timeout must map to planner timeout")

    http_planner = OpenAICompatibleImportedProblemPlanner(
        api_key="test-not-a-secret",
        base_url="https://example.invalid/v1",
        model="test-model",
        transport=ScriptedTransport(
            [URLError("connection refused")]
        ),
    )
    try:
        http_planner.plan(ConfirmedProblem("12 + 7", "en"))
    except ImportedPlannerRequestError:
        return
    raise AssertionError("HTTP error must map to request error")


def assert_null_and_fake():
    null = NullImportedProblemPlanner()
    assert null.is_available() is False
    fake = FakeImportedProblemPlanner()
    assert fake.is_available() is True
    plan = fake.plan(ConfirmedProblem("2x + 5 = 17", "en"))
    assert plan.normalized_topic == "unknown_numbers"


def main():
    assert_prompt_contract()
    assert_parse_rejects_unknown_schema()
    assert_parse_rejects_extra_field()
    assert_parse_rejects_empty_steps()
    assert_parse_rejects_missing_expected_answer()
    assert_parse_rejects_prose_and_fences()
    assert_parse_result_latex_optional_and_carried()
    assert_parse_rejects_malformed_result_latex()
    assert_equation_fixture_has_step_results()
    assert_compile_carries_result_latex()
    assert_compile_without_result_latex_still_works()
    assert_compile_uses_confirmed_statement()
    assert_unsupported_topic_does_not_compile()
    assert_request_payload_is_text_only()
    assert_gpt6_astra_request_compatibility()
    assert_repair_then_success()
    assert_repair_exhausted()
    assert_timeout_and_http_error()
    assert_null_and_fake()
    print("imported_problem_planner tests passed")


if __name__ == "__main__":
    main()
