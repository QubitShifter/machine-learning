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
    return format_template(text, **params)
