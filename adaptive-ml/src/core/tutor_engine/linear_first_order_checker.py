import sympy as sp
from tokenize import TokenError

from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


x = sp.symbols("x")


TRANSFORMATIONS = (
    standard_transformations
    + (
        implicit_multiplication_application,
        convert_xor,
    )
)


def normalize_expression(
    text: str,
) -> str:
    text = text.strip()

    text = text.replace(
        "X",
        "x",
    )

    text = text.replace(
        "^",
        "**",
    )

    text = text.replace(
        "×",
        "*",
    )

    text = text.replace(
        "÷",
        "/",
    )

    return text


def parse_math(
    expression: str,
):
    return parse_expr(
        expression,
        transformations=TRANSFORMATIONS,
        local_dict={
            "x": x,
        },
        evaluate=True,
    )


def evaluate_p_q_identification(
    student_p: str,
    student_q: str,
    expected_p,
    expected_q,
) -> dict:
    """
    Validate the student's identification of:

        P(x)
        Q(x)

    from:

        y' + P(x)y = Q(x)
    """

    student_p = normalize_expression(
        student_p
    )

    student_q = normalize_expression(
        student_q
    )

    try:
        parsed_p = parse_math(
            student_p
        )

        parsed_q = parse_math(
            student_q
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
                "I could not understand one of "
                "the expressions."
            ),
            "suggestion": (
                "Write only the expressions for "
                "P(x) and Q(x)."
            ),
        }

    p_correct = (
        sp.simplify(
            parsed_p - expected_p
        ) == 0
    )

    q_correct = (
        sp.simplify(
            parsed_q - expected_q
        ) == 0
    )

    if p_correct and q_correct:
        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. You identified both "
                "P(x) and Q(x)."
            ),
            "suggestion": (
                "Next, use P(x) to construct "
                "the integrating factor."
            ),
        }

    if not p_correct and q_correct:
        return {
            "correct": False,
            "error_type": "incorrect_p",
            "feedback": (
                "Your Q(x) is correct, but P(x) "
                "does not match the coefficient of y."
            ),
            "suggestion": (
                "In y' + P(x)y = Q(x), "
                "P(x) is the expression multiplying y."
            ),
        }

    if p_correct and not q_correct:
        return {
            "correct": False,
            "error_type": "incorrect_q",
            "feedback": (
                "Your P(x) is correct, but Q(x) "
                "is not the right-hand side."
            ),
            "suggestion": (
                "Q(x) is everything on the right "
                "side of the standard linear form."
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_p_and_q",
        "feedback": (
            "Neither P(x) nor Q(x) matches "
            "the standard linear form."
        ),
        "suggestion": (
            "Compare the equation with "
            "y' + P(x)y = Q(x)."
        ),
    }

def evaluate_integrating_factor(
    student_answer: str,
    expected_p,
) -> dict:
    """
    Validate the integrating factor: mu(x) = exp(integral(P(x)) dx)
    Example: P(x) = 2*x
    gives: mu(x) = exp(x**2)
    """

    answer = normalize_expression(
        student_answer
    )

    # Allow forms like:
    # mu = exp(x**2)
    # mu(x) = exp(x**2)
    # exp(x**2)

    if "=" in answer:
        left_text, right_text = answer.split(
            "=",
            maxsplit=1,
        )

        expression_text = right_text.strip()

    else:
        expression_text = answer

    try:
        student_mu = parse_math(
            expression_text
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
                "I could not understand the integrating factor."
            ),
            "suggestion": (
                "Use mu(x) = exp(integral(P(x)) dx)."
            ),
        }

    integrated_p = sp.integrate(
        expected_p,
        x,
    )

    expected_mu = sp.exp(
        integrated_p
    )

    mathematically_correct = (
        sp.simplify(
            student_mu - expected_mu
        ) == 0
    )

    if mathematically_correct:
        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. You found the integrating factor."
            ),
            "suggestion": (
                "Next, multiply every term in the differential "
                "equation by the integrating factor."
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_integrating_factor",
        "feedback": (
            "That does not match the integrating factor "
            "generated from P(x)."
        ),
        "suggestion": (
            f"First calculate integral({sp.sstr(expected_p)}) dx, "
            "then place the result inside exp(...)."
        ),
    }

def evaluate_multiply_by_integrating_factor(
    student_answer: str,
    expected_p,
    expected_q,
) -> dict:
    """
    Validate multiplication of the whole ODE

        y' + P(x)y = Q(x)

    by the integrating factor

        mu(x) = exp(integral(P(x)) dx)

    Expected result:

        mu*y' + mu*P*y = mu*Q
    """

    y = sp.symbols("y")
    yp = sp.symbols("yp")

    answer = normalize_expression(
        student_answer
    )

    #
    # Accept convenient derivative notation:
    #
    # y'
    # dy/dx
    #
    answer = answer.replace(
        "dy/dx",
        "yp",
    )

    answer = answer.replace(
        "y'",
        "yp",
    )

    if "=" not in answer:
        return {
            "correct": False,
            "error_type": "missing_equals",
            "feedback": (
                "Write the complete equation after multiplying "
                "every term by the integrating factor."
            ),
            "suggestion": (
                "Both sides of the equation must be multiplied "
                "by mu(x)."
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
                "yp": yp,
                "exp": sp.exp,
            },
            evaluate=True,
        )

        right = parse_expr(
            right_text,
            transformations=TRANSFORMATIONS,
            local_dict={
                "x": x,
                "y": y,
                "yp": yp,
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
                "I could not understand the multiplied equation."
            ),
            "suggestion": (
                "Write the complete equation, for example:\n"
                "exp(...)*y' + exp(...)*P(x)*y "
                "= exp(...)*Q(x)"
            ),
        }

    integrated_p = sp.integrate(
        expected_p,
        x,
    )

    mu = sp.exp(
        integrated_p
    )

    expected_left = (
        mu * yp
        + mu * expected_p * y
    )

    expected_right = (
        mu * expected_q
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
                "Correct. You multiplied every term in the "
                "differential equation by the integrating factor."
            ),
            "suggestion": (
                "Next, look at the two terms on the left. "
                "They form the derivative of a product."
            ),
        }

    if not left_correct and right_correct:
        return {
            "correct": False,
            "error_type": "incorrect_left_side",
            "feedback": (
                "The right side is correct, but not every term "
                "on the left was multiplied correctly."
            ),
            "suggestion": (
                "Multiply both y' and P(x)y by mu(x)."
            ),
        }

    if left_correct and not right_correct:
        return {
            "correct": False,
            "error_type": "incorrect_right_side",
            "feedback": (
                "The left side is correct, but remember that "
                "the right side must also be multiplied by mu(x)."
            ),
            "suggestion": (
                "The right side should be mu(x)*Q(x)."
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_multiplication",
        "feedback": (
            "The equation does not yet represent multiplying "
            "every term by the integrating factor."
        ),
        "suggestion": (
            "Start with y' + P(x)y = Q(x), then multiply "
            "all three terms by mu(x)."
        ),
    }

def evaluate_product_derivative(
    student_answer: str,
    expected_p,
    expected_q,
) -> dict:
    """
    Validate recognition that  mu*y' + mu*P*y  is the derivative d/dx(mu*y)
    where: mu = exp(integral(P dx))
    The student is expected to rewrite the whole equation as: d/dx(mu*y) = mu*Q
    """

    y = sp.symbols("y")
    yp = sp.symbols("yp")

    answer = normalize_expression(
        student_answer
    )

    integrated_p = sp.integrate(
        expected_p,
        x,
    )

    mu = sp.exp(
        integrated_p
    )

    expected_right = sp.simplify(
        mu * expected_q
    )

    # We will allow several human-friendly forms:
    # d/dx(exp(x**2)*y) = x*exp(x**2)
    # derivative(exp(x**2)*y) = x*exp(x**2)
    # D(exp(x**2)*y) = x*exp(x**2)
 
    if "=" not in answer:
        return {
            "correct": False,
            "error_type": "missing_equals",
            "feedback": (
                "Write the complete transformed equation."
            ),
            "suggestion": (
                "The left side should become "
                "d/dx(mu(x)*y)."
            ),
        }

    left_text, right_text = answer.split(
        "=",
        maxsplit=1,
    )

    left_text = left_text.strip()
    right_text = right_text.strip()

    try:
        right = parse_expr(
            right_text,
            transformations=TRANSFORMATIONS,
            local_dict={
                "x": x,
                "y": y,
                "exp": sp.exp,
            },
            evaluate=True,
        )

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        TokenError,
        sp.SympifyError,
    ):
        return {
            "correct": False,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand the right-hand side."
            ),
            "suggestion": (
                "Check the parentheses and keep the right side as mu(x)*Q(x)."
            ),
        }

    right_correct = (
        sp.simplify(
            right - expected_right
        ) == 0
    )

    #
    # Detect derivative notation.
    #
    derivative_prefixes = [
        "d/dx",
        "derivative",
        "D",
    ]

    derivative_expression = None

    for prefix in derivative_prefixes:
        if left_text.startswith(
            prefix
        ):
            derivative_expression = (
                left_text[
                    len(prefix):
                ].strip()
            )

            break

    if derivative_expression is None:
        return {
            "correct": False,
            "error_type": (
                "product_derivative_not_recognized"
            ),
            "feedback": (
                "The left side has not yet been written "
                "as the derivative of a product."
            ),
            "suggestion": (
                "Use the product rule backward:\n"
                "mu*y' + mu'*y = d/dx(mu*y)."
            ),
        }

    #
    # Remove surrounding parentheses:
    #
    # d/dx(exp(x**2)*y)
    #
    if (
        derivative_expression.startswith("(")
        and derivative_expression.endswith(")")
    ):
        derivative_expression = (
            derivative_expression[1:-1]
        )

    try:
        inside_derivative = parse_expr(
            derivative_expression,
            transformations=TRANSFORMATIONS,
            local_dict={
                "x": x,
                "y": y,
                "exp": sp.exp,
            },
            evaluate=True,
        )

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        TokenError,
        sp.SympifyError,
    ):
        return {
            "correct": False,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand the expression "
                "inside the derivative."
            ),
            "suggestion": (
                "Check the parentheses. "
                "The product should be mu(x)*y."
            ),
        }

    expected_product = (
        mu * y
    )

    product_correct = (
        sp.simplify(
            inside_derivative
            - expected_product
        ) == 0
    )

    if product_correct and right_correct:
        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. The two left-hand terms are "
                "the derivative of the product mu(x)*y."
            ),
            "suggestion": (
                "Next, integrate both sides with respect to x."
            ),
        }

    if not product_correct and right_correct:
        return {
            "correct": False,
            "error_type": "incorrect_product",
            "feedback": (
                "The right side is correct, but the expression "
                "inside the derivative is not mu(x)*y."
            ),
            "suggestion": (
                "Use d/dx(mu(x)*y)."
            ),
        }

    if product_correct and not right_correct:
        return {
            "correct": False,
            "error_type": "incorrect_right_side",
            "feedback": (
                "You recognized the product derivative correctly, "
                "but the right-hand side changed."
            ),
            "suggestion": (
                "Keep the right side equal to mu(x)*Q(x)."
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_product_derivative",
        "feedback": (
            "The product derivative and the right-hand side "
            "do not yet match the transformed equation."
        ),
        "suggestion": (
            "Rewrite it as "
            "d/dx(mu(x)*y) = mu(x)*Q(x)."
        ),
    }

def evaluate_linear_integration_step(
    student_answer: str,
    expected_p,
    expected_q,
) -> dict:
    """
    Validate integration of

        d/dx(mu*y) = mu*Q

    giving

        mu*y = integral(mu*Q dx) + C
    """

    y = sp.symbols("y")
    C = sp.symbols("C")

    answer = normalize_expression(
        student_answer
    )

    if "=" not in answer:
        return {
            "correct": False,
            "error_type": "missing_equals",
            "feedback": (
                "Write the complete equation after integrating "
                "both sides."
            ),
            "suggestion": (
                "The left side becomes mu(x)*y, and the right "
                "side becomes the integral of mu(x)*Q(x), plus C."
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
                "I could not understand the integrated equation."
            ),
            "suggestion": (
                "Write something like "
                "exp(x**2)*y = exp(x**2)/2 + C."
            ),
        }

    integrated_p = sp.integrate(
        expected_p,
        x,
    )

    mu = sp.exp(
        integrated_p
    )

    expected_left = (
        mu * y
    )

    integrand = sp.simplify(
        mu * expected_q
    )

    expected_integral = sp.integrate(
        integrand,
        x,
    )

    left_correct = (
        sp.simplify(
            left - expected_left
        ) == 0
    )

    #
    # C is arbitrary, so compare the non-constant x-dependent
    # part by differentiating the student's right-hand side.
    #
    right_derivative_correct = (
        sp.simplify(
            sp.diff(right, x)
            - integrand
        ) == 0
    )

    has_constant = (
        right.has(C)
    )

    if (
        left_correct
        and right_derivative_correct
        and has_constant
    ):
        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. You integrated both sides and included "
                "the arbitrary constant C."
            ),
            "suggestion": (
                "Next, divide by the integrating factor to "
                "solve explicitly for y."
            ),
        }

    if (
        left_correct
        and right_derivative_correct
        and not has_constant
    ):
        return {
            "correct": False,
            "error_type": "missing_constant",
            "feedback": (
                "Your integration is correct, but the arbitrary "
                "constant is missing."
            ),
            "suggestion": (
                "Add + C because this is an indefinite integral."
            ),
        }

    if (
        not left_correct
        and right_derivative_correct
    ):
        return {
            "correct": False,
            "error_type": "incorrect_left_side",
            "feedback": (
                "The right-hand integration is correct, but the "
                "left side should become mu(x)*y."
            ),
            "suggestion": (
                "Integrating d/dx(mu*y) gives mu*y."
            ),
        }

    if (
        left_correct
        and not right_derivative_correct
    ):
        return {
            "correct": False,
            "error_type": "incorrect_integral",
            "feedback": (
                "The left side is correct, but the integral on "
                "the right is not correct."
            ),
            "suggestion": (
                f"Integrate {sp.sstr(integrand)} with respect to x."
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_integration_step",
        "feedback": (
            "The integrated equation does not yet match the "
            "previous differential equation."
        ),
        "suggestion": (
            "Integrate both sides of "
            "d/dx(mu*y) = mu*Q."
        ),
    }

def evaluate_linear_solve_for_y(
    student_answer: str,
    expected_p,
    expected_q,
) -> dict:
    """
    Validate the final general solution obtained from

        mu*y = integral(mu*Q dx) + C

    by dividing through by mu.

    The checker compares the student's solution symbolically.
    """

    y = sp.symbols("y")
    C = sp.symbols("C")

    answer = normalize_expression(
        student_answer
    )

    if "=" not in answer:
        return {
            "correct": False,
            "error_type": "missing_equals",
            "feedback": (
                "Write the complete solution in the form y = ..."
            ),
            "suggestion": (
                "Divide both sides of the integrated equation "
                "by the integrating factor."
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
                "I could not understand the proposed solution."
            ),
            "suggestion": (
                "Write the solution in the form y = expression."
            ),
        }

    if sp.simplify(left - y) != 0:
        return {
            "correct": False,
            "error_type": "y_not_isolated",
            "feedback": (
                "The solution is not yet written explicitly "
                "with y isolated."
            ),
            "suggestion": (
                "Divide through by the integrating factor "
                "so that the left side is only y."
            ),
        }

    integrated_p = sp.integrate(
        expected_p,
        x,
    )

    mu = sp.exp(
        integrated_p
    )

    integrand = sp.simplify(
        mu * expected_q
    )

    antiderivative = sp.integrate(
        integrand,
        x,
    )

    expected_solution = sp.simplify(
        (
            antiderivative + C
        )
        / mu
    )

    mathematically_correct = (
        sp.simplify(
            right - expected_solution
        ) == 0
    )

    if mathematically_correct:
        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. You divided by the integrating factor "
                "and solved explicitly for y."
            ),
            "suggestion": (
                "Next, verify the solution by substituting it "
                "back into the original differential equation."
            ),
        }

    #
    # Check whether the non-constant part is correct
    # but the arbitrary constant was omitted.
    #
    expected_without_c = sp.simplify(
        antiderivative / mu
    )

    missing_constant = (
        sp.simplify(
            right - expected_without_c
        ) == 0
    )

    if missing_constant:
        return {
            "correct": False,
            "error_type": "missing_constant",
            "feedback": (
                "The non-constant part is correct, but the "
                "arbitrary constant term is missing."
            ),
            "suggestion": (
                "Do not lose C when dividing by the "
                "integrating factor."
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_solution",
        "feedback": (
            "That does not match the solution obtained after "
            "dividing by the integrating factor."
        ),
        "suggestion": (
            "Start from mu*y = integral(mu*Q dx) + C "
            "and divide every term on the right by mu."
        ),
    }