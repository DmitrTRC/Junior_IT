import re


def anonymize(text, stems):
    """Имена детей -> «Ученик N». Стем матчится с начала слова."""
    result = text
    for i, stem in enumerate(stems, start=1):
        pattern = re.compile(rf"\b{re.escape(stem)}\w*", re.IGNORECASE)
        result = pattern.sub(f"Ученик {i}", result)
    return result
