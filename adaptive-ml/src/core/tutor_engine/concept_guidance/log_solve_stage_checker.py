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


def normalize_expression(text: str) -> str:
    return (
        text.strip()
        .replace("X", "x")
        .replace("Y", "y")
        .replace("^", "**")
        .replace("×", "*")
        .replace("÷", "/")
        .replace("ln(", "log(")
    )


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
        return {
            "correct": False,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand that expression."
            ),
            "suggestion": (
                "Try something like: "
                "|y| = exp(2*x**3 + C)"
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

    Accept equivalent multiplication forms.
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
                "Try something like: "
                "|y| = exp(2*x**3) * exp(C)"
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

    has_split_structure = (
        isinstance(right, sp.Mul)
        and sp.exp(integrated_fx) in right.args
        and sp.exp(C) in right.args
    )

    if (left_correct and mathematically_equivalent and has_split_structure):
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
    """
    Expected transformation:

        |y| = K * exp(F(x))

    becomes:

        y = +/- K * exp(F(x))

    Accept forms such as:
        y = K*exp(...)
        y = -K*exp(...)
        y = +/-K*exp(...)

    But distinguish whether the student explicitly recognized
    both possible signs.
    """

    answer = normalize_expression(
        student_answer
    )

    answer = (
        answer
        .replace("±", "+/-")
        .replace("+-", "+/-")
    )

    if "=" not in answer:
        return {
            "correct": False,
            "error_type": "missing_equals",
            "feedback": (
                "Write the equation after removing "
                "the absolute value."
            ),
            "suggestion": (
                "Think about both possibilities: "
                "y can be positive or negative."
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
            "error_type": "absolute_value_not_removed",
            "feedback": (
                "At this step, remove |y| and write y "
                "on the left."
            ),
            "suggestion": (
                "The left side should now simply be y."
            ),
        }

    K = sp.symbols(
        "K",
        positive=True,
    )

    expected_positive = (
        K * sp.exp(integrated_fx)
    )

    expected_negative = (
        -K * sp.exp(integrated_fx)
    )

    #
    # Explicit +/- form
    #
    has_plus_minus = (
        "+/-" in right_text
    )

    if has_plus_minus:
        expression_without_sign = (
            right_text.replace(
                "+/-",
                "",
            )
        )

        try:
            unsigned_expr = parse_expr(
                expression_without_sign,
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
            return {
                "correct": False,
                "error_type": "parse_error",
                "feedback": (
                    "I could not understand the "
                    "expression after +/-."
                ),
                "suggestion": (
                    "Try: y = +/- K*exp(...)"
                ),
            }

        unsigned_correct = (
            sp.simplify(
                unsigned_expr
                - expected_positive
            ) == 0
        )

        if unsigned_correct:
            return {
                "correct": True,
                "error_type": None,
                "feedback": (
                    "Correct. Removing the absolute value "
                    "gives both a positive and a negative "
                    "possibility for y."
                ),
                "suggestion": (
                    "Next, combine +/- K into one new "
                    "arbitrary constant."
                ),
            }

        return {
            "correct": False,
            "error_type": "incorrect_expression",
            "feedback": (
                "You correctly included both signs, "
                "but the expression after +/- is not right."
            ),
            "suggestion": (
                f"Try: y = +/- K*exp("
                f"{sp.sstr(integrated_fx)})"
            ),
        }

    #
    # Single-sign answer
    #
    try:
        right = parse_expr(
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
        return {
            "correct": False,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand that expression."
            ),
            "suggestion": (
                "Try: y = +/- K*exp(...)"
            ),
        }

    is_positive_case = (
        sp.simplify(
            right - expected_positive
        ) == 0
    )

    is_negative_case = (
        sp.simplify(
            right - expected_negative
        ) == 0
    )

    if is_positive_case or is_negative_case:
        return {
            "correct": False,
            "error_type": "only_one_sign",
            "feedback": (
                "That is one valid branch, but |y| means "
                "there are two possibilities for y."
            ),
            "suggestion": (
                "Include both signs using +/-."
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_expression",
        "feedback": (
            "The absolute value creates positive and "
            "negative possibilities."
        ),
        "suggestion": (
            f"Try: y = +/- K*exp("
            f"{sp.sstr(integrated_fx)})"
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