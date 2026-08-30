import sympy as sp

from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


x = sp.symbols("x")
y = sp.symbols("y")
C = sp.symbols("C")


TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

def detect_common_function_typo(text: str) -> str | None:
    lowered = text.lower()

    common_typos = {
        "ecp(": "exp(",
        "expp(": "exp(",
        "epx(": "exp(",
        "l n(": "ln(",
        "logg(": "log(",
    }

    for typo, correction in common_typos.items():
        if typo in lowered:
            return correction

    return None


def normalize_expression(text: str) -> str:
    text = text.strip()

    text = text.replace("X", "x")
    text = text.replace("Y", "y")

    text = text.replace("×", "*")
    text = text.replace("÷", "/")

    text = text.replace("Exp(", "exp(")
    text = text.replace("EXP(", "exp(")

    text = text.replace("Ln(", "ln(")
    text = text.replace("LN(", "ln(")

    text = text.replace("Log(", "log(")
    text = text.replace("LOG(", "log(")

    text = text.replace("ln(", "log(")

    return text


def parse_math(expression: str):
    return parse_expr(
        expression,
        transformations=TRANSFORMATIONS,
        local_dict={
            "x": x,
            "y": y,
            "C": C,
            "exp": sp.exp,
            "log": sp.log,
        },
        evaluate=True,
    )


def evaluate_apply_exp_step(
    student_answer: str,
    integrated_fx,
) -> dict:
    """
    Expected transformation:

        ln|y| = F(x) + C

    becomes:

        exp(ln|y|) = exp(F(x) + C)

    For terminal input we accept log(y) instead of log(abs(y))
    for now.
    """

    answer = normalize_expression(
        student_answer
    )

    typo_correction = detect_common_function_typo(
        student_answer
    )

    if typo_correction is not None:
        return {
            "correct": False,
            "error_type": "likely_typo",
            "feedback": (
                "Your mathematical idea may be right, but "
                "I noticed what looks like a function-name typo."
            ),
            "suggestion": (
                f"Did you mean '{typo_correction}'?"
            ),
        }

    if "=" not in answer:
        return {
            "correct": False,
            "error_type": "missing_equals",
            "feedback": (
                "Apply exp to both sides and write the "
                "result as an equation."
            ),
            "suggestion": (
                "Try a form like: "
                "exp(ln(y)) = exp(... + C)"
            ),
        }

    left_text, right_text = answer.split(
        "=",
        maxsplit=1,
    )

    try:
        left = parse_math(left_text)
        right = parse_math(right_text)

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        sp.SympifyError,
    ):

        typo_correction = detect_common_function_typo(
            student_answer
        )

        if typo_correction is not None:
            return {
                "correct": False,
                "error_type": "likely_typo",
                "feedback": (
                    "Your mathematical idea may be right, but "
                    "I noticed what looks like a function-name typo."
                ),
                "suggestion": (
                    f"Did you mean '{typo_correction}'?"
                ),
            }
        
        return {
            "correct": False,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand that expression."
            ),
            "suggestion": (
                "Write something like: "
                "exp(ln(y)) = exp(2*x**3 + C)"
            ),
        }

    expected_left = sp.exp(
        sp.log(y)
    )

    expected_right = sp.exp(
        integrated_fx + C
    )

    left_correct = (
        sp.simplify(
            left - expected_left
        ) == 0
    )

    right_correct = (
        sp.simplify(
            right - expected_right
        ) == 0
    )

    if left_correct and right_correct:
        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. You applied exp to both sides."
            ),
            "suggestion": (
                "Next, simplify exp(ln(y)). "
                "What does that become?"
            ),
        }

    if not left_correct:
        return {
            "correct": False,
            "error_type": "incorrect_left_side",
            "feedback": (
                "You need to apply exp to the entire "
                "left side, not just part of it."
            ),
            "suggestion": (
                "The left side should look like: "
                "exp(ln(y))"
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_right_side",
        "feedback": (
            "The left side is good, but exp must also "
            "be applied to the entire right side."
        ),
        "suggestion": (
            f"Try: exp({sp.sstr(integrated_fx)} + C)"
        ),
    }

def evaluate_cancel_log_step(
    student_answer: str,
    integrated_fx,
) -> dict:
    """
    Expected transformation:

        exp(ln|y|) = exp(F(x) + C)

    becomes:

        |y| = exp(F(x) + C)

    For terminal input, accept:
        y = exp(...)
        abs(y) = exp(...)
        Abs(y) = exp(...)

    Later we can distinguish absolute-value handling more strictly.
    """

    answer = normalize_expression(
        student_answer
    )

    answer = answer.replace(
        "|y|",
        "Abs(y)",
    )

    if "=" not in answer:
        return {
            "correct": False,
            "error_type": "missing_equals",
            "feedback": (
                "Write the simplified equation using '='."
            ),
            "suggestion": (
                "Try a form like: "
                "|y| = exp(... + C)"
            ),
        }

    left_text, right_text = answer.split(
        "=",
        maxsplit=1,
    )

    try:
        left = parse_expr(
            left_text,
            transformations=TRANSFORMATIONS,
            local_dict={
                "x": x,
                "y": y,
                "C": C,
                "exp": sp.exp,
                "log": sp.log,
                "Abs": sp.Abs,
            },
            evaluate=True,
        )

        right = parse_expr(
            right_text,
            transformations=TRANSFORMATIONS,
            local_dict={
                "x": x,
                "y": y,
                "C": C,
                "exp": sp.exp,
                "log": sp.log,
                "Abs": sp.Abs,
            },
            evaluate=True,
        )

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        sp.SympifyError,
    ):

        typo_correction = detect_common_function_typo(
            student_answer
        )

        if typo_correction is not None:
            return {
                "correct": False,
                "error_type": "likely_typo",
                "feedback": (
                    "Your mathematical idea may be right, but "
                    "I noticed what looks like a function-name typo."
                ),
                "suggestion": (
                    f"Did you mean '{typo_correction}'?"
                ),
            }

        return {
            "correct": False,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand that expression."
            ),
            "suggestion": (
                f"Try something like: "
                f"|y| = exp({sp.sstr(integrated_fx)} + C)"
            ),
        }

    expected_right = sp.exp(
        integrated_fx + C
    )

    left_is_abs_y = (
        left == sp.Abs(y)
    )

    left_is_y = (
        left == y
    )

    right_correct = (
        sp.simplify(
            right - expected_right
        ) == 0
    )

    if left_is_abs_y and right_correct:
        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. exp and ln are inverse functions, "
                "so exp(ln|y|) becomes |y|."
            ),
            "suggestion": (
                "Next, use exp(a + b) = exp(a)*exp(b) "
                "to separate the + C in the exponent."
            ),
        }

    if left_is_y and right_correct:
        return {
            "correct": True,
            "error_type": "absolute_value_skipped",
            "feedback": (
                "Your main idea is correct, but you skipped "
                "the absolute-value step. Strictly, "
                "exp(ln|y|) becomes |y| first."
            ),
            "suggestion": (
                "Keep |y| for now. We will handle the "
                "positive/negative sign in a later step."
            ),
        }

    if not left_is_abs_y and not left_is_y:
        return {
            "correct": False,
            "error_type": "incorrect_left_side",
            "feedback": (
                "Focus on exp(ln|y|). "
                "Because exp and ln are inverse functions, "
                "that part simplifies to |y|."
            ),
            "suggestion": (
                "The left side should become: |y|"
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_right_side",
        "feedback": (
            "The left side is correct, but the right side "
            "should remain exp(F(x) + C) at this step."
        ),
        "suggestion": (
            f"Try: |y| = exp("
            f"{sp.sstr(integrated_fx)} + C)"
        ),
    }

def evaluate_split_exponential_step(
    student_answer: str,
    integrated_fx,
) -> dict:
    """
    Expected transformation:

        |y| = exp(F(x) + C)

    becomes:

        |y| = exp(F(x)) * exp(C)

    Accept mathematically equivalent multiplication forms.
    """

    typo_correction = detect_common_function_typo(
        student_answer
    )

    if typo_correction is not None:
        return {
            "correct": False,
            "error_type": "likely_typo",
            "feedback": (
                "Your mathematical idea may be right, but "
                "I noticed what looks like a function-name typo."
            ),
            "suggestion": (
                f"Did you mean '{typo_correction}'?"
            ),
        }

    answer = normalize_expression(
        student_answer
    )

    answer = answer.replace(
        "|y|",
        "Abs(y)",
    )

    if "=" not in answer:
        return {
            "correct": False,
            "error_type": "missing_equals",
            "feedback": (
                "Write the transformed equation using '='."
            ),
            "suggestion": (
                "Use exp(a + b) = exp(a)*exp(b)."
            ),
        }

    left_text, right_text = answer.split(
        "=",
        maxsplit=1,
    )

    try:
        left = parse_expr(
            left_text,
            transformations=TRANSFORMATIONS,
            local_dict={
                "x": x,
                "y": y,
                "C": C,
                "exp": sp.exp,
                "log": sp.log,
                "Abs": sp.Abs,
            },
            evaluate=True,
        )

        right = parse_expr(
            right_text,
            transformations=TRANSFORMATIONS,
            local_dict={
                "x": x,
                "y": y,
                "C": C,
                "exp": sp.exp,
                "log": sp.log,
                "Abs": sp.Abs,
            },
            evaluate=True,
        )

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        sp.SympifyError,
    ):
        return {
            "correct": False,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand that expression."
            ),
            "suggestion": (
                f"Try something like: "
                f"|y| = exp({sp.sstr(integrated_fx)}) * exp(C)"
            ),
        }

    expected_left = sp.Abs(y)

    expected_right = (
        sp.exp(integrated_fx)
        * sp.exp(C)
    )

    left_correct = (
        left == expected_left
    )

    mathematically_equivalent = (
        sp.simplify(
            right - expected_right
        ) == 0
    )

    #
    # Check that the student actually split the exponential
    # into two factors.
    #
    has_split_structure = False

    if isinstance(right, sp.Mul):
        factors = list(right.args)

        has_exp_c = any(
            sp.simplify(
                factor - sp.exp(C)
            ) == 0
            for factor in factors
        )

        has_exp_fx = any(
            sp.simplify(
                factor - sp.exp(integrated_fx)
            ) == 0
            for factor in factors
        )

        has_split_structure = (
            has_exp_c
            and has_exp_fx
        )

    #
    # Correct mathematical result AND requested structure.
    #
    if (
        left_correct
        and mathematically_equivalent
        and has_split_structure
    ):
        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. You used "
                "exp(a + b) = exp(a)*exp(b)."
            ),
            "suggestion": (
                "Next, think about exp(C). "
                "Since C is arbitrary, exp(C) is just "
                "some positive constant. What could we "
                "rename it?"
            ),
        }

    #
    # Mathematically equivalent but not split yet.
    #
    if (
        left_correct
        and mathematically_equivalent
        and not has_split_structure
    ):
        return {
            "correct": False,
            "error_type": "not_split_yet",
            "feedback": (
                "Your expression is mathematically equivalent, "
                "but you have not performed the requested "
                "exponential-splitting step yet."
            ),
            "suggestion": (
                f"Rewrite exp({sp.sstr(integrated_fx)} + C) "
                f"as exp({sp.sstr(integrated_fx)}) * exp(C)."
            ),
        }

    if not left_correct:
        return {
            "correct": False,
            "error_type": "incorrect_left_side",
            "feedback": (
                "Keep the left side as |y| during this step."
            ),
            "suggestion": (
                "Only transform the exponential on the "
                "right side."
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_exponential_split",
        "feedback": (
            "Remember that an exponential of a sum "
            "becomes a product of exponentials."
        ),
        "suggestion": (
            f"Use: exp({sp.sstr(integrated_fx)} + C) "
            f"= exp({sp.sstr(integrated_fx)}) * exp(C)"
        ),
    }

def evaluate_rename_exp_constant_step(
    student_answer: str,
    integrated_fx,
) -> dict:
    """
    Expected conceptual transformation:

        |y| = exp(F(x)) * exp(C)

    becomes:

        |y| = K * exp(F(x))

    where K is a positive constant representing exp(C).
    """

    answer = normalize_expression(
        student_answer
    )

    answer = answer.replace(
        "|y|",
        "Abs(y)",
    )

    if "=" not in answer:
        return {
            "correct": False,
            "error_type": "missing_equals",
            "feedback": (
                "Write the rewritten equation using '='."
            ),
            "suggestion": (
                "Try something like: "
                "|y| = K*exp(...)"
            ),
        }

    left_text, right_text = answer.split(
        "=",
        maxsplit=1,
    )

    K = sp.symbols("K")

    try:
        left = parse_expr(
            left_text,
            transformations=TRANSFORMATIONS,
            local_dict={
                "x": x,
                "y": y,
                "C": C,
                "K": K,
                "exp": sp.exp,
                "log": sp.log,
                "Abs": sp.Abs,
            },
            evaluate=True,
        )

        right = parse_expr(
            right_text,
            transformations=TRANSFORMATIONS,
            local_dict={
                "x": x,
                "y": y,
                "C": C,
                "K": K,
                "exp": sp.exp,
                "log": sp.log,
                "Abs": sp.Abs,
            },
            evaluate=True,
        )

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        sp.SympifyError,
    ):

        typo_correction = detect_common_function_typo(
            student_answer
        )

        if typo_correction is not None:
            return {
                "correct": False,
                "error_type": "likely_typo",
                "feedback": (
                    "Your mathematical idea may be right, but "
                    "I noticed what looks like a function-name typo."
                ),
                "suggestion": (
                    f"Did you mean '{typo_correction}'?"
                ),
            }

        return {
            "correct": False,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand that expression."
            ),
            "suggestion": (
                "Try something like: "
                "|y| = K*exp(2*x**3)"
            ),
        }

    expected_left = sp.Abs(y)

    expected_right = (
        K * sp.exp(integrated_fx)
    )

    left_correct = (
        left == expected_left
    )

    right_correct = (
        sp.simplify(
            right - expected_right
        ) == 0
    )

    has_k = (
        K in right.free_symbols
    )

    if (
        left_correct
        and right_correct
        and has_k
    ):
        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. You renamed exp(C) as a new "
                "positive constant K."
            ),
            "suggestion": (
                "Next, remove the absolute value. "
                "If |y| = K*exp(...), what are the "
                "two possible signs for y?"
            ),
        }

    if not left_correct:
        return {
            "correct": False,
            "error_type": "incorrect_left_side",
            "feedback": (
                "Keep the left side as |y| for this step."
            ),
            "suggestion": (
                "Only replace exp(C) with a new constant."
            ),
        }

    if not has_k:
        return {
            "correct": False,
            "error_type": "constant_not_renamed",
            "feedback": (
                "The goal of this step is to replace exp(C) "
                "with a simpler constant symbol."
            ),
            "suggestion": (
                "Let K = exp(C), then write "
                "|y| = K*exp(...)."
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_constant_form",
        "feedback": (
            "You introduced K, but the rest of the "
            "expression is not quite right."
        ),
        "suggestion": (
            f"Try: |y| = K*exp("
            f"{sp.sstr(integrated_fx)})"
        ),
    }

def evaluate_remove_absolute_value_step(
    student_answer: str,
    integrated_fx,
) -> dict:

    typo_correction = detect_common_function_typo(
        student_answer
    )

    if typo_correction is not None:
        return {
            "correct": False,
            "error_type": "likely_typo",
            "feedback": (
                "Your mathematical idea may be right, but "
                "I noticed what looks like a function-name typo."
            ),
            "suggestion": (
                f"Did you mean '{typo_correction}'?"
            ),
        }

    answer = normalize_expression(
        student_answer
    )

    answer = (
        answer
        .replace("±", "+/-")
        .replace("+-", "+/-")
    )

    # ... rest of the existing function

    if "=" not in answer:
        return {
            "correct": False,
            "error_type": "missing_equals",
            "feedback": (
                "Write the equation after removing "
                "the absolute value."
            ),
            "suggestion": (
                "Show both possibilities for y. "
                "For example: y = +/- K*exp(...)"
            ),
        }

    left_text, right_text = answer.split(
        "=",
        maxsplit=1,
    )

    left_text = left_text.strip()
    right_text = right_text.strip()

    K = sp.symbols(
        "K",
        positive=True,
    )

    expected_unsigned = (
        K * sp.exp(integrated_fx)
    )

    #
    # CASE 1:
    #
    #     y = +/- K*exp(...)
    #
    if left_text == "y" and "+/-" in right_text:
        unsigned_text = (
            right_text
            .replace("+/-", "")
            .strip()
        )

        try:
            unsigned_expr = parse_expr(
                unsigned_text,
                transformations=TRANSFORMATIONS,
                local_dict={
                    "x": x,
                    "y": y,
                    "C": C,
                    "K": K,
                    "exp": sp.exp,
                },
                evaluate=True,
            )

        except (
            SyntaxError,
            TypeError,
            ValueError,
            NameError,
            sp.SympifyError,
        ):

            typo_correction = detect_common_function_typo(
                student_answer
            )

            if typo_correction is not None:
                return {
                    "correct": False,
                    "error_type": "likely_typo",
                    "feedback": (
                        "Your mathematical idea may be right, but "
                        "I noticed what looks like a function-name typo."
                    ),
                    "suggestion": (
                        f"Did you mean '{typo_correction}'?"
                    ),
                }

            return {
                "correct": False,
                "error_type": "parse_error",
                "feedback": (
                    "I understood that you want both signs, "
                    "but I could not understand the expression "
                    "after +/-."
                ),
                "suggestion": (
                    f"Try: y = +/- K*exp("
                    f"{sp.sstr(integrated_fx)})"
                ),
            }

        if (
            sp.simplify(
                unsigned_expr
                - expected_unsigned
            )
            == 0
        ):
            return {
                "correct": True,
                "error_type": None,
                "feedback": (
                    "Correct. You included both the positive "
                    "and negative possibilities for y."
                ),
                "suggestion": (
                    "Next, combine +/- K into one new "
                    "arbitrary constant C."
                ),
            }

        return {
            "correct": False,
            "error_type": "incorrect_expression",
            "feedback": (
                "The +/- idea is correct, but the expression "
                "after it is not equivalent to the current "
                "right-hand side."
            ),
            "suggestion": (
                f"Try: y = +/- K*exp("
                f"{sp.sstr(integrated_fx)})"
            ),
        }

    #
    # CASE 2:
    #
    #     +/- y = K*exp(...)
    #
    # This expresses the same two branches:
    #
    #     +y = RHS
    #     -y = RHS
    #
    # which is equivalent to:
    #
    #     y = +/- RHS
    #
    if "+/-" in left_text:
        left_without_sign = (
            left_text
            .replace("+/-", "")
            .strip()
        )

        if left_without_sign != "y":
            return {
                "correct": False,
                "error_type": "incorrect_left_side",
                "feedback": (
                    "I see the +/- sign, but it should "
                    "be associated with y."
                ),
                "suggestion": (
                    "You can write either "
                    "'+/- y = ...' or 'y = +/- ...'."
                ),
            }

        try:
            right_expr = parse_expr(
                right_text,
                transformations=TRANSFORMATIONS,
                local_dict={
                    "x": x,
                    "y": y,
                    "C": C,
                    "K": K,
                    "exp": sp.exp,
                },
                evaluate=True,
            )

        except (
            SyntaxError,
            TypeError,
            ValueError,
            NameError,
            sp.SympifyError,
        ):

            typo_correction = detect_common_function_typo(
                student_answer
            )

            if typo_correction is not None:
                return {
                    "correct": False,
                    "error_type": "likely_typo",
                    "feedback": (
                        "Your mathematical idea may be right, but "
                        "I noticed what looks like a function-name typo."
                    ),
                    "suggestion": (
                        f"Did you mean '{typo_correction}'?"
                    ),
                }


            return {
                "correct": False,
                "error_type": "parse_error",
                "feedback": (
                    "I understood your +/- idea, but I "
                    "could not understand the right side."
                ),
                "suggestion": (
                    f"Try: +/- y = K*exp("
                    f"{sp.sstr(integrated_fx)})"
                ),
            }

        if (
            sp.simplify(
                right_expr
                - expected_unsigned
            )
            == 0
        ):
            return {
                "correct": True,
                "error_type": None,
                "feedback": (
                    "Correct. Writing +/- y on the left "
                    "expresses the same two sign possibilities."
                ),
                "suggestion": (
                    "A more standard way to write this is "
                    "y = +/- K*exp(...). "
                    "Next, combine +/- K into one arbitrary "
                    "constant C."
                ),
            }

        return {
            "correct": False,
            "error_type": "incorrect_expression",
            "feedback": (
                "Your +/- placement is acceptable, but "
                "the right-hand expression is not correct."
            ),
            "suggestion": (
                f"Try: +/- y = K*exp("
                f"{sp.sstr(integrated_fx)})"
            ),
        }

    #
    # CASE 3:
    #
    # Student writes just one branch:
    #
    #     y = K*exp(...)
    #     y = -K*exp(...)
    #
    if left_text == "y":
        try:
            right_expr = parse_expr(
                right_text,
                transformations=TRANSFORMATIONS,
                local_dict={
                    "x": x,
                    "y": y,
                    "C": C,
                    "K": K,
                    "exp": sp.exp,
                },
                evaluate=True,
            )

        except (
            SyntaxError,
            TypeError,
            ValueError,
            NameError,
            sp.SympifyError,
        ):

            typo_correction = detect_common_function_typo(
                student_answer
            )

            if typo_correction is not None:
                return {
                    "correct": False,
                    "error_type": "likely_typo",
                    "feedback": (
                        "Your mathematical idea may be right, but "
                        "I noticed what looks like a function-name typo."
                    ),
                    "suggestion": (
                        f"Did you mean '{typo_correction}'?"
                    ),
                }


            return {
                "correct": False,
                "error_type": "parse_error",
                "feedback": (
                    "I could not understand the expression."
                ),
                "suggestion": (
                    f"Try: y = +/- K*exp("
                    f"{sp.sstr(integrated_fx)})"
                ),
            }

        positive_case = (
            sp.simplify(
                right_expr
                - expected_unsigned
            )
            == 0
        )

        negative_case = (
            sp.simplify(
                right_expr
                + expected_unsigned
            )
            == 0
        )

        if positive_case or negative_case:
            return {
                "correct": False,
                "error_type": "only_one_sign",
                "feedback": (
                    "That is one valid branch of the solution. "
                    "But |y| represents both a positive and "
                    "a negative possibility."
                ),
                "suggestion": (
                    f"Combine both branches as: "
                    f"y = +/- K*exp("
                    f"{sp.sstr(integrated_fx)})"
                ),
            }

    return {
        "correct": False,
        "error_type": "incorrect_expression",
        "feedback": (
            "After removing |y|, we need to represent "
            "both possible signs of y."
        ),
        "suggestion": (
            f"You can write either:\n"
            f"    y = +/- K*exp({sp.sstr(integrated_fx)})\n"
            f"or:\n"
            f"    +/- y = K*exp({sp.sstr(integrated_fx)})"
        ),
    }

def evaluate_absorb_constant_step(
    student_answer: str,
    integrated_fx,
) -> dict:
    """
    Expected transformation:

        y = +/- K * exp(F(x))

    becomes:

        y = C * exp(F(x))

    where C is now a new arbitrary constant.
    """

    answer = normalize_expression(
        student_answer
    )

    if "=" not in answer:
        return {
            "correct": False,
            "error_type": "missing_equals",
            "feedback": (
                "Write the final rewritten equation using '='."
            ),
            "suggestion": (
                "Replace +/- K with one new arbitrary constant C."
            ),
        }

    left_text, right_text = answer.split(
        "=",
        maxsplit=1,
    )

    left_text = left_text.strip()
    right_text = right_text.strip()

    if left_text != "y":
        return {
            "correct": False,
            "error_type": "incorrect_left_side",
            "feedback": (
                "The left side should now simply be y."
            ),
            "suggestion": (
                "Write the final form as y = C*exp(...)."
            ),
        }

    try:
        right = parse_expr(
            right_text,
            transformations=TRANSFORMATIONS,
            local_dict={
                "x": x,
                "y": y,
                "C": C,
                "exp": sp.exp,
            },
            evaluate=True,
        )

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        sp.SympifyError,
    ):

        typo_correction = detect_common_function_typo(
            student_answer
        )

        if typo_correction is not None:
            return {
                "correct": False,
                "error_type": "likely_typo",
                "feedback": (
                    "Your mathematical idea may be right, but "
                    "I noticed what looks like a function-name typo."
                ),
                "suggestion": (
                    f"Did you mean '{typo_correction}'?"
                ),
            }

        return {
            "correct": False,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand that final expression."
            ),
            "suggestion": (
                f"Try: y = C*exp("
                f"{sp.sstr(integrated_fx)})"
            ),
        }

    expected = (
        C * sp.exp(integrated_fx)
    )

    mathematically_correct = (
        sp.simplify(
            right - expected
        ) == 0
    )

    has_c = (
        C in right.free_symbols
    )

    if mathematically_correct and has_c:
        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. The +/- sign and the positive "
                "constant K have been combined into one "
                "new arbitrary constant C."
            ),
            "suggestion": (
                "You now have the standard general solution. "
                "The next step is to verify that it satisfies "
                "the original differential equation."
            ),
        }

    if not has_c:
        return {
            "correct": False,
            "error_type": "missing_arbitrary_constant",
            "feedback": (
                "The final general solution still needs "
                "an arbitrary constant."
            ),
            "suggestion": (
                f"Use a form like: "
                f"y = C*exp({sp.sstr(integrated_fx)})"
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_final_form",
        "feedback": (
            "You included C, but the rest of the expression "
            "does not match the expected solution."
        ),
        "suggestion": (
            f"Try: y = C*exp("
            f"{sp.sstr(integrated_fx)})"
        ),
    }