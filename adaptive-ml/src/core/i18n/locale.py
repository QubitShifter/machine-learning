SUPPORTED_LOCALES = ("en", "bg")
DEFAULT_LOCALE = "en"


def normalize_locale(value: str | None) -> str:
    if value is None:
        return DEFAULT_LOCALE

    locale = str(value).strip().lower()
    if locale in SUPPORTED_LOCALES:
        return locale

    return DEFAULT_LOCALE
