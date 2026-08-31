from src.core.question_generation.linear_first_order import (
    generate_linear_first_order_question,
)


for difficulty in [
    1,
    2,
    3,
]:
    print(
        f"\n--- Difficulty {difficulty} ---"
    )

    for _ in range(5):
        question = (
            generate_linear_first_order_question(
                difficulty=difficulty
            )
        )

        print(
            question["question"]
        )

        print(
            "P(x) =",
            question["P"],
        )

        print(
            "Q(x) =",
            question["Q"],
        )