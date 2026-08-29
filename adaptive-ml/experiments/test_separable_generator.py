from src.core.question_generation.separable import (
    generate_separable_question,
)


for difficulty in range(1, 4):
    print(
        f"\nDIFFICULTY {difficulty}"
    )

    for _ in range(3):
        question = (
            generate_separable_question(
                difficulty=difficulty
            )
        )

        print(
            question["question"]
        )

        print(
            "Answer:",
            question["answer"]["expression"]
        )