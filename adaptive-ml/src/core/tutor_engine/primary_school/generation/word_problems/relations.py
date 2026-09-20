from src.core.tutor_engine.primary_school.generation.word_problems.model import (
    OP_ADD,
    OP_DOUBLE,
    OP_MUL,
    OP_SUB,
    Relation,
)


def apply_relation(
    relation: Relation,
    quantities: dict[str, int],
) -> int:
    values = [
        _require_quantity(quantities, name)
        for name in relation.inputs
    ]
    if relation.op == OP_ADD:
        if len(values) != 2:
            raise ValueError("Addition needs two inputs.")
        return values[0] + values[1]
    if relation.op == OP_SUB:
        if len(values) != 2:
            raise ValueError("Subtraction needs two inputs.")
        result = values[0] - values[1]
        if result <= 0:
            raise ValueError("Subtraction is not positive.")
        return result
    if relation.op == OP_MUL:
        if len(values) != 2:
            raise ValueError("Multiplication needs two inputs.")
        if values[0] <= 0 or values[1] <= 0:
            raise ValueError("Multiplication factors must be positive.")
        return values[0] * values[1]
    if relation.op == OP_DOUBLE:
        if len(values) != 1:
            raise ValueError("Doubling needs one input.")
        return values[0] * 2
    raise ValueError(f"Unsupported relation op: {relation.op}")


def undo_relation(
    relation: Relation,
    quantities: dict[str, int],
) -> tuple[str, int]:
    unknown_inputs = [
        name
        for name in relation.inputs
        if name not in quantities
    ]
    if len(unknown_inputs) != 1:
        raise ValueError(
            "Reverse step must recover exactly one input."
        )
    unknown = unknown_inputs[0]
    output = _require_quantity(quantities, relation.output)
    recovered = _undo_value(relation, unknown, output, quantities)
    return unknown, recovered


def render_forward_operation(
    relation: Relation,
    quantities: dict[str, int],
) -> str:
    values = [
        _require_quantity(quantities, name)
        for name in relation.inputs
    ]
    if relation.op == OP_ADD:
        return f"{values[0]} + {values[1]}"
    if relation.op == OP_SUB:
        return f"{values[0]} - {values[1]}"
    if relation.op == OP_MUL:
        return f"{values[0]} × {values[1]}"
    if relation.op == OP_DOUBLE:
        return f"{values[0]} × 2"
    raise ValueError(f"Unsupported relation op: {relation.op}")


def render_undo_operation(
    relation: Relation,
    unknown: str,
    quantities: dict[str, int],
) -> str:
    output = _require_quantity(quantities, relation.output)
    if relation.op == OP_ADD:
        other = _other_input(relation, unknown)
        return (
            f"{output} - {_require_quantity(quantities, other)}"
        )
    if relation.op == OP_SUB:
        if unknown != relation.inputs[0]:
            raise ValueError("Can only recover the minuend.")
        other = relation.inputs[1]
        return (
            f"{output} + {_require_quantity(quantities, other)}"
        )
    if relation.op == OP_MUL:
        other = _other_input(relation, unknown)
        factor = _require_quantity(quantities, other)
        return f"{output} ÷ {factor}"
    if relation.op == OP_DOUBLE:
        return f"{output} ÷ 2"
    raise ValueError(f"Unsupported relation op: {relation.op}")


def evaluate_quantities(
    relations: tuple[Relation, ...] | list[Relation],
    slots: dict[str, int],
) -> dict[str, int]:
    quantities = dict(slots)
    for relation in relations:
        if relation.output in quantities:
            raise ValueError(
                f"Quantity {relation.output} is already set."
            )
        quantities[relation.output] = apply_relation(
            relation,
            quantities,
        )
    return quantities


def recover_hidden(
    relations: tuple[Relation, ...] | list[Relation],
    known: dict[str, int],
) -> dict[str, int]:
    quantities = dict(known)
    for relation in reversed(list(relations)):
        unknown, value = undo_relation(relation, quantities)
        quantities[unknown] = value
    return quantities


def _undo_value(
    relation: Relation,
    unknown: str,
    output: int,
    quantities: dict[str, int],
) -> int:
    if relation.op == OP_ADD:
        other = _other_input(relation, unknown)
        result = output - _require_quantity(quantities, other)
        if result <= 0:
            raise ValueError("Undoing addition is not positive.")
        return result
    if relation.op == OP_SUB:
        if unknown != relation.inputs[0]:
            raise ValueError("Can only recover the minuend.")
        other = relation.inputs[1]
        return output + _require_quantity(quantities, other)
    if relation.op == OP_MUL:
        other = _other_input(relation, unknown)
        factor = _require_quantity(quantities, other)
        if factor <= 0 or output % factor != 0:
            raise ValueError("Undoing multiplication is not exact.")
        result = output // factor
        if result <= 0:
            raise ValueError("Undoing multiplication is not positive.")
        return result
    if relation.op == OP_DOUBLE:
        if output % 2 != 0:
            raise ValueError("Undoing doubling is not exact.")
        result = output // 2
        if result <= 0:
            raise ValueError("Undoing doubling is not positive.")
        return result
    raise ValueError(f"Unsupported relation op: {relation.op}")


def _other_input(relation: Relation, unknown: str) -> str:
    others = [name for name in relation.inputs if name != unknown]
    if len(others) != 1:
        raise ValueError("Expected exactly one known input.")
    return others[0]


def _require_quantity(quantities: dict[str, int], name: str) -> int:
    if name not in quantities:
        raise ValueError(f"Missing quantity: {name}")
    value = quantities[name]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Quantity {name} is not an integer.")
    return value
