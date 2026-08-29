from src.core.question_generation.answer_checker import (
    evaluate_indefinite_solution,
)


expected = "C + x**4/2"

answers = [
    "x**4/2 + C",
    "C + x**4/2",
    "2*x**4/4 + C",
    "y = x**4/2 + C",
    "x**4/2",
    "x**4",
    "this is not math",
]


for answer in answers:
    result = evaluate_indefinite_solution(
        student_answer=answer,
        expected_expression=expected,
    )

    print(f"\nStudent answer: {answer}")
    print(f"Correct:          {result['correct']}")
    print(f"Core correct:     {result['core_correct']}")
    print(f"Missing C:        {result['missing_constant']}")
    print(f"Parse error:      {result['parse_error']}")
    print(f"Feedback:         {result['feedback']}")