def ask_for_difficulty() -> str:
    print(
        "\nBefore we continue, tell me what part "
        "you find difficult to understand."
    )

    return input("What is unclear? ").strip()


def student_says_everything_is_clear(student_message: str) -> bool:
    message = student_message.lower().strip()

    clear_phrases = [
        "everything is clear",
        "all clear",
        "it is clear",
        "it's clear",
        "i understand",
        "i understand now",
        "i got it",
        "got it",
        "makes sense",
        "that makes sense",
        "nothing",
        "nothing is unclear",
        "no questions",
        "no question",
        "no problem",
        "im good",
        "i'm good",
    ]

    return any(
        phrase in message
        for phrase in clear_phrases
    )


def respond_to_difficulty(student_message: str) -> str:
    message = student_message.lower()

    if student_says_everything_is_clear(student_message):
        return (
            "Good. Let's continue with the same problem "
            "so you can apply the idea."
        )

    mentions_integrate = (
        "integrat" in message
        or "integration" in message
    )

    mentions_differentiate = (
        "differentiat" in message
        or "derivative" in message
    )

    mentions_constant = (
        "constant" in message
        or "variable" in message
    )

    mentions_indefinite = (
        "indefinite" in message
        and "integral" in message
    )

    if mentions_indefinite:
        return (
            "You know this requires an indefinite integral because "
            "the equation gives you the derivative of y and asks you "
            "to recover y.\n\n"
            "For example:\n"
            "    dy/dx = -4*x**3\n\n"
            "The left side dy/dx means the derivative of y "
            "with respect to x.\n\n"
            "To recover y, reverse differentiation:\n"
            "    y = integral(-4*x**3) dx\n\n"
            "There are no lower and upper integration bounds, "
            "so this is an indefinite integral.\n\n"
            "That means we are finding a family of functions, "
            "which is why we include + C."
        )

    if (
        mentions_integrate
        and mentions_differentiate
        and mentions_constant
    ):
        return (
            "There are two separate ideas here.\n\n"
            "To choose the operation:\n"
            "    given y -> differentiate -> dy/dx\n"
            "    given dy/dx -> integrate -> y\n\n"
            "To identify the variable, look at the differential.\n"
            "If we integrate with dx, x is the variable.\n\n"
            "Numbers such as 6 are constant coefficients."
        )

    if mentions_integrate and mentions_differentiate:
        return (
            "Think about which direction you are going.\n\n"
            "    y -> differentiate -> dy/dx\n"
            "    dy/dx -> integrate -> y\n\n"
            "If dy/dx is given and you need y, integration "
            "reverses the differentiation."
        )

    if mentions_constant:
        return (
            "Look at the variable with respect to which the operation "
            "is performed.\n\n"
            "For example:\n"
            "    integral(6*x**5) dx\n\n"
            "The dx tells us x is the variable. "
            "The number 6 is a constant coefficient."
        )

    if mentions_integrate:
        return (
            "Integration is used when you want to recover a function "
            "from its derivative.\n\n"
            "For example:\n"
            "    dy/dx = 4*x**3\n\n"
            "To recover y:\n"
            "    y = integral(4*x**3) dx\n"
            "    y = x**4 + C"
        )

    if mentions_differentiate:
        return (
            "Differentiation starts with a function and finds "
            "its derivative.\n\n"
            "For example:\n"
            "    y = x**4\n"
            "    dy/dx = 4*x**3\n\n"
            "Integration goes in the opposite direction."
        )

    return (
        "I did not identify the exact concept you are asking about yet.\n\n"
        "You can describe what is confusing in your own words, "
        "or simply say that everything is clear."
    )