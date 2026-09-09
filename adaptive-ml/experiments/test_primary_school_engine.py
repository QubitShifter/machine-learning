from src.core.tutor_engine.contracts import (
    StudentSubmission,
)

from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)

from src.core.tutor_engine.primary_school.reverse_reasoning_solver import (
    load_reverse_reasoning_problem,
)


problem = load_reverse_reasoning_problem(
    "grade4_reverse_reasoning_001"
)

engine = PrimarySchoolTutorEngine(
    problem=problem
)


def print_response(
    label: str,
    response,
):
    print()
    print(label)
    print("-" * len(label))

    print(
        "Status:",
        response.status,
    )

    print(
        "Feedback:",
        response.feedback,
    )

    print(
        "Suggestion:",
        response.suggestion,
    )

    print(
        "Current step:",
        response.current_step,
    )

    print(
        "Total steps:",
        response.total_steps,
    )

    print(
        "Completed:",
        response.completed,
    )

    print(
        "Hint available:",
        response.hint_available,
    )

    print(
        "Metadata:",
        response.metadata,
    )


#
# Initial state
#
response = engine.get_current_response()

print_response(
    "Initial state",
    response,
)


#
# Wrong answer on step 1
#
response = engine.submit(
    StudentSubmission(
        answer="6"
    )
)

print_response(
    "Wrong answer",
    response,
)


#
# Request hint
#
response = engine.request_hint()

print_response(
    "Hint request",
    response,
)


#
# Correct answer on step 1
#
response = engine.submit(
    StudentSubmission(
        answer="7"
    )
)

print_response(
    "Correct step 1",
    response,
)


#
# Finish remaining steps
#
answers = [
    "12",
    "24",
    "28",
    "56",
    "58",
    "116",
]

for answer in answers:
    response = engine.submit(
        StudentSubmission(
            answer=answer
        )
    )

    print_response(
        f"Answer {answer}",
        response,
    )


#
# Final session statistics
#
print()
print(
    "Final session statistics"
)

print(
    "Completed:",
    engine.session.is_complete(),
)

print(
    "Completed steps:",
    engine.session.get_completed_step_count(),
)

print(
    "Total attempts:",
    engine.session.get_total_attempts(),
)

print(
    "Total hints:",
    engine.session.get_total_hints_used(),
)