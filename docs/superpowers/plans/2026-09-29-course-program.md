# Программа курса на год — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Опубликовать программу курса 2026/27 на странице `program.html` с тремя ракурсами (Ученику / Родителям / Почему так) из одного источника данных `meta/program.yml`.

**Architecture:** `meta/program.yml` описывает блоки по месяцам; `tools/build_program.py` разрешает модули через манифесты `tracks/` и статусы карты курса и пишет `program.json`; `program.html` (vanilla JS) рисует ленту месяцев под выбранный ракурс; `build_site.sh` собирает всё в `_site`. Лендинг получает две ссылки на страницу.

**Tech Stack:** Python 3 + PyYAML (генератор), pytest (`cd tools && .venv/bin/python -m pytest -q`), статический HTML/CSS/JS без сборки, bash `tools/build_site.sh`.

**Spec:** `docs/superpowers/specs/2026-09-29-course-program-design.md`

## Global Constraints

- Идентификаторы (id модулей, ключи YAML/JSON, имена файлов) — английские; тексты для людей — русские; термины парой «русский (english)».
- Никаких имён детей и запрещённой лексики (дружина, отряд, контроль, проверки, инспекции) в `program.yml`, `program.html` и тестовых фикстурах.
- Цвета только из токенов бренда: `--bg #0a0a14`, `--card #1a1a2e`, `--card-2 #16213e`, `--deep #0f3460`, `--yellow #ffd60a`, `--cyan #00ffc8`; треки `--track-book #7aa2ff`, `--track-py #00ffc8`, `--track-pas #ff5722`, `--track-ops #00e676`, `--track-cs #ff0096`, `--track-web #8892b0`. Шрифты Rubik 700 / Manrope / JetBrains Mono.
- Страница работает на ширине 400px без горизонтального скролла; `img{max-width:100%}` не нужен, картинок нет.
- Ссылки на учебник в формате `"7:1.2"` (параграф) и `"7:1"` (глава), как в `module.yml`.
- Ракурс по умолчанию `#parents`; hash-значения ровно `student`, `parents`, `why`.
- Коммиты без эмодзи, тесты обязательны для каждой функции генератора; `git push` не делать.
- Тесты запускать из `tools/`: `.venv/bin/python -m pytest -q`; полный прогон перед каждым коммитом.

## Review Focus

1. `program.yml` ссылается на модуль, у которого позже появился `module.yml`, но в программе остались `title`/`track` — программа должна упасть с понятной ошибкой, а не тихо показать два разных названия (тест в Task 2).
2. Месяц из прошлого (сентябрь) после смены календаря должен сам стать `done`, а январь 2027 — `upcoming` в декабре 2026: сравнение месяцев строковое по `YYYY-MM`, проверить границу года (тест в Task 1).
3. Блок без модулей (май) допустим только с событиями; блок без модулей и без событий — ошибка (тест в Task 1).
4. Страница открыта без `program.json` (локально из файла или сборка упала) — показать человеческую фразу, не пустой экран (Task 5, ручная проверка + тест на строку-заглушку).
5. Ссылка `program.html#student` из мессенджера должна открыть ракурс ученика даже если в `localStorage` сохранён другой (Task 5, тест на порядок в `currentView`).

---

### Task 1: Загрузка и проверка `program.yml`, подписи и статусы

**Files:**
- Create: `tools/build_program.py`
- Test: `tools/tests/test_build_program.py`

**Interfaces:**
- Consumes: `build_course_map.TRACKS_META` (список треков с `id`).
- Produces:
  - `load_program(repo_root) -> dict` — прочитанный и проверенный `meta/program.yml`; у каждого блока гарантированы списки `modules`, `textbook`, `trainer`, `events` и строка `month`.
  - `textbook_label(ref: str) -> str` — `"7:1.2"` → `"7 кл §1.2"`, `"8:1"` → `"8 кл гл. 1"`.
  - `month_label(month: str) -> str` — `"2026-10"` → `"Октябрь"`.
  - `block_status(month: str, today: date) -> "done" | "current" | "upcoming"`.

- [ ] **Step 1: Написать падающие тесты**

```python
# tools/tests/test_build_program.py
from datetime import date
from pathlib import Path

import pytest
import yaml

from build_program import block_status, load_program, month_label, textbook_label

TODAY = date(2026, 10, 5)


def program_yaml(blocks, **over):
    data = {
        "year": "2026/27",
        "goal": {"student": "Своя программа на GitHub.", "parents": "Ребёнок пишет программы на Python."},
        "disclaimer": "Программа живая: темп подстраивается под учеников.",
        "next_year": "Восьмой класс: Python глубже.",
        "principles": ["Учебник с опережением школы."],
        "blocks": blocks,
    }
    data.update(over)
    return data


def write_program(repo_root, blocks, **over):
    meta = repo_root / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "program.yml").write_text(
        yaml.safe_dump(program_yaml(blocks, **over), allow_unicode=True), encoding="utf-8")


def block(month, modules=(), events=(), **over):
    data = {"month": month, "title": f"Тема {month}", "outcome": f"Результат {month}",
            "why": f"Потому что {month}", "modules": list(modules), "events": list(events)}
    data.update(over)
    return data


def test_textbook_labels():
    assert textbook_label("7:1.2") == "7 кл §1.2"
    assert textbook_label("8:1") == "8 кл гл. 1"
    with pytest.raises(ValueError):
        textbook_label("глава 1")


def test_month_label_and_block_status_across_year_boundary():
    assert month_label("2026-10") == "Октябрь"
    assert month_label("2027-01") == "Январь"
    assert block_status("2026-09", TODAY) == "done"
    assert block_status("2026-10", TODAY) == "current"
    assert block_status("2027-01", date(2026, 12, 20)) == "upcoming"


def test_load_program_normalizes_lists(tmp_path):
    write_program(tmp_path, [block("2026-10", modules=["python/m-02-variables"])])
    program = load_program(tmp_path)
    first = program["blocks"][0]
    assert first["month"] == "2026-10"
    assert first["textbook"] == [] and first["trainer"] == [] and first["events"] == []
    assert first["modules"] == ["python/m-02-variables"]


def test_load_program_rejects_unordered_or_duplicate_months(tmp_path):
    write_program(tmp_path, [block("2026-11", events=["x"]), block("2026-10", events=["x"])])
    with pytest.raises(ValueError, match="по возрастанию"):
        load_program(tmp_path)
    write_program(tmp_path, [block("2026-10", events=["x"]), block("2026-10", events=["y"])])
    with pytest.raises(ValueError, match="уникальн"):
        load_program(tmp_path)


def test_load_program_requires_modules_or_events(tmp_path):
    write_program(tmp_path, [block("2027-05")])
    with pytest.raises(ValueError, match="без модулей и без событий"):
        load_program(tmp_path)
    write_program(tmp_path, [block("2027-05", events=["демо-день"])])
    assert load_program(tmp_path)["blocks"][0]["events"] == ["демо-день"]


def test_load_program_requires_top_fields_and_month_format(tmp_path):
    write_program(tmp_path, [block("2026-10", events=["x"])], disclaimer="")
    with pytest.raises(ValueError, match="disclaimer"):
        load_program(tmp_path)
    write_program(tmp_path, [block("октябрь", events=["x"])])
    with pytest.raises(ValueError, match="YYYY-MM"):
        load_program(tmp_path)
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd tools && .venv/bin/python -m pytest -q tests/test_build_program.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_program'`.

- [ ] **Step 3: Минимальная реализация**

```python
# tools/build_program.py
#!/usr/bin/env python3
"""Собирает program.json — программу курса на год — из meta/program.yml.

Существующие модули берутся из tracks/*/*/module.yml и карты курса
(статусы), будущие описаны прямо в program.yml полями title и track.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml

from build_course_map import TRACKS_META, load_modules, load_sessions, module_links, module_statuses

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
TEXTBOOK_RE = re.compile(r"^(?P<grade>\d{1,2}):(?P<chapter>\d+)(?:\.(?P<paragraph>\d+))?$")
MONTH_NAMES = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
               "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
TRACK_IDS = {t["id"] for t in TRACKS_META}
ARCHIVE_TRACKS = {"web"}
REQUIRED_TOP = ("year", "goal", "disclaimer", "next_year", "principles", "blocks")
REQUIRED_BLOCK = ("month", "title", "outcome", "why")
LIST_FIELDS = ("modules", "textbook", "trainer", "events")


def textbook_label(ref):
    match = TEXTBOOK_RE.match(str(ref))
    if not match:
        raise ValueError(f"ссылка на учебник не по формату grade:chapter[.paragraph]: {ref!r}")
    grade, chapter, paragraph = match.group("grade", "chapter", "paragraph")
    if paragraph is None:
        return f"{grade} кл гл. {chapter}"
    return f"{grade} кл §{chapter}.{paragraph}"


def month_label(month):
    return MONTH_NAMES[int(month[5:7]) - 1]


def block_status(month, today):
    current = today.strftime("%Y-%m")
    if month < current:
        return "done"
    return "current" if month == current else "upcoming"


def load_program(repo_root):
    path = Path(repo_root) / "meta" / "program.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"битая программа: {path}")
    missing = [key for key in REQUIRED_TOP if not data.get(key)]
    if missing:
        raise ValueError(f"program.yml: пустые или отсутствующие поля {missing}")
    for key in ("student", "parents"):
        if not data["goal"].get(key):
            raise ValueError(f"program.yml: goal.{key} пустой")
    months = []
    for block in data["blocks"]:
        missing = [key for key in REQUIRED_BLOCK if not block.get(key)]
        if missing:
            raise ValueError(f"program.yml: блок {block.get('month')!r} без полей {missing}")
        month = str(block["month"])
        if not MONTH_RE.match(month):
            raise ValueError(f"program.yml: месяц не по формату YYYY-MM: {month!r}")
        block["month"] = month
        for key in LIST_FIELDS:
            block[key] = list(block.get(key) or [])
        if not block["modules"] and not block["events"]:
            raise ValueError(f"program.yml: блок {month} без модулей и без событий")
        months.append(month)
    if len(set(months)) != len(months):
        raise ValueError("program.yml: месяцы должны быть уникальны")
    if months != sorted(months):
        raise ValueError("program.yml: месяцы должны идти по возрастанию")
    return data
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `cd tools && .venv/bin/python -m pytest -q tests/test_build_program.py`
Expected: 6 passed. Затем полный прогон `.venv/bin/python -m pytest -q` — всё зелёное.

- [ ] **Step 5: Коммит**

```bash
git add tools/build_program.py tools/tests/test_build_program.py
git commit -m "feat(program): загрузка и проверка program.yml, подписи учебника, статусы месяцев"
```

---

### Task 2: Разрешение модулей и сборка `program.json`

**Files:**
- Modify: `tools/build_program.py` (добавить `resolve_module`, `build_program`)
- Test: `tools/tests/test_build_program.py`

**Interfaces:**
- Consumes: `load_program`, `textbook_label`, `month_label`, `block_status` (Task 1); `build_course_map.load_modules(repo_root)`, `load_sessions(repo_root)`, `module_statuses(modules, sessions, today)`, `module_links(module)`.
- Produces:
  - `resolve_module(entry, modules_by_id, statuses) -> dict` с ключами `id, title, track, status, minutes, links`.
  - `build_program(repo_root, today: date) -> dict` — структура `program.json` из спеки: `generated_at, year, goal, disclaimer, next_year, principles, current_month, blocks[]`; блок: `month, label, status, title, outcome, why, textbook[{ref,label}], trainer[{ref,label}], events[], modules[]`.

- [ ] **Step 1: Написать падающие тесты**

Добавить в `tools/tests/test_build_program.py`:

```python
from build_program import build_program


def make_module(repo_root, module_id, level="core", minutes=25):
    track, name = module_id.split("/")
    module_dir = repo_root / "tracks" / track / name
    (module_dir / "shared").mkdir(parents=True)
    (module_dir / "student").mkdir()
    (module_dir / "shared" / "slides.html").write_text("x", encoding="utf-8")
    (module_dir / "student" / "cheatsheet.html").write_text("x", encoding="utf-8")
    manifest = {"id": module_id, "title": f"Тест {name} (test)", "track": track,
                "level": level, "minutes": minutes, "textbook": []}
    (module_dir / "module.yml").write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    return module_dir


def make_session(repo_root, day, modules):
    session_dir = repo_root / "playground" / day.isoformat()
    session_dir.mkdir(parents=True)
    data = {"date": day.isoformat(), "theme": "Тема",
            "playlist": [{"module": m, "minutes": 25} for m in modules]}
    (session_dir / "session.yml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_existing_module_resolves_from_manifest_and_map(tmp_path):
    make_module(tmp_path, "python/m-01-first-run")
    make_session(tmp_path, date(2026, 9, 27), ["python/m-01-first-run"])
    write_program(tmp_path, [block("2026-09", modules=["python/m-01-first-run"], textbook=["8:5.1"])])
    program = build_program(tmp_path, TODAY)
    assert program["current_month"] == "2026-10"
    first = program["blocks"][0]
    assert first["label"] == "Сентябрь" and first["status"] == "done"
    assert first["textbook"] == [{"ref": "8:5.1", "label": "8 кл §5.1"}]
    module = first["modules"][0]
    assert module["title"] == "Тест m-01-first-run (test)" and module["track"] == "python"
    assert module["status"] == "done" and module["minutes"] == 25
    assert module["links"]["cheatsheet"] == "tracks/python/m-01-first-run/student/cheatsheet.html"


def test_future_module_needs_title_and_track(tmp_path):
    write_program(tmp_path, [block("2026-10", modules=["python/m-02-variables"])])
    with pytest.raises(ValueError, match="python/m-02-variables"):
        build_program(tmp_path, TODAY)
    write_program(tmp_path, [block("2026-10", modules=[
        {"id": "python/m-02-variables", "title": "Переменные (variables)", "track": "python"}])])
    module = build_program(tmp_path, TODAY)["blocks"][0]["modules"][0]
    assert module == {"id": "python/m-02-variables", "title": "Переменные (variables)",
                      "track": "python", "status": "planned", "minutes": None, "links": {}}


def test_future_module_track_must_be_known_and_match_id(tmp_path):
    write_program(tmp_path, [block("2026-10", modules=[
        {"id": "python/m-02-variables", "title": "x", "track": "devops"}])])
    with pytest.raises(ValueError, match="не совпадает с треком"):
        build_program(tmp_path, TODAY)
    write_program(tmp_path, [block("2026-10", modules=[
        {"id": "ruby/m-01-start", "title": "x", "track": "ruby"}])])
    with pytest.raises(ValueError, match="неизвестный трек"):
        build_program(tmp_path, TODAY)


def test_existing_module_with_title_in_program_is_an_error(tmp_path):
    make_module(tmp_path, "python/m-01-first-run")
    write_program(tmp_path, [block("2026-09", modules=[
        {"id": "python/m-01-first-run", "title": "Другое имя", "track": "python"}])])
    with pytest.raises(ValueError, match="лишние"):
        build_program(tmp_path, TODAY)


def test_every_core_module_must_appear_once(tmp_path):
    make_module(tmp_path, "python/m-01-first-run")
    make_module(tmp_path, "devops/m-01-terminal-first-steps")
    make_module(tmp_path, "web/m-01-html-css", level="library")
    write_program(tmp_path, [block("2026-09", modules=["python/m-01-first-run"])])
    with pytest.raises(ValueError, match="devops/m-01-terminal-first-steps"):
        build_program(tmp_path, TODAY)
    write_program(tmp_path, [block("2026-09", modules=["python/m-01-first-run", "devops/m-01-terminal-first-steps"]),
                             block("2026-10", modules=["python/m-01-first-run"])])
    with pytest.raises(ValueError, match="дважды"):
        build_program(tmp_path, TODAY)
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd tools && .venv/bin/python -m pytest -q tests/test_build_program.py`
Expected: 5 новых FAIL с `ImportError: cannot import name 'build_program'`.

- [ ] **Step 3: Реализация**

Добавить в `tools/build_program.py` после `load_program`:

```python
def resolve_module(entry, modules_by_id, statuses):
    if isinstance(entry, str):
        entry = {"id": entry}
    if not isinstance(entry, dict) or not entry.get("id"):
        raise ValueError(f"program.yml: модуль без id: {entry!r}")
    module_id = str(entry["id"])
    existing = modules_by_id.get(module_id)
    if existing is not None:
        extra = [key for key in ("title", "track") if key in entry]
        if extra:
            raise ValueError(f"program.yml: {module_id} есть в tracks/, поля {extra} лишние")
        return {"id": module_id, "title": existing["title"], "track": existing["track"],
                "status": statuses[module_id], "minutes": existing["minutes"],
                "links": module_links(existing)}
    missing = [key for key in ("title", "track") if not entry.get(key)]
    if missing:
        raise ValueError(f"program.yml: будущий модуль {module_id} без полей {missing}")
    track = entry["track"]
    if track not in TRACK_IDS:
        raise ValueError(f"program.yml: {module_id}: неизвестный трек {track!r}")
    if not module_id.startswith(track + "/"):
        raise ValueError(f"program.yml: {module_id}: id не совпадает с треком {track!r}")
    return {"id": module_id, "title": entry["title"], "track": track,
            "status": "planned", "minutes": None, "links": {}}


def build_program(repo_root, today):
    program = load_program(repo_root)
    modules = load_modules(repo_root)
    sessions = load_sessions(repo_root)
    statuses = module_statuses(modules, sessions, today)
    modules_by_id = {m["id"]: m for m in modules}

    blocks, seen = [], set()
    for block in program["blocks"]:
        resolved = [resolve_module(entry, modules_by_id, statuses) for entry in block["modules"]]
        for module in resolved:
            if module["id"] in seen:
                raise ValueError(f"program.yml: модуль {module['id']} встречается дважды")
            seen.add(module["id"])
        blocks.append({
            "month": block["month"], "label": month_label(block["month"]),
            "status": block_status(block["month"], today),
            "title": block["title"], "outcome": block["outcome"], "why": block["why"],
            "textbook": [{"ref": ref, "label": textbook_label(ref)} for ref in block["textbook"]],
            "trainer": [{"ref": ref, "label": textbook_label(ref)} for ref in block["trainer"]],
            "events": block["events"], "modules": resolved,
        })
    core = [m["id"] for m in modules
            if m["level"] in ("core", "deep") and m["track"] not in ARCHIVE_TRACKS]
    forgotten = sorted(set(core) - seen)
    if forgotten:
        raise ValueError(f"program.yml: модули из tracks/ не вошли в программу: {forgotten}")
    return {
        "generated_at": today.isoformat(), "year": program["year"], "goal": program["goal"],
        "disclaimer": program["disclaimer"], "next_year": program["next_year"],
        "principles": list(program["principles"]),
        "current_month": today.strftime("%Y-%m"),
        "blocks": blocks,
    }
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `cd tools && .venv/bin/python -m pytest -q tests/test_build_program.py`
Expected: 11 passed. Полный прогон зелёный.

- [ ] **Step 5: Коммит**

```bash
git add tools/build_program.py tools/tests/test_build_program.py
git commit -m "feat(program): разрешение модулей через tracks/ и карту курса, сборка program.json"
```

---

### Task 3: Плоский текст для мессенджера и CLI

**Files:**
- Modify: `tools/build_program.py` (добавить `program_text`, `main`)
- Test: `tools/tests/test_build_program.py`

**Interfaces:**
- Consumes: `build_program` (Task 2).
- Produces:
  - `program_text(program: dict, view: "student" | "parents") -> str` — без markdown, оговорка в третьей строке, пустая строка между месяцами.
  - `main(argv=None) -> int`: `build_program.py <repo_root> [<out_dir>] [--text student|parents]`; без `--text` пишет `<out_dir>/program.json` (по умолчанию `<repo_root>/program.json`) и печатает `программа курса: <path>`; с `--text` печатает текст в stdout и ничего не пишет; ошибка данных → код 1 и сообщение в stderr.

- [ ] **Step 1: Написать падающие тесты**

```python
from build_program import main, program_text


def test_program_text_parents_and_student(tmp_path, capsys):
    make_module(tmp_path, "python/m-01-first-run")
    write_program(tmp_path, [
        block("2026-09", modules=["python/m-01-first-run"], textbook=["8:5.1"]),
        block("2027-05", events=["демо-день"]),
    ])
    program = build_program(tmp_path, TODAY)
    parents = program_text(program, "parents")
    lines = parents.splitlines()
    assert lines[0] == "Программа Junior_IT 2026/27"
    assert lines[1] == "Ребёнок пишет программы на Python."
    assert lines[2] == "Программа живая: темп подстраивается под учеников."
    assert "Сентябрь — Тема 2026-09" in parents and "Результат 2026-09" in parents
    assert "Учебник: 8 кл §5.1" in parents and "Восьмой класс: Python глубже." in parents
    assert "**" not in parents and "#" not in parents
    student = program_text(program, "student")
    assert "- Тест m-01-first-run (test)" in student and "- демо-день" in student
    assert "Результат 2026-09" not in student
    with pytest.raises(ValueError):
        program_text(program, "teacher")


def test_main_writes_json_or_prints_text(tmp_path, capsys):
    make_module(tmp_path, "python/m-01-first-run")
    write_program(tmp_path, [block("2026-09", modules=["python/m-01-first-run"])])
    out = tmp_path / "site"
    out.mkdir()
    assert main([str(tmp_path), str(out)]) == 0
    data = json.loads((out / "program.json").read_text(encoding="utf-8"))
    assert data["year"] == "2026/27" and data["blocks"][0]["modules"][0]["id"] == "python/m-01-first-run"
    assert main([str(tmp_path), "--text", "student"]) == 0
    assert "Тест m-01-first-run (test)" in capsys.readouterr().out
    assert not (tmp_path / "program.json").exists()


def test_main_reports_broken_program(tmp_path, capsys):
    write_program(tmp_path, [block("2026-10", modules=["python/m-02-variables"])])
    assert main([str(tmp_path), str(tmp_path)]) == 1
    assert "python/m-02-variables" in capsys.readouterr().err
```

Добавить `import json` в шапку тестов.

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd tools && .venv/bin/python -m pytest -q tests/test_build_program.py`
Expected: 3 FAIL с `ImportError: cannot import name 'main'`.

- [ ] **Step 3: Реализация**

Добавить в конец `tools/build_program.py`:

```python
def program_text(program, view):
    if view not in ("student", "parents"):
        raise ValueError(f"ракурс должен быть student или parents: {view!r}")
    lines = [f"Программа Junior_IT {program['year']}", program["goal"][view], program["disclaimer"], ""]
    for block in program["blocks"]:
        lines.append(f"{block['label']} — {block['title']}")
        if view == "parents":
            lines.append(block["outcome"])
            refs = [item["label"] for item in block["textbook"]]
            if refs:
                lines.append("Учебник: " + ", ".join(refs))
        else:
            lines.extend(f"- {module['title']}" for module in block["modules"])
            lines.extend(f"- {event}" for event in block["events"])
        lines.append("")
    if view == "parents":
        lines.append(program["next_year"])
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    view = None
    if "--text" in args:
        at = args.index("--text")
        if at + 1 >= len(args):
            print("usage: build_program.py <repo_root> [<out_dir>] [--text student|parents]", file=sys.stderr)
            return 2
        view = args[at + 1]
        del args[at:at + 2]
    repo_root = Path(args[0]) if args else Path(__file__).resolve().parent.parent
    try:
        program = build_program(repo_root, date.today())
        if view is not None:
            print(program_text(program, view), end="")
            return 0
    except (yaml.YAMLError, KeyError, ValueError, OSError) as exc:
        print(f"program: не удалось собрать программу ({exc})", file=sys.stderr)
        return 1
    out_dir = Path(args[1]) if len(args) > 1 else repo_root
    out_path = out_dir / "program.json"
    out_path.write_text(json.dumps(program, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"программа курса: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `cd tools && .venv/bin/python -m pytest -q tests/test_build_program.py`
Expected: 14 passed. Полный прогон зелёный.

- [ ] **Step 5: Коммит**

```bash
git add tools/build_program.py tools/tests/test_build_program.py
git commit -m "feat(program): текст программы для мессенджера и CLI генератора"
```

---

### Task 4: Настоящий `meta/program.yml`, сборка в `build_site.sh`, публикация `program.json`

**Files:**
- Create: `meta/program.yml`
- Modify: `tools/build_site.sh` (вызов генератора после карты курса)
- Test: `tools/tests/test_build_program.py` (интеграционный тест на реальный репо), `tools/tests/test_build_site.py`

**Interfaces:**
- Consumes: `build_program(repo_root, today)`, CLI `build_program.py <repo_root> <out_dir>`.
- Produces: `_site/program.json` при сборке сайта; `meta/program.yml` как источник правды.

- [ ] **Step 1: Написать падающие тесты**

В `tools/tests/test_build_program.py`:

```python
REPO = Path(__file__).resolve().parents[2]
FORBIDDEN = ("дружин", "отряд", "контрол", "проверк", "инспекц")
KID_NAMES = ("Неля", "Маша", "Мария", "Матвей")


def test_real_program_builds_and_is_clean():
    program = build_program(REPO, date.today())
    ids = [m["id"] for b in program["blocks"] for m in b["modules"]]
    assert "python/m-01-first-run" in ids and "cs/m-03-languages" in ids
    assert program["blocks"][0]["month"] == "2026-09" and program["blocks"][-1]["month"] == "2027-05"
    raw = (REPO / "meta" / "program.yml").read_text(encoding="utf-8")
    assert not any(word in raw.lower() for word in FORBIDDEN)
    assert not any(name in raw for name in KID_NAMES)
    assert "живая" in program["disclaimer"]
```

В `tools/tests/test_build_site.py`:

```python
def test_program_json_is_published(tmp_path):
    out = build(tmp_path)
    data = json.loads((out / "program.json").read_text(encoding="utf-8"))
    assert data["year"] == "2026/27" and len(data["blocks"]) == 9
```

Добавить `import json` в шапку `test_build_site.py`.

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd tools && .venv/bin/python -m pytest -q tests/test_build_program.py::test_real_program_builds_and_is_clean tests/test_build_site.py::test_program_json_is_published`
Expected: FAIL — `FileNotFoundError: meta/program.yml` и отсутствующий `program.json`.

- [ ] **Step 3: Записать `meta/program.yml`**

```yaml
# Программа курса на учебный год. Источник правды для program.html и
# текста в мессенджер. Существующие модули — строкой с id (title и статус
# берутся из tracks/ и карты курса), будущие — объектом с title и track.
# Ссылки на учебник: "7:1.2" — параграф, "7:1" — глава.
year: "2026/27"
goal:
  student: "К маю — своя программа на Python на GitHub с тестами, которую не стыдно показать."
  parents: "К маю ребёнок пишет программы на Python, ведёт проект на GitHub с автотестами и закрывает учебник 7 класса с опережением школы."
disclaimer: "Программа живая: темп подстраивается под занятость и успехи учеников, порядок тем может сдвигаться. Цель года не меняется."
next_year: "Восьмой класс: Python глубже (классы, модули, простые библиотеки), проект побольше в команде из двух-трёх человек, учебник 8 класса целиком с тем же опережением."
principles:
  - "Учебник идёт с опережением школы на 2–6 недель: в классе ребёнок узнаёт, а не открывает. Главы 3–5 седьмого класса (текст, графика, мультимедиа) без отдельных занятий: это навыки пользователя, закрываем тренажёром."
  - "Git и GitHub в октябре, а не в конце: с ноября домашки живут в репозитории, к маю у ребёнка год истории коммитов."
  - "Циклы раньше списков, функции перед первым проектом: инструмент появляется за месяц до того, как без него нельзя."
  - "Паскаль только читать: он есть в учебнике 8 класса, писать на нём не будем. Понадобится перевод программы — добавим модуль."
  - "«Компьютер изнутри» вставками между блоками кода, как передышка от клавиатуры."
  - "Курс живой: темп и порядок подстраиваются под занятость и успехи учеников, цель года не меняется."
blocks:
  - month: "2026-09"
    title: "Старт: терминал и первый Python"
    modules:
      - book/m-01-information-and-data
      - devops/m-01-terminal-first-steps
      - python/m-01-first-run
    outcome: "Терминал не пугает, первая программа запущена, первая ошибка прочитана снизу вверх."
    textbook: ["7:1.1", "7:2.3", "8:5.1"]
    why: "Сначала место, где живёт код, потом сам код: терминал и папка проекта до первой строки на Python."

  - month: "2026-10"
    title: "Программа спрашивает и решает"
    modules:
      - {id: python/m-02-variables, title: "Переменные и ввод (variables, input)", track: python}
      - {id: python/m-03-conditions, title: "Программа решает: условия (conditions)", track: python}
      - {id: devops/m-02-git-first-commit, title: "Git: первый коммит (commit)", track: devops}
      - {id: devops/m-03-github, title: "GitHub: репозиторий домашек (remote)", track: devops}
      - {id: book/m-02-information-processes, title: "Информационные процессы (information processes)", track: book}
      - {id: book/m-03-representation, title: "Представление информации (representation)", track: book}
    outcome: "Программа-диалог: спрашивает, считает и отвечает по-разному в зависимости от ответа. Домашки сдаются в своём репозитории на GitHub."
    textbook: ["7:1.2", "7:1.3", "8:5.2", "8:5.3", "8:5.4"]
    why: "Условия — первое место, где программа перестаёт быть списком команд. Git и GitHub здесь же, чтобы каждая следующая домашка уже жила в репозитории."

  - month: "2026-11"
    title: "Программа повторяет"
    modules:
      - {id: python/m-04-loops, title: "Программа повторяет: циклы (loops)", track: python}
      - {id: python/m-05-lists, title: "Списки (lists)", track: python}
      - {id: devops/m-04-vscode, title: "VS Code: свой дом для кода (code editor)", track: devops}
      - {id: devops/m-05-pytest, title: "Первый автотест (pytest)", track: devops}
      - {id: book/m-04-binary, title: "Двоичное представление данных (binary)", track: book}
      - cs/m-02-layers
      - {id: book/m-05-measuring, title: "Измерение информации (measuring information)", track: book}
    outcome: "Игра «угадай число» с циклом; первый автотест зелёный; зачёт по главе 1 учебника."
    textbook: ["7:1.4", "7:1.5", "8:5.5"]
    trainer: ["7:1"]
    why: "Цикл нужен раньше списка: список без цикла — просто длинная переменная. Тест появляется, когда есть что проверять."

  - month: "2026-12"
    title: "Мини-проект: викторина"
    modules:
      - {id: python/m-06-strings, title: "Строки (strings)", track: python}
      - {id: python/m-07-functions, title: "Своя команда: функции (functions)", track: python}
      - cs/m-01-computer
    events: ["мини-проект «викторина в консоли» — два занятия, показ родителям перед каникулами"]
    outcome: "Викторина в консоли на GitHub с тестами, показ родителям перед каникулами."
    textbook: ["7:2.1", "7:2.2"]
    why: "Функции перед первым проектом: без них викторина превращается в одну длинную простыню. «Компьютер изнутри» — передышка от клавиатуры перед спринтом."

  - month: "2027-01"
    title: "Случайность, файлы, двоичный мир"
    modules:
      - {id: python/m-08-random-games, title: "Случайность и игры (random)", track: python}
      - {id: python/m-09-files, title: "Файлы: программа помнит (files)", track: python}
      - {id: book/m-06-number-systems, title: "Системы счисления на Python (number systems)", track: book}
      - {id: cs/m-04-networks, title: "Сети и интернет (networks)", track: cs}
    outcome: "Программа сохраняет результаты в файл; переводит числа в двоичную систему и обратно."
    textbook: ["7:2.4", "7:2.5", "7:2.6", "8:1"]
    trainer: ["7:3"]
    why: "Системы счисления из учебника 8 класса берём на Python: bin() и int() делают тему осязаемой, а не табличной."

  - month: "2027-02"
    title: "Логика и словари"
    modules:
      - {id: book/m-07-logic, title: "Логика на Python: and, or, not (logic)", track: book}
      - {id: python/m-10-dicts, title: "Словари (dicts)", track: python}
      - cs/m-03-languages
    outcome: "Программа-справочник; логические выражения читает и составляет; зачёт по главе 2 учебника."
    textbook: ["8:2"]
    trainer: ["7:2", "7:4"]
    why: "Логика из 8 класса ложится на условия, которые уже месяц в руках: таблицы истинности проверяем кодом, а не мелом."

  - month: "2027-03"
    title: "Алгоритмы и чужой язык"
    modules:
      - {id: book/m-08-algorithms, title: "Алгоритмы, исполнители, блок-схемы (algorithms)", track: book}
      - {id: pascal/m-01-reading-pascal, title: "Читаем Паскаль (reading Pascal)", track: pascal}
      - {id: python/m-11-modules, title: "Структура программы: свои модули и import (modules)", track: python}
    outcome: "Одна и та же программа на Python и на Паскале; блок-схема своей программы."
    textbook: ["8:3", "8:4"]
    trainer: ["7:5"]
    why: "Алгоритмы по учебнику — это то, что дети уже написали на Python; Паскаль читаем, чтобы в учебнике он не пугал."

  - month: "2027-04"
    title: "Проект года, спринт 1"
    modules:
      - {id: devops/m-06-readme-release, title: "README и структура репозитория (release)", track: devops}
    events: ["выбор проекта", "спринты по два занятия", "ревью в репозитории", "итоговый зачёт за 7 класс в тренажёре"]
    outcome: "Проект растёт коммитами; итоговый зачёт за 7 класс сдан."
    textbook: ["7:1", "7:2", "7:3", "7:4", "7:5"]
    why: "Проект начинается, когда все инструменты уже в руках: функции, списки, файлы, тесты, репозиторий."

  - month: "2027-05"
    title: "Проект года, финал"
    modules: []
    events: ["спринт 2", "тесты", "релиз тегом", "демо-день для родителей"]
    outcome: "Готовый проект на GitHub с тестами и README; демо родителям; разговор «куда дальше в 8-м»."
    why: "Май — только доводка и показ: новых тем нет, чтобы проект дошёл до релиза, а не до «почти»."
```

Проверить, что в `tracks/` уровень модулей `cs/m-01..03` — `core` (`grep level tracks/cs/*/module.yml`); если у какого-то `library`, тест покрытия его не потребует, и это нормально.

- [ ] **Step 4: Подключить генератор в `tools/build_site.sh`**

После строки с `build_course_map.py` добавить:

```bash
"$PYBIN" "$ROOT/tools/build_program.py" "$ROOT" "$OUT"
```

- [ ] **Step 5: Убедиться, что тесты проходят**

Run: `cd tools && .venv/bin/python -m pytest -q`
Expected: всё зелёное, включая оба новых теста. Дополнительно `cd tools && .venv/bin/python build_program.py .. --text parents | head -20` — текст читается человеком, без markdown.

- [ ] **Step 6: Коммит**

```bash
git add meta/program.yml tools/build_site.sh tools/tests/test_build_program.py tools/tests/test_build_site.py
git commit -m "feat(program): программа 2026/27 в meta/program.yml, program.json собирается на сайт"
```

---

### Task 5: Страница `program.html` с тремя ракурсами

**Files:**
- Create: `program.html`
- Modify: `tools/build_site.sh` (добавить `program.html` в `PUBLISH`)
- Test: `tools/tests/test_program_page.py`, `tools/tests/test_build_site.py`

**Interfaces:**
- Consumes: `program.json` (структура из Task 2), токены бренда.
- Produces: страница `program.html` в корне; hash `#student | #parents | #why`; `localStorage['program-view']`.

- [ ] **Step 1: Написать падающие тесты**

```python
# tools/tests/test_program_page.py
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAGE = REPO / "program.html"
VOID = {"meta", "link", "br", "img", "hr", "input"}
FORBIDDEN = ("дружин", "отряд", "контрол", "проверк", "инспекц")
KID_NAMES = ("Неля", "Маша", "Мария", "Матвей")


class BalanceChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unbalanced </{tag}> (stack: {self.stack[-3:]})")
        else:
            self.stack.pop()


def page_text():
    return PAGE.read_text(encoding="utf-8")


def js_text():
    return page_text().split("<script")[-1]


def test_page_is_balanced_html():
    checker = BalanceChecker()
    checker.feed(page_text())
    assert not checker.errors and not checker.stack


def test_page_fetches_program_json_and_has_fallback():
    assert "fetch('program.json')" in js_text()
    assert "Программа пока не собрана" in js_text()


def test_three_views_and_default():
    text = page_text()
    for view in ("student", "parents", "why"):
        assert f'data-view="{view}"' in text
    js = js_text()
    assert "return 'parents';" in js
    assert js.index("location.hash") < js.index("localStorage.getItem")   # hash важнее сохранённого выбора


def test_brand_and_forbidden_words():
    text = page_text()
    assert "Rubik" in text and "Manrope" in text and "JetBrains+Mono" in text
    assert "#0a0a14" in text and "#ffd60a" in text
    lower = text.lower()
    assert not any(word in lower for word in FORBIDDEN)
    assert not any(name in text for name in KID_NAMES)
```

В `tools/tests/test_build_site.py`:

```python
def test_program_page_is_published(tmp_path):
    out = build(tmp_path)
    assert (out / "program.html").is_file()
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd tools && .venv/bin/python -m pytest -q tests/test_program_page.py tests/test_build_site.py::test_program_page_is_published`
Expected: FAIL — `FileNotFoundError: program.html`.

- [ ] **Step 3: Написать `program.html`**

```html
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>Программа года · Junior_IT</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@700&family=Manrope:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a14; --card: #1a1a2e; --card-2: #16213e; --deep: #0f3460;
    --yellow: #ffd60a; --cyan: #00ffc8; --text: #e8e8f0; --muted: #9aa0b5;
    --track-book: #7aa2ff; --track-py: #00ffc8; --track-pas: #ff5722;
    --track-ops: #00e676; --track-cs: #ff0096; --track-web: #8892b0;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { background: var(--bg); color: var(--text); font-family: 'Manrope', sans-serif; line-height: 1.55; }
  body { padding: 20px 16px 60px; }
  .container { max-width: 760px; margin: 0 auto; }
  h1, h2, h3 { font-family: 'Rubik', sans-serif; }
  header h1 { font-size: clamp(26px, 6vw, 34px); }
  .kicker { font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: .08em; color: var(--yellow); text-transform: uppercase; }
  .goal { margin-top: 10px; font-size: 17px; font-weight: 600; }
  .disclaimer { margin-top: 8px; font-size: 13px; color: var(--muted); }
  .switch { display: flex; gap: 6px; margin: 20px 0; padding: 4px; background: var(--card); border-radius: 14px;
            position: sticky; top: env(safe-area-inset-top, 0px); z-index: 2; }
  .switch button { flex: 1; padding: 10px 6px; border: 0; border-radius: 10px; background: transparent; color: var(--muted);
                   font: 600 14px 'Manrope', sans-serif; cursor: pointer; }
  .switch button[aria-pressed="true"] { background: var(--deep); color: var(--text); }
  .principles, .month, .next-year { background: var(--card); border-radius: 16px; padding: 16px 18px; margin-bottom: 12px; }
  .principles li { margin: 6px 0 6px 18px; }
  .month { border: 1px solid transparent; }
  .month[data-status="current"] { border-color: var(--yellow); }
  .month[data-status="done"] { opacity: .72; }
  .month-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; flex-wrap: wrap; }
  .month-head h2 { font-size: 18px; }
  .month-label { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--muted); }
  .month-label.now { color: var(--yellow); }
  .outcome, .why { margin-top: 8px; }
  .meta-line { margin-top: 8px; font-size: 13px; color: var(--muted); }
  .modules { list-style: none; margin-top: 10px; }
  .module { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 8px 0; border-top: 1px solid rgba(255,255,255,.06); }
  .module-title { flex: 1 1 200px; }
  .chip { font-family: 'JetBrains Mono', monospace; font-size: 11px; padding: 2px 7px; border-radius: 6px;
          background: rgba(255,255,255,.08); color: var(--track-color, var(--cyan)); }
  .status { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); }
  .status[data-status="done"] { color: var(--track-ops); }
  .status[data-status="current"] { color: var(--yellow); }
  .links { display: flex; gap: 6px; flex-wrap: wrap; width: 100%; }
  .links a { font-family: 'JetBrains Mono', monospace; font-size: 11px; padding: 3px 8px; border-radius: 6px;
             background: rgba(255,255,255,.08); color: inherit; text-decoration: none; }
  .links a:hover { background: var(--track-color, var(--cyan)); color: var(--bg); }
  .events { margin-top: 8px; font-size: 14px; color: var(--muted); }
  .next-year { background: var(--card-2); }
  footer { margin-top: 32px; font-size: 13px; color: var(--muted); }
  footer a { color: var(--yellow); }
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="kicker">Junior_IT · программа года</div>
    <h1 id="title">Программа года</h1>
    <p class="goal" id="goal"></p>
    <p class="disclaimer" id="disclaimer"></p>
  </header>

  <div class="switch" role="group" aria-label="Ракурс">
    <button type="button" data-view="student">Ученику</button>
    <button type="button" data-view="parents">Родителям</button>
    <button type="button" data-view="why">Почему так</button>
  </div>

  <main id="program"><p class="meta-line">Загружаю программу…</p></main>

  <footer>Junior_IT · <a href="index.html">на главную</a> · <a href="index.html#hub">карта курса</a></footer>
</div>

<script>
  (function () {
    var VIEWS = ['student', 'parents', 'why'];
    var TRACK_TOKENS = { book: '--track-book', python: '--track-py', pascal: '--track-pas',
                         devops: '--track-ops', cs: '--track-cs', web: '--track-web' };
    var TRACK_CHIPS = { book: 'BOOK', python: 'PY', pascal: 'PAS', devops: 'OPS', cs: 'CS', web: 'WEB' };
    var MODULE_STATUS = { done: 'пройден', current: 'сейчас', planned: 'впереди', library: 'архив' };
    var BLOCK_STATUS = { done: 'прошли', current: 'сейчас', upcoming: 'впереди' };
    var MATERIALS = [['slides', 'слайды'], ['cheatsheet', 'шпаргалка'], ['glossary', 'словарик'], ['homework', 'домашка']];
    var program = null;

    function currentView() {
      var fromHash = location.hash.replace('#', '');
      if (VIEWS.indexOf(fromHash) !== -1) return fromHash;
      try {
        var saved = localStorage.getItem('program-view');
        if (VIEWS.indexOf(saved) !== -1) return saved;
      } catch (e) {}
      return 'parents';
    }

    function el(tag, className, text) {
      var node = document.createElement(tag);
      if (className) node.className = className;
      if (text) node.textContent = text;
      return node;
    }

    function renderModule(m) {
      var li = el('li', 'module');
      li.style.setProperty('--track-color', 'var(' + (TRACK_TOKENS[m.track] || '--cyan') + ')');
      li.appendChild(el('span', 'chip', TRACK_CHIPS[m.track] || m.track));
      li.appendChild(el('span', 'module-title', m.title));
      var status = el('span', 'status', MODULE_STATUS[m.status] || m.status);
      status.dataset.status = m.status;
      li.appendChild(status);
      var links = m.links || {};
      var row = el('span', 'links');
      MATERIALS.forEach(function (pair) {
        if (!links[pair[0]]) return;
        var a = el('a', null, pair[1]);
        a.href = links[pair[0]];
        row.appendChild(a);
      });
      if (row.childNodes.length) li.appendChild(row);
      return li;
    }

    function renderBlock(block, view) {
      var card = el('section', 'month');
      card.dataset.status = block.status;
      var head = el('div', 'month-head');
      head.appendChild(el('h2', null, block.label + ' · ' + block.title));
      var label = el('span', 'month-label' + (block.status === 'current' ? ' now' : ''), BLOCK_STATUS[block.status] || '');
      head.appendChild(label);
      card.appendChild(head);

      if (view === 'student') {
        if (block.modules.length) {
          var list = el('ul', 'modules');
          block.modules.forEach(function (m) { list.appendChild(renderModule(m)); });
          card.appendChild(list);
        }
        if (block.events.length) card.appendChild(el('p', 'events', block.events.join(' · ')));
      } else if (view === 'parents') {
        card.appendChild(el('p', 'outcome', block.outcome));
        if (block.textbook.length) {
          card.appendChild(el('p', 'meta-line', 'Учебник: ' + block.textbook.map(function (t) { return t.label; }).join(', ')));
        }
        if (block.trainer.length) {
          card.appendChild(el('p', 'meta-line', 'Зачёт: ' + block.trainer.map(function (t) { return t.label; }).join(', ')));
        }
      } else {
        card.appendChild(el('p', 'why', block.why));
      }
      return card;
    }

    function render(view) {
      var root = document.getElementById('program');
      root.textContent = '';
      document.getElementById('goal').textContent = view === 'student' ? program.goal.student : program.goal.parents;
      if (view === 'why') {
        var box = el('div', 'principles');
        box.appendChild(el('h3', null, 'Принципы'));
        var ul = el('ul');
        program.principles.forEach(function (p) { ul.appendChild(el('li', null, p)); });
        box.appendChild(ul);
        root.appendChild(box);
      }
      program.blocks.forEach(function (b) { root.appendChild(renderBlock(b, view)); });
      if (view === 'why') {
        var next = el('div', 'next-year');
        next.appendChild(el('h3', null, 'Куда дальше'));
        next.appendChild(el('p', null, program.next_year));
        root.appendChild(next);
      }
    }

    function setView(view) {
      if (location.hash !== '#' + view) history.replaceState(null, '', '#' + view);
      try { localStorage.setItem('program-view', view); } catch (e) {}
      document.querySelectorAll('.switch button').forEach(function (b) {
        b.setAttribute('aria-pressed', String(b.dataset.view === view));
      });
      if (program) render(view);
    }

    document.querySelectorAll('.switch button').forEach(function (b) {
      b.addEventListener('click', function () { setView(b.dataset.view); });
    });
    window.addEventListener('hashchange', function () { setView(currentView()); });
    setView(currentView());

    fetch('program.json')
      .then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
      .then(function (data) {
        program = data;
        document.getElementById('title').textContent = 'Программа года ' + data.year;
        document.getElementById('disclaimer').textContent = data.disclaimer;
        render(currentView());
      })
      .catch(function () {
        document.getElementById('program').textContent = 'Программа пока не собрана — загляни позже.';
      });
  })();
</script>
</body>
</html>
```

- [ ] **Step 4: Добавить `program.html` в белый список `tools/build_site.sh`**

В массив `PUBLISH=(` после `index.html` добавить строку `  program.html`.

- [ ] **Step 5: Убедиться, что тесты проходят**

Run: `cd tools && .venv/bin/python -m pytest -q`
Expected: всё зелёное.

- [ ] **Step 6: Проверка в браузере на 400px**

Собрать сайт `PYBIN=tools/.venv/bin/python tools/build_site.sh /tmp/jit-site`, поднять `python3 -m http.server 8765` из `/tmp/jit-site`, открыть `http://127.0.0.1:8765/program.html#student`, `#parents`, `#why` при ширине 400px (Playwright MCP или Chrome). Проверить: нет горизонтального скролла (`document.documentElement.scrollWidth <= 400`), текущий месяц подсвечен жёлтой рамкой, переключатель липнет к верху, чипы материалов у сентябрьских модулей ведут на существующие страницы. Скриншоты трёх ракурсов приложить к отчёту. Открыть `program.html` без `program.json` (например, из папки репо через file://) — видна фраза «Программа пока не собрана».

- [ ] **Step 7: Коммит**

```bash
git add program.html tools/build_site.sh tools/tests/test_program_page.py tools/tests/test_build_site.py
git commit -m "feat(program): страница программы года с ракурсами Ученику / Родителям / Почему так"
```

---

### Task 6: Ссылки с лендинга

**Files:**
- Modify: `index.html` (hero `btn-row` строка ~447; блок ссылок под картой строка ~532)
- Test: `tools/tests/test_landing.py`

**Interfaces:**
- Consumes: `program.html` (Task 5).
- Produces: две ссылки `href="program.html"` на лендинге.

- [ ] **Step 1: Написать падающий тест**

```python
def test_landing_links_to_program_page():
    text = landing_text()
    assert text.count('href="program.html"') >= 2
    assert "Программа года" in text
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `cd tools && .venv/bin/python -m pytest -q tests/test_landing.py::test_landing_links_to_program_page`
Expected: FAIL на `count >= 2`.

- [ ] **Step 3: Правки в `index.html`**

В hero, после строки `<a class="btn btn-outline" href="#how">Как проходят занятия</a>`:

```html
          <a class="btn btn-outline" href="program.html">Программа года</a>
```

В блоке ссылок под картой, перед `<a class="setup-link" href="trainer/">Тренажёр →</a>`:

```html
        <a class="setup-link" href="program.html">Программа года →</a>
```

Кнопка «Домашка сейчас» добавляется скриптом в конец `btn-row`, порядок в hero станет: Карта курса · Как проходят занятия · Программа года · Домашка сейчас — на телефоне четыре кнопки в столбик, это допустимо, но проверить скриншотом.

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `cd tools && .venv/bin/python -m pytest -q`
Expected: всё зелёное.

- [ ] **Step 5: Бренд-проверка и скриншот**

`/brand-check` (brand-guardian) на `program.html`, `meta/program.yml`, правки `index.html`. Скриншот hero лендинга на 400px с четырьмя кнопками. Замечания исправить до коммита.

- [ ] **Step 6: Коммит**

```bash
git add index.html tools/tests/test_landing.py
git commit -m "feat(landing): ссылки на программу года из hero и блока ссылок"
```

Деплой — отдельно по слову Димаса (`/deploy`), пуш в план не входит.
