from src.core.tutor_engine.primary_school.reverse_reasoning_solver import (
    load_reverse_reasoning_problem,
)

from src.core.tutor_engine.primary_school.session import (
    PrimarySchoolSession,
)


problem = load_reverse_reasoning_problem(
    "grade4_reverse_reasoning_001"
)

session = PrimarySchoolSession(
    problem=problem
)


print(
    "Complete:",
    session.is_complete(),
)

print(
    "Current step:",
    session.get_current_step().step_number,
)


session.record_attempt()
session.record_attempt()

print(
    "Attempts on step 1:",
    session.get_attempts_for_current_step(),
)


session.record_hint()

print(
    "Hints on step 1:",
    session.get_hints_for_current_step(),
)


session.advance()

print(
    "Current step after advance:",
    session.get_current_step().step_number,
)


while not session.is_complete():
    session.record_attempt()
    session.advance()


print(
    "Complete:",
    session.is_complete(),
)

print(
    "Completed steps:",
    session.get_completed_step_count(),
)

print(
    "Total attempts:",
    session.get_total_attempts(),
)

print(
    "Total hints:",
    session.get_total_hints_used(),
)