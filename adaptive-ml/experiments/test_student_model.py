from src.core.student_model.student import StudentModel


student = StudentModel(student_id="student_001")

skill = "solve_direct_integration"

student.initialize_skill(
    skill_id=skill,
    initial_mastery=0.50
)

print(
    "Initial mastery:",
    student.get_mastery(skill)
)


evaluations = [
    {
        "correct": True,
        "core_correct": True,
        "missing_constant": False,
        "parse_error": False,
    },
    {
        "correct": False,
        "core_correct": True,
        "missing_constant": True,
        "parse_error": False,
    },
    {
        "correct": False,
        "core_correct": False,
        "missing_constant": False,
        "parse_error": False,
    },
    {
        "correct": True,
        "core_correct": True,
        "missing_constant": False,
        "parse_error": False,
    },
]


for number, evaluation in enumerate(
    evaluations,
    start=1
):
    mastery = student.update_mastery(
        skill_id=skill,
        evaluation=evaluation
    )

    print(
        f"After answer {number}: {mastery:.2f}"
    )