import sympy as sp

from src.core.question_engine.alternative_methods import (
    match_alternative_method_explanation,
)
from src.core.question_engine.contracts import TutorQuestionContext
from src.core.tutor_engine.concept_guidance.linear_first_order_guidance import (
    explain_specific_linear_concept,
)
from src.core.tutor_engine.concept_guidance.separable_guidance import (
    respond_to_stage3_concept_question,
)
from src.core.tutor_engine.concept_guidance.unknown_number_guidance import (
    match_unknown_number_explanation,
)
from src.core.tutor_engine.concept_guidance.logical_reasoning_guidance import (
    match_logical_reasoning_explanation,
)
from src.core.tutor_engine.concept_guidance.word_problem_guidance import (
    match_word_problem_explanation,
)


def match_local_concept(
    question: str,
    context: TutorQuestionContext,
) -> str | None:
    topic = context.topic
    metadata = context.tutor_metadata
    if not isinstance(metadata, dict):
        metadata = {}

    if topic == "first_order_linear":
        alternative = match_alternative_method_explanation(
            question,
            context,
        )
        if alternative:
            return alternative
        p_expression = metadata.get("p_expression")
        if isinstance(p_expression, str):
            try:
                p_expression = sp.sympify(p_expression)
            except (
                sp.SympifyError,
                TypeError,
                ValueError,
                SyntaxError,
            ):
                p_expression = None
        return explain_specific_linear_concept(
            question,
            p_expression=p_expression,
            language=context.language,
        )

    if topic == "separable_equations":
        return respond_to_stage3_concept_question(
            question,
        )

    if topic == "unknown_numbers":
        return match_unknown_number_explanation(
            question,
            context,
        )

    if topic == "story_problems":
        return match_word_problem_explanation(
            question,
            context,
        )

    if topic == "logical_reasoning":
        return match_logical_reasoning_explanation(
            question,
            context,
        )

    return None
