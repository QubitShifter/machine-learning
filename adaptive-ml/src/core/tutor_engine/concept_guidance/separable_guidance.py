import sympy as sp


x = sp.symbols("x")
y = sp.symbols("y")


def answer_means_yes(answer: str) -> bool:
    answer = answer.lower().strip()

    phrases = [
        "yes",
        "yeah",
        "yep",
        "i understand",
        "understand",
        "got it",
        "makes sense",
        "clear",
    ]

    return any(
        phrase in answer
        for phrase in phrases
    )


def answer_means_no(answer: str) -> bool:
    answer = answer.lower().strip()

    phrases = [
        "no",
        "not really",
        "don't understand",
        "do not understand",
        "not clear",
        "confused",
        "i dont know",
        "i don't know",
    ]

    return any(
        phrase in answer
        for phrase in phrases
    )


def explain_natural_logarithm() -> None:
    print("\nTutor:")
    print(
        "ln means the natural logarithm.\n"
    )

    print(
        "The most important idea here is that ln and the "
        "exponential function exp are inverse operations."
    )

    print(
        "\nYou can think of inverse operations like this:"
    )

    print(
        "    addition <-> subtraction"
    )

    print(
        "    multiplication <-> division"
    )

    print(
        "    ln <-> exp"
    )

    print(
        "\nFor example:"
    )

    print(
        "    ln(exp(3)) = 3"
    )

    print(
        "and:"
    )

    print(
        "    exp(ln(5)) = 5"
    )

    print(
        "\nSo exp can 'undo' ln."
    )


def explain_why_ln_appears() -> None:
    print("\nTutor:")
    print(
        "The ln appears because after separating variables "
        "we integrate 1/y."
    )

    print(
        "\nThe integration rule is:"
    )

    print(
        "    integral(1/y) dy = ln|y| + C"
    )

    print(
        "\nThis is different from the ordinary power rule."
    )

    print(
        "The power rule would require dividing by n + 1, "
        "but for 1/y we have y^(-1)."
    )

    print(
        "That would make n + 1 = 0, so this is the special "
        "logarithm case."
    )


def explain_ln_to_y(
    integrated_fx: sp.Expr
) -> None:
    print("\nTutor:")
    print(
        "Now suppose we have reached:"
    )

    print(
        f"\n    ln|y| = {sp.sstr(integrated_fx)} + C"
    )

    print(
        "\nOur goal is to get y by itself."
    )

    print(
        "Because exp and ln are inverse functions, "
        "we apply exp to BOTH sides:"
    )

    print(
        f"\n    exp(ln|y|) = "
        f"exp({sp.sstr(integrated_fx)} + C)"
    )

    print(
        "\nOn the left:"
    )

    print(
        "    exp(ln|y|) = |y|"
    )

    print(
        "\nThe logarithm did not simply disappear."
    )

    print(
        "We applied its inverse operation, so the two operations "
        "cancel each other."
    )

    print(
        "\nOn the right we can use:"
    )

    print(
        "    exp(a + b) = exp(a) * exp(b)"
    )

    print(
        "\nTherefore:"
    )

    print(
        f"    |y| = exp({sp.sstr(integrated_fx)}) * exp(C)"
    )

    print(
        "\nBecause C is arbitrary, exp(C), together with the "
        "possible positive/negative sign from |y|, can be represented "
        "by another arbitrary constant."
    )

    print(
        "\nWe conventionally call that new constant C again."
    )

    print(
        "\nTherefore:"
    )

    print(
        f"    y = C*exp({sp.sstr(integrated_fx)})"
    )


def respond_to_concept_question(
    student_message: str,
    integrated_fx: sp.Expr
) -> bool:
    """
    Respond to common conceptual questions.

    Returns True when a known concept was recognized.
    """

    message = student_message.lower()

    asks_about_ln = (
        "what is ln" in message
        or "what does ln" in message
        or "what is log" in message
        or "logarithm" in message
    )

    asks_why_ln = (
        (
            "why" in message
            and "ln" in message
        )
        or "why logarithm" in message
    )

    asks_ln_disappears = (
        "only y" in message
        or "become y" in message
        or "became y" in message
        or "ln disappear" in message
        or "ln cancel" in message
        or (
            "ln" in message
            and "exp" in message
        )
    )

    if asks_about_ln:
        explain_natural_logarithm()

        if asks_ln_disappears:
            explain_ln_to_y(
                integrated_fx
            )

        return True

    if asks_why_ln:
        explain_why_ln_appears()
        return True

    if asks_ln_disappears:
        explain_ln_to_y(
            integrated_fx
        )
        return True

    return False


def run_separable_guidance(
    rhs: sp.Expr
) -> None:
    """
    Teach the currently generated family:

        dy/dx = f(x) * y

    interactively, one conceptual step at a time.
    """

    fx = sp.simplify(
        rhs / y
    )

    integrated_fx = sp.integrate(
        fx,
        x
    )

    print("\nTutor:")
    print(
        "Let's work through the idea one step at a time "
        "instead of jumping directly to the answer."
    )

    print(
        f"\nWe start with:"
    )

    print(
        f"    dy/dx = {sp.sstr(rhs)}"
    )

    print(
        "\nFirst, look at the right-hand side."
    )

    print(
        "It contains both x and y."
    )

    response = input(
        "\nCan you see that we want to move the y part "
        "away from the x part? "
    ).strip()

    if response.lower() == "quit":
        return

    if answer_means_no(response):
        print("\nTutor:")
        print(
            "That's the main idea behind a separable equation."
        )

        print(
            "We want one side of the equation to contain only y "
            "and the other side to contain only x."
        )

    print("\nTutor:")
    print(
        "Since y is multiplying the right-hand side, "
        "divide by y."
    )

    print(
        "\nThat gives:"
    )

    print(
        f"    (1/y) dy = {sp.sstr(fx)} dx"
    )

    response = input(
        "\nWhy do you think this is useful? "
    ).strip()

    if response.lower() == "quit":
        return

    if not answer_means_yes(response):
        print("\nTutor:")
        print(
            "It is useful because the variables are now separated:"
        )

        print(
            "    left side -> only y"
        )

        print(
            "    right side -> only x"
        )

    print("\nTutor:")
    print(
        "Once the variables are separated, "
        "we integrate both sides."
    )

    print(
        "\n    integral(1/y) dy"
        f" = integral({sp.sstr(fx)}) dx"
    )

    response = input(
        "\nDo you know what the integral of 1/y is? "
    ).strip()

    if response.lower() == "quit":
        return

    normalized = response.lower().replace(" ", "")

    understands_ln = (
        "ln" in normalized
        or "log" in normalized
    )

    if not understands_ln:
        explain_why_ln_appears()

    print("\nTutor:")
    print(
        "So after integrating we obtain:"
    )

    print(
        f"\n    ln|y| = {sp.sstr(integrated_fx)} + C"
    )

    response = input(
        "\nNow we want y by itself. "
        "Do you know what operation undoes ln? "
    ).strip()

    if response.lower() == "quit":
        return

    normalized = response.lower()

    knows_exp = (
        "exp" in normalized
        or "exponent" in normalized
        or "e^" in normalized
        or "power of e" in normalized
    )

    if not knows_exp:
        explain_natural_logarithm()

    explain_ln_to_y(
        integrated_fx
    )

    print("\nTutor:")
    response = input(
        "Does the reason ln disappears now make sense? "
    ).strip()

    if response.lower() == "quit":
        return

    if answer_means_no(response):
        print("\nTutor:")
        print(
            "The key is not that ln disappears automatically."
        )

        print(
            "We deliberately apply exp to both sides."
        )

        print(
            "\nBecause:"
        )

        print(
            "    exp(ln(a)) = a"
        )

        print(
            "\nso:"
        )

        print(
            "    exp(ln|y|) = |y|"
        )

    print("\nTutor:")
    print(
        "Good. Now return to the original ODE and try solving it "
        "again using these steps."
    )

def explain_arbitrary_constant_absorption() -> str:
    return (
        "Let's unpack that carefully.\n\n"
        "We reached:\n\n"
        "    |y| = exp(x**2) * exp(C)\n\n"
        "First, C is arbitrary. That means C can be any real number.\n\n"
        "Because exp(C) is the exponential of an arbitrary real number, "
        "exp(C) can be any positive constant.\n\n"
        "For example:\n"
        "    C = 0       -> exp(C) = 1\n"
        "    C = ln(2)   -> exp(C) = 2\n"
        "    C = ln(10)  -> exp(C) = 10\n\n"
        "So instead of repeatedly writing exp(C), we could rename it K:\n\n"
        "    |y| = K * exp(x**2)\n\n"
        "where K is some positive constant.\n\n"
        "Now consider the absolute value |y|.\n"
        "If |y| = K*exp(x**2), then y could be positive or negative:\n\n"
        "    y = +K*exp(x**2)\n"
        "or\n"
        "    y = -K*exp(x**2)\n\n"
        "We can combine the + or - sign with K into one new arbitrary "
        "constant A:\n\n"
        "    A = +/- K\n\n"
        "So we can write:\n\n"
        "    y = A*exp(x**2)\n\n"
        "The letter used for an arbitrary constant does not matter, so "
        "we normally rename A back to C:\n\n"
        "    y = C*exp(x**2)\n\n"
        "So 'absorbed into a new arbitrary constant' means that several "
        "constant pieces, such as exp(C) and the possible +/- sign, are "
        "combined and represented by one new constant."
    )


def respond_to_stage3_concept_question(
    student_message: str,
) -> str | None:
    message = student_message.lower().strip()

    asks_about_absorbing_constant = (
        "absorb" in message
        or "absorbed" in message
        or "exp(c)" in message
        or "e^c" in message
        or "arbitrary constant" in message
        or (
            "constant" in message
            and "mean" in message
        )
    )

    asks_about_absolute_value = (
        "|y|" in message
        or "absolute value" in message
        or (
            "why" in message
            and "sign" in message
        )
    )

    if asks_about_absorbing_constant:
        return explain_arbitrary_constant_absorption()

    if asks_about_absolute_value:
        return (
            "The absolute value |y| means y may be positive or negative.\n\n"
            "If:\n"
            "    |y| = K*exp(x**2)\n\n"
            "then both of these are possible:\n"
            "    y = +K*exp(x**2)\n"
            "    y = -K*exp(x**2)\n\n"
            "Instead of carrying the +/- sign separately, we allow the "
            "arbitrary constant itself to carry the sign."
        )

    asks_about_denominator = (
        "denominator" in message
        or "denom" in message
        or (
            "where did" in message
            and "2" in message
        )
        or (
            "why" in message
            and "2" in message
        )
    )

    if asks_about_denominator:
        return (
            "The denominator did not disappear.\n\n"
            "If the integrated expression is:\n\n"
            "    x^2/2\n\n"
            "then it stays inside the exponent:\n\n"
            "    exp(x^2/2)\n\n"
            "So after we absorb the arbitrary constant, "
            "the solution has the form:\n\n"
            "    y = K*exp(x^2/2)\n\n"
            "Only if the coefficient simplifies, for example:\n\n"
            "    6*x^2/2 = 3*x^2\n\n"
            "would the denominator disappear through ordinary algebraic "
            "simplification.\n\n"
            "In your current equation, x^2/2 does not simplify further."
        )

    return None