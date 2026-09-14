import sympy as sp

from src.core.i18n.ode import ot
from src.core.i18n.locale import normalize_locale
from src.core.tutor_engine.concept_guidance.log_solve_stage_checker import (
    evaluate_absorb_constant_step,
    evaluate_apply_exp_step,
    evaluate_cancel_log_step,
    evaluate_remove_absolute_value_step,
    evaluate_rename_exp_constant_step,
    evaluate_split_exponential_step,
)
from src.core.tutor_engine.concept_guidance.separable_guidance import (
    respond_to_stage3_concept_question,
)
from src.core.tutor_engine.concept_guidance.separable_session import (
    LogSolveStage,
)


def looks_like_concept_question(
    message: str,
) -> bool:
    message = message.lower().strip()

    question_phrases = [
        "why",
        "what",
        "where",
        "how",
        "explain",
        "help",
        "don't understand",
        "dont understand",
        "do not understand",
        "confused",
        "what does",
        "what is",
        "can you",
        "защо",
        "какво е",
        "какво представлява",
        "обясни",
        "не разбирам",
        "как се",
        "как да",
    ]

    return (
        "?" in message
        or any(
            phrase in message
            for phrase in question_phrases
        )
    )


class SeparableLogEngine:
    def __init__(
        self,
        integrated_fx,
        language: str | None = None,
    ):
        self.integrated_fx = integrated_fx
        self.language = normalize_locale(language)

    def get_step_title(
        self,
        stage: LogSolveStage,
    ) -> str:
        titles = {
            LogSolveStage.APPLY_EXP:
                "separable.log.title.apply_exp",

            LogSolveStage.CANCEL_LOG:
                "separable.log.title.cancel",

            LogSolveStage.SPLIT_EXPONENTIAL:
                "separable.log.title.split",

            LogSolveStage.RENAME_EXP_CONSTANT:
                "separable.log.title.rename",

            LogSolveStage.REMOVE_ABSOLUTE_VALUE:
                "separable.log.title.abs",

            LogSolveStage.ABSORB_CONSTANT:
                "separable.log.title.absorb",

            LogSolveStage.COMPLETE:
                "separable.log.title.complete",
        }

        return ot(self.language, titles[stage])

    def get_prompt(
        self,
        stage: LogSolveStage,
    ) -> str:
        fx_text = sp.sstr(
            self.integrated_fx
        )

        prompts = {
            LogSolveStage.APPLY_EXP:
                "separable.log.prompt.apply_exp",

            LogSolveStage.CANCEL_LOG:
                "separable.log.prompt.cancel",

            LogSolveStage.SPLIT_EXPONENTIAL:
                "separable.log.prompt.split",

            LogSolveStage.RENAME_EXP_CONSTANT:
                "separable.log.prompt.rename",

            LogSolveStage.REMOVE_ABSOLUTE_VALUE:
                "separable.log.prompt.abs",

            LogSolveStage.ABSORB_CONSTANT:
                "separable.log.prompt.absorb",

            LogSolveStage.COMPLETE:
                "separable.log.prompt.complete",
        }

        return ot(
            self.language,
            prompts[stage],
            fx=fx_text,
        )

    def evaluate(
        self,
        stage: LogSolveStage,
        student_answer: str,
    ) -> dict:
        if looks_like_concept_question(
            student_answer
        ):
            concept_response = (
                respond_to_stage3_concept_question(
                    student_answer,
                    integrated_fx=self.integrated_fx,
                )
            )

            if concept_response is not None:
                return {
                    "kind": "concept",
                    "correct": False,
                    "advance": False,
                    "feedback": concept_response,
                    "suggestion": None,
                }

        validator = self._get_validator(
            stage
        )

        if validator is None:
            return {
                "kind": "complete",
                "correct": True,
                "advance": False,
                "feedback": (
                    "The logarithmic transformation "
                    "is already complete."
                ),
                "suggestion": None,
            }

        result = validator(
            student_answer=student_answer,
            integrated_fx=self.integrated_fx,
        )

        return {
            "kind": "math",
            "correct": result["correct"],
            "advance": result["correct"],
            "steps_completed": result.get(
                "steps_completed",
                1 if result["correct"] else 0,
            ),
            "feedback": result["feedback"],
            "suggestion": result.get(
                "suggestion"
            ),
            "error_type": result.get(
                "error_type"
            ),
        }

    def _get_validator(
        self,
        stage: LogSolveStage,
    ):
        validators = {
            LogSolveStage.APPLY_EXP:
                evaluate_apply_exp_step,

            LogSolveStage.CANCEL_LOG:
                evaluate_cancel_log_step,

            LogSolveStage.SPLIT_EXPONENTIAL:
                evaluate_split_exponential_step,

            LogSolveStage.RENAME_EXP_CONSTANT:
                evaluate_rename_exp_constant_step,

            LogSolveStage.REMOVE_ABSOLUTE_VALUE:
                evaluate_remove_absolute_value_step,

            LogSolveStage.ABSORB_CONSTANT:
                evaluate_absorb_constant_step,
        }

        return validators.get(stage)