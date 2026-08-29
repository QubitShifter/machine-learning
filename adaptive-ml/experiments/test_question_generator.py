from src.core.question_generation.direct_integration import (
    generate_direct_integration_question,
)


for difficulty in range(1, 4):
    print(f"\nDIFFICULTY {difficulty}")

    for _ in range(3):
        question = generate_direct_integration_question(
            difficulty=difficulty
        )

        print(question["question"])
        print(
            "Answer:",
            question["answer"]["expression"]
        )