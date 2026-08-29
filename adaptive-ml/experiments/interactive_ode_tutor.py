from src.core.question_generation.answer_checker import (
    evaluate_indefinite_solution,
)
from src.core.question_generation.direct_integration import (
    generate_direct_integration_question,
)
from src.core.student_model.skill_session import (
    SkillSession,
)
from src.core.student_model.student import (
    StudentModel,
)
from src.core.tutor_engine.reflection import (
    ask_for_difficulty,
    respond_to_difficulty,
    student_says_everything_is_clear,
)


def choose_difficulty(
    mastery: float,
) -> int:
    if mastery < 0.40:
        return 1

    if mastery < 0.75:
        return 2

    return 3


student = StudentModel(
    student_id="student_001"
)

skill = "solve_direct_integration"

student.initialize_skill(
    skill_id=skill,
    initial_mastery=0.50,
)

session = SkillSession(
    skill_id=skill,
    min_questions=5,
    mastery_threshold=0.90,
    required_first_attempt_streak=3,
)


print("Adaptive ODE Tutor")
print("------------------")
print("Type 'quit' to stop.")
print("Type 'skip' to give up on the current question.\n")


while True:
    mastery = student.get_mastery(
        skill
    )

    if session.is_mastered(
        mastery
    ):
        summary = session.get_summary()

        print("\nSkill mastered!")
        print(f"Skill: {skill}")
        print(
            f"Final mastery: "
            f"{mastery:.2f}"
        )
        print(
            f"Questions completed: "
            f"{summary['questions_completed']}"
        )
        print(
            f"Total attempts: "
            f"{summary['total_attempts']}"
        )
        print(
            "First-attempt correct streak: "
            f"{summary['first_attempt_correct_streak']}"
        )

        print(
            "\nYou are ready to move "
            "to the next skill."
        )

        break

    difficulty = choose_difficulty(
        mastery
    )

    question = (
        generate_direct_integration_question(
            difficulty=difficulty
        )
    )

    print(
        f"\nCurrent mastery: "
        f"{mastery:.2f}"
    )

    print(
        f"Difficulty: "
        f"{difficulty}"
    )

    print(
        f"Questions completed: "
        f"{session.questions_completed}"
    )

    print(
        "First-attempt streak: "
        f"{session.first_attempt_correct_streak}"
    )

    print(
        f"\nQuestion: "
        f"{question['question']}"
    )

    attempt_number = 1
    question_completed = False

    while not question_completed:
        student_answer = input(
            "Your answer: "
        ).strip()

        command = student_answer.lower()

        if command == "quit":
            print(
                f"\nFinal mastery: "
                f"{student.get_mastery(skill):.2f}"
            )
            raise SystemExit

        if command == "skip":
            final_evaluation = {
                "correct": False,
                "core_correct": False,
                "missing_constant": False,
                "parse_error": False,
                "error_type": "question_skipped",
                "feedback": "Question skipped.",
                "steps": [],
            }

            updated_mastery = (
                student.update_mastery_after_question(
                    skill_id=skill,
                    attempts=attempt_number,
                    final_evaluation=final_evaluation,
                )
            )

            session.record_question(
                attempts=attempt_number,
                correct=False,
            )

            print(
                "\nTutor: We'll move on "
                "and revisit this skill later."
            )

            print(
                f"Updated mastery: "
                f"{updated_mastery:.2f}"
            )

            question_completed = True
            continue

        evaluation = (
            evaluate_indefinite_solution(
                student_answer=student_answer,
                expected_expression=(
                    question["answer"]["expression"]
                ),
            )
        )

        print(
            f"\nFeedback: "
            f"{evaluation['feedback']}"
        )

        if evaluation["steps"]:
            print("\nSuggested steps:")

            for number, step in enumerate(
                evaluation["steps"],
                start=1,
            ):
                print(
                    f"  {number}. {step}"
                )

        if evaluation["correct"]:
            updated_mastery = (
                student.update_mastery_after_question(
                    skill_id=skill,
                    attempts=attempt_number,
                    final_evaluation=evaluation,
                )
            )

            session.record_question(
                attempts=attempt_number,
                correct=True,
            )

            print(
                f"\nQuestion completed "
                f"in {attempt_number} attempt(s)."
            )

            print(
                f"Updated mastery: "
                f"{updated_mastery:.2f}"
            )

            print(
                "\nGood. Let's move "
                "to the next question."
            )

            question_completed = True
            continue

        if evaluation["core_correct"]:
            print(
                "\nYour main mathematical reasoning "
                "is correct."
            )

        difficulty_description = (
            ask_for_difficulty()
        )

        command = (
            difficulty_description
            .lower()
            .strip()
        )

        if command == "quit":
            print(
                f"\nFinal mastery: "
                f"{student.get_mastery(skill):.2f}"
            )
            raise SystemExit

        if command == "skip":
            skipped_evaluation = {
                "correct": False,
                "core_correct": False,
                "missing_constant": False,
                "parse_error": False,
                "error_type": "question_skipped",
                "feedback": "Question skipped.",
                "steps": [],
            }

            updated_mastery = (
                student.update_mastery_after_question(
                    skill_id=skill,
                    attempts=attempt_number,
                    final_evaluation=skipped_evaluation,
                )
            )

            session.record_question(
                attempts=attempt_number,
                correct=False,
            )

            print(
                "\nTutor: We'll move on "
                "and revisit this later."
            )

            print(
                f"Updated mastery: "
                f"{updated_mastery:.2f}"
            )

            question_completed = True
            continue

        if student_says_everything_is_clear(
            difficulty_description
        ):
            print(
                "\nTutor: Good. Let's try "
                "the same question again."
            )

        else:
            tutor_response = (
                respond_to_difficulty(
                    difficulty_description
                )
            )

            print("\nTutor:")
            print(tutor_response)

        attempt_number += 1

        print(
            f"\nTry the same question again "
            f"(attempt {attempt_number})."
        )

        print(
            f"Question: "
            f"{question['question']}"
        )