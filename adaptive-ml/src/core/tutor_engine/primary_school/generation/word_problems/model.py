from dataclasses import dataclass
from collections.abc import Callable


FAMILY_SEVERAL = "several_operations"
FAMILY_COMPARISON = "comparison"
FAMILY_REVERSE = "reverse"

SUPPORTED_FAMILIES = (
    FAMILY_SEVERAL,
    FAMILY_COMPARISON,
    FAMILY_REVERSE,
)

OP_ADD = "add"
OP_SUB = "sub"
OP_MUL = "mul"
OP_DOUBLE = "double"

SUPPORTED_OPS = (OP_ADD, OP_SUB, OP_MUL, OP_DOUBLE)


@dataclass(frozen=True)
class Relation:
    op: str
    inputs: tuple[str, ...]
    output: str


@dataclass(frozen=True)
class TemplateSemantics:
    en_required: tuple[str, ...]
    bg_required: tuple[str, ...]
    en_forbidden: tuple[str, ...]
    bg_forbidden: tuple[str, ...]
    larger_id: str | None = None
    smaller_id: str | None = None
    double_input: str | None = None
    double_output: str | None = None
    meaning: str = ""


@dataclass(frozen=True)
class StoryTemplate:
    template_id: str
    family: str
    difficulty: int
    relations: tuple[Relation, ...]
    ask: str
    identify_known: str
    hidden: tuple[str, ...]
    statement_ids: tuple[str, ...]
    sampler: Callable
    semantics: TemplateSemantics

    @property
    def relation_count(self) -> int:
        return len(self.relations)

    @property
    def statement_key(self) -> str:
        return f"gen.story.{self.template_id}.statement"
