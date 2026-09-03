#!/usr/bin/env python3
"""Тесты парсера JSONC. Запуск: python3 provisioning/test-jsonc.py"""
import json
import sys

import jsonc

CASES = [
    ("чистый json",          '{"a": 1}',                              {"a": 1}),
    ("строчный комментарий", '{\n  // коммент\n  "a": 1\n}',          {"a": 1}),
    ("комментарий в конце",  '{"a": 1 // хвост\n}',                   {"a": 1}),
    ("блочный комментарий",  '{/* блок */ "a": 1}',                   {"a": 1}),
    ("многострочный блок",   '{\n/* один\n   два */\n"a": 1}',        {"a": 1}),
    ("висячая запятая",      '{"a": 1,}',                             {"a": 1}),
    ("висячая в массиве",    '{"a": [1, 2,]}',                        {"a": [1, 2]}),
    ("url в строке",         '{"a": "https://x.dev"}',                {"a": "https://x.dev"}),
    ("слэши в строке",       '{"a": "/* не коммент */"}',             {"a": "/* не коммент */"}),
    ("экранированная кавычка", '{"a": "он сказал \\" и всё"}',        {"a": 'он сказал " и всё'}),
    ("запятая внутри строки", '{"a": "x,", "b": 2}',                  {"a": "x,", "b": 2}),
    ("пустой файл",          '',                                      {}),
    ("реальный settings",
     '{\n  // тема\n  "workbench.colorTheme": "Dracula", /* ок */\n  "editor.fontSize": 17,\n}',
     {"workbench.colorTheme": "Dracula", "editor.fontSize": 17}),
]

def main():
    failed = 0
    for name, src, want in CASES:
        try:
            got = json.loads(jsonc.strip(src)) if src.strip() else {}
        except Exception as exc:
            print(f"  ✗ {name}: упал — {exc}")
            failed += 1
            continue
        if got == want:
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name}: получил {got!r}, ждал {want!r}")
            failed += 1

    print(f"\n{len(CASES) - failed} из {len(CASES)} прошли")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
