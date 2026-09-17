from src.core.i18n.question import qt
from src.core.question_engine.contracts import (
    TutorQuestionContext,
)
from src.core.question_engine.grounding import (
    METHOD_SEPARABLE,
    VerifiedTransformation,
)


_ALT_INTENT_PHRASES = (
    "another way",
    "another method",
    "another solution method",
    "other method",
    "other way",
    "other solution method",
    "what other method",
    "any other method",
    "different method",
    "without an integrating factor",
    "without the integrating factor",
    "without integrating factor",
    "separation of variables",
    "друг начин",
    "други начини",
    "друг метод",
    "други методи",
    "какъв друг метод",
    "какви други методи",
    "без интегриращ фактор",
    "без интегриращия фактор",
    "разделяне на променливите",
)


_SEPARATION_PHRASES = (
    "separation of variables",
    "разделяне на променливите",
)
_LINEAR_TOPIC = "first_order_linear"


def _fold_question(question: str) -> str:
    text = question.strip().lower()
    for mark in (",", ".", "!", "?", ";", ":", "„", "“", "”", "'", '"'):
        text = text.replace(mark, " ")
    return " ".join(text.split())


def asks_about_separation_of_variables(question: str) -> bool:
    folded = _fold_question(question)
    if not folded:
        return False
    return any(
        phrase in folded for phrase in _SEPARATION_PHRASES
    )


def asks_about_alternative_method(question: str) -> bool:
    folded = _fold_question(question)
    if not folded:
        return False
    return any(phrase in folded for phrase in _ALT_INTENT_PHRASES)


def verified_separable_transformation(
    metadata: dict | None,
) -> VerifiedTransformation | None:
    if not isinstance(metadata, dict):
        return None
    if metadata.get("separable_transformation_verified") is not True:
        return None

    evidence = metadata.get("verified_method_evidence")
    if not isinstance(evidence, list) or not evidence:
        return None

    item = evidence[0]
    if not isinstance(item, dict):
        return None
    if item.get("method") != METHOD_SEPARABLE:
        return None
    if item.get("verified") is not True:
        return None

    original = item.get("original_equation")
    rearranged = item.get("rearranged_equation")
    separated = item.get("separated_equation")
    if not all(
        isinstance(value, str) and value.strip()
        for value in (original, rearranged, separated)
    ):
        return None

    conditions = item.get("conditions") or ()
    constants = item.get("constant_solutions") or ()
    if not isinstance(conditions, (list, tuple)):
        conditions = ()
    if not isinstance(constants, (list, tuple)):
        constants = ()

    integration = item.get("integration_step")
    if not isinstance(integration, str) or not integration.strip():
        integration = None

    return VerifiedTransformation(
        method=METHOD_SEPARABLE,
        original_equation=original.strip(),
        rearranged_equation=rearranged.strip(),
        separated_equation=separated.strip(),
        integration_step=integration,
        conditions=tuple(
            str(entry) for entry in conditions if str(entry).strip()
        ),
        constant_solutions=tuple(
            str(entry) for entry in constants if str(entry).strip()
        ),
    )


def build_verified_alternative_explanation(
    evidence: VerifiedTransformation | None,
    language: str | None,
) -> str | None:
    if evidence is None:
        return None
    if evidence.method != METHOD_SEPARABLE:
        return None
    if not evidence.separated_equation:
        return None

    sections = [
        qt(language, "question.alternative.intro"),
        _math_block(evidence.original_equation),
        qt(language, "question.alternative.rearrange"),
        _math_block(evidence.rearranged_equation),
        qt(language, "question.alternative.separate"),
        _math_block(evidence.separated_equation),
    ]

    restriction_sections = _restriction_sections(
        evidence,
        language,
    )
    sections.extend(restriction_sections)

    sections.append(qt(language, "question.alternative.next_step"))
    return "\n\n".join(sections)


def match_verified_alternative_explanation(
    question: str,
    context: TutorQuestionContext,
) -> str | None:
    try:
        if not asks_about_alternative_method(question):
            return None
        if context.topic != _LINEAR_TOPIC:
            return None
        evidence = verified_separable_transformation(
            context.tutor_metadata,
        )
        return build_verified_alternative_explanation(
            evidence,
            context.language,
        )
    except (
        TypeError,
        ValueError,
        KeyError,
        AttributeError,
    ):
        return None


def match_alternative_method_explanation(
    question: str,
    context: TutorQuestionContext,
) -> str | None:
    try:
        if not asks_about_alternative_method(question):
            return None
        if context.topic != _LINEAR_TOPIC:
            return None
        evidence = verified_separable_transformation(
            context.tutor_metadata,
        )
        verified = build_verified_alternative_explanation(
            evidence,
            context.language,
        )
        if verified:
            return verified
        return build_unverified_alternative_explanation(
            question,
            context,
        )
    except (
        TypeError,
        ValueError,
        KeyError,
        AttributeError,
    ):
        if (
            asks_about_alternative_method(question)
            and context.topic == _LINEAR_TOPIC
        ):
            return build_unverified_alternative_explanation(
                question,
                context,
            )
        return None


def build_unverified_alternative_explanation(
    question: str,
    context: TutorQuestionContext,
) -> str:
    sections = [
        qt(
            context.language,
            "question.alternative.unverified.if_applies",
        ),
    ]
    equation = _current_equation(context)
    if equation:
        sections.append(_math_block(equation))
    if asks_about_separation_of_variables(question):
        sections.append(
            qt(
                context.language,
                "question.alternative.unverified.separation",
            )
        )
    else:
        sections.append(
            qt(
                context.language,
                "question.alternative.unverified.no_verified",
            )
        )
    sections.append(
        qt(
            context.language,
            "question.alternative.unverified.not_impossible",
        )
    )
    sections.append(
        qt(
            context.language,
            "question.alternative.unverified.continue",
        )
    )
    return "\n\n".join(sections)


def _current_equation(context: TutorQuestionContext) -> str | None:
    metadata = context.tutor_metadata or {}
    equation = metadata.get("equation")
    if isinstance(equation, str) and equation.strip():
        return equation.strip()
    statement = context.problem_statement
    if isinstance(statement, str) and statement.strip():
        return statement.strip()
    return None


def _math_block(expression: str) -> str:
    return f"    {expression.strip()}"


def _restriction_sections(
    evidence: VerifiedTransformation,
    language: str | None,
) -> list[str]:
    sections: list[str] = []
    if evidence.conditions:
        sections.append(
            qt(language, "question.alternative.restriction_lead")
        )
        for condition in evidence.conditions:
            sections.append(_math_block(condition))
    if evidence.constant_solutions:
        sections.append(
            qt(language, "question.alternative.equilibrium_lead")
        )
        for constant in evidence.constant_solutions:
            sections.append(_math_block(constant))
        sections.append(
            qt(language, "question.alternative.equilibrium_tail")
        )
    return sections
