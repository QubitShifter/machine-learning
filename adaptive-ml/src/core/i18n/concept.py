from src.core.i18n.locale import normalize_locale


CANONICAL_YES = "yes"
CANONICAL_NO = "no"

_SHARED_YES = frozenset({"yes", "y"})
_SHARED_NO = frozenset({"no", "n"})

_LOCALE_YES = {
    "en": frozenset(
        {
            "true",
            "correct",
            "it is",
            "yes it is",
        }
    ),
    "bg": frozenset(
        {
            "да",
            "да съвпадат",
            "съвпадат",
            "те съвпадат",
            "еднакви са",
            "равни са",
            "да равни са",
        }
    ),
}

_LOCALE_NO = {
    "en": frozenset(),
    "bg": frozenset(
        {
            "не",
            "не съвпадат",
            "не не съвпадат",
            "различни са",
            "не са равни",
        }
    ),
}


def _normalize_text(answer: str) -> str:
    text = answer.strip().lower()
    for mark in (",", ".", "!", "?"):
        text = text.replace(mark, "")
    return " ".join(text.split())


def normalize_concept_answer(
    answer: str | None,
    language: str | None = None,
) -> str | None:
    if answer is None:
        return None

    text = _normalize_text(str(answer))
    if not text:
        return None

    locale = normalize_locale(language)
    yes_aliases = _SHARED_YES | _LOCALE_YES.get(
        locale,
        frozenset(),
    )
    no_aliases = _SHARED_NO | _LOCALE_NO.get(
        locale,
        frozenset(),
    )

    if text in yes_aliases:
        return CANONICAL_YES

    if text in no_aliases:
        return CANONICAL_NO

    return None
