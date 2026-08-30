import sympy as sp

from src.core.tutor_engine.separable_verification_engine import (
    SeparableVerificationEngine,
)


x = sp.symbols("x")
y = sp.symbols("y")
C = sp.symbols("C")


rhs_expression = (
    -5 * x * y
)

solution_expression = (
    C * sp.exp(
        -5 * x**2 / 2
    )
)


engine = SeparableVerificationEngine(
    rhs_expression=rhs_expression,
    solution_expression=solution_expression,
)


print(
    "\n" + engine.get_title()
)

print(
    engine.get_prompt()
)

result = engine.evaluate(
    "dy/dx = -5*x*C*exp(-5*x**2/2)"
)

print(
    "\nCorrect:",
    result["correct"],
)

print(
    "Feedback:",
    result["feedback"],
)


print(
    "\n" + engine.get_title()
)

print(
    engine.get_prompt()
)

result = engine.evaluate(
    "-5*x*C*exp(-5*x**2/2)"
)

print(
    "\nCorrect:",
    result["correct"],
)

print(
    "Feedback:",
    result["feedback"],
)


print(
    "\n" + engine.get_title()
)

print(
    engine.get_prompt()
)

result = engine.evaluate(
    "yes"
)

print(
    "\nCorrect:",
    result["correct"],
)

print(
    "Feedback:",
    result["feedback"],
)

print(
    "\nComplete:",
    engine.is_complete(),
)