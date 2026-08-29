import sympy as sp

from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from src.core.question_generation.separable import (
    generate_separable_question,
)
from src.core.student_model.skill_session import (
    SkillSession,
)
from src.core.student_model.student import (
    StudentModel,
)
from src.core.tutor_engine.concept_guidance.separable_session import (
    SeparableSolutionSession,
    SeparableStage,
)
from src.core.tutor_engine.concept_guidance.separable_stage_checker import (
    evaluate_integration_step,
    evaluate_separation_step,
)

from src.core.tutor_engine.concept_guidance.separable_guidance import (
    respond_to_stage3_concept_question,
)

from src.core.tutor_engine.concept_guidance.log_solve_stage_checker import (
    evaluate_apply_exp_step,
    evaluate_cancel_log_step,
    evaluate_split_exponential_step,
    evaluate_rename_exp_constant_step,
    evaluate_remove_absolute_value_step,
    evaluate_absorb_constant_step,
)

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def choose_difficulty(mastery: float) -> int:
    if mastery < 0.40:
        return 1

    if mastery < 0.75:
        return 2

    return 3


def response_means_understood(message: str) -> bool:
    message = message.lower().strip()

    phrases = [
        "yes",
        "yeah",
        "yep",
        "clear",
        "makes sense",
        "i understand",
        "understand now",
        "got it",
        "i got it",
        "everything is clear",
    ]

    return any(
        phrase in message
        for phrase in phrases
    )


def response_requests_more_help(message: str) -> bool:
    message = message.lower().strip()

    phrases = [
        "explain",
        "more",
        "why",
        "how",
        "not clear",
        "don't understand",
        "dont understand",
        "do not understand",
        "confused",
        "not really",
        "help",
        "can't remember",
        "cant remember",
        "i don't know",
        "i dont know",
        "no",
    ]

    return any(
        phrase in message
        for phrase in phrases
    )


def normalize_final_answer(answer: str) -> str:
    normalized = (
        answer
        .replace("X", "x")
        .replace("×", "*")
        .replace("÷", "/")
        .strip()
    )

    if normalized.startswith("y="):
        normalized = normalized[2:].strip()

    elif normalized.startswith("y ="):
        normalized = normalized[3:].strip()

    return normalized


def parse_final_expression(
    expression: str,
    x: sp.Symbol,
    C: sp.Symbol,
):
    return parse_expr(
        expression,
        transformations=TRANSFORMATIONS,
        local_dict={
            "x": x,
            "C": C,
            "exp": sp.exp,
            "e": sp.E,
        },
        evaluate=True,
    )


student = StudentModel(
    student_id="student_001"
)

skill = "separate_variables"

student.initialize_skill(
    skill_id=skill,
    initial_mastery=0.50,
)

skill_session = SkillSession(
    skill_id=skill,
    min_questions=5,
    mastery_threshold=0.90,
    required_first_attempt_streak=3,
)


print("Adaptive ODE Tutor")
print("Separable Equations")
print("-------------------")
print("Type 'quit' to stop.")
print("Type 'skip' to skip the current question.\n")


while True:
    mastery = student.get_mastery(
        skill
    )

    if skill_session.is_mastered(
        mastery
    ):
        summary = skill_session.get_summary()

        print("\nSkill mastered!")
        print(f"Skill: {skill}")
        print(
            f"Final mastery: "
            f"{mastery:.2f}"
        )
        print(
            "Questions completed: "
            f"{summary['questions_completed']}"
        )
        print(
            "Total attempts: "
            f"{summary['total_attempts']}"
        )
        print(
            "First-attempt correct streak: "
            f"{summary['first_attempt_correct_streak']}"
        )

        break

    difficulty = choose_difficulty(
        mastery
    )

    question = generate_separable_question(
        difficulty=difficulty
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
        "Questions completed: "
        f"{skill_session.questions_completed}"
    )
    print(
        "First-attempt streak: "
        f"{skill_session.first_attempt_correct_streak}"
    )

    print(
        f"\nODE: "
        f"{question['question']}"
    )

    solution_session = (
        SeparableSolutionSession()
    )

    question_attempts = 1
    question_complete = False

    while not question_complete:
        stage = solution_session.get_stage()

        #
        # STAGE 1
        #
        if stage == SeparableStage.SEPARATE_VARIABLES:
            print(
                "\nStage 1 — Separate the variables"
            )

            print(
                solution_session.get_prompt()
            )

            print(
                "\nFor now, write only the separated "
                "coefficient form."
            )

            print(
                "Example:"
            )

            print(
                "    1/y = 5*x"
            )

            student_answer = input(
                "\nYour step: "
            ).strip()

            command = student_answer.lower()

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
                }

                updated_mastery = (
                    student.update_mastery_after_question(
                        skill_id=skill,
                        attempts=question_attempts,
                        final_evaluation=skipped_evaluation,
                    )
                )

                skill_session.record_question(
                    attempts=question_attempts,
                    correct=False,
                )

                print(
                    "\nTutor: We'll revisit separation "
                    "of variables later."
                )

                print(
                    f"Updated mastery: "
                    f"{updated_mastery:.2f}"
                )

                question_complete = True
                continue

            solution_session.record_attempt()

            evaluation = (
                evaluate_separation_step(
                    student_answer=student_answer,
                    rhs_expression=question[
                        "rhs_expression"
                    ],
                )
            )

            print(
                f"\nTutor: "
                f"{evaluation['feedback']}"
            )

            if evaluation["correct"]:
                print(
                    "\nGood. You have successfully "
                    "separated the variables."
                )

                solution_session.advance()
                continue

            question_attempts += 1

            print(
                "\nLet's look at the original equation:"
            )

            print(
                f"    {question['question']}"
            )

            rhs = sp.sympify(
                question["rhs_expression"]
            )

            y = sp.symbols("y")

            fx = sp.simplify(
                rhs / y
            )

            print(
                "\nThe equation has the form:"
            )

            print(
                "    dy/dx = f(x) * y"
            )

            print(
                "\nHere:"
            )

            print(
                f"    f(x) = {sp.sstr(fx)}"
            )

            print(
                "\nTo separate the variables, divide "
                "both sides by y."
            )

            print(
                "\nThat makes the y-side:"
            )

            print(
                "    1/y"
            )

            print(
                "\nand the x-side stays:"
            )

            print(
                f"    {sp.sstr(fx)}"
            )

            print(
                "\nTry the separation step again."
            )

            continue

        #
        # STAGE 2
        #
        if stage == SeparableStage.INTEGRATE_BOTH_SIDES:
            print(
                "\nStage 2 — Integrate both sides"
            )

            rhs = sp.sympify(
                question["rhs_expression"]
            )

            y = sp.symbols("y")

            fx = sp.simplify(
                rhs / y
            )

            print(
                "\nFrom Stage 1 we have:"
            )

            print(
                f"    (1/y) dy = "
                f"{sp.sstr(fx)} dx"
            )

            print(
                "\nNow integrate both sides."
            )

            print(
                "\nWrite the result after integration."
            )

            print(
                "Example:"
            )

            print(
                "    ln(y) = 5*x^2/2 + C"
            )

            student_answer = input(
                "\nYour step: "
            ).strip()

            command = student_answer.lower()

            if command == "quit":
                print(
                    f"\nFinal mastery: "
                    f"{student.get_mastery(skill):.2f}"
                )
                raise SystemExit

            solution_session.record_attempt()

            evaluation = (
                evaluate_integration_step(
                    student_answer=student_answer,
                    rhs_expression=question[
                        "rhs_expression"
                    ],
                )
            )

            print(
                f"\nTutor: "
                f"{evaluation['feedback']}"
            )

            if evaluation["correct"]:
                print(
                    "\nGood. Both sides were "
                    "integrated correctly."
                )

                solution_session.advance()
                continue

            error_type = evaluation[
                "error_type"
            ]

            if error_type == "missing_constant":
                print("\nTutor:")

                print(
                    "Your actual integrations are correct."
                )

                print(
                    "The only missing piece is the arbitrary "
                    "constant of integration."
                )

                print(
                    "\nBecause these are indefinite integrals, "
                    "we need + C."
                )

            elif error_type == "incorrect_y_integral":
                print("\nTutor:")

                print(
                    "Let's focus only on the left side:"
                )

                print(
                    "\n    integral(1/y) dy"
                )

                print(
                    "\nA very important special integration rule is:"
                )

                print(
                    "    integral(1/y) dy = ln|y| + C"
                )

                print(
                    "\nWhy doesn't the ordinary power rule "
                    "work here?"
                )

                print(
                    "Because:"
                )

                print(
                    "    1/y = y^(-1)"
                )

                print(
                    "\nThe normal power rule is:"
                )

                print(
                    "    integral(y^n) dy "
                    "= y^(n+1)/(n+1)"
                )

                print(
                    "\nBut here n = -1."
                )

                print(
                    "That would require dividing by:"
                )

                print(
                    "    n + 1 = 0"
                )

                print(
                    "\nDivision by zero is not allowed."
                )

                print(
                    "So n = -1 is the special logarithm case:"
                )

                print(
                    "    integral(1/y) dy = ln|y|"
                )

                concept_answer = input(
                    "\nDoes that distinction make sense? "
                ).strip()

                if concept_answer.lower() == "quit":
                    raise SystemExit

                if response_requests_more_help(
                    concept_answer
                ):
                    print("\nTutor:")

                    print(
                        "Another way to see it is to work "
                        "backwards using differentiation."
                    )

                    print(
                        "\nWe know:"
                    )

                    print(
                        "    d/dy ln|y| = 1/y"
                    )

                    print(
                        "\nSo if differentiating ln|y| gives 1/y, "
                        "then integrating 1/y must give ln|y|."
                    )

                    print(
                        "\nThat is why logarithm appears here."
                    )

            elif error_type == "incorrect_x_integral":
                print("\nTutor:")

                print(
                    "Your logarithm on the y-side is correct."
                )

                print(
                    "The issue is only on the x-side."
                )

                print(
                    "\nWe need to calculate:"
                )

                print(
                    f"    integral({sp.sstr(fx)}) dx"
                )

                print(
                    "\nRemember the power rule:"
                )

                print(
                    "    integral(x^n) dx "
                    "= x^(n+1)/(n+1) + C"
                )

            else:
                print("\nTutor:")

                print(
                    "Let's try the integration step "
                    "again carefully."
                )

            question_attempts += 1

            print(
                "\nTry Stage 2 again."
            )

            continue

        #
        # STAGE 3
        #
        if stage == SeparableStage.SOLVE_LOG_EQUATION:
            rhs = sp.sympify(
                question["rhs_expression"]
            )

            y = sp.symbols("y")
            x = sp.symbols("x")

            fx = sp.simplify(
                rhs / y
            )

            integrated_fx = sp.integrate(
                fx,
                x
            )

            print(
                "\nStage 3 — Solve the logarithmic equation for y"
            )

            print(
                "\nFrom Stage 2 we have:"
            )

            print(
                f"    ln|y| = "
                f"{sp.sstr(integrated_fx)} + C"
            )

            #
            # Each Stage-3 equation now has its own
            # intermediate reasoning state.
            #
            log_stage = 1

            while log_stage <= 6:
                #
                # SUBSTEP 1
                # Apply exp to both sides
                #
                if log_stage == 1:
                    print(
                        "\nStep 3.1 — Apply the inverse of ln"
                    )

                    print(
                        "\nWe want to remove ln."
                    )

                    print(
                        "Which operation is the inverse of ln?"
                    )

                    print(
                        "\nApply it to BOTH sides."
                    )

                    print(
                        "\nWrite the whole transformed equation."
                    )

                    print(
                        "Example form:"
                    )

                    print(
                        "    exp(ln(y)) = exp(... + C)"
                    )

                    student_answer = input(
                        "\nYour step or question: "
                    ).strip()

                    if student_answer.lower() == "quit":
                        raise SystemExit

                    concept_response = (
                        respond_to_stage3_concept_question(
                            student_answer
                        )
                    )

                    if concept_response is not None:
                        print("\nTutor:")
                        print(concept_response)
                        continue

                    evaluation = evaluate_apply_exp_step(
                        student_answer=student_answer,
                        integrated_fx=integrated_fx,
                    )

                    print(
                        f"\nTutor: {evaluation['feedback']}"
                    )

                    print(
                        f"Suggestion: {evaluation['suggestion']}"
                    )

                    if evaluation["correct"]:
                        log_stage = 2
                    else:
                        question_attempts += 1

                    continue

                #
                # SUBSTEP 2
                # exp(ln|y|) -> |y|
                #
                if log_stage == 2:
                    print(
                        "\nStep 3.2 — Simplify exp(ln|y|)"
                    )

                    print(
                        "\nWe currently have:"
                    )

                    print(
                        f"    exp(ln|y|) = "
                        f"exp({sp.sstr(integrated_fx)} + C)"
                    )

                    print(
                        "\nSince exp and ln are inverse functions,"
                    )

                    print(
                        "what does the left side become?"
                    )

                    print(
                        "\nWrite the complete equation."
                    )

                    student_answer = input(
                        "\nYour step or question: "
                    ).strip()

                    if student_answer.lower() == "quit":
                        raise SystemExit

                    concept_response = (
                        respond_to_stage3_concept_question(
                            student_answer
                        )
                    )

                    if concept_response is not None:
                        print("\nTutor:")
                        print(concept_response)
                        continue

                    evaluation = evaluate_cancel_log_step(
                        student_answer=student_answer,
                        integrated_fx=integrated_fx,
                    )

                    print(
                        f"\nTutor: {evaluation['feedback']}"
                    )

                    print(
                        f"Suggestion: {evaluation['suggestion']}"
                    )

                    if evaluation["correct"]:
                        log_stage = 3
                    else:
                        question_attempts += 1

                    continue

                #
                # SUBSTEP 3
                # exp(F + C) -> exp(F)exp(C)
                #
                if log_stage == 3:
                    print(
                        "\nStep 3.3 — Split the exponential"
                    )

                    print(
                        "\nWe now have:"
                    )

                    print(
                        f"    |y| = "
                        f"exp({sp.sstr(integrated_fx)} + C)"
                    )

                    print(
                        "\nUse:"
                    )

                    print(
                        "    exp(a + b) = exp(a)*exp(b)"
                    )

                    print(
                        "\nRewrite the right side."
                    )

                    student_answer = input(
                        "\nYour step or question: "
                    ).strip()

                    if student_answer.lower() == "quit":
                        raise SystemExit

                    concept_response = (
                        respond_to_stage3_concept_question(
                            student_answer
                        )
                    )

                    if concept_response is not None:
                        print("\nTutor:")
                        print(concept_response)
                        continue

                    evaluation = (
                        evaluate_split_exponential_step(
                            student_answer=student_answer,
                            integrated_fx=integrated_fx,
                        )
                    )

                    print(
                        f"\nTutor: {evaluation['feedback']}"
                    )

                    print(
                        f"Suggestion: {evaluation['suggestion']}"
                    )

                    if evaluation["correct"]:
                        log_stage = 4
                    else:
                        question_attempts += 1

                    continue

                #
                # SUBSTEP 4
                # exp(C) -> K
                #
                if log_stage == 4:
                    print(
                        "\nStep 3.4 — Rename exp(C)"
                    )

                    print(
                        "\nWe now have:"
                    )

                    print(
                        f"    |y| = "
                        f"exp({sp.sstr(integrated_fx)}) * exp(C)"
                    )

                    print(
                        "\nC is arbitrary."
                    )

                    print(
                        "Therefore exp(C) is some positive constant."
                    )

                    print(
                        "\nLet:"
                    )

                    print(
                        "    K = exp(C)"
                    )

                    print(
                        "\nRewrite the equation using K."
                    )

                    student_answer = input(
                        "\nYour step or question: "
                    ).strip()

                    if student_answer.lower() == "quit":
                        raise SystemExit

                    concept_response = (
                        respond_to_stage3_concept_question(
                            student_answer
                        )
                    )

                    if concept_response is not None:
                        print("\nTutor:")
                        print(concept_response)
                        continue

                    evaluation = (
                        evaluate_rename_exp_constant_step(
                            student_answer=student_answer,
                            integrated_fx=integrated_fx,
                        )
                    )

                    print(
                        f"\nTutor: {evaluation['feedback']}"
                    )

                    print(
                        f"Suggestion: {evaluation['suggestion']}"
                    )

                    if evaluation["correct"]:
                        log_stage = 5
                    else:
                        question_attempts += 1

                    continue

                #
                # SUBSTEP 5
                # |y| -> +/- y
                #
                if log_stage == 5:
                    print(
                        "\nStep 3.5 — Remove the absolute value"
                    )

                    print(
                        "\nWe have:"
                    )

                    print(
                        f"    |y| = "
                        f"K*exp({sp.sstr(integrated_fx)})"
                    )

                    print(
                        "\nIf |y| equals something positive,"
                    )

                    print(
                        "then y can have two possible signs."
                    )

                    print(
                        "\nWrite both possibilities in one expression."
                    )

                    print(
                        "You can use +/- or ±."
                    )

                    student_answer = input(
                        "\nYour step or question: "
                    ).strip()

                    if student_answer.lower() == "quit":
                        raise SystemExit

                    concept_response = (
                        respond_to_stage3_concept_question(
                            student_answer
                        )
                    )

                    if concept_response is not None:
                        print("\nTutor:")
                        print(concept_response)
                        continue

                    evaluation = (
                        evaluate_remove_absolute_value_step(
                            student_answer=student_answer,
                            integrated_fx=integrated_fx,
                        )
                    )

                    print(
                        f"\nTutor: {evaluation['feedback']}"
                    )

                    print(
                        f"Suggestion: {evaluation['suggestion']}"
                    )

                    if evaluation["correct"]:
                        log_stage = 6
                    else:
                        question_attempts += 1

                    continue

                #
                # SUBSTEP 6
                # +/-K -> C
                #
                if log_stage == 6:
                    print(
                        "\nStep 3.6 — Absorb the constants"
                    )

                    print(
                        "\nWe now have:"
                    )

                    print(
                        f"    y = +/- K*exp("
                        f"{sp.sstr(integrated_fx)})"
                    )

                    print(
                        "\nThe combination +/- K can be represented "
                        "by one new arbitrary constant."
                    )

                    print(
                        "\nConventionally we call that new constant C."
                    )

                    print(
                        "\nRewrite the solution in its standard form."
                    )

                    student_answer = input(
                        "\nYour step or question: "
                    ).strip()

                    if student_answer.lower() == "quit":
                        raise SystemExit

                    concept_response = (
                        respond_to_stage3_concept_question(
                            student_answer
                        )
                    )

                    if concept_response is not None:
                        print("\nTutor:")
                        print(concept_response)
                        continue

                    evaluation = (
                        evaluate_absorb_constant_step(
                            student_answer=student_answer,
                            integrated_fx=integrated_fx,
                        )
                    )

                    print(
                        f"\nTutor: {evaluation['feedback']}"
                    )

                    print(
                        f"Suggestion: {evaluation['suggestion']}"
                    )

                    if evaluation["correct"]:
                        log_stage = 7
                    else:
                        question_attempts += 1

                    continue

            print(
                "\nExcellent. You solved the logarithmic part "
                "step by step."
            )

            solution_session.advance()

            continue

        #
        # STAGE 4
        #
        if stage == SeparableStage.FINAL_SOLUTION:
            rhs = sp.sympify(
                question["rhs_expression"]
            )

            y = sp.symbols("y")
            x = sp.symbols("x")
            C = sp.symbols("C")

            fx = sp.simplify(
                rhs / y
            )

            integrated_fx = sp.integrate(
                fx,
                x
            )

            expected_expr = (
                C * sp.exp(integrated_fx)
            )

            print(
                "\nStage 4 — Final solution"
            )

            print(
                "\nNow write the general solution for y."
            )

            print(
                "For example:"
            )

            print(
                "    y = C*exp(...)"
            )

            student_answer = input(
                "\nYour final answer or question: "
            ).strip()

            if student_answer.lower() == "quit":
                raise SystemExit

            message = student_answer.lower()

            looks_like_question = (
                "why" in message
                or "where" in message
                or "how" in message
                or "what" in message
                or "don't understand" in message
                or "do not understand" in message
                or "confused" in message
                or "?" in message
            )

            if looks_like_question:
                if (
                    "denominator" in message
                    or (
                        "where" in message
                        and "2" in message
                    )
                ):
                    print("\nTutor:")

                    print(
                        "The denominator did not disappear. "
                        "The expression was simplified."
                    )

                    print(
                        "\nFor example:"
                    )

                    print(
                        "    6*x^2/2"
                    )

                    print(
                        "\nThe coefficient is:"
                    )

                    print(
                        "    6/2 = 3"
                    )

                    print(
                        "\nTherefore:"
                    )

                    print(
                        "    6*x^2/2 = 3*x^2"
                    )

                    print(
                        "\nThose two expressions are mathematically "
                        "equivalent."
                    )

                else:
                    print("\nTutor:")

                    print(
                        "That's a conceptual question rather "
                        "than a final answer."
                    )

                    print(
                        "Ask about the specific transformation "
                        "that is unclear and we'll work through it."
                    )

                continue

            normalized = normalize_final_answer(
                student_answer
            )

            try:
                student_expr = parse_final_expression(
                    expression=normalized,
                    x=x,
                    C=C,
                )

            except (
                sp.SympifyError,
                SyntaxError,
                TypeError,
                ValueError,
                NameError,
            ):
                print(
                    "\nTutor: I could not understand that "
                    "mathematical expression."
                )

                print(
                    "You can write something like:"
                )

                print(
                    f"    y = {sp.sstr(expected_expr)}"
                )

                continue

            equivalent = (
                sp.simplify(
                    student_expr - expected_expr
                ) == 0
            )

            if equivalent:
                print(
                    "\nTutor: Correct. Your expression is "
                    "mathematically equivalent to the "
                    "general solution."
                )

                simplified = sp.simplify(
                    student_expr
                )

                if simplified != student_expr:
                    print(
                        "\nIt can also be simplified to:"
                    )

                    print(
                        f"    y = {sp.sstr(simplified)}"
                    )

                solution_session.advance()
                continue

            print(
                "\nTutor: That expression is not equivalent "
                "to the expected general solution."
            )

            print(
                "\nExpected form:"
            )

            print(
                f"    y = {sp.sstr(expected_expr)}"
            )

            question_attempts += 1

            print(
                "\nTry Stage 4 again."
            )

            continue

        #
        # COMPLETE QUESTION
        #
        if stage == SeparableStage.COMPLETE:
            final_evaluation = {
                "correct": True,
                "core_correct": True,
                "missing_constant": False,
                "parse_error": False,
            }

            updated_mastery = (
                student.update_mastery_after_question(
                    skill_id=skill,
                    attempts=question_attempts,
                    final_evaluation=final_evaluation,
                )
            )

            skill_session.record_question(
                attempts=question_attempts,
                correct=True,
            )

            print(
                "\nQuestion completed."
            )

            print(
                f"Updated mastery for "
                f"'{skill}': {updated_mastery:.2f}"
            )

            question_complete = True