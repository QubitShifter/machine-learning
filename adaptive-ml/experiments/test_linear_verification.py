import sympy as sp

from src.core.tutor_engine.linear_first_order_verification import (
    LinearFirstOrderVerificationEngine,
)


x = sp.symbols("x")
C = sp.symbols("C")


# Original ODE:
#
# y' + 2*x*y = x
#
# Proposed solution:
#
# y = 1/2 + C*exp(-x**2)

engine = LinearFirstOrderVerificationEngine(
    p_expression=2 * x,
    q_expression=x,
    solution_expression=(
        sp.Rational(1, 2)
        + C * sp.exp(-x**2)
    ),
)


print(
    "Expected derivative:",
    engine.get_expected_derivative(),
)

print(
    "Expected substituted LHS:",
    engine.get_expected_lhs(),
)


print(
    "\n--- Step 8.1 ---"
)

result = engine.evaluate(
    "-2*x*C*exp(-x**2)"
)

print(result)

if result["correct"]:
    engine.advance()


print(
    "\n--- Step 8.2 ---"
)

result = engine.evaluate(
    "x"
)

print(result)

if result["correct"]:
    engine.advance()


print(
    "\n--- Step 8.3 ---"
)

result = engine.evaluate(
    "they match"
)

print(result)

if result["correct"]:
    engine.advance()


print(
    "\nComplete:",
    engine.is_complete()
)