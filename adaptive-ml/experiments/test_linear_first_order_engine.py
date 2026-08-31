import sympy as sp

from src.core.tutor_engine.linear_first_order_engine import (
    LinearFirstOrderEngine,
)

from src.core.tutor_engine.linear_first_order_session import (
    LinearODEStage,
)


x = sp.symbols("x")


#
# Running example:
#
# y' + 2*x*y = x
#
engine = LinearFirstOrderEngine(
    p_expression=2 * x,
    q_expression=x,
)


print(
    "\n--- Derived mathematics ---"
)

print(
    "P(x):",
    engine.p_expression,
)

print(
    "Q(x):",
    engine.q_expression,
)

print(
    "Integral P:",
    engine.get_integrated_p(),
)

print(
    "mu(x):",
    engine.get_integrating_factor(),
)

print(
    "mu(x)Q(x):",
    engine.get_integrand(),
)

print(
    "Integral mu*Q:",
    engine.get_antiderivative(),
)

print(
    "General solution:",
    engine.get_general_solution(),
)


#
# Stage 1
#
print(
    "\n--- Stage 1 ---"
)

result = engine.evaluate(
    stage=LinearODEStage.IDENTIFY_STANDARD_FORM,
    student_answer="yes",
)

print(result)


#
# Stage 2
#
print(
    "\n--- Stage 2 ---"
)

result = engine.evaluate(
    stage=LinearODEStage.IDENTIFY_P_Q,
    student_p="2x",
    student_q="x",
)

print(result)


#
# Stage 3
#
print(
    "\n--- Stage 3 ---"
)

result = engine.evaluate(
    stage=LinearODEStage.FIND_INTEGRATING_FACTOR,
    student_answer="exp(x**2)",
)

print(result)


#
# Stage 4
#
print(
    "\n--- Stage 4 ---"
)

result = engine.evaluate(
    stage=(
        LinearODEStage
        .MULTIPLY_BY_INTEGRATING_FACTOR
    ),
    student_answer=(
        "exp(x**2)*y' "
        "+ 2*x*exp(x**2)*y "
        "= x*exp(x**2)"
    ),
)

print(result)


#
# Stage 5
#
print(
    "\n--- Stage 5 ---"
)

result = engine.evaluate(
    stage=(
        LinearODEStage
        .RECOGNIZE_PRODUCT_DERIVATIVE
    ),
    student_answer=(
        "d/dx(exp(x**2)*y) "
        "= x*exp(x**2)"
    ),
)

print(result)


#
# Stage 6
#
print(
    "\n--- Stage 6 ---"
)

result = engine.evaluate(
    stage=LinearODEStage.INTEGRATE_BOTH_SIDES,
    student_answer=(
        "exp(x**2)*y "
        "= exp(x**2)/2 + C"
    ),
)

print(result)


#
# Stage 7
#
print(
    "\n--- Stage 7 ---"
)

result = engine.evaluate(
    stage=LinearODEStage.SOLVE_FOR_Y,
    student_answer=(
        "y = 1/2 + C*exp(-x**2)"
    ),
)

print(result)