from src.core.tutor_engine.primary_school.checker import (
    evaluate_step_answer,
)

from src.core.tutor_engine.primary_school.reverse_reasoning_solver import (
    load_reverse_reasoning_problem,
)

from src.core.tutor_engine.primary_school.session import (
    PrimarySchoolSession,
)


PROBLEM_ID = "grade4_reverse_reasoning_001"


def print_header() -> None:
    print()
    print("MATH_PAL")
    print("Primary School Mathematics Tutor")
    print("--------------------------------")
    print()
    print("Commands:")
    print("  hint  - show a hint")
    print("  quit  - stop the tutor")
    print()


def print_problem(
    session: PrimarySchoolSession,
) -> None:
    problem = session.problem

    print(
        f"Grade {problem.grade}"
    )

    print(
        f"Topic: {problem.topic}"
    )

    print()
    print(
        problem.title
    )

    print()
    print(
        problem.problem_text
    )

    print()


def print_step(
    session: PrimarySchoolSession,
) -> None:
    step = session.get_current_step()

    if step is None:
        return

    total_steps = (
        session.problem.get_number_of_steps()
    )

    print()
    print(
        f"Step {step.step_number} "
        f"of {total_steps}"
    )

    print()
    print(
        step.prompt
    )

    print()


def show_hint(
    session: PrimarySchoolSession,
) -> None:
    step = session.get_current_step()

    if step is None:
        return

    session.record_hint()

    print()

    if step.hint:
        print(
            "Hint:",
            step.hint,
        )

    else:
        print(
            "Tutor: No additional hint is "
            "available for this step yet."
        )

    print()


def run_problem(
    problem_id: str,
) -> str:
    problem = load_reverse_reasoning_problem(
        problem_id
    )

    session = PrimarySchoolSession(
        problem=problem
    )

    print_problem(
        session
    )

    while not session.is_complete():
        print_step(
            session
        )

        student_answer = input(
            "Your answer: "
        )

        command = (
            student_answer
            .strip()
            .lower()
        )

        if command == "quit":
            return "quit"

        if command == "hint":
            show_hint(
                session
            )

            continue

        #
        # Only actual answer submissions
        # count as attempts.
        #
        session.record_attempt()

        step = session.get_current_step()

        result = evaluate_step_answer(
            student_answer=student_answer,
            expected_answer=(
                step.expected_answer
            ),
        )

        print()
        print(
            "Tutor:",
            result["feedback"],
        )

        if result["correct"]:
            session.advance()

            if not session.is_complete():
                print(
                    "Good. Let's continue."
                )

            continue

        #
        # Give the stored hint automatically
        # after a second incorrect attempt.
        #
        attempts = (
            session
            .get_attempts_for_current_step()
        )

        if (
            attempts >= 2
            and step.hint
        ):
            session.record_hint()

            print(
                "Hint:",
                step.hint,
            )

    print()
    print(
        "Excellent. You solved the problem."
    )

    print()
    print(
        "Final answer:",
        problem.final_answer,
    )

    print()
    print(
        "Session summary:"
    )

    print(
        "Steps completed:",
        session.get_completed_step_count(),
    )

    print(
        "Total attempts:",
        session.get_total_attempts(),
    )

    print(
        "Hints used:",
        session.get_total_hints_used(),
    )

    return "complete"


def main() -> None:
    print_header()

    result = run_problem(
        PROBLEM_ID
    )

    if result == "quit":
        print()
        print(
            "Tutor stopped."
        )


if __name__ == "__main__":
    main()