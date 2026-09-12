import re


class MathInputError(ValueError):
    """
    Raised when a mathematical answer cannot be normalized
    safely.
    """


LATEX_COMMANDS = {
    r"\cdot": "*",
    r"\times": "*",
    r"\div": "/",
    r"\left": "",
    r"\right": "",
    r"\middle": "",
    r"\mleft": "",
    r"\mright": "",
    r"\,": "",
    r"\;": "",
    r"\:": "",
    r"\!": "",
    r"\pi": "pi",
    r"\mu": "mu",
    r"\ln": "log",
    r"\log": "log",
    r"\pm": "+/-",
    r"\sin": "sin",
    r"\cos": "cos",
    r"\tan": "tan",
    r"\sqrt": "sqrt",
}

KNOWN_FUNCTIONS = (
    "exp",
    "sqrt",
    "log",
    "sin",
    "cos",
    "tan",
)


def _read_balanced(
    text: str,
    start_index: int,
    opening: str,
    closing: str,
) -> tuple[str, int]:
    if (
        start_index >= len(text)
        or text[start_index] != opening
    ):
        raise MathInputError(
            f"Expected '{opening}' in mathematical input."
        )

    depth = 0

    for index in range(start_index, len(text)):
        character = text[index]

        if character == opening:
            depth += 1

        elif character == closing:
            depth -= 1

            if depth == 0:
                return (
                    text[start_index + 1:index],
                    index + 1,
                )

    raise MathInputError(
        "Unbalanced mathematical grouping."
    )


def _replace_derivative_fraction(
    text: str,
) -> str:
    text = re.sub(
        r"\\frac\s*\{\s*d\s*y\s*\}\s*\{\s*d\s*x\s*\}",
        "yp",
        text,
    )

    text = text.replace(
        "dy/dx",
        "yp",
    )
    text = text.replace(
        "y'",
        "yp",
    )

    return text


def _replace_fractions(
    text: str,
) -> str:
    result = []
    index = 0

    while index < len(text):
        if text.startswith(r"\frac", index):
            numerator, after_numerator = _read_balanced(
                text,
                index + len(r"\frac"),
                "{",
                "}",
            )
            denominator, after_denominator = _read_balanced(
                text,
                after_numerator,
                "{",
                "}",
            )

            result.append(
                "("
                + latex_to_sympy_text(numerator)
                + ")/("
                + latex_to_sympy_text(denominator)
                + ")"
            )
            index = after_denominator
            continue

        result.append(text[index])
        index += 1

    return "".join(result)


def _read_simple_exponent(
    text: str,
    start_index: int,
) -> tuple[str, int]:
    index = start_index

    if index < len(text) and text[index] in "+-":
        index += 1

    while index < len(text) and (
        text[index].isalnum()
        or text[index] in "_\\"
    ):
        index += 1

    if index == start_index:
        raise MathInputError(
            "Missing exponent in mathematical input."
        )

    return text[start_index:index], index


def _replace_exponential_notation(
    text: str,
) -> str:
    result = []
    index = 0

    while index < len(text):
        if text.startswith(r"\exp", index):
            result.append("exp")
            index += len(r"\exp")
            continue

        if (
            text[index] == "e"
            and index + 1 < len(text)
            and text[index + 1] == "^"
        ):
            exponent_start = index + 2

            if exponent_start >= len(text):
                raise MathInputError(
                    "Missing exponent in exponential input."
                )

            if text[exponent_start] == "{":
                exponent, next_index = _read_balanced(
                    text,
                    exponent_start,
                    "{",
                    "}",
                )

            elif text[exponent_start] == "(":
                exponent, next_index = _read_balanced(
                    text,
                    exponent_start,
                    "(",
                    ")",
                )

            else:
                exponent, next_index = _read_simple_exponent(
                    text,
                    exponent_start,
                )

            result.append(
                "exp("
                + latex_to_sympy_text(
                    _normalize_nested_exponent(exponent)
                )
                + ")"
            )
            index = next_index
            continue

        result.append(text[index])
        index += 1

    return "".join(result)


def _normalize_nested_exponent(
    exponent: str,
) -> str:
    """
    MathLive can produce grouped exponents like x^{^2}
    while the editor visually shows x^2. Inside an exponent
    group, a leading caret is a redundant exponent marker.
    """

    stripped = exponent.strip()

    if stripped.startswith("^") and len(stripped) > 1:
        return stripped[1:].strip()

    return exponent


def _replace_grouped_powers(
    text: str,
) -> str:
    result = []
    index = 0

    while index < len(text):
        if (
            text[index] == "^"
            and index + 1 < len(text)
            and text[index + 1] == "{"
        ):
            exponent, next_index = _read_balanced(
                text,
                index + 1,
                "{",
                "}",
            )
            result.append(
                "**("
                + latex_to_sympy_text(
                    _normalize_nested_exponent(exponent)
                )
                + ")"
            )
            index = next_index
            continue

        result.append(text[index])
        index += 1

    return "".join(result)


def _replace_latex_commands(
    text: str,
) -> str:
    for latex_command, replacement in LATEX_COMMANDS.items():
        text = text.replace(
            latex_command,
            replacement,
        )

    return text


def _replace_named_operator_commands(
    text: str,
) -> str:
    """
    MathLive may emit named functions as \operatorname{exp}
    or \mathrm{exp}. Convert only known math functions into
    the same command path handled by the rest of the parser.
    """

    return re.sub(
        (
            r"\\(?:operatorname|mathrm)\s*\{\s*"
            r"(exp|ln|log|sqrt|sin|cos|tan)"
            r"\s*\}"
        ),
        lambda match: "\\" + match.group(1),
        text,
    )


def _replace_absolute_value_delimiters(
    text: str,
) -> str:
    """
    Normalize common paired LaTeX absolute-value delimiters
    without treating every vertical bar as absolute value.
    Existing separable ODE checkers already understand |y|.
    """

    delimiter_patterns = [
        (
            r"\\left\s*\\lvert\s*(?P<body>[^=|]+?)\s*\\right\s*\\rvert",
            r"|\g<body>|",
        ),
        (
            r"\\left\s*\\vert\s*(?P<body>[^=|]+?)\s*\\right\s*\\vert",
            r"|\g<body>|",
        ),
        (
            r"\\lvert\s*(?P<body>[^=|]+?)\s*\\rvert",
            r"|\g<body>|",
        ),
        (
            r"\\vert\s*(?P<body>[^=|]+?)\s*\\vert",
            r"|\g<body>|",
        ),
        (
            r"\\left\s*\|\s*(?P<body>[^=|]+?)\s*\\right\s*\|",
            r"|\g<body>|",
        ),
    ]

    for pattern, replacement in delimiter_patterns:
        text = re.sub(
            pattern,
            replacement,
            text,
        )

    return text


def _replace_log_absolute_value_notation(
    text: str,
) -> str:
    text = re.sub(
        r"\b(?:log|ln)\s*\(\s*\|\s*([^|]+?)\s*\|\s*\)",
        lambda match: (
            "log(Abs("
            + latex_to_sympy_text(match.group(1))
            + "))"
        ),
        text,
    )
    text = re.sub(
        r"\b(?:log|ln)\s*\|\s*([^|]+?)\s*\|",
        lambda match: (
            "log(Abs("
            + latex_to_sympy_text(match.group(1))
            + "))"
        ),
        text,
    )

    return text


def _insert_implicit_multiplication(
    text: str,
) -> str:
    function_pattern = (
        "|".join(KNOWN_FUNCTIONS)
    )

    text = re.sub(
        rf"\b({function_pattern})\s+\(",
        r"\1(",
        text,
    )

    text = re.sub(
        rf"(?<=[0-9xyCK)])\s+(?=(?:{function_pattern})\()",
        "*",
        text,
    )
    text = re.sub(
        r"(?<=[0-9xyCK)])\s+(?=[0-9xyCK(])",
        "*",
        text,
    )
    text = re.sub(
        r"(?<=[0-9)])(?=[A-Za-z])",
        "*",
        text,
    )
    text = re.sub(
        r"(?<=[xyCK])(?=[xyCK])",
        "*",
        text,
    )
    text = re.sub(
        rf"(?<=[xyCK])(?=(?:{function_pattern})\()",
        "*",
        text,
    )
    text = re.sub(
        r"(?<!/dx)(?<=[xyCK])(?=\()",
        "*",
        text,
    )

    return text


def _validate_balanced_delimiters(
    text: str,
) -> None:
    pairs = {
        ")": "(",
        "}": "{",
        "]": "[",
    }
    stack = []

    for character in text:
        if character in "({[":
            stack.append(character)

        elif character in pairs:
            if not stack or stack[-1] != pairs[character]:
                raise MathInputError(
                    "Unbalanced mathematical grouping."
                )

            stack.pop()

    if stack:
        raise MathInputError(
            "Unbalanced mathematical grouping."
        )


def latex_to_sympy_text(
    text: str,
) -> str:
    """
    Convert a small, safe subset of LaTeX/MathLive output
    into text that SymPy's parser can consume.
    """

    text = text.strip()

    if not text:
        raise MathInputError(
            "Empty mathematical input."
        )

    text = text.strip("$")
    _validate_balanced_delimiters(text)

    text = _replace_named_operator_commands(text)
    text = _replace_absolute_value_delimiters(text)
    text = _replace_derivative_fraction(text)
    text = _replace_fractions(text)
    text = _replace_exponential_notation(text)
    text = _replace_grouped_powers(text)
    text = _replace_latex_commands(text)

    text = text.replace("^", "**")
    text = text.replace("{", "(")
    text = text.replace("}", ")")
    text = _replace_log_absolute_value_notation(text)
    text = _insert_implicit_multiplication(text)

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text
