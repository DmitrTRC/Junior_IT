import re


def anonymize(text, stems):
    """Имена детей -> «Ученик N».

    Элемент stems — либо строка-стем (матчится с начала слова, хвост
    словоформы любой), либо список ТОЧНЫХ словоформ одного ребёнка
    (обе границы слова) — так «Маши» не съедает «машину».
    """
    result = text
    for i, entry in enumerate(stems, start=1):
        if isinstance(entry, str):
            patterns = [rf"\b{re.escape(entry)}\w*"]
        else:
            patterns = [rf"\b{re.escape(form)}\b" for form in entry]
        for pattern in patterns:
            result = re.sub(pattern, f"Ученик {i}", result,
                            flags=re.IGNORECASE)
    return result
