import json
import logging
from dataclasses import dataclass

from src.core.i18n.locale import normalize_locale
from src.core.i18n.story_guidance import has_story_guidance_key, sgt
from src.core.question_engine.contracts import (
    TutorQuestionContext,
)
from src.core.question_engine.providers import (
    ModelProviderError,
    coerce_guided_elaboration_timeout_seconds,
    env_flag,
)
from src.core.tutor_engine.concept_guidance.story_step_guidance import (
    build_story_guidance_context,
)


logger = logging.getLogger(__name__)

GUIDED_STRATEGY_SCHEMA = "matpal.guided_strategy.v1"
ELABORATABLE_QUESTION_IDS = frozenset(
    {
        "story.phrase.doubled",
    }
)
STRATEGIES = frozenset(
    {
        "simpler_words",
        "analogy",
        "concrete_example",
    }
)
EXAMPLES_BY_QUESTION = {
    "story.phrase.doubled": frozenset(
        {
            "double.apples.3x2",
        }
    ),
}
ALLOWED_RESPONSE_KEYS = frozenset(
    {
        "schema",
        "strategy",
        "example_id",
    }
)
MAX_MODEL_OUTPUT_CHARS = 400

STATUS_APPLIED = "applied"
STATUS_OFF = "off"
STATUS_UNAVAILABLE = "unavailable"
STATUS_UNSUPPORTED = "unsupported"
STATUS_FAILED = "failed"
STATUS_STALE = "stale"
STATUS_DUPLICATE = "duplicate"


@dataclass(frozen=True)
class GuidedStrategySelection:
    strategy: str
    example_id: str | None


def guided_ai_mode() -> str:
    value = env_flag("MATPAL_GUIDED_AI_MODE", "off").lower()
    if value in {"off", "optional"}:
        return value
    return "off"


def guided_elaboration_timeout_seconds() -> float:
    return coerce_guided_elaboration_timeout_seconds(
        env_flag("MATPAL_GUIDED_ELABORATION_TIMEOUT_SECONDS")
    )


def elaboration_is_available(
    question_id: str,
    *,
    provider_available: bool,
) -> bool:
    return (
        guided_ai_mode() == "optional"
        and provider_available
        and question_id in ELABORATABLE_QUESTION_IDS
    )


def select_guided_strategy(
    question_id: str,
    *,
    language: str,
    model_provider,
) -> GuidedStrategySelection | None:
    if question_id not in ELABORATABLE_QUESTION_IDS:
        return None
    if not model_provider.is_available():
        return None
    prompt = build_strategy_prompt(question_id, language)
    question = (
        f"Select a teaching strategy for {question_id}."
    )
    context = TutorQuestionContext(
        language=normalize_locale(language),
        subject="mathematics",
        domain="primary_school",
        topic="story_problems",
        problem_id="",
        problem_title="",
        problem_statement="",
        current_step=0,
        total_steps=0,
        current_prompt="",
        expected_input_type="number",
        tutor_metadata={},
        recent_question_history=(),
        session_id=None,
        student_id=None,
    )
    try:
        answer = model_provider.answer(
            question=question,
            context=context,
            sources=(),
            prompt=prompt,
            timeout_seconds=guided_elaboration_timeout_seconds(),
        )
    except (ModelProviderError, TimeoutError, OSError, ValueError):
        logger.warning("Guided elaboration provider failed.")
        return None
    except Exception:
        logger.warning("Guided elaboration provider failed.")
        return None
    return parse_strategy_response(
        getattr(answer, "text", "") or "",
        question_id=question_id,
    )


def outgoing_strategy_request(
    *,
    question_id: str,
    language: str,
) -> dict:
    question = (
        f"Select a teaching strategy for {question_id}."
    )
    return {
        "messages": [
            {
                "role": "system",
                "content": build_strategy_prompt(
                    question_id,
                    language,
                ),
            },
            {
                "role": "user",
                "content": question,
            },
        ]
    }


def build_strategy_prompt(question_id: str, language: str) -> str:
    locale = normalize_locale(language)
    examples = sorted(EXAMPLES_BY_QUESTION.get(question_id, ()))
    strategies = ", ".join(sorted(STRATEGIES))
    example_ids = ", ".join(examples) if examples else "(none)"
    return (
        "You help MAT-PAL choose a teaching strategy.\n"
        f"Language: {locale}\n"
        "Level: grade 4\n"
        f"Question ID: {question_id}\n"
        "Task: choose one reviewed strategy for explaining "
        "what doubled means. Do not explain. Do not invent "
        "mathematics. Do not mention any student's problem. "
        "Reply with a JSON object and nothing else.\n"
        f"Allowed strategies: {strategies}\n"
        f"Allowed example_id values for concrete_example: "
        f"{example_ids}\n"
        "For simpler_words and analogy, example_id must be null.\n"
        "Exact keys: schema, strategy, example_id.\n"
        f'schema must be "{GUIDED_STRATEGY_SCHEMA}".'
    )


def parse_strategy_response(
    text: str,
    *,
    question_id: str,
) -> GuidedStrategySelection | None:
    raw = text.lstrip("\ufeff").strip()
    if not raw or len(raw) > MAX_MODEL_OUTPUT_CHARS:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if set(payload.keys()) != ALLOWED_RESPONSE_KEYS:
        return None
    if payload.get("schema") != GUIDED_STRATEGY_SCHEMA:
        return None
    strategy = payload.get("strategy")
    if strategy not in STRATEGIES:
        return None
    example_id = payload.get("example_id")
    allowed_examples = EXAMPLES_BY_QUESTION.get(question_id, frozenset())
    if strategy == "concrete_example":
        if example_id not in allowed_examples:
            return None
    elif example_id is not None:
        return None
    return GuidedStrategySelection(
        strategy=strategy,
        example_id=example_id,
    )


def render_guided_strategy(
    question_id: str,
    selection: GuidedStrategySelection,
    *,
    language: str,
    problem,
    live_response,
) -> str | None:
    if question_id != "story.phrase.doubled":
        return None
    locale = normalize_locale(language)
    if selection.strategy == "simpler_words":
        key = "story.guide.phrase.doubled.simpler_words"
    elif selection.strategy == "analogy":
        key = "story.guide.phrase.doubled.analogy"
    elif selection.strategy == "concrete_example":
        if selection.example_id == "double.apples.3x2":
            key = "story.guide.phrase.doubled.example.apples"
        else:
            return None
    else:
        return None
    if not has_story_guidance_key(locale, key):
        return None
    text = sgt(locale, key)
    story = build_story_guidance_context(
        problem,
        live_response,
        locale,
    )
    if story is None:
        return text
    here_key = (
        f"story.guide.phrase.here.{story.template_id}.doubled"
    )
    if has_story_guidance_key(locale, here_key):
        here = sgt(locale, here_key, **story.visible_values)
        if here and "{" not in here:
            return f"{text} {here}"
    return text
