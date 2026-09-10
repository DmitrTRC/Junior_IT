# Публичное лицо курса: генератор карты, лендинг, README — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Заменить витрину курса: лендинг с живой картой курса и терминалом-героем, README с нуля, данные прогресса — генерацией из файлов курса.

**Architecture:** `tools/build_course_map.py` собирает `course-map.json` из `tracks/*/*/module.yml` и `playground/*/session.yml` (никаких других источников). Лендинг — один самодостаточный `index.html`: витрина работает без JS, хаб рендерит JSON чистым JS с fallback-блоком. README — статический документ с mermaid-диаграммой и матрицей видимости.

**Tech Stack:** Python 3.12 + PyYAML + pytest (генератор), статический HTML/CSS/JS без библиотек (лендинг), Markdown + mermaid (README), bash (сборка).

**Spec:** `docs/superpowers/specs/2026-09-11-public-face-design.md`

## Global Constraints

- **Позиционирование, дословно:** «Углублённая информатика и программирование · 7–8 классы». Имя курса — **Junior_IT**, не меняется.
- **Цвета треков** (тёмный фон / печать): book `#7aa2ff`/`#2b4fa8`, python `#00ffc8`/`#00806a`, pascal `#ff5722`/`#b3350f`, devops `#00e676`/`#00803d`, cs `#ff0096`/`#a8005f`, web `#8892b0`/`#4a5568`. Базовая палитра: `--bg #0a0a14`, `--card #1a1a2e`, `--card-2 #16213e`, `--deep #0f3460`, `--yellow #ffd60a`, `--green #00e676`, `--cyan #00ffc8`, `--magenta #ff0096`, `--bg-light #faf7f2`. Источник истины — `meta/brand-tokens.css`.
- **Шрифты:** Rubik 700 заголовки, Manrope 400/500/600 текст, JetBrains Mono 400/700 код и чипы. Google Fonts — единственный внешний ресурс.
- **HTML самодостаточен:** стили инлайном, JS инлайном, без CDN и библиотек.
- **Автор описывается нейтрально:** senior-разработчик, 30+ лет в индустрии, стек, ссылка на GitHub. **Никаких упоминаний ЮДО, ОТО, отделов полиции, ведомств.**
- **Жёсткие запреты (блокируют публикацию):** символика СССР, ФСБ, силовых ведомств, политически нагруженные знаки; слова «дружина», «отряд» — нигде; в текстах для родителей нет слов «контроль», «проверки», «инспекции», «кружковая методика как в школе».
- **`teacher/` и `live-code.md` не публикуются** и не получают ссылок с публикуемых страниц.
- Идентификаторы английские, тексты русские. Термины парой ру/en. Без эмодзи в коммитах и именах файлов.
- Правки хирургические: `CLAUDE.md` и `meta/project-instructions.md` — только перечисленные строки; раздел жёстких запретов в `CLAUDE.md` не трогать.
- Тесты: `cd tools && .venv/bin/python -m pytest -v`. Сейчас 36, после плана 59.
- Валидатор модулей должен оставаться зелёным: `cd tools && .venv/bin/python validate_modules.py ..`.
- Анимации уважают `prefers-reduced-motion` (статичный финальный кадр).
- Ветка `public-face` уже создана, работать в ней.

---

### Task 1: Генератор — сбор модулей и статусы

**Files:**
- Create: `tools/build_course_map.py`
- Create: `tools/tests/test_build_course_map.py`

**Interfaces:**
- Consumes: `yaml`, `pathlib` (окружение `tools/.venv` готово); структуры `tracks/*/*/module.yml` (поля `id, track, title, level, minutes, textbook`) и `playground/*/session.yml` (поля `date, theme, playlist: [{module, minutes}]`, опционально `completed: [id]`).
- Produces:
  - `TRACKS_META: list[dict]` — фиксированный порядок шести треков: `{"id": "book", "title": "Учебник", "chip": "BOOK"}`, `{"id": "python", "title": "Python", "chip": "PY"}`, `{"id": "pascal", "title": "Pascal", "chip": "PAS"}`, `{"id": "devops", "title": "DevOps", "chip": "OPS"}`, `{"id": "cs", "title": "Компьютер изнутри", "chip": "CS"}`, `{"id": "web", "title": "Web (архив)", "chip": "WEB"}`
  - `load_modules(repo_root: Path) -> list[dict]` — по одному dict на модуль, поля манифеста как есть
  - `load_sessions(repo_root: Path) -> list[dict]` — отсортированы по дате, `date` приведён к `datetime.date`
  - `module_statuses(modules, sessions, today: date) -> dict[str, str]` — id модуля → `done|current|planned|library`

- [ ] **Step 1: Написать падающие тесты**

`tools/tests/test_build_course_map.py`:

```python
from datetime import date
from pathlib import Path

import pytest
import yaml

from build_course_map import load_modules, load_sessions, module_statuses

TODAY = date(2026, 9, 12)


def make_module(repo_root, module_id, level="core", minutes=25, textbook=None,
                shared=("slides.html",), student=("cheatsheet.html",)):
    """Модуль на диске: манифест + файлы ролей."""
    track, name = module_id.split("/")
    module_dir = repo_root / "tracks" / track / name
    for role in ("shared", "student", "teacher"):
        (module_dir / role).mkdir(parents=True)
    for f in shared:
        (module_dir / "shared" / f).write_text("x", encoding="utf-8")
    for f in student:
        (module_dir / "student" / f).write_text("x", encoding="utf-8")
    (module_dir / "teacher" / "scenario.md").write_text("x", encoding="utf-8")
    manifest = {
        "id": module_id, "title": f"Тест {name} (test)", "track": track,
        "level": level, "minutes": minutes, "textbook": textbook or [],
    }
    (module_dir / "module.yml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    return module_dir


def make_session(repo_root, day, modules, completed=None, theme="Тема"):
    session_dir = repo_root / "playground" / day.isoformat()
    session_dir.mkdir(parents=True)
    data = {
        "date": day.isoformat(), "theme": theme,
        "playlist": [{"module": m, "minutes": 25} for m in modules],
    }
    if completed is not None:
        data["completed"] = completed
    (session_dir / "session.yml").write_text(
        yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_collects_all_modules_with_fields(tmp_path):
    make_module(tmp_path, "book/m-01-info", textbook=["7:1.1"])
    make_module(tmp_path, "web/m-01-html", level="optional")
    modules = load_modules(tmp_path)
    assert {m["id"] for m in modules} == {"book/m-01-info", "web/m-01-html"}
    info = next(m for m in modules if m["id"] == "book/m-01-info")
    assert info["textbook"] == ["7:1.1"] and info["minutes"] == 25


def test_sessions_sorted_and_dates_parsed(tmp_path):
    make_session(tmp_path, date(2026, 9, 20), ["a/b"])
    make_session(tmp_path, date(2026, 9, 13), ["c/d"])
    sessions = load_sessions(tmp_path)
    assert [s["date"] for s in sessions] == [date(2026, 9, 13), date(2026, 9, 20)]


def test_status_done_for_past_session(tmp_path):
    make_module(tmp_path, "book/m-01-info")
    make_session(tmp_path, date(2026, 9, 10), ["book/m-01-info"])
    statuses = module_statuses(load_modules(tmp_path), load_sessions(tmp_path), TODAY)
    assert statuses["book/m-01-info"] == "done"


def test_status_current_for_next_upcoming_session(tmp_path):
    make_module(tmp_path, "python/m-01-run")
    make_module(tmp_path, "book/m-02-later")
    make_session(tmp_path, date(2026, 9, 13), ["python/m-01-run"])
    make_session(tmp_path, date(2026, 9, 16), ["book/m-02-later"])
    statuses = module_statuses(load_modules(tmp_path), load_sessions(tmp_path), TODAY)
    assert statuses["python/m-01-run"] == "current"
    assert statuses["book/m-02-later"] == "planned"


def test_session_today_is_current(tmp_path):
    make_module(tmp_path, "python/m-01-run")
    make_session(tmp_path, TODAY, ["python/m-01-run"])
    statuses = module_statuses(load_modules(tmp_path), load_sessions(tmp_path), TODAY)
    assert statuses["python/m-01-run"] == "current"


def test_status_planned_when_not_scheduled(tmp_path):
    make_module(tmp_path, "cs/m-01-computer")
    statuses = module_statuses(load_modules(tmp_path), [], TODAY)
    assert statuses["cs/m-01-computer"] == "planned"


def test_status_library_for_optional(tmp_path):
    make_module(tmp_path, "web/m-01-html", level="optional")
    make_session(tmp_path, date(2026, 9, 10), ["web/m-01-html"])
    statuses = module_statuses(load_modules(tmp_path), load_sessions(tmp_path), TODAY)
    assert statuses["web/m-01-html"] == "library"


def test_completed_field_overrides_playlist(tmp_path):
    make_module(tmp_path, "book/m-01-info")
    make_module(tmp_path, "python/m-01-run")
    make_session(tmp_path, date(2026, 9, 10),
                 ["book/m-01-info", "python/m-01-run"],
                 completed=["book/m-01-info"])
    statuses = module_statuses(load_modules(tmp_path), load_sessions(tmp_path), TODAY)
    assert statuses["book/m-01-info"] == "done"
    assert statuses["python/m-01-run"] == "planned"


def test_empty_playground_yields_no_done(tmp_path):
    make_module(tmp_path, "book/m-01-info")
    assert load_sessions(tmp_path) == []
    statuses = module_statuses(load_modules(tmp_path), [], TODAY)
    assert "done" not in statuses.values()
```

- [ ] **Step 2: Убедиться, что падают**

Run: `cd tools && .venv/bin/python -m pytest tests/test_build_course_map.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_course_map'`

- [ ] **Step 3: Реализация**

`tools/build_course_map.py`:

```python
#!/usr/bin/env python3
"""Собирает course-map.json для лендинга из манифестов и журналов занятий.

Единственные источники правды — tracks/*/*/module.yml и
playground/*/session.yml. Атлас и прочие документы не читаются:
меньше парсеров — меньше расхождений.
"""

import json
import sys
from datetime import date
from pathlib import Path

import yaml

POSITIONING = "Углублённая информатика и программирование · 7–8 классы"

TRACKS_META = [
    {"id": "book", "title": "Учебник", "chip": "BOOK"},
    {"id": "python", "title": "Python", "chip": "PY"},
    {"id": "pascal", "title": "Pascal", "chip": "PAS"},
    {"id": "devops", "title": "DevOps", "chip": "OPS"},
    {"id": "cs", "title": "Компьютер изнутри", "chip": "CS"},
    {"id": "web", "title": "Web (архив)", "chip": "WEB"},
]


def load_modules(repo_root):
    modules = []
    for manifest in sorted(Path(repo_root).glob("tracks/*/*/module.yml")):
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        data["_dir"] = manifest.parent
        modules.append(data)
    return modules


def load_sessions(repo_root):
    sessions = []
    for path in sorted(Path(repo_root).glob("playground/*/session.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "date" not in data:
            continue
        data["date"] = date.fromisoformat(str(data["date"]))
        sessions.append(data)
    return sorted(sessions, key=lambda s: s["date"])


def _playlist_ids(session):
    return [item["module"] for item in session.get("playlist") or []]


def module_statuses(modules, sessions, today):
    """id модуля -> done | current | planned | library."""
    done, current = set(), set()
    for session in sessions:
        if session["date"] < today:
            if "completed" in session:
                done.update(session["completed"] or [])
            else:
                done.update(_playlist_ids(session))
    upcoming = [s for s in sessions if s["date"] >= today]
    if upcoming:
        current.update(_playlist_ids(upcoming[0]))

    statuses = {}
    for module in modules:
        mid = module["id"]
        if module.get("level") == "optional":
            statuses[mid] = "library"
        elif mid in done:
            statuses[mid] = "done"
        elif mid in current:
            statuses[mid] = "current"
        else:
            statuses[mid] = "planned"
    return statuses


if __name__ == "__main__":
    raise SystemExit(main())
```

Ссылка на `main` в хвосте — задел под Task 2; чтобы Step 4 прошёл, добавь
временную заглушку `def main(argv=None): return 0` над `if __name__` (Task 2
заменит её настоящей).

- [ ] **Step 4: Прогнать тесты**

Run: `cd tools && .venv/bin/python -m pytest -v`
Expected: PASS, 45 тестов (36 + 9)

- [ ] **Step 5: Commit**

```bash
git add tools/build_course_map.py tools/tests/test_build_course_map.py
git commit -m "tools: генератор карты курса — сбор модулей и статусы"
```

---

### Task 2: Генератор — links, счётчики, JSON, CLI, сборка

**Files:**
- Modify: `tools/build_course_map.py`
- Modify: `tools/tests/test_build_course_map.py`
- Modify: `tools/build_site.sh` (один новый шаг)
- Modify: `tools/tests/test_build_site.py` (один тест)
- Modify: `.gitignore` (одна строка)

**Interfaces:**
- Consumes: всё из Task 1.
- Produces:
  - `module_links(module: dict) -> dict` — только существующие файлы: `{"slides": "tracks/.../shared/slides.html", "cheatsheet": "tracks/.../student/cheatsheet.html"}`; ключ отсутствует, если файла нет; `teacher/` и `live-code.md` не попадают никогда
  - `build_course_map(repo_root: Path, today: date) -> dict` — полный словарь по контракту спеки: `generated_at, positioning, tracks, modules, next_session, counters`
  - `main(argv=None) -> int` — CLI `build_course_map.py [корень] [выходной файл]`, по умолчанию корень репо и `course-map.json` в нём; код 1 и сообщение в stderr при нечитаемом манифесте

- [ ] **Step 1: Дописать падающие тесты**

Добавить в `tools/tests/test_build_course_map.py`:

```python
import json

from build_course_map import build_course_map, main


def test_links_only_existing_files(tmp_path):
    make_module(tmp_path, "book/m-01-info", student=())  # нет шпаргалки
    result = build_course_map(tmp_path, TODAY)
    module = result["modules"][0]
    assert module["links"] == {"slides": "tracks/book/m-01-info/shared/slides.html"}


def test_links_never_teacher_or_livecode(tmp_path):
    make_module(tmp_path, "book/m-01-info",
                shared=("slides.html", "live-code.md"))
    result = build_course_map(tmp_path, TODAY)
    dumped = json.dumps(result)
    assert "teacher/" not in dumped
    assert "live-code.md" not in dumped


def test_counters(tmp_path):
    make_module(tmp_path, "book/m-01-info", textbook=["7:1.1"])
    make_module(tmp_path, "devops/m-01-term", textbook=["7:2.3"])
    make_module(tmp_path, "web/m-01-html", level="optional")
    make_session(tmp_path, date(2026, 9, 10),
                 ["book/m-01-info", "devops/m-01-term"])
    counters = build_course_map(tmp_path, TODAY)["counters"]
    assert counters == {"modules_done": 2, "modules_core_total": 2,
                        "paragraphs_closed": 2}


def test_next_session_earliest_future(tmp_path):
    make_module(tmp_path, "python/m-01-run")
    make_session(tmp_path, date(2026, 9, 16), ["python/m-01-run"], theme="Git")
    make_session(tmp_path, date(2026, 9, 20), ["python/m-01-run"])
    ns = build_course_map(tmp_path, TODAY)["next_session"]
    assert ns["date"] == "2026-09-16" and ns["theme"] == "Git"
    assert ns["modules"] == ["python/m-01-run"]


def test_no_future_session_gives_null(tmp_path):
    make_module(tmp_path, "book/m-01-info")
    make_session(tmp_path, date(2026, 9, 10), ["book/m-01-info"])
    assert build_course_map(tmp_path, TODAY)["next_session"] is None


def test_main_writes_valid_json(tmp_path):
    make_module(tmp_path, "book/m-01-info")
    out = tmp_path / "course-map.json"
    assert main([str(tmp_path), str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["positioning"].startswith("Углублённая")
    assert "generated_at" in data
    assert [t["id"] for t in data["tracks"]] == \
        ["book", "python", "pascal", "devops", "cs", "web"]


def test_main_fails_loudly_on_broken_manifest(tmp_path, capsys):
    module_dir = tmp_path / "tracks" / "book" / "m-01-bad"
    module_dir.mkdir(parents=True)
    (module_dir / "module.yml").write_text("id: [unclosed", encoding="utf-8")
    assert main([str(tmp_path), str(tmp_path / "out.json")]) == 1
    assert "m-01-bad" in capsys.readouterr().err
```

- [ ] **Step 2: Убедиться, что падают**

Run: `cd tools && .venv/bin/python -m pytest tests/test_build_course_map.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_course_map'`

- [ ] **Step 3: Реализация**

Дописать в `tools/build_course_map.py` (заглушку `main` заменить):

```python
def module_links(module):
    """Ссылки только на реально существующие публикуемые файлы."""
    module_dir = module["_dir"]
    rel = f"tracks/{module['id']}"
    links = {}
    if (module_dir / "shared" / "slides.html").is_file():
        links["slides"] = f"{rel}/shared/slides.html"
    if (module_dir / "student" / "cheatsheet.html").is_file():
        links["cheatsheet"] = f"{rel}/student/cheatsheet.html"
    return links


def build_course_map(repo_root, today):
    modules = load_modules(repo_root)
    sessions = load_sessions(repo_root)
    statuses = module_statuses(modules, sessions, today)

    out_modules = []
    for m in modules:
        out_modules.append({
            "id": m["id"], "track": m["track"], "title": m["title"],
            "level": m["level"], "minutes": m["minutes"],
            "textbook": m.get("textbook") or [],
            "status": statuses[m["id"]],
            "links": module_links(m),
        })

    upcoming = [s for s in sessions if s["date"] >= today]
    next_session = None
    if upcoming:
        s = upcoming[0]
        next_session = {"date": s["date"].isoformat(),
                        "theme": s.get("theme", ""),
                        "modules": _playlist_ids(s)}

    done = [m for m in out_modules if m["status"] == "done"]
    core_total = sum(1 for m in out_modules if m["level"] in ("core", "deep"))
    paragraphs = {ref for m in done for ref in m["textbook"]}

    return {
        "generated_at": today.isoformat(),
        "positioning": POSITIONING,
        "tracks": TRACKS_META,
        "modules": out_modules,
        "next_session": next_session,
        "counters": {"modules_done": len(done),
                     "modules_core_total": core_total,
                     "paragraphs_closed": len(paragraphs)},
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    repo_root = Path(args[0]) if args else Path(__file__).resolve().parent.parent
    out_path = Path(args[1]) if len(args) > 1 else repo_root / "course-map.json"
    try:
        course_map = build_course_map(repo_root, date.today())
    except (yaml.YAMLError, KeyError, ValueError) as exc:
        broken = [p.parent.name for p in Path(repo_root).glob("tracks/*/*/module.yml")]
        print(f"course-map: не удалось собрать карту ({exc}); "
              f"модули: {broken}", file=sys.stderr)
        return 1
    out_path.write_text(
        json.dumps(course_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(f"карта курса: {out_path}")
    return 0
```

Замечание к сообщению об ошибке: тест проверяет, что имя сломанного модуля
попадает в stderr — перечисление всех манифестов в сообщении это
обеспечивает; точнее локализовать необязательно.

- [ ] **Step 4: Шаг сборки и gitignore**

В `tools/build_site.sh` после rsync, перед финальным `echo` (локально работает
`.venv`, в CI его нет — поэтому интерпретатор переопределяем переменной):

```bash
PYBIN="${PYBIN:-$ROOT/tools/.venv/bin/python}"
"$PYBIN" "$ROOT/tools/build_course_map.py" "$ROOT" "$OUT/course-map.json"
```

В `.github/workflows/deploy.yml` перед шагом Build site:

```yaml
      - name: Setup Python for course map
        run: pip install pyyaml
```

и сам шаг сборки запускать как `PYBIN=python3 ./tools/build_site.sh _site`.

В `.gitignore` после строки `_site/`:

```gitignore
# Артефакт сборки карты курса
course-map.json
```

В `tools/tests/test_build_site.py` добавить:

```python
def test_course_map_generated_and_valid(tmp_path):
    import json
    out = build(tmp_path)
    data = json.loads((out / "course-map.json").read_text(encoding="utf-8"))
    assert data["modules"], "карта не должна быть пустой на живом репо"
```

- [ ] **Step 5: Прогнать всё**

Run: `cd tools && .venv/bin/python -m pytest -v`
Expected: PASS, 53 теста (45 + 7 + 1)

Run: `./tools/build_site.sh /tmp/jit_map && python3 -c "import json;d=json.load(open('/tmp/jit_map/course-map.json'));print(d['counters'], d['next_session']['date'] if d['next_session'] else None)"`
Expected: счётчики по живому репо; next_session `2026-09-13`

- [ ] **Step 6: Commit**

```bash
git add tools/build_course_map.py tools/tests/test_build_course_map.py tools/build_site.sh tools/tests/test_build_site.py .gitignore .github/workflows/deploy.yml
git commit -m "tools: карта курса собирается в course-map.json на сборке сайта"
```

---

### Task 3: Лендинг — витрина

**Files:**
- Modify: `index.html` (полная замена содержимого)

**Interfaces:**
- Consumes: токены из `meta/brand-tokens.css`; тексты ниже.
- Produces: этаж «Витрина» целиком + статический fallback-блок хаба с якорем `id="hub"` и контейнером `id="course-map"` — Task 4 заменит содержимое контейнера JS-картой, не трогая витрину.

- [ ] **Step 1: Снять эталон старого лендинга**

```bash
git show HEAD:index.html > /tmp/old-landing.html
```

Старый файл — источник приёмов (SVG-паттерны, сетка карточек), но контент
не переносится: он описывает старый курс.

- [ ] **Step 2: Написать витрину**

Полная замена `index.html`. Требования к содержимому — точные:

**Шапка `<head>`:** `<title>Junior_IT — углублённая информатика и программирование</title>`, мета-описание «Индивидуальный курс информатики и программирования для 7–8 классов: школьный учебник с опережением, Python, настоящие инструменты разработчика», viewport, Google Fonts (Rubik 700, Manrope 400;500;600;700, JetBrains Mono 400;700 — сабсет cyrillic у всех трёх проверен ранее). Весь CSS в `<style>`, блок токенов скопирован из `meta/brand-tokens.css` с комментарием-указателем на источник.

**Герой** — грид две колонки (на узком экране — одна, терминал под текстом):

Левая колонка:
- бейдж-строка малым капсом: `7–8 классы · два занятия в неделю · один на один`
- `<h1>Junior_IT</h1>` (Rubik 700, крупно)
- подзаголовок: `Углублённая информатика и программирование · 7–8 классы` (цвет `--yellow`)
- строка-крючок: `Школьный учебник — с опережением. Инструменты — настоящие.`
- две кнопки: `Карта курса` (якорь `#hub`, заливка `--cyan`, текст `--bg`) и `Как проходят занятия` (якорь `#how`, обводка)

Правая колонка — окно терминала: рамка `--card`, скруглённая, три точки-светофора (`#ff5f57`, `#febc2e`, `#28c840`), фон тела `#0c0c11`, JetBrains Mono. JS печатает по символам сценарий:

```
$ python3 hello.py
Привет! Я учусь программировать
$ git push
✓ CI: все проверки пройдены
```

Строки с `$` — цвет `#7fd0ff`, вывод — `#e8e8f0`, галка — `--green`. Скорость ~45 мс/символ, пауза 700 мс между строками, по завершении курсор мигает; цикл не повторяется (одного прохода достаточно, повтор раздражает). При `prefers-reduced-motion: reduce` — все четыре строки показаны сразу, курсор без анимации. Терминал — `aria-hidden="true"`, это декор.

**Три карточки сути** (секция `id="how"`, грид 3×1, на узком — столбик), каждая с чипом-меткой в цвете трека:

1. Чип `BOOK` (цвет `--track-book`) — **Учебник — с опережением**: «Идём по школьному учебнику информатики — на главу впереди класса по теории и на год по программированию. Тесты учебника сдаём все, плюс свои.»
2. Чип `PY` (цвет `--track-py`) — **Инструменты — настоящие**: «Терминал, git и тесты, которые сами прогоняют домашку, — то, чем работают взрослые разработчики. Не учебная песочница, а настоящий Python на настоящем компьютере.»
3. Чип `1:1` (цвет `--green`) — **Один на один**: «Ученик пишет код сам — преподаватель рядом. Теория блоками не дольше двух минут, остальное — руки на клавиатуре.»

**Блок «Кто ведёт»** (узкая полоса, `--card-2`): «Ведёт Дмитрий Морозов — senior-разработчик, 30+ лет в индустрии: ASM, C/C++, Python, JS/TS, Go, Rust. Материалы курса открыты — методику можно читать на GitHub.» Ссылка на `https://github.com/DmitrTRC/Junior_IT`.

**Fallback-хаб** (секция `id="hub"`): заголовок `Карта курса`, контейнер `<div id="course-map">` со статическим содержимым — шесть карточек треков (чип, название из TRACKS_META, одна строка описания: Учебник — «теория по Босовой, 7–8 класс»; Python — «основной язык курса»; Pascal — «второй диалект: тот же алгоритм, другой синтаксис»; DevOps — «терминал, git, зелёная галка CI»; Компьютер изнутри — «как это всё устроено под капотом»; Web (архив) — «HTML/CSS/JS — по запросу»). Карточки с левой полосой цвета трека, как в модулях. Ниже — заглушка `<div id="hub-extras">` (пустая, Task 4 наполнит) и плашка «Тренажёр — скоро» (приглушённая, без ссылки), рядом — ссылка «Настройка компьютера» на `docs/setup-guide.html`.

**Подвал:** «Junior_IT · материалы открыты · MIT» + ссылка на GitHub + строка `Сделано без конструкторов: HTML, CSS и ванильный JS.` Никаких организаций.

Запрещено в файле: слова «дружина», «отряд», «контроль», «проверки», «инспекции», упоминания ведомств; `position:absolute`-декорации в hero; цвета вне токенов (кроме светофора окна и Dracula-палитры консоли, узаконенных в `CLAUDE.md`).

- [ ] **Step 3: Проверить рендер локально**

Run: `cd /Users/dmitrymorozov/Projects/Junior_IT && python3 -m http.server 8017 &` затем открыть `http://localhost:8017/` (или headless-скриншот). Проверить: обе колонки героя на десктопе, столбик на 390px, терминал печатает, кнопка ведёт на `#hub`. Убить сервер.

- [ ] **Step 4: Прогнать grep запретов**

Run: `grep -inE "дружин|отряд|контрол|проверк|инспекц|полици|фсб|ссср|юдо|ото" index.html; echo "exit=$?"`
Expected: `exit=1` (ничего не найдено). Слово «автопроверка» не должно ловиться — если ловится, поправить паттерн проверки на границы слова, но текст карточки DevOps использовать «автопроверка» — при grep выше слово «проверк» его поймает: **использовать формулировку «домашки проверяет машина»** в карточке DevOps и fallback-описании, чтобы grep оставался простым. Проверить глазами каждое совпадение, если exit=0.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "landing: витрина — герой с терминалом, карточки сути, fallback-хаб"
```

---

### Task 4: Лендинг — живой хаб + тест лендинга

**Files:**
- Modify: `index.html` (JS хаба + стили карты; витрину не трогать)
- Create: `tools/tests/test_landing.py`

**Interfaces:**
- Consumes: `course-map.json` по контракту Task 2 (fetch относительным путём `course-map.json`); контейнеры `#course-map`, `#hub-extras` из Task 3.
- Produces: готовый лендинг.

- [ ] **Step 1: Написать падающий тест**

`tools/tests/test_landing.py`:

```python
import re
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LANDING = REPO / "index.html"

VOID = {"meta", "link", "br", "img", "hr", "input", "path", "circle",
        "rect", "line", "polyline", "stop", "use"}


class BalanceChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"несбалансированный </{tag}>")
        else:
            self.stack.pop()


def landing_text():
    return LANDING.read_text(encoding="utf-8")


def test_html_balanced():
    checker = BalanceChecker()
    checker.feed(landing_text())
    assert not checker.errors and not checker.stack


def test_positioning_and_identity_present():
    text = landing_text()
    assert "Углублённая информатика и программирование" in text
    assert "Junior_IT" in text


def test_no_forbidden_words():
    text = landing_text().lower()
    for word in ("дружин", "отряд", "инспекц", "полици", "фсб", "ссср", "юдо"):
        assert word not in text, word


def test_no_links_to_unpublished():
    text = landing_text()
    assert "teacher/" not in text
    assert "live-code.md" not in text
    assert "homework/" not in text


def test_fallback_tracks_present_without_js():
    text = landing_text()
    assert 'id="course-map"' in text
    for chip in ("BOOK", "PY", "PAS", "OPS", "CS", "WEB"):
        assert chip in text, chip


def test_fetches_course_map():
    assert re.search(r"fetch\(['\"]course-map\.json['\"]\)", landing_text())
```

- [ ] **Step 2: Убедиться в падении**

Run: `cd tools && .venv/bin/python -m pytest tests/test_landing.py -v`
Expected: FAIL минимум на `test_fetches_course_map` (JS ещё нет). Тесты витрины из Task 3 пройдут — это нормально.

- [ ] **Step 3: Написать JS хаба**

В конец `index.html` перед `</body>` — `<script>` без внешних зависимостей:

```javascript
(async function () {
  let map;
  try {
    const resp = await fetch('course-map.json');
    if (!resp.ok) return;                 // fallback-блок остаётся
    map = await resp.json();
  } catch (e) { return; }

  renderNextSession(map.next_session);
  renderCounters(map.counters);
  renderMap(map);
  renderQuickLinks(map.modules);
})();
```

Функции (все — построение DOM через `document.createElement`, без innerHTML с данными из JSON — данные свои, но дисциплина дешёвая):

- `renderNextSession(ns)` — если `ns` не null, карточка в начало `#hub-extras`: «Ближайшее занятие — <дата словами по-русски>, тема: <theme>» + список модулей (название из `map.modules` по id). Дата форматируется `new Intl.DateTimeFormat('ru', {day:'numeric', month:'long', weekday:'long'})`.
- `renderCounters(c)` — полоса из трёх позиций: `«Модулей пройдено N из M»` (`modules_done`/`modules_core_total`), `«Параграфов учебника закрыто K»`, статический бейдж `«Python — материал 8 класса, мы в 7-м»`.
- `renderMap(map)` — заменяет содержимое `#course-map`: для каждого трека из `map.tracks` — дорожка: слева вертикальная плашка с чипом (фон — цвет трека из CSS-переменной `--track-<id>`; соответствие id→токен захардкожено в JS-объекте: `{book:'--track-book', python:'--track-py', pascal:'--track-pas', devops:'--track-ops', cs:'--track-cs', web:'--track-web'}`), справа — горизонтальная лента узлов-модулей этого трека. Узел: скруглённая карточка с названием и минутами; `done` — заливка цветом трека, текст `--bg`; `current` — обводка цветом трека + CSS-анимация пульса (отключена при reduced-motion); `planned` — приглушённая (`opacity:.45`); модули `library` — не в дорожках, а отдельной свёрнутой секцией `«Архив web — по запросу»` ниже карты (details/summary). Пустая дорожка (`pascal`) — подпись «впереди» приглушённым текстом. Узел с непустым `links` — ссылка на `links.slides || links.cheatsheet`; без links — не ссылка. Тултип — `title`-атрибут: `«25 мин · §7:1.1»`. Лента узлов скроллится горизонтально внутри дорожки (`overflow-x:auto`), страница — нет.
- `renderQuickLinks(modules)` — в `#hub-extras`: до трёх последних `done`-модулей со шпаргалками (`links.cheatsheet`), подпись «Свежие шпаргалки». Если `done` нет — блок не рендерится.

Стили карты — в общий `<style>` (дорожки, узлы, пульс `@keyframes`, `@media (prefers-reduced-motion: reduce)` глушит анимацию, `@media (max-width: 720px)` — компактные узлы).

- [ ] **Step 4: Прогнать тесты и живой рендер**

Run: `cd tools && .venv/bin/python -m pytest -v`
Expected: PASS, 59 тестов (53 + 6)

Run: `./tools/build_site.sh /tmp/jit_hub && cd /tmp/jit_hub && python3 -m http.server 8018 &` — открыть, проверить: карта отрисовалась поверх fallback, три модуля `current` пульсируют (занятие 13.09 ещё впереди на дату сборки), web в свёрнутом архиве, pascal — «впереди», счётчики `0 из 6` (core: book 1, devops 1, python 1, cs 3). Убить сервер.

- [ ] **Step 5: Commit**

```bash
git add index.html tools/tests/test_landing.py
git commit -m "landing: живой хаб — карта курса, счётчики, ближайшее занятие"
```

---

### Task 5: README с нуля + баннер

**Files:**
- Modify: `README.md` (полная замена)
- Modify: `.github/assets/banner.svg` (подзаголовок)

**Interfaces:**
- Consumes: матрица видимости и FAQ из спеки (раздел README, дословно перенести смысл); TRACKS_META-названия треков.
- Produces: README — главный документ репозитория.

- [ ] **Step 1: Баннер**

Открыть `.github/assets/banner.svg`, заменить текст подзаголовка на «Углублённая информатика и программирование · 7–8 классы». Стиль, палитру, композицию не менять. Если текущий подзаголовок другой длины — подогнать кегль/позицию, чтобы не вылезал за рамку (проверить рендер: `open .github/assets/banner.svg`).

- [ ] **Step 2: README — десять блоков**

Полная замена `README.md`. Структура и обязательное содержимое:

1. Баннер (`<img>` на `.github/assets/banner.svg`), строка бейджей shields.io: Pages deploy (badge workflow), `license-MIT`, `классы-7–8`, `python-3.12`, `tests-59 passed`.
2. **Суть** — один абзац: индивидуальный курс углублённой информатики и программирования для 7–8 классов; опора — школьный учебник (Босова), ход — с опережением программы; основной язык Python; инструменты настоящие: терминал, git, автоматическая проверка домашних заданий. Тон — спокойная уверенность, без восклицательных знаков.
3. **Как устроено занятие**: 1:1 через Zoom, ученик сам за клавиатурой и делится экраном; два занятия в неделю (среда и воскресенье); 75 минут потолок; теория — блоками не дольше двух минут.
4. **Как работает ученик** — mermaid `flowchart LR`: `Занятие -->|в конце| Шпаргалка --> Домашка -->|ветка + PR| Свой_репозиторий -->|pytest| CI{Зелёная галка?}`; `CI -->|да| Merge --> Эталоны[Два эталонных решения + разбор]`; `CI -->|нет| Домашка`. Подпись: git и автопроверка включаются со второго занятия; до того домашки сдаются в мессенджер.
5. **Треки курса** — таблица: чип, название, что внутри, статус. Шесть строк по TRACKS_META. Pascal — «второй диалект: та же задача, другой синтаксис — главы 4 и 5 учебника 8 класса зеркальны»; web — «архив первого сезона, выдаётся по запросу». Ссылка на живую карту: `https://dmitrtrc.github.io/Junior_IT/#hub`.
6. **Структура репозитория** — дерево с одной строкой на каталог: `tracks/` (библиотека модулей: `shared/` — экран, `student/` — ученику, `teacher/` — преподавателю), `playground/` (журналы занятий), `textbook/` (атлас соответствия учебнику и поправки к нему), `homework/` (условия домашних заданий), `trainer/` (тренажёр — в работе), `tools/` (валидатор, генератор карты, сборка сайта), `meta/` (методика и канон модуля), `docs/` (гайды), `lessons/` (редиректы со старых адресов), `provisioning/` (настройка учебного компьютера).
7. **Кто что видит** — таблица трёх слоёв из спеки дословно по смыслу + два абзаца: методика открыта сознательно — сценарии занятий можно читать, это часть качества курса; эталонные решения домашних заданий в открытый репозиторий не попадают — ученик получает их после сдачи. Персональное — записи занятий, работы ученика, переписка — не покидает компьютера преподавателя.
8. **FAQ** — шесть вопросов `<details>`-блоками: «Сколько времени нужно вне занятий?» (домашка 30–60 минут между занятиями); «Какой компьютер нужен?» (любой не старше ~10 лет; курс идёт на macOS, Windows — с оговорками на занятии); «Что ребёнок будет уметь через полгода?» (уверенный терминал и git, Python на уровне 8–9 класса углублённой программы, привычка к автопроверке и code review); «Как проверяются домашки?» (тесты запускаются автоматически при отправке; зелёная галка — сдано, преподаватель смотрит только качество); «Что видно публично и безопасно ли это?» (см. матрицу выше; имя ребёнка, лицо, записи — не публикуются); «Мы не программисты — сможем ли помогать?» (помощь не нужна: материалы самодостаточны, преподаватель на связи; лучший вклад — время и место для занятий).
9. **Для разработчиков** — полэкрана: `cd tools && .venv/bin/python -m pytest`, `validate_modules.py ..`, `build_site.sh`, `/new-module` в Claude CLI. Одной строкой: PR извне не ожидаются, но методику можно переиспользовать — MIT.
10. Подвал: «Ведёт Дмитрий Морозов — senior-разработчик, 30+ лет в индустрии · [GitHub](https://github.com/DmitrTRC) · MIT».

Запреты те же, что у лендинга. Слова «проверка/проверяются» допустимы только про код и тесты, никогда про ребёнка или семью — запрет из CLAUDE.md бьёт по «контролю/проверкам» в адрес семей, а не по CI. Эмодзи в заголовках разделов — можно (конвенция markdown-документов проекта).

- [ ] **Step 3: Проверить рендер mermaid и grep**

Пуш ещё не делаем, поэтому mermaid проверить локально: блок начинается с ` ```mermaid ` и валиден синтаксически (без пробелов перед `flowchart`). Прогнать: `grep -inE "дружин|отряд|инспекц|полици|фсб|ссср|юдо|контрол" README.md; echo exit=$?` — ожидается `exit=1`; каждое совпадение при `exit=0` разобрать глазами (слово «проверк» в README легально: «автоматическая проверка» — это про код, не про семьи; в грепе его нет намеренно).

- [ ] **Step 4: Commit**

```bash
git add README.md .github/assets/banner.svg
git commit -m "docs: README под новое позиционирование, баннер обновлён"
```

---

### Task 6: Минимальные правки канонов + финальная проверка

**Files:**
- Modify: `CLAUDE.md` (две точечные правки)
- Modify: `meta/project-instructions.md` (одна строка)

**Interfaces:**
- Consumes: всё предыдущее.
- Produces: согласованные каноны; ветка готова к финальному ревью.

- [ ] **Step 1: CLAUDE.md**

Две правки, больше ничего:
1. В TL;DR первое предложение дополнить позиционированием: «**Junior_IT** — курс углублённой информатики и программирования для 7–8 классов: подготовка к учебнику Босовой с опережением…» (сохранив остальное предложение как есть).
2. В раздел «Рабочие конвенции» добавить строку: «Карта курса на лендинге собирается из `module.yml` и `session.yml` генератором `tools/build_course_map.py` — руками её не редактировать; после занятия при расхождении фактического и планового — поле `completed:` в `session.yml`.»

Раздел «⛔ Жёсткие запреты» — не открывать даже для чтения-с-правкой.

- [ ] **Step 2: project-instructions.md**

В шапке раздела «О проекте» первую строку дополнить: «IT-направление…» → перед ним строка «**Позиционирование курса:** углублённая информатика и программирование, 7–8 классы.» Остальное не трогать.

- [ ] **Step 3: Полный прогон**

```bash
cd tools && .venv/bin/python -m pytest -v          # 59 passed
.venv/bin/python validate_modules.py ..            # 0 ошибок
cd .. && ./tools/build_site.sh /tmp/jit_final
python3 - <<'EOF'
import json
d = json.load(open('/tmp/jit_final/course-map.json'))
assert d['positioning'].startswith('Углублённая')
assert len(d['tracks']) == 6
print('карта ок:', d['counters'])
EOF
grep -rinE "юдо|ото |полици|дружин|отряд " index.html README.md CLAUDE.md; echo "exit=$?"   # exit=1
```

- [ ] **Step 4: brand-check**

Прогнать `/brand-check index.html README.md` (или агент brand-guardian), починить найденное.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md meta/project-instructions.md
git commit -m "docs: позиционирование в канонах, конвенция карты курса"
```

---

## Вне плана

- **Тренажёр** — следующий подпроект, отдельная спека и план.
- Полная чистка `CLAUDE.md`/`project-instructions.md` от устаревших слоёв.
- Пуш и мерж — команда Димаса; после мержа не забыть проверить живой Pages: карта, редиректы, слайды занятия.
