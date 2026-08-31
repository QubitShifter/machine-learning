import sympy as sp

from src.core.question_generation.linear_first_order import (
    generate_linear_first_order_question,
)

from src.core.student_model.student import (
    StudentModel,
)

from src.core.student_model.skill_session import (
    SkillSession,
)

from src.core.student_model.progress_store import (
    get_skill_progress,
    load_progress,
    save_progress,
    update_skill_progress,
)

from src.core.tutor_engine.linear_first_order_engine import (
    LinearFirstOrderEngine,
)

from src.core.tutor_engine.linear_first_order_session import (
    LinearODEStage,
    LinearODESolutionSession,
)

from src.core.tutor_engine.linear_first_order_verification import (
    LinearFirstOrderVerificationEngine,
    LinearVerificationStage,
)


x = sp.symbols("x")
C = sp.symbols("C")


# ---------------------------------------------------------
# General helpers
# ---------------------------------------------------------


def get_difficulty(
    mastery: float,
) -> int:
    """
    Convert mastery into question difficulty.

    This follows the same simple prototype logic used
    by the separable-equation tutor.
    """

    if mastery < 0.40:
        return 1

    if mastery < 0.75:
        return 2

    return 3


def print_feedback(
    result: dict,
):
    print(
        "\nTutor:",
        result["feedback"],
    )

    suggestion = result.get(
        "suggestion"
    )

    if suggestion:
        print(
            "Suggestion:",
            suggestion,
        )


def handle_special_command(
    student_input: str,
):
    """
    Return:
        "quit"
        "skip"
        None
    """

    command = (
        student_input
        .strip()
        .lower()
    )

    if command == "quit":
        return "quit"

    if command == "skip":
        return "skip"

    return None


# ---------------------------------------------------------
# Stage presentation
# ---------------------------------------------------------


def print_stage_header(
    engine: LinearFirstOrderEngine,
    stage: LinearODEStage,
):
    print()
    print(
        engine.get_stage_title(
            stage
        )
    )
    print()

    print(
        engine.get_stage_prompt(
            stage
        )
    )

    print()


# ---------------------------------------------------------
# Stage 1
# ---------------------------------------------------------


def run_stage_1(
    engine: LinearFirstOrderEngine,
    solution_session: LinearODESolutionSession,
):
    stage = (
        LinearODEStage
        .IDENTIFY_STANDARD_FORM
    )

    while True:
        print_stage_header(
            engine,
            stage,
        )

        student_answer = input(
            "Your answer: "
        )

        command = handle_special_command(
            student_answer
        )

        if command is not None:
            return command

        solution_session.record_attempt()

        result = engine.evaluate(
            stage=stage,
            student_answer=student_answer,
        )

        print_feedback(
            result
        )

        if result["correct"]:
            solution_session.advance()
            return "continue"


# ---------------------------------------------------------
# Stage 2
# ---------------------------------------------------------


def run_stage_2(
    engine: LinearFirstOrderEngine,
    solution_session: LinearODESolutionSession,
):
    stage = (
        LinearODEStage.IDENTIFY_P_Q
    )

    while True:
        print_stage_header(
            engine,
            stage,
        )

        student_p = input(
            "P(x) = "
        )

        command = handle_special_command(
            student_p
        )

        if command is not None:
            return command

        student_q = input(
            "Q(x) = "
        )

        command = handle_special_command(
            student_q
        )

        if command is not None:
            return command

        solution_session.record_attempt()

        result = engine.evaluate(
            stage=stage,
            student_p=student_p,
            student_q=student_q,
        )

        print_feedback(
            result
        )

        if result["correct"]:
            solution_session.advance()
            return "continue"


# ---------------------------------------------------------
# Generic stages 3–7
# ---------------------------------------------------------


def run_math_stage(
    engine: LinearFirstOrderEngine,
    solution_session: LinearODESolutionSession,
    stage: LinearODEStage,
):
    while True:
        print_stage_header(
            engine,
            stage,
        )

        student_answer = input(
            "Your step: "
        )

        command = handle_special_command(
            student_answer
        )

        if command is not None:
            return command

        solution_session.record_attempt()

        result = engine.evaluate(
            stage=stage,
            student_answer=student_answer,
        )

        print_feedback(
            result
        )

        if result["correct"]:
            solution_session.advance()
            return "continue"


# ---------------------------------------------------------
# Stage 8 verification
# ---------------------------------------------------------


def print_verification_stage(
    verification_engine:
        LinearFirstOrderVerificationEngine,
):
    stage = (
        verification_engine.get_stage()
    )

    solution = (
        verification_engine
        .solution_expression
    )

    P = (
        verification_engine
        .p_expression
    )

    Q = (
        verification_engine
        .q_expression
    )

    print()
    print(
        "Stage 8 — Verify the solution"
    )
    print()

    if (
        stage
        == LinearVerificationStage.DIFFERENTIATE
    ):
        print(
            "Step 8.1 — Differentiate the proposed solution"
        )
        print()

        print(
            "Your proposed solution is:"
        )

        print(
            f"    y = {sp.sstr(solution)}"
        )

        print()

        print(
            "Differentiate it with respect to x."
        )

        print(
            "You may write:"
        )

        print(
            "    dy/dx = ..."
        )

    elif (
        stage
        == LinearVerificationStage.SUBSTITUTE
    ):
        print(
            "Step 8.2 — Substitute into the left-hand side"
        )
        print()

        print(
            "The original equation is:"
        )

        print(
            f"    y' + ({sp.sstr(P)})*y "
            f"= {sp.sstr(Q)}"
        )

        print()

        print(
            "Substitute your proposed y and its derivative "
            "into:"
        )

        print(
            "    y' + P(x)y"
        )

        print()

        print(
            "Write the simplified left-hand side."
        )

    elif (
        stage
        == LinearVerificationStage.COMPARE
    ):
        expected_lhs = (
            verification_engine
            .get_expected_lhs()
        )

        print(
            "Step 8.3 — Compare both sides"
        )

        print()

        print(
            "After substitution:"
        )

        print(
            f"    LHS = {sp.sstr(expected_lhs)}"
        )

        print(
            f"    RHS = {sp.sstr(Q)}"
        )

        print()

        print(
            "Do they match?"
        )


def run_verification(
    engine: LinearFirstOrderEngine,
    solution_session: LinearODESolutionSession,
):
    solution_expression = (
        engine.get_general_solution()
    )

    verification_engine = (
        LinearFirstOrderVerificationEngine(
            p_expression=engine.p_expression,
            q_expression=engine.q_expression,
            solution_expression=solution_expression,
        )
    )

    while not verification_engine.is_complete():
        print_verification_stage(
            verification_engine
        )

        print()

        student_answer = input(
            "Your step or answer: "
        )

        command = handle_special_command(
            student_answer
        )

        if command is not None:
            return command

        solution_session.record_attempt()

        result = verification_engine.evaluate(
            student_answer
        )

        print_feedback(
            result
        )

        if result["correct"]:
            verification_engine.advance()

    print()

    print(
        "Excellent. The solution has been verified "
        "against the original linear ODE."
    )

    solution_session.advance()

    return "continue"


# ---------------------------------------------------------
# Question execution
# ---------------------------------------------------------


def run_question(
    question: dict,
):
    P = question["p_expression"]
    Q = question["q_expression"]

    engine = LinearFirstOrderEngine(
        p_expression=P,
        q_expression=Q,
    )

    solution_session = (
        LinearODESolutionSession()
    )

    question_had_error = False

    print()

    print(
        "ODE:",
        question["question"].replace(
            "Solve ",
            "",
        ),
    )

    #
    # Stage 1
    #
    before_attempts = (
        solution_session
        .get_attempts_for_current_stage()
    )

    command = run_stage_1(
        engine,
        solution_session,
    )

    if command in {
        "quit",
        "skip",
    }:
        return {
            "command": command,
            "correct": False,
            "attempts": 0,
        }

    after_attempts = (
        solution_session
        .attempts_by_stage[
            LinearODEStage
            .IDENTIFY_STANDARD_FORM
        ]
    )

    if (
        after_attempts
        - before_attempts
        > 1
    ):
        question_had_error = True

    #
    # Stage 2
    #
    command = run_stage_2(
        engine,
        solution_session,
    )

    if command in {
        "quit",
        "skip",
    }:
        return {
            "command": command,
            "correct": False,
            "attempts": 0,
        }

    if (
        solution_session
        .attempts_by_stage[
            LinearODEStage.IDENTIFY_P_Q
        ]
        > 1
    ):
        question_had_error = True

    #
    # Stages 3–7
    #
    stages = [
        LinearODEStage
        .FIND_INTEGRATING_FACTOR,

        LinearODEStage
        .MULTIPLY_BY_INTEGRATING_FACTOR,

        LinearODEStage
        .RECOGNIZE_PRODUCT_DERIVATIVE,

        LinearODEStage
        .INTEGRATE_BOTH_SIDES,

        LinearODEStage
        .SOLVE_FOR_Y,
    ]

    for stage in stages:
        command = run_math_stage(
            engine,
            solution_session,
            stage,
        )

        if command in {
            "quit",
            "skip",
        }:
            return {
                "command": command,
                "correct": False,
                "attempts": 0,
            }

        if (
            solution_session
            .attempts_by_stage[
                stage
            ]
            > 1
        ):
            question_had_error = True

    #
    # Stage 8
    #
    command = run_verification(
        engine,
        solution_session,
    )

    if command in {
        "quit",
        "skip",
    }:
        return {
            "command": command,
            "correct": False,
            "attempts": 0,
        }

    verification_attempts = (
        solution_session
        .attempts_by_stage[
            LinearODEStage
            .VERIFY_SOLUTION
        ]
    )

    #
    # run_verification currently records all three
    # verification substeps under VERIFY_SOLUTION.
    #
    # Three attempts means:
    #   one correct attempt per verification step.
    #
    if verification_attempts > 3:
        question_had_error = True

    #
    # Convert the entire question into the same simple
    # first-attempt concept used by SkillSession.
    #
    question_attempts = (
        2
        if question_had_error
        else 1
    )

    return {
        "command": "continue",
        "correct": True,
        "attempts": question_attempts,
    }


# ---------------------------------------------------------
# Main tutor
# ---------------------------------------------------------


def main():
    print(
        "Adaptive ODE Tutor"
    )

    print(
        "First-Order Linear Equations"
    )

    print(
        "----------------------------"
    )

    print(
        "Type 'quit' to stop."
    )

    print(
        "Type 'skip' to skip the current question."
    )

    print()

    #
    # -----------------------------------------------------
    # Student + persistence
    # -----------------------------------------------------
    #

    student = StudentModel(
        student_id="student_001"
    )

    skill = "linear_first_order"

    progress = load_progress()

    saved_skill = get_skill_progress(
        progress,
        skill,
        default_mastery=0.50,
    )

    saved_mastery = (
        saved_skill["mastery"]
    )

    saved_questions_completed = (
        saved_skill[
            "questions_completed"
        ]
    )

    saved_first_attempt_streak = (
        saved_skill[
            "first_attempt_streak"
        ]
    )

    student.initialize_skill(
        skill_id=skill,
        initial_mastery=saved_mastery,
    )

    skill_session = SkillSession(
        skill_id=skill,
        min_questions=5,
        mastery_threshold=0.90,
        required_first_attempt_streak=3,
    )

    skill_session.questions_completed = (
        saved_questions_completed
    )

    skill_session.first_attempt_correct_streak = (
        saved_first_attempt_streak
    )

    #
    # -----------------------------------------------------
    # Main question loop
    # -----------------------------------------------------
    #

    while True:
        current_mastery = (
            student.get_mastery(
                skill
            )
        )

        difficulty = get_difficulty(
            current_mastery
        )

        print()

        print(
            f"Current mastery: "
            f"{current_mastery:.2f}"
        )

        print(
            f"Difficulty: "
            f"{difficulty}"
        )

        print(
            "Questions completed:",
            skill_session.questions_completed,
        )

        print(
            "First-attempt streak:",
            skill_session
            .first_attempt_correct_streak,
        )

        #
        # Stop automatically once the skill is mastered.
        #
        if skill_session.is_mastered(
            current_mastery
        ):
            print()

            print(
                "Skill mastered."
            )

            print(
                "You have demonstrated sufficient mastery "
                "of first-order linear ODEs."
            )

            break

        question = (
            generate_linear_first_order_question(
                difficulty=difficulty
            )
        )

        result = run_question(
            question
        )

        command = result[
            "command"
        ]

        if command == "quit":
            break

        if command == "skip":
            print()

            print(
                "Question skipped."
            )

            continue

        #
        # Successful completion
        #
        question_attempts = (
            result["attempts"]
        )

        #
        # Use the existing student-model update logic.
        #
        updated_mastery = (
            student.update_mastery_after_question(
                skill_id=skill,
                attempts=question_attempts,
                correct=True,
            )
        )

        skill_session.record_question(
            attempts=question_attempts,
            correct=True,
        )

        print()

        print(
            "Question completed."
        )

        print(
            f"Updated mastery for "
            f"'{skill}': "
            f"{updated_mastery:.2f}"
        )

        #
        # -------------------------------------------------
        # Save persistent progress
        # -------------------------------------------------
        #

        update_skill_progress(
            progress=progress,
            skill=skill,
            mastery=updated_mastery,
            questions_completed=(
                skill_session
                .questions_completed
            ),
            first_attempt_streak=(
                skill_session
                .first_attempt_correct_streak
            ),
        )

        save_progress(
            progress
        )

    #
    # Save once again before exit.
    #
    final_mastery = (
        student.get_mastery(
            skill
        )
    )

    update_skill_progress(
        progress=progress,
        skill=skill,
        mastery=final_mastery,
        questions_completed=(
            skill_session.questions_completed
        ),
        first_attempt_streak=(
            skill_session
            .first_attempt_correct_streak
        ),
    )

    save_progress(
        progress
    )

    print()

    print(
        f"Final mastery: "
        f"{final_mastery:.2f}"
    )


if __name__ == "__main__":
    main()