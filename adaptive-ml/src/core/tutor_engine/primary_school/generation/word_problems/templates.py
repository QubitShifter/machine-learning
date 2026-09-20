import random

from src.core.tutor_engine.primary_school.generation.word_problems.model import (
    FAMILY_COMPARISON,
    FAMILY_REVERSE,
    FAMILY_SEVERAL,
    OP_ADD,
    OP_DOUBLE,
    OP_MUL,
    OP_SUB,
    Relation,
    StoryTemplate,
    TemplateSemantics,
)


FORBIDDEN_GLOBAL_EN = (
    "twice as many as remained were put in",
    "twice as many as remained were added",
    "put in twice as many as remained",
)

FORBIDDEN_GLOBAL_BG = (
    "два пъти повече от останалите бяха сложени",
    "сложили два пъти повече от останалите",
    "два пъти повече от останалите бутилки",
)


def _require_distinct_positive(
    values: dict[str, int],
    maximum: int,
) -> dict[str, int]:
    seen: set[int] = set()
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} is not an integer.")
        if value <= 0:
            raise ValueError(f"{name} must be positive.")
        if value > maximum:
            raise ValueError(f"{name} exceeds bounds.")
        if value in seen:
            raise ValueError("Sampled values are not unique.")
        seen.add(value)
    return values


def sample_cards_total(rng: random.Random) -> dict[str, int]:
    red = rng.randint(3, 12)
    blue = rng.randint(3, 12)
    return _require_distinct_positive(
        {"red": red, "blue": blue},
        maximum=24,
    )


def sample_stamps_then_stickers(
    rng: random.Random,
) -> dict[str, int]:
    stamps = rng.randint(4, 12)
    more = rng.randint(2, 8)
    times = rng.choice((2, 3))
    return _require_distinct_positive(
        {
            "stamps": stamps,
            "more": more,
            "times": times,
        },
        maximum=20,
    )


def sample_boxes_then_stickers(
    rng: random.Random,
) -> dict[str, int]:
    boxes = rng.randint(2, 5)
    each = rng.randint(3, 8)
    more = rng.randint(2, 7)
    times = rng.choice((2, 3))
    return _require_distinct_positive(
        {
            "boxes": boxes,
            "each": each,
            "more": more,
            "times": times,
        },
        maximum=20,
    )


def sample_more_than(rng: random.Random) -> dict[str, int]:
    base = rng.randint(4, 14)
    extra = rng.randint(2, 8)
    return _require_distinct_positive(
        {"base": base, "extra": extra},
        maximum=20,
    )


def sample_fewer_than(rng: random.Random) -> dict[str, int]:
    extra = rng.randint(2, 8)
    leo = rng.randint(3, 12)
    if leo == extra:
        raise ValueError("Leo would equal the visible extra amount.")
    base = leo + extra
    return _require_distinct_positive(
        {"base": base, "fewer": extra},
        maximum=24,
    )


def sample_twice_as_many(rng: random.Random) -> dict[str, int]:
    base = rng.randint(3, 12)
    return _require_distinct_positive(
        {"base": base},
        maximum=20,
    )


def sample_more_then_together(
    rng: random.Random,
) -> dict[str, int]:
    base = rng.randint(4, 12)
    extra = rng.randint(2, 7)
    return _require_distinct_positive(
        {"base": base, "extra": extra},
        maximum=20,
    )


def sample_books_from_class(rng: random.Random) -> dict[str, int]:
    girls = rng.randint(4, 10)
    extra = rng.randint(2, 6)
    return _require_distinct_positive(
        {"girls": girls, "extra": extra},
        maximum=16,
    )


def sample_remaining_after_taken(
    rng: random.Random,
) -> dict[str, int]:
    taken = rng.randint(2, 8)
    remaining = rng.randint(3, 12)
    start = remaining + taken
    return _require_distinct_positive(
        {"start": start, "taken": taken},
        maximum=24,
    )


def sample_removed_then_doubled(
    rng: random.Random,
) -> dict[str, int]:
    taken = rng.randint(2, 8)
    remaining = rng.randint(4, 12)
    start = remaining + taken
    return _require_distinct_positive(
        {"start": start, "taken": taken},
        maximum=30,
    )


def sample_removed_doubled_then_added(
    rng: random.Random,
) -> dict[str, int]:
    taken = rng.randint(2, 7)
    remaining = rng.randint(4, 10)
    added = rng.randint(2, 8)
    start = remaining + taken
    return _require_distinct_positive(
        {
            "start": start,
            "taken": taken,
            "added": added,
        },
        maximum=30,
    )


STORY_TEMPLATES: tuple[StoryTemplate, ...] = (
    StoryTemplate(
        template_id="cards_total",
        family=FAMILY_SEVERAL,
        difficulty=1,
        relations=(
            Relation(OP_ADD, ("red", "blue"), "total"),
        ),
        ask="total",
        identify_known="red",
        hidden=(),
        statement_ids=("red", "blue"),
        sampler=sample_cards_total,
        semantics=TemplateSemantics(
            en_required=("in all",),
            bg_required=("общо",),
            en_forbidden=("more than", "twice"),
            bg_forbidden=("повече от", "два пъти"),
            meaning=(
                "total = red + blue. "
                "The story asks for the combined count."
            ),
        ),
    ),
    StoryTemplate(
        template_id="stamps_then_stickers",
        family=FAMILY_SEVERAL,
        difficulty=2,
        relations=(
            Relation(OP_ADD, ("stamps", "more"), "stamps_now"),
            Relation(OP_MUL, ("times", "stamps_now"), "stickers"),
        ),
        ask="stickers",
        identify_known="stamps",
        hidden=(),
        statement_ids=("stamps", "more", "times"),
        sampler=sample_stamps_then_stickers,
        semantics=TemplateSemantics(
            en_required=("times as many stickers as",),
            bg_required=("пъти толкова лепенки, колкото",),
            en_forbidden=("times more stickers",),
            bg_forbidden=("пъти повече лепенки",),
            meaning=(
                "stamps_now = stamps + more. "
                "stickers = times × stamps_now. "
                "'times as many' is multiplication, not addition."
            ),
        ),
    ),
    StoryTemplate(
        template_id="boxes_then_stickers",
        family=FAMILY_SEVERAL,
        difficulty=3,
        relations=(
            Relation(OP_MUL, ("boxes", "each"), "boxed"),
            Relation(OP_ADD, ("boxed", "more"), "stamps_now"),
            Relation(OP_MUL, ("times", "stamps_now"), "stickers"),
        ),
        ask="stickers",
        identify_known="each",
        hidden=(),
        statement_ids=("boxes", "each", "more", "times"),
        sampler=sample_boxes_then_stickers,
        semantics=TemplateSemantics(
            en_required=(
                "in each box",
                "times as many stickers as",
            ),
            bg_required=(
                "в кутия",
                "пъти толкова лепенки, колкото",
            ),
            en_forbidden=("times more stickers",),
            bg_forbidden=("пъти повече лепенки",),
            meaning=(
                "boxed = boxes × each. "
                "stamps_now = boxed + more. "
                "stickers = times × stamps_now."
            ),
        ),
    ),
    StoryTemplate(
        template_id="more_than",
        family=FAMILY_COMPARISON,
        difficulty=1,
        relations=(
            Relation(OP_ADD, ("base", "extra"), "nina"),
        ),
        ask="nina",
        identify_known="base",
        hidden=(),
        statement_ids=("base", "extra"),
        sampler=sample_more_than,
        semantics=TemplateSemantics(
            en_required=("more than leo",),
            bg_required=("повече топчета от лео",),
            en_forbidden=("fewer", "less than", "twice"),
            bg_forbidden=("по-малко", "два пъти"),
            larger_id="nina",
            smaller_id="base",
            meaning=(
                "nina = base + extra. "
                "'N more than Leo' makes Nina larger."
            ),
        ),
    ),
    StoryTemplate(
        template_id="fewer_than",
        family=FAMILY_COMPARISON,
        difficulty=1,
        relations=(
            Relation(OP_SUB, ("base", "fewer"), "leo"),
        ),
        ask="leo",
        identify_known="base",
        hidden=(),
        statement_ids=("base", "fewer"),
        sampler=sample_fewer_than,
        semantics=TemplateSemantics(
            en_required=("fewer than nina",),
            bg_required=("по-малко топчета от нина",),
            en_forbidden=("more than", "twice"),
            bg_forbidden=("повече топчета от нина", "два пъти"),
            larger_id="base",
            smaller_id="leo",
            meaning=(
                "leo = base - fewer. "
                "'N fewer than Nina' makes Leo smaller."
            ),
        ),
    ),
    StoryTemplate(
        template_id="twice_as_many",
        family=FAMILY_COMPARISON,
        difficulty=1,
        relations=(
            Relation(OP_DOUBLE, ("base",), "nina"),
        ),
        ask="nina",
        identify_known="base",
        hidden=(),
        statement_ids=("base",),
        sampler=sample_twice_as_many,
        semantics=TemplateSemantics(
            en_required=("twice as many marbles as leo",),
            bg_required=("два пъти толкова топчета, колкото лео",),
            en_forbidden=("two more", "twice more"),
            bg_forbidden=("два пъти повече", "с 2 повече"),
            larger_id="nina",
            smaller_id="base",
            double_input="base",
            double_output="nina",
            meaning=(
                "nina = 2 × base. "
                "'Twice as many' is doubling, not +2."
            ),
        ),
    ),
    StoryTemplate(
        template_id="more_then_together",
        family=FAMILY_COMPARISON,
        difficulty=2,
        relations=(
            Relation(OP_ADD, ("base", "extra"), "nina"),
            Relation(OP_ADD, ("base", "nina"), "total"),
        ),
        ask="total",
        identify_known="base",
        hidden=(),
        statement_ids=("base", "extra"),
        sampler=sample_more_then_together,
        semantics=TemplateSemantics(
            en_required=("more than leo", "together"),
            bg_required=("повече от лео", "заедно"),
            en_forbidden=("fewer", "twice"),
            bg_forbidden=("по-малко", "два пъти"),
            larger_id="nina",
            smaller_id="base",
            meaning=(
                "nina = base + extra. "
                "total = base + nina."
            ),
        ),
    ),
    StoryTemplate(
        template_id="books_from_class",
        family=FAMILY_COMPARISON,
        difficulty=3,
        relations=(
            Relation(OP_ADD, ("girls", "extra"), "boys"),
            Relation(OP_ADD, ("girls", "boys"), "children"),
            Relation(OP_DOUBLE, ("children",), "books"),
        ),
        ask="books",
        identify_known="girls",
        hidden=(),
        statement_ids=("girls", "extra"),
        sampler=sample_books_from_class,
        semantics=TemplateSemantics(
            en_required=(
                "more boys than girls",
                "twice as many books as children",
            ),
            bg_required=(
                "с {extra} повече от момичетата",
                "два пъти толкова, колкото са децата",
            ),
            en_forbidden=("fewer boys", "two more books"),
            bg_forbidden=(
                "по-малко момчета",
                "два пъти повече книги",
            ),
            larger_id="boys",
            smaller_id="girls",
            double_input="children",
            double_output="books",
            meaning=(
                "boys = girls + extra. "
                "children = girls + boys. "
                "books = 2 × children. "
                "'More boys than girls' makes boys larger. "
                "'Twice as many books as children' doubles children."
            ),
        ),
    ),
    StoryTemplate(
        template_id="remaining_after_taken",
        family=FAMILY_REVERSE,
        difficulty=1,
        relations=(
            Relation(OP_SUB, ("start", "taken"), "remaining"),
        ),
        ask="start",
        identify_known="remaining",
        hidden=("start",),
        statement_ids=("taken", "remaining"),
        sampler=sample_remaining_after_taken,
        semantics=TemplateSemantics(
            en_required=(
                "were taken out",
                "were left",
                "at the start",
            ),
            bg_required=("извадили", "останали", "в началото"),
            en_forbidden=("doubled", "twice"),
            bg_forbidden=("удвоен", "два пъти"),
            meaning=(
                "remaining = start - taken. "
                "The story gives remaining and asks for start, "
                "so add the taken bottles back."
            ),
        ),
    ),
    StoryTemplate(
        template_id="removed_then_doubled",
        family=FAMILY_REVERSE,
        difficulty=2,
        relations=(
            Relation(OP_SUB, ("start", "taken"), "remaining"),
            Relation(OP_DOUBLE, ("remaining",), "final"),
        ),
        ask="start",
        identify_known="final",
        hidden=("start",),
        statement_ids=("taken", "final"),
        sampler=sample_removed_then_doubled,
        semantics=TemplateSemantics(
            en_required=(
                "were taken out",
                "the number of remaining bottles was doubled",
                "at the start",
            ),
            bg_required=(
                "извадили",
                "броят на останалите бутилки бил удвоен",
                "в началото",
            ),
            en_forbidden=FORBIDDEN_GLOBAL_EN,
            bg_forbidden=FORBIDDEN_GLOBAL_BG,
            double_input="remaining",
            double_output="final",
            meaning=(
                "remaining = start - taken. "
                "final = remaining × 2. "
                "'Was doubled' multiplies the remainder by 2; "
                "it does not add twice the remainder."
            ),
        ),
    ),
    StoryTemplate(
        template_id="removed_doubled_then_added",
        family=FAMILY_REVERSE,
        difficulty=3,
        relations=(
            Relation(OP_SUB, ("start", "taken"), "remaining"),
            Relation(OP_DOUBLE, ("remaining",), "doubled"),
            Relation(OP_ADD, ("doubled", "added"), "final"),
        ),
        ask="start",
        identify_known="final",
        hidden=("start",),
        statement_ids=("taken", "added", "final"),
        sampler=sample_removed_doubled_then_added,
        semantics=TemplateSemantics(
            en_required=(
                "were taken out",
                "the number of remaining bottles was doubled",
                "more bottles were put in",
                "at the start",
            ),
            bg_required=(
                "извадили",
                "броят на останалите бутилки бил удвоен",
                "сложили още",
                "в началото",
            ),
            en_forbidden=FORBIDDEN_GLOBAL_EN,
            bg_forbidden=FORBIDDEN_GLOBAL_BG,
            double_input="remaining",
            double_output="doubled",
            meaning=(
                "remaining = start - taken. "
                "doubled = remaining × 2. "
                "final = doubled + added. "
                "'Was doubled' multiplies the remainder by 2, "
                "then a later addition puts more bottles in."
            ),
        ),
    ),
)

TEMPLATES_BY_ID = {
    template.template_id: template
    for template in STORY_TEMPLATES
}


def templates_for_difficulty(difficulty: int) -> tuple[StoryTemplate, ...]:
    found = tuple(
        template
        for template in STORY_TEMPLATES
        if template.difficulty == difficulty
    )
    if not found:
        raise ValueError(
            f"No story templates for difficulty {difficulty}."
        )
    return found
