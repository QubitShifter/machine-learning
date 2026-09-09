from src.api.mat_pal.schemas import AnswerRequest
from src.api.mat_pal.session_store import (
    MATH_INPUT_PROBE_PROBLEM_ID,
    start_session,
    submit_answer,
)


probe_session = start_session(
    MATH_INPUT_PROBE_PROBLEM_ID
)

assert probe_session.problem_id == (
    MATH_INPUT_PROBE_PROBLEM_ID
)
assert probe_session.status == "waiting_for_answer"
assert probe_session.expected_input_type == "math"
assert not probe_session.completed

probe_response = submit_answer(
    probe_session.session_id,
    AnswerRequest(
        answer=r"e^{-x^2}",
        input_type="math",
    ),
)

assert probe_response is not None
assert probe_response.status == "complete"
assert probe_response.completed
assert probe_response.expected_input_type == "math"
assert probe_response.metadata[
    "received_answer"
] == r"e^{-x^2}"
assert probe_response.metadata[
    "received_input_type"
] == "math"
assert probe_response.metadata[
    "normalized_input"
] == "exp(-x**2)"
assert probe_response.metadata[
    "normalization_ok"
] is True

primary_school_session = start_session(
    "grade4_reverse_reasoning_001"
)

assert primary_school_session.status == (
    "waiting_for_answer"
)
assert primary_school_session.expected_input_type == "text"

primary_school_response = submit_answer(
    primary_school_session.session_id,
    AnswerRequest(
        answer="7",
        input_type="text",
    ),
)

assert primary_school_response is not None
assert primary_school_response.status == "correct"
assert primary_school_response.current_step == 2

print(
    "Math input probe session tests passed."
)
