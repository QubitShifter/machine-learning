from src.core.tutor_engine.primary_school.reverse_reasoning_solver import (
    load_reverse_reasoning_problem,
)


problem = load_reverse_reasoning_problem(
    "grade4_reverse_reasoning_001"
)


print(
    "Problem ID:",
    problem.problem_id,
)

print(
    "Title:",
    problem.title,
)

print(
    "Grade:",
    problem.grade,
)

print(
    "Problem type:",
    problem.problem_type.value,
)

print()
print(
    "Problem text:"
)

print(
    problem.problem_text
)

print()
print(
    "Strategy:",
    problem.strategy,
)

print(
    "Final answer:",
    problem.final_answer,
)

print()
print(
    "Number of steps:",
    problem.get_number_of_steps(),
)

print()
print(
    "Skills:"
)

for skill_id in problem.get_skill_ids():
    print(
        " -",
        skill_id,
    )

print()
print(
    "Solution steps:"
)

for step in problem.solution_steps:
    print()
    print(
        f"Step {step.step_number}"
    )

    print(
        "Skill:",
        step.skill_id,
    )

    print(
        "Type:",
        step.step_type.value,
    )

    print(
        "Prompt:",
        step.prompt,
    )

    print(
        "Expected answer:",
        step.expected_answer,
    )

    print(
        "Operation:",
        step.operation,
    )

    print(
        "Hint:",
        step.hint,
    )