"""Text normalization utilities for form inputs."""


def normalize_form_text(text: str | None) -> str | None:
    """
    Normalize text input for forms:
    - First letter uppercase
    - Rest lowercase

    Example: "MARKET ALIŞVERIŞI" → "Market alışverişı"
    """
    if not text or not isinstance(text, str):
        return text

    trimmed = text.strip()
    if not trimmed:
        return ""

    return trimmed[0].upper() + trimmed[1:].lower()


def normalize_form_data(data: dict, fields_to_normalize: list[str]) -> dict:
    """
    Apply normalization to multiple fields in a dictionary.
    """
    normalized = data.copy()
    for field in fields_to_normalize:
        if field in normalized and isinstance(normalized[field], str):
            normalized[field] = normalize_form_text(normalized[field])
    return normalized
