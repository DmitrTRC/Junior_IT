#!/usr/bin/env python3
"""Разбор JSONC — JSON с комментариями и висячими запятыми.

Именно в таком виде VS Code хранит settings.json, и наивный json.loads на нём
падает. Комментарии вырезаем токенизатором, а не регуляркой: иначе "https://..."
внутри строки будет принят за начало комментария.
"""
import json


def strip(text: str) -> str:
    """Убирает // и /* */ комментарии и висячие запятые вне строк."""
    out = []
    i, n = 0, len(text)
    in_string = False

    while i < n:
        ch = text[i]

        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < n:      # экранированный символ — берём парой
                out.append(text[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
        else:
            out.append(ch)
            i += 1

    cleaned = "".join(out)

    # висячие запятые: ,} и ,] — тоже только вне строк
    result = []
    i, n, in_string = 0, len(cleaned), False
    while i < n:
        ch = cleaned[i]
        if in_string:
            result.append(ch)
            if ch == "\\" and i + 1 < n:
                result.append(cleaned[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
        elif ch == ",":
            j = i + 1
            while j < n and cleaned[j] in " \t\r\n":
                j += 1
            if j < n and cleaned[j] in "}]":
                i += 1                         # запятая перед закрывающей скобкой — выкидываем
            else:
                result.append(ch)
                i += 1
        else:
            result.append(ch)
            i += 1

    return "".join(result)


def load(path: str) -> dict:
    """Читает JSONC-файл. Бросает исключение, если файл есть, но битый."""
    try:
        raw = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return {}
    if not raw.strip():
        return {}
    return json.loads(strip(raw))
