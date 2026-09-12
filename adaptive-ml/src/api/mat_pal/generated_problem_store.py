from collections import OrderedDict

from src.api.mat_pal.tutor_registry import (
    TutorRegistration,
)


MAX_GENERATED_PROBLEMS = 128

_generated_registrations: OrderedDict[
    str,
    TutorRegistration,
] = OrderedDict()


def add_generated_problem(
    registration: TutorRegistration,
) -> TutorRegistration:
    _generated_registrations[
        registration.problem_id
    ] = registration
    _generated_registrations.move_to_end(
        registration.problem_id
    )

    while (
        len(_generated_registrations)
        > MAX_GENERATED_PROBLEMS
    ):
        _generated_registrations.popitem(
            last=False
        )

    return registration


def get_generated_problem(
    problem_id: str,
) -> TutorRegistration | None:
    registration = _generated_registrations.get(
        problem_id
    )

    if registration is not None:
        _generated_registrations.move_to_end(
            problem_id
        )

    return registration


def clear_generated_problems() -> None:
    _generated_registrations.clear()
