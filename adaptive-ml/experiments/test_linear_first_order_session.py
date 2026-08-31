from src.core.tutor_engine.linear_first_order_session import (
    LinearODEStage,
    LinearODESolutionSession,
)


session = LinearODESolutionSession()

print(
    "Initial stage:",
    session.get_stage()
)

while not session.is_complete():
    print(
        "Current:",
        session.get_stage_name()
    )

    session.record_attempt()

    session.advance()

print(
    "Final stage:",
    session.get_stage()
)

print(
    "\nSummary:"
)

print(
    session.get_summary()
)