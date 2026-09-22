from src.core.i18n.locale import (
    DEFAULT_LOCALE,
    normalize_locale,
)


def format_template(text: str, **params) -> str:
    for key, value in params.items():
        text = text.replace(
            "{" + key + "}",
            str(value),
        )
    return text


def smooth_bulgarian_v_preposition(text: str) -> str:
    """Use във before words that start with в or ф."""
    if not text:
        return text
    smoothed = (
        text.replace(" в в", " във в")
        .replace(" в ф", " във ф")
        .replace(" В в", " Във в")
        .replace(" В ф", " Във ф")
    )
    if smoothed.startswith("В в") or smoothed.startswith("В ф"):
        smoothed = "Във" + smoothed[1:]
    if smoothed.startswith("в в") or smoothed.startswith("в ф"):
        smoothed = "във" + smoothed[1:]
    return smoothed


def tr(
    catalog: dict[str, dict[str, str]],
    language: str | None,
    key: str,
    **params,
) -> str:
    locale = normalize_locale(language)
    table = catalog.get(locale) or catalog[DEFAULT_LOCALE]
    fallback = catalog[DEFAULT_LOCALE]
    text = table.get(key) or fallback.get(key) or key
    rendered = format_template(text, **params)
    if locale == "bg":
        return smooth_bulgarian_v_preposition(rendered)
    return rendered
