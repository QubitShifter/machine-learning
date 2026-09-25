from typing import Literal


GuidanceMode = Literal[
    "independent",
    "guided",
    "supported",
]
GuidanceReason = Literal[
    "guidance_independent",
    "guidance_after_error",
    "guidance_repeated_errors",
    "guidance_supported",
]

MATH_ERROR_TYPE = "incorrect_answer"
FORMAT_ERROR_TYPES = frozenset(
    {
        "empty_answer",
        "not_numeric",
        "not_integer",
    }
)
GUIDANCE_TOPICS = frozenset(
    {
        "story_problems",
        "logical_reasoning",
    }
)


def choose_guidance_mode(
    math_errors_on_step: int,
) -> tuple[GuidanceMode, GuidanceReason]:
    """
    Choose tutor support from current-step math errors only.
    """

    count = int(math_errors_on_step)
    if count <= 0:
        return "independent", "guidance_independent"
    if count == 1:
        return "independent", "guidance_after_error"
    if count == 2:
        return "guided", "guidance_repeated_errors"
    return "supported", "guidance_supported"
