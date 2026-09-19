from dataclasses import dataclass


_ADD_PREC = 1
_MUL_PREC = 2
_LEAF_PREC = 3
_OP_SYMBOL = {
    "+": "+",
    "-": "-",
    "*": "×",
}


@dataclass(frozen=True)
class ArithmeticExpr:
    op: str | None
    value: int | None = None
    left: "ArithmeticExpr | None" = None
    right: "ArithmeticExpr | None" = None

    def evaluate(self) -> int:
        if self.op is None:
            if self.value is None:
                raise ValueError("Leaf is missing a value.")
            return self.value
        if self.left is None or self.right is None:
            raise ValueError("Operator is missing a child.")
        left = self.left.evaluate()
        right = self.right.evaluate()
        if self.op == "+":
            return left + right
        if self.op == "-":
            return left - right
        if self.op == "*":
            return left * right
        raise ValueError(f"Unsupported operator: {self.op}")

    def render(self) -> str:
        return self._render(parent_prec=0, is_right=False)

    def values(self) -> list[int]:
        if self.op is None:
            return [self.value or 0]
        return self.left.values() + self.right.values()

    def intermediates(self) -> list[int]:
        found: list[int] = []
        if self.op is None:
            return found
        found.extend(self.left.intermediates())
        found.extend(self.right.intermediates())
        found.append(self.evaluate())
        return found

    def to_dict(self) -> dict:
        if self.op is None:
            return {"op": None, "value": self.value}
        return {
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }

    def _prec(self) -> int:
        if self.op is None:
            return _LEAF_PREC
        if self.op == "*":
            return _MUL_PREC
        return _ADD_PREC

    def _render(self, parent_prec: int, is_right: bool) -> str:
        if self.op is None:
            return str(self.value)

        prec = self._prec()
        left = self.left._render(prec, False)
        right = self.right._render(prec, True)
        text = f"{left} {_OP_SYMBOL[self.op]} {right}"
        needs_paren = prec < parent_prec
        if (
            is_right
            and prec == parent_prec
            and self.op == "-"
        ):
            needs_paren = True
        if needs_paren:
            return f"({text})"
        return text


def leaf(value: int) -> ArithmeticExpr:
    return ArithmeticExpr(op=None, value=value)


def combine(
    op: str,
    left: ArithmeticExpr,
    right: ArithmeticExpr,
) -> ArithmeticExpr:
    return ArithmeticExpr(
        op=op,
        left=left,
        right=right,
    )


def expr_from_dict(data: dict) -> ArithmeticExpr:
    if data.get("op") is None:
        return leaf(int(data["value"]))
    return combine(
        data["op"],
        expr_from_dict(data["left"]),
        expr_from_dict(data["right"]),
    )
