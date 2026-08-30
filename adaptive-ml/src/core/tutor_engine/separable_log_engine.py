import sympy as sp

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
    ):
        self.integrated_fx = integrated_fx

    def get_step_title(
        self,
        stage: LogSolveStage,
    ) -> str:
        titles = {
            LogSolveStage.APPLY_EXP:
                "Step 3.1 — Apply exp to both sides",

            LogSolveStage.CANCEL_LOG:
                "Step 3.2 — Simplify exp(ln|y|)",

            LogSolveStage.SPLIT_EXPONENTIAL:
                "Step 3.3 — Split the exponential",

            LogSolveStage.RENAME_EXP_CONSTANT:
                "Step 3.4 — Rename exp(C)",

            LogSolveStage.REMOVE_ABSOLUTE_VALUE:
                "Step 3.5 — Remove the absolute value",

            LogSolveStage.ABSORB_CONSTANT:
                "Step 3.6 — Absorb the constants",

            LogSolveStage.COMPLETE:
                "Stage 3 complete",
        }

        return titles[stage]

    def get_prompt(
        self,
        stage: LogSolveStage,
    ) -> str:
        fx_text = sp.sstr(
            self.integrated_fx
        )

        prompts = {
            LogSolveStage.APPLY_EXP: (
                "Starting from:\n"
                f"    ln|y| = {fx_text} + C\n\n"
                "Apply the inverse of ln to BOTH sides.\n"
                "Write the complete transformed equation."
            ),

            LogSolveStage.CANCEL_LOG: (
                "Current equation:\n"
                f"    exp(ln|y|) = exp({fx_text} + C)\n\n"
                "Simplify exp(ln|y|).\n"
                "Write the complete equation."
            ),

            LogSolveStage.SPLIT_EXPONENTIAL: (
                "Current equation:\n"
                f"    |y| = exp({fx_text} + C)\n\n"
                "Use:\n"
                "    exp(a + b) = exp(a)*exp(b)\n\n"
                "Rewrite the complete equation."
            ),

            LogSolveStage.RENAME_EXP_CONSTANT: (
                "Current equation:\n"
                f"    |y| = exp({fx_text})*exp(C)\n\n"
                "Since exp(C) is a positive constant, "
                "rename it as K.\n"
                "Rewrite the equation."
            ),

            LogSolveStage.REMOVE_ABSOLUTE_VALUE: (
                "Current equation:\n"
                f"    |y| = K*exp({fx_text})\n\n"
                "Remove the absolute value and represent "
                "both possible signs of y."
            ),

            LogSolveStage.ABSORB_CONSTANT: (
                "Current equation:\n"
                f"    y = +/- K*exp({fx_text})\n\n"
                "Combine +/- K into one new arbitrary "
                "constant C."
            ),

            LogSolveStage.COMPLETE:
                "The logarithmic transformation is complete.",
        }

        return prompts[stage]

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