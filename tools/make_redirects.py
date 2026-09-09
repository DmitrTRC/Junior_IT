#!/usr/bin/env python3
"""Заглушки-редиректы на старых URL уроков.

Ссылки на уроки разосланы родителям и живут в записях занятий — ломать их
нельзя. Скрипт идемпотентен: гоняется повторно после каждого переезда.
"""

import sys
from pathlib import Path

MOVES = {
    "lesson-01-html-css": "web/m-01-html-css",
    "lesson-02-js": "web/m-02-js-alive",
    "lesson-02b-js-console": "web/m-03-js-console",
    "lesson-02c-js-conditions": "web/m-04-js-conditions",
    "lesson-02d-js-loops": "web/m-05-js-loops",
    "lesson-02e-js-recap": "web/m-06-js-recap",
    "lesson-02f-js-functions": "web/m-07-js-functions",
    "lesson-02g-vscode": "web/m-08-vscode",
    "lesson-cs-01-computer": "cs/m-01-computer",
    "lesson-cs-02-layers": "cs/m-02-layers",
    "lesson-cs-03-languages": "cs/m-03-languages",
}

ROLE_OF = {
    "cheatsheet.html": "student",
    "homework.html": "student",
    "slides.html": "shared",
    "index-final.html": "shared",
}


def redirect_html(target_url):
    """Страница-заглушка: мгновенный переход плюс видимая ссылка."""
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Материал переехал</title>
<link rel="canonical" href="{target_url}">
<meta http-equiv="refresh" content="0; url={target_url}">
</head>
<body>
<p>Материал переехал: <a href="{target_url}">открыть новую страницу</a>.</p>
</body>
</html>
"""


def plan_redirects(repo_root):
    """Пары (куда положить заглушку, относительный URL цели)."""
    repo_root = Path(repo_root)
    plan = []
    for old_dir, new_module in sorted(MOVES.items()):
        for filename, role in sorted(ROLE_OF.items()):
            target = repo_root / "tracks" / new_module / role / filename
            if not target.is_file():
                continue
            stub = repo_root / "lessons" / old_dir / filename
            url = f"../../tracks/{new_module}/{role}/{filename}"
            plan.append((stub, url))
    return plan


def write_redirects(repo_root):
    """Пишет заглушки, возвращает их количество."""
    written = 0
    for stub, url in plan_redirects(repo_root):
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text(redirect_html(url), encoding="utf-8")
        written += 1
    return written


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    repo_root = Path(args[0]) if args else Path(__file__).resolve().parent.parent
    print(f"создано заглушек: {write_redirects(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
