from src.core.tutor_engine.concept_guidance.separable_guidance import (
    respond_to_stage3_concept_question,
)


tests = [
    "what is opposite to ln?",
    "what is the inverse of ln?",
    "what reverses ln?",
    "what cancels ln?",
]


for question in tests:
    print("\nQuestion:")
    print(question)

    response = respond_to_stage3_concept_question(
        question
    )

    print("\nTutor:")
    print(response)