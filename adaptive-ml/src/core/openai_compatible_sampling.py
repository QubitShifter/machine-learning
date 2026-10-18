def normalized_model_name(model: str) -> str:
    name = model.strip().lower().replace("_", "-")
    return name.rsplit("/", 1)[-1]


def is_gpt6_family(model: str) -> bool:
    return normalized_model_name(model).startswith("gpt-6")


def supports_custom_temperature(model: str) -> bool:
    return not is_gpt6_family(model)


def uses_max_completion_tokens(model: str) -> bool:
    return is_gpt6_family(model)


def completion_token_parameter(model: str) -> str:
    if uses_max_completion_tokens(model):
        return "max_completion_tokens"
    return "max_tokens"
