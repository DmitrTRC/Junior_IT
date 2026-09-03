#!/usr/bin/env python3
"""Мержит defaults.json в target.json: наши ключи поверх, чужие не трогаем.

Использование: merge-json.py <target.json> <defaults.json>

Если target существует, но не разбирается — выходим с ошибкой и НИЧЕГО не пишем.
Затирать чужие настройки молча нельзя, даже с бэкапом.
"""
import json
import sys

import jsonc


def main():
    if len(sys.argv) != 3:
        sys.exit("Использование: merge-json.py <target.json> <defaults.json>")

    target, defaults = sys.argv[1], sys.argv[2]

    try:
        merged = jsonc.load(target)
    except json.JSONDecodeError as exc:
        sys.exit(f"{target} не разбирается ({exc}). Ничего не менял — разберись руками.")

    merged.update(jsonc.load(defaults))

    with open(target, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


if __name__ == "__main__":
    main()
