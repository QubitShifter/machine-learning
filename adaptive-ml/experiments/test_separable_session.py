from src.core.tutor_engine.concept_guidance.separable_session import (
    SeparableSolutionSession,
)


session = SeparableSolutionSession()

while not session.is_complete():
    print(
        "\nCurrent stage:",
        session.get_stage_name(),
    )

    print(
        "Prompt:",
        session.get_prompt(),
    )

    session.record_attempt()

    print(
        "Attempts:",
        session.get_attempts_for_current_stage(),
    )

    session.advance()


print("\nSession complete.")

print(
    session.get_summary()
)