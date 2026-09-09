# Каркас нового курса: tracks, роли, миграция — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перевести репозиторий на структуру `tracks/` + `playground/` + `textbook/` с разделением ролей, не сломав разосланные ссылки, и обеспечить материалами занятие 13.09.

**Architecture:** Библиотека модулей вместо линейных уроков. Модуль — папка с `module.yml` и тремя папками ролей (`shared/`, `student/`, `teacher/`). Связность держит валидатор на Python с pytest. Деплой перестаёт отдавать репозиторий как есть и собирает `_site/` без `teacher/`. Существующие уроки переезжают через `git mv` с сохранением истории, на старых путях остаются HTML-редиректы.

**Tech Stack:** Python 3.12 + PyYAML + pytest (инструменты), bash + rsync (сборка сайта), GitHub Actions (деплой), статический HTML/CSS без фреймворков (материалы).

**Spec:** `docs/superpowers/specs/2026-09-09-course-restructure-design.md`

## Global Constraints

- **Идентификаторы только английские.** Никакой транслитерации в именах папок, файлов, полей YAML и веток: `m-04-branching`, не `m-04-vetvlenie`.
- **Термины подаются парой ру/en** везде, где учебник вводит термин: «Ветвление (branching)», «Исполнитель (executor)», «ИЛИ (OR)».
- **Треки:** `book`, `python`, `pascal`, `devops`, `cs`, `web`. Уровни: `core`, `deep`, `optional`.
- **Токены треков** (тёмный / светлый для печати): book `#7aa2ff` / `#2b4fa8`, python `#00ffc8` / `#00806a`, pascal `#ff5722` / `#b3350f`, devops `#00e676` / `#00803d`, cs `#ff0096` / `#a8005f`, web `#8892b0` / `#4a5568`.
- **Базовая палитра не меняется:** `--bg #0a0a14`, `--card #1a1a2e`, `--card-2 #16213e`, `--deep #0f3460`, `--yellow #ffd60a`, `--orange #ff5722`, `--green #00e676`, `--cyan #00ffc8`, `--magenta #ff0096`, `--bg-light #faf7f2`.
- **Шрифты:** Rubik 700 (заголовки), Manrope 400/500/600 (текст), JetBrains Mono 400/700 (код и чипы). Новый шрифт — только после проверки сабсета `cyrillic`.
- **Запреты (блокируют публикацию):** символика СССР, ФСБ, силовых ведомств, политически нагруженные знаки; слово «дружина»; в текстах родителям — «контроль», «проверки», «инспекции», «отряд», «кружковая методика как в школе».
- **`teacher/` не публикуется** на GitHub Pages.
- **Эталонные решения не коммитятся** в этот репозиторий (живут в приватном `Junior_IT-keys`).
- **PDF учебников не коммитятся** — `refs/` в `.gitignore`.
- **HTML-материалы самодостаточны:** стили инлайном, без внешних CSS-файлов. Шпаргалку отправляют ребёнку одним файлом.
- **Правки хирургические.** Не переписывать соседний код заодно. Рефакторинг — отдельным коммитом.
- **Без эмодзи** в коммитах, идентификаторах и именах файлов.
- **Тесты гоняются так:** `cd tools && python3 -m pytest -v`

---

### Task 1: Каркас дерева и вынос PDF

**Files:**
- Create: `tracks/.gitkeep`, `playground/.gitkeep`, `textbook/quizzes/.gitkeep`, `trainer/.gitkeep`, `homework/.gitkeep`
- Modify: `.gitignore`
- Move: `docs/1702130649_informatika_-uchebnik_-7-kl_-bosova.pdf`, `docs/1702130814_informatika_-uchebnik_-8-kl_-bosova.pdf` → `refs/`

**Interfaces:**
- Consumes: ничего
- Produces: дерево каталогов, на которое опираются все следующие задачи; `refs/` вне git

- [ ] **Step 1: Создать каркас каталогов**

```bash
cd /Users/dmitrymorozov/Projects/Junior_IT
mkdir -p tracks/{book,python,pascal,devops,cs,web} playground textbook/quizzes trainer homework tools/tests refs
touch tracks/.gitkeep playground/.gitkeep textbook/quizzes/.gitkeep trainer/.gitkeep homework/.gitkeep
```

- [ ] **Step 2: Перенести PDF учебников в refs/**

PDF пока не в индексе git (untracked), поэтому обычный `mv`, не `git mv`:

```bash
mv docs/1702130649_informatika_-uchebnik_-7-kl_-bosova.pdf refs/informatika-7-bosova.pdf
mv docs/1702130814_informatika_-uchebnik_-8-kl_-bosova.pdf refs/informatika-8-bosova.pdf
```

- [ ] **Step 3: Дописать .gitignore**

Добавить в конец файла:

```gitignore

# Учебники и производные OCR — чужой копирайт, десятки мегабайт
refs/

# Сборка сайта для GitHub Pages
_site/

# Виртуальное окружение инструментов
tools/.venv/
```

- [ ] **Step 4: Проверить, что PDF не попадут в коммит**

Run: `git status --short | grep -c refs/`
Expected: `0` — каталог `refs/` игнорируется целиком.

- [ ] **Step 5: Commit**

```bash
git add .gitignore tracks/.gitkeep playground/.gitkeep textbook/quizzes/.gitkeep trainer/.gitkeep homework/.gitkeep
git commit -m "chore: каркас дерева курса, учебники вынесены в refs/"
```

---

### Task 2: Токены треков

**Files:**
- Create: `meta/brand-tokens.css`
- Create: `tools/module_schema.py` (только константы на этом шаге)
- Create: `tools/tests/test_brand_tokens.py`
- Create: `tools/requirements.txt`

**Interfaces:**
- Consumes: список треков из Global Constraints
- Produces: `module_schema.TRACKS` (кортеж имён треков), `module_schema.TRACK_TOKEN` (трек → короткое имя токена), `meta/brand-tokens.css` как источник истины по цветам

- [ ] **Step 1: Создать файл зависимостей инструментов**

`tools/requirements.txt`:

```
pyyaml>=6.0
pytest>=8.0
```

- [ ] **Step 2: Поднять окружение**

```bash
cd /Users/dmitrymorozov/Projects/Junior_IT/tools
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
```

Дальше во всех задачах `python3` означает `tools/.venv/bin/python`.

- [ ] **Step 3: Написать падающий тест**

`tools/tests/test_brand_tokens.py`:

```python
from pathlib import Path

from module_schema import TRACKS, TRACK_TOKEN

REPO = Path(__file__).resolve().parents[2]
TOKENS_CSS = REPO / "meta" / "brand-tokens.css"


def test_every_track_has_dark_and_ink_token():
    css = TOKENS_CSS.read_text(encoding="utf-8")
    for track in TRACKS:
        short = TRACK_TOKEN[track]
        assert f"--track-{short}:" in css, f"нет тёмного токена для трека {track}"
        assert f"--track-{short}-ink:" in css, f"нет печатного токена для трека {track}"


def test_base_palette_survives():
    css = TOKENS_CSS.read_text(encoding="utf-8")
    for token, value in [
        ("--bg", "#0a0a14"),
        ("--card", "#1a1a2e"),
        ("--yellow", "#ffd60a"),
        ("--bg-light", "#faf7f2"),
    ]:
        assert f"{token}: {value}" in css, f"базовый токен {token} потерян или изменён"
```

- [ ] **Step 4: Добавить конфигурацию pytest**

`tools/pytest.ini`:

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 5: Запустить тест и убедиться, что падает**

Run: `cd tools && .venv/bin/python -m pytest -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'module_schema'`

- [ ] **Step 6: Создать константы**

`tools/module_schema.py`:

```python
"""Схема и проверки module.yml."""

TRACKS = ("book", "python", "pascal", "devops", "cs", "web")

TRACK_TOKEN = {
    "book": "book",
    "python": "py",
    "pascal": "pas",
    "devops": "ops",
    "cs": "cs",
    "web": "web",
}

LEVELS = ("core", "deep", "optional")
REQUIRED_FIELDS = ("id", "title", "track", "level", "minutes")
ROLE_DIRS = ("shared", "student", "teacher")
```

- [ ] **Step 7: Создать канон токенов**

`meta/brand-tokens.css`:

```css
/* Junior_IT — канон токенов оформления.
   Источник истины для материалов и агента brand-guardian.
   HTML-материалы самодостаточны: этот блок вставляется в <style> страницы,
   а не подключается ссылкой. */

:root {
  --bg: #0a0a14;
  --card: #1a1a2e;
  --card-2: #16213e;
  --deep: #0f3460;
  --yellow: #ffd60a;
  --orange: #ff5722;
  --green: #00e676;
  --cyan: #00ffc8;
  --magenta: #ff0096;
  --bg-light: #faf7f2;

  /* Направления курса. Первый цвет — тёмный фон материалов,
     второй (-ink) — печать шпаргалок на --bg-light. */
  --track-book: #7aa2ff;
  --track-book-ink: #2b4fa8;
  --track-py: #00ffc8;
  --track-py-ink: #00806a;
  --track-pas: #ff5722;
  --track-pas-ink: #b3350f;
  --track-ops: #00e676;
  --track-ops-ink: #00803d;
  --track-cs: #ff0096;
  --track-cs-ink: #a8005f;
  --track-web: #8892b0;
  --track-web-ink: #4a5568;
}
```

- [ ] **Step 8: Запустить тесты и убедиться, что проходят**

Run: `cd tools && .venv/bin/python -m pytest -v`
Expected: PASS, 2 теста

- [ ] **Step 9: Commit**

```bash
git add meta/brand-tokens.css tools/module_schema.py tools/tests/test_brand_tokens.py tools/requirements.txt tools/pytest.ini
git commit -m "brand: токены направлений курса и канон палитры"
```

---

### Task 3: Проверка полей module.yml

**Files:**
- Modify: `tools/module_schema.py`
- Create: `tools/tests/test_module_schema.py`

**Interfaces:**
- Consumes: `TRACKS`, `LEVELS`, `REQUIRED_FIELDS` из Task 2
- Produces: `check_fields(data: dict) -> list[str]` — возвращает список текстовых ошибок, пустой список означает «всё в порядке»

- [ ] **Step 1: Написать падающие тесты**

`tools/tests/test_module_schema.py`:

```python
from module_schema import check_fields


def valid_module():
    return {
        "id": "python/m-04-branching",
        "title": "Ветвление (branching): if / elif / else",
        "track": "python",
        "level": "core",
        "minutes": 25,
        "textbook": ["8:3.5", "8:5.4"],
        "terms": [{"ru": "ветвление", "en": "branching"}],
    }


def test_valid_module_has_no_errors():
    assert check_fields(valid_module()) == []


def test_missing_required_field_is_reported():
    data = valid_module()
    del data["minutes"]
    errors = check_fields(data)
    assert any("minutes" in e for e in errors)


def test_unknown_track_is_reported():
    data = valid_module()
    data["track"] = "informatika"
    errors = check_fields(data)
    assert any("informatika" in e for e in errors)


def test_unknown_level_is_reported():
    data = valid_module()
    data["level"] = "hard"
    errors = check_fields(data)
    assert any("hard" in e for e in errors)


def test_minutes_must_be_positive_int():
    data = valid_module()
    data["minutes"] = 0
    assert check_fields(data) != []
    data["minutes"] = "25"
    assert check_fields(data) != []


def test_textbook_reference_format_is_checked():
    data = valid_module()
    data["textbook"] = ["8-3.5"]
    errors = check_fields(data)
    assert any("8-3.5" in e for e in errors)


def test_term_without_english_is_reported():
    data = valid_module()
    data["terms"] = [{"ru": "ветвление"}]
    errors = check_fields(data)
    assert any("en" in e for e in errors)


def test_non_dict_input_is_reported():
    assert check_fields("не словарь") != []
```

- [ ] **Step 2: Запустить и убедиться, что падают**

Run: `cd tools && .venv/bin/python -m pytest tests/test_module_schema.py -v`
Expected: FAIL — `ImportError: cannot import name 'check_fields'`

- [ ] **Step 3: Реализовать проверку полей**

Дописать в `tools/module_schema.py`:

```python
import re

TEXTBOOK_RE = re.compile(r"^[78]:\d+\.\d+$")


def check_fields(data):
    """Проверяет содержимое module.yml. Возвращает список ошибок."""
    if not isinstance(data, dict):
        return ["module.yml должен быть словарём"]

    errors = []

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"нет обязательного поля {field}")

    track = data.get("track")
    if track is not None and track not in TRACKS:
        errors.append(f"неизвестный трек {track!r}, ожидается один из {list(TRACKS)}")

    level = data.get("level")
    if level is not None and level not in LEVELS:
        errors.append(f"неизвестный level {level!r}, ожидается один из {list(LEVELS)}")

    minutes = data.get("minutes")
    if minutes is not None and (not isinstance(minutes, int) or minutes <= 0):
        errors.append(f"minutes должно быть положительным целым, получено {minutes!r}")

    for ref in data.get("textbook") or []:
        if not TEXTBOOK_RE.match(str(ref)):
            errors.append(
                f"ссылка на учебник {ref!r} должна быть вида '7:1.3' или '8:5.4'"
            )

    for term in data.get("terms") or []:
        if not isinstance(term, dict) or not term.get("ru") or not term.get("en"):
            errors.append(f"термин {term!r} должен иметь непустые ru и en")

    return errors
```

`import re` поставить в начало файла, рядом с докстрингом.

- [ ] **Step 4: Запустить тесты**

Run: `cd tools && .venv/bin/python -m pytest -v`
Expected: PASS, 10 тестов

- [ ] **Step 5: Commit**

```bash
git add tools/module_schema.py tools/tests/test_module_schema.py
git commit -m "tools: проверка полей module.yml"
```

---

### Task 4: Проверка структуры и связей модуля

**Files:**
- Modify: `tools/module_schema.py`
- Modify: `tools/tests/test_module_schema.py`

**Interfaces:**
- Consumes: `check_fields`, `ROLE_DIRS` из Task 3
- Produces:
  - `check_layout(module_dir: Path) -> list[str]`
  - `check_links(data: dict, module_dir: Path, repo_root: Path) -> list[str]`
  - `validate_module(module_dir: Path, repo_root: Path) -> list[str]` — читает `module.yml` и объединяет все три проверки

- [ ] **Step 1: Написать падающие тесты**

Дописать в `tools/tests/test_module_schema.py`:

```python
from pathlib import Path

import pytest
import yaml

from module_schema import check_layout, check_links, validate_module


@pytest.fixture
def fake_repo(tmp_path):
    """Мини-репозиторий с одним валидным модулем python/m-01-first-run."""
    module_dir = tmp_path / "tracks" / "python" / "m-01-first-run"
    for role in ("shared", "student", "teacher"):
        (module_dir / role).mkdir(parents=True)
    (tmp_path / "homework" / "python-01-first-run").mkdir(parents=True)
    manifest = {
        "id": "python/m-01-first-run",
        "title": "Первый запуск Python",
        "track": "python",
        "level": "core",
        "minutes": 25,
        "homework": "homework/python-01-first-run",
    }
    (module_dir / "module.yml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8"
    )
    return tmp_path, module_dir


def test_layout_ok_when_all_role_dirs_exist(fake_repo):
    _, module_dir = fake_repo
    assert check_layout(module_dir) == []


def test_missing_role_dir_is_reported(fake_repo):
    _, module_dir = fake_repo
    (module_dir / "teacher").rmdir()
    errors = check_layout(module_dir)
    assert any("teacher" in e for e in errors)


def test_id_must_match_path(fake_repo):
    repo_root, module_dir = fake_repo
    data = {"id": "python/m-99-wrong"}
    errors = check_links(data, module_dir, repo_root)
    assert any("m-99-wrong" in e for e in errors)


def test_missing_dependency_is_reported(fake_repo):
    repo_root, module_dir = fake_repo
    data = {"id": "python/m-01-first-run", "requires": ["python/m-00-nonexistent"]}
    errors = check_links(data, module_dir, repo_root)
    assert any("m-00-nonexistent" in e for e in errors)


def test_missing_homework_path_is_reported(fake_repo):
    repo_root, module_dir = fake_repo
    data = {"id": "python/m-01-first-run", "homework": "homework/nope"}
    errors = check_links(data, module_dir, repo_root)
    assert any("homework/nope" in e for e in errors)


def test_validate_module_accepts_good_module(fake_repo):
    repo_root, module_dir = fake_repo
    assert validate_module(module_dir, repo_root) == []


def test_validate_module_reports_missing_manifest(tmp_path):
    module_dir = tmp_path / "tracks" / "python" / "m-02-io"
    module_dir.mkdir(parents=True)
    errors = validate_module(module_dir, tmp_path)
    assert any("module.yml" in e for e in errors)


def test_validate_module_reports_broken_yaml(fake_repo):
    repo_root, module_dir = fake_repo
    (module_dir / "module.yml").write_text("id: [unclosed", encoding="utf-8")
    errors = validate_module(module_dir, repo_root)
    assert errors != []
```

- [ ] **Step 2: Запустить и убедиться, что падают**

Run: `cd tools && .venv/bin/python -m pytest tests/test_module_schema.py -v`
Expected: FAIL — `ImportError: cannot import name 'check_layout'`

- [ ] **Step 3: Реализовать проверки**

Дописать в `tools/module_schema.py` (и добавить `import yaml` в начало файла):

```python
def check_layout(module_dir):
    """Проверяет, что у модуля есть все три папки ролей."""
    return [
        f"нет папки {role}/"
        for role in ROLE_DIRS
        if not (module_dir / role).is_dir()
    ]


def check_links(data, module_dir, repo_root):
    """Проверяет, что id совпадает с путём, а ссылки ведут в существующее."""
    errors = []

    expected_id = f"{module_dir.parent.name}/{module_dir.name}"
    if data.get("id") != expected_id:
        errors.append(f"id {data.get('id')!r} не совпадает с путём {expected_id!r}")

    for dep in data.get("requires") or []:
        if not (repo_root / "tracks" / dep).is_dir():
            errors.append(f"requires: модуль {dep!r} не найден")

    for field in ("quiz", "homework"):
        target = data.get(field)
        if target and not (repo_root / target).exists():
            errors.append(f"{field}: путь {target!r} не найден")

    return errors


def validate_module(module_dir, repo_root):
    """Полная проверка модуля: манифест, поля, папки ролей, ссылки."""
    manifest = module_dir / "module.yml"
    if not manifest.is_file():
        return ["нет module.yml"]

    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"module.yml не читается: {exc}"]

    return (
        check_fields(data)
        + check_layout(module_dir)
        + check_links(data, module_dir, repo_root)
    )
```

- [ ] **Step 4: Запустить тесты**

Run: `cd tools && .venv/bin/python -m pytest -v`
Expected: PASS, 18 тестов

- [ ] **Step 5: Commit**

```bash
git add tools/module_schema.py tools/tests/test_module_schema.py
git commit -m "tools: проверка структуры и связей модуля"
```

---

### Task 5: CLI-валидатор всей библиотеки

**Files:**
- Create: `tools/validate_modules.py`
- Create: `tools/tests/test_validate_modules.py`

**Interfaces:**
- Consumes: `validate_module` из Task 4
- Produces:
  - `iter_module_dirs(repo_root: Path) -> list[Path]` — отсортированный список папок модулей
  - `main(argv: list[str] | None = None) -> int` — 0 если всё чисто, 1 если есть ошибки

- [ ] **Step 1: Написать падающие тесты**

`tools/tests/test_validate_modules.py`:

```python
import yaml

from validate_modules import iter_module_dirs, main


def make_module(repo_root, track, name, manifest=None):
    module_dir = repo_root / "tracks" / track / name
    for role in ("shared", "student", "teacher"):
        (module_dir / role).mkdir(parents=True)
    data = manifest or {
        "id": f"{track}/{name}",
        "title": "Тестовый модуль",
        "track": track,
        "level": "core",
        "minutes": 20,
    }
    (module_dir / "module.yml").write_text(
        yaml.safe_dump(data, allow_unicode=True), encoding="utf-8"
    )
    return module_dir


def test_iter_finds_modules_sorted(tmp_path):
    make_module(tmp_path, "python", "m-02-io")
    make_module(tmp_path, "book", "m-01-information")
    found = [d.name for d in iter_module_dirs(tmp_path)]
    assert found == ["m-01-information", "m-02-io"]


def test_iter_returns_empty_without_tracks_dir(tmp_path):
    assert iter_module_dirs(tmp_path) == []


def test_main_returns_zero_when_all_modules_valid(tmp_path):
    make_module(tmp_path, "python", "m-01-first-run")
    assert main([str(tmp_path)]) == 0


def test_main_returns_one_when_module_broken(tmp_path):
    make_module(
        tmp_path,
        "python",
        "m-01-first-run",
        manifest={"id": "python/m-01-first-run", "track": "python"},
    )
    assert main([str(tmp_path)]) == 1


def test_main_prints_module_name_and_error(tmp_path, capsys):
    make_module(
        tmp_path,
        "python",
        "m-01-first-run",
        manifest={"id": "python/m-01-first-run", "track": "wrong"},
    )
    main([str(tmp_path)])
    out = capsys.readouterr().out
    assert "m-01-first-run" in out
    assert "wrong" in out
```

- [ ] **Step 2: Запустить и убедиться, что падают**

Run: `cd tools && .venv/bin/python -m pytest tests/test_validate_modules.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'validate_modules'`

- [ ] **Step 3: Реализовать CLI**

`tools/validate_modules.py`:

```python
#!/usr/bin/env python3
"""Проверка библиотеки модулей: python3 tools/validate_modules.py [корень репо]"""

import sys
from pathlib import Path

from module_schema import validate_module


def iter_module_dirs(repo_root):
    """Все папки модулей вида tracks/<track>/<module>/ с манифестом."""
    tracks_dir = Path(repo_root) / "tracks"
    if not tracks_dir.is_dir():
        return []
    return sorted(p.parent for p in tracks_dir.glob("*/*/module.yml"))


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    repo_root = Path(args[0]) if args else Path(__file__).resolve().parent.parent

    failed = 0
    for module_dir in iter_module_dirs(repo_root):
        errors = validate_module(module_dir, repo_root)
        name = module_dir.relative_to(repo_root)
        if errors:
            failed += 1
            print(f"FAIL {name}")
            for error in errors:
                print(f"     {error}")
        else:
            print(f"ok   {name}")

    print(f"\nмодулей с ошибками: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Запустить тесты**

Run: `cd tools && .venv/bin/python -m pytest -v`
Expected: PASS, 23 теста

- [ ] **Step 5: Проверить на живом репозитории**

Run: `cd tools && .venv/bin/python validate_modules.py ..`
Expected: `модулей с ошибками: 0` — модулей пока нет, валидатор не падает на пустой библиотеке.

- [ ] **Step 6: Commit**

```bash
git add tools/validate_modules.py tools/tests/test_validate_modules.py
git commit -m "tools: CLI-валидатор библиотеки модулей"
```

---

### Task 6: Шаблон модуля

**Files:**
- Create: `meta/module-template/module.yml`
- Create: `meta/module-template/shared/slides.html`
- Create: `meta/module-template/shared/live-code.md`
- Create: `meta/module-template/student/cheatsheet.html`
- Create: `meta/module-template/student/glossary.md`
- Create: `meta/module-template/teacher/scenario.md`
- Create: `meta/module-anatomy.md`
- Delete: `meta/lesson-anatomy.md`

**Interfaces:**
- Consumes: токены из `meta/brand-tokens.css` (Task 2), схему полей (Task 3)
- Produces: шаблон, от которого пляшут Task 7 и Task 11–13; `meta/module-anatomy.md` как канон для `/new-module` и `brand-guardian`

- [ ] **Step 1: Создать манифест-шаблон**

`meta/module-template/module.yml`:

```yaml
id: TRACK/m-NN-slug
title: "Тема (topic in English)"
track: TRACK
level: core                # core | deep | optional
minutes: 25
textbook: []               # ["7:1.1"] — какие параграфы закрывает
requires: []               # ["python/m-01-first-run"]
terms:
  - {ru: термин, en: term}
homework: homework/TRACK-NN-slug
```

- [ ] **Step 2: Создать шаблон шпаргалки**

`meta/module-template/student/cheatsheet.html` — самодостаточный файл. Токены инлайном из `meta/brand-tokens.css`, чип трека моноширинным шрифтом, светлый фон для печати:

```html
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Шпаргалка · ТЕМА</title>
<link href="https://fonts.googleapis.com/css2?family=Rubik:wght@700&family=Manrope:wght@400;500;600&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a14; --card: #1a1a2e; --card-2: #16213e; --deep: #0f3460;
    --yellow: #ffd60a; --green: #00e676; --bg-light: #faf7f2;
    --track: #00ffc8; --track-ink: #00806a;
  }
  body {
    background: var(--bg); color: #e8e8f0;
    font-family: Manrope, system-ui, sans-serif;
    margin: 0; padding: 2rem 1.25rem; line-height: 1.6;
  }
  .wrap { max-width: 46rem; margin: 0 auto; }
  h1 { font-family: Rubik, system-ui, sans-serif; color: var(--track); margin: 0 0 .25rem; }
  .chip {
    font-family: "JetBrains Mono", monospace; font-weight: 700; font-size: .75rem;
    letter-spacing: .08em; color: var(--bg); background: var(--track);
    padding: .15rem .5rem; border-radius: .25rem;
  }
  .card {
    background: var(--card); border-left: 4px solid var(--track);
    border-radius: .75rem; padding: 1rem 1.25rem; margin: 1rem 0;
  }
  code, pre { font-family: "JetBrains Mono", monospace; }
  pre { background: var(--card-2); padding: .9rem 1rem; border-radius: .5rem; overflow-x: auto; }
  .term { color: var(--yellow); }
  .term span { color: #9aa0b5; font-style: italic; }
  @media print {
    body { background: var(--bg-light); color: #1a1a1a; }
    h1 { color: var(--track-ink); }
    .chip { background: var(--track-ink); color: #fff; }
    .card { background: #fff; border-left-color: var(--track-ink); }
    pre { background: #f0ede8; }
  }
</style>
</head>
<body>
<div class="wrap">
  <span class="chip">PY</span>
  <h1>Тема урока</h1>
  <div class="card">
    <p class="term">Термин <span>(term)</span> — что это одной строкой.</p>
  </div>
</div>
</body>
</html>
```

При создании модуля меняются: значения `--track` / `--track-ink` на пару своего трека, текст чипа, заголовок и содержимое.

- [ ] **Step 3: Создать остальные файлы шаблона**

`meta/module-template/student/glossary.md`:

```markdown
# Словарик

| Учебник (рус) | В проде (eng) | Что это одной строкой |
|---|---|---|
| термин | term | объяснение без зубрёжки |
```

`meta/module-template/shared/live-code.md`:

```markdown
# Живой код

Шаги, которые набираются на экране при ученице. Один шаг — одно действие.

1. **Что делаем** — что видно на экране после этого шага.
```

`meta/module-template/teacher/scenario.md`:

```markdown
# Сценарий

**Длительность:** NN мин. **Трек:** TRACK.

| Мин | Что происходит | Чем закончится |
|---|---|---|
| 0–3 | Зацепка | Ученица понимает, зачем это |

## Где залипнет

- Место, на котором внимание рвётся, и что сказать.

## Чек-лист готовности

- [ ] Файлы модуля на месте, валидатор зелёный
- [ ] Экран и звук проверены
```

`meta/module-template/shared/slides.html` — копия структуры `cheatsheet.html` с переключением слайдов по `←` / `→`. Взять за образец существующий `lessons/lesson-cs-03-languages/slides.html` (он ещё не переехал — миграция идёт в Task 7) и заменить в нём цвета на пару токенов трека.

- [ ] **Step 4: Переписать анатомию**

`meta/module-anatomy.md` — заменяет `meta/lesson-anatomy.md`. Содержит:

- таблицу «файл → что это» по трём ролям;
- полную схему `module.yml` со всеми полями и допустимыми значениями;
- правило нумерации: номер отражает порядок создания внутри трека, не порядок прохождения;
- правило двуязычных терминов и формат таблицы глоссария;
- таблицу цветов треков и правило чипа;
- отступления блока `cs`: живая схема вместо живого кодинга, одна демка вместо трёх эстетик;
- команду проверки: `cd tools && .venv/bin/python validate_modules.py ..`

- [ ] **Step 5: Удалить старую анатомию**

```bash
git rm meta/lesson-anatomy.md
```

- [ ] **Step 6: Проверить, что шаблон не ломает валидатор**

Шаблон лежит в `meta/`, а не в `tracks/`, поэтому в обход не попадает:

Run: `cd tools && .venv/bin/python validate_modules.py ..`
Expected: `модулей с ошибками: 0`

- [ ] **Step 7: Commit**

```bash
git add meta/module-template meta/module-anatomy.md
git commit -m "meta: шаблон модуля и анатомия вместо анатомии урока"
```

---

### Task 7: Миграция существующих уроков в tracks/

**Files:**
- Move: `lessons/lesson-*` → `tracks/web/`, `tracks/cs/` (11 модулей)
- Move: `hello-world-sizes/` → `tracks/cs/m-03-languages/shared/hello-world-sizes/`
- Move: `docs/js-history.md`, `docs/js-vs-ts.md` → `tracks/web/reading/`
- Move: `lessons/playground`, `lessons/sandbox` → `playground/archive-2026-08/`
- Create: `module.yml` в каждом из 11 модулей

**Interfaces:**
- Consumes: шаблон `module.yml` (Task 6), валидатор (Task 5)
- Produces: 11 валидных модулей; карта переездов, на которую опирается Task 8

- [ ] **Step 1: Перенести папки уроков**

Карта переездов:

| Было | Стало |
|---|---|
| `lessons/lesson-01-html-css` | `tracks/web/m-01-html-css` |
| `lessons/lesson-02-js` | `tracks/web/m-02-js-alive` |
| `lessons/lesson-02b-js-console` | `tracks/web/m-03-js-console` |
| `lessons/lesson-02c-js-conditions` | `tracks/web/m-04-js-conditions` |
| `lessons/lesson-02d-js-loops` | `tracks/web/m-05-js-loops` |
| `lessons/lesson-02e-js-recap` | `tracks/web/m-06-js-recap` |
| `lessons/lesson-02f-js-functions` | `tracks/web/m-07-js-functions` |
| `lessons/lesson-02g-vscode` | `tracks/web/m-08-vscode` |
| `lessons/lesson-cs-01-computer` | `tracks/cs/m-01-computer` |
| `lessons/lesson-cs-02-layers` | `tracks/cs/m-02-layers` |
| `lessons/lesson-cs-03-languages` | `tracks/cs/m-03-languages` |

```bash
cd /Users/dmitrymorozov/Projects/Junior_IT
git mv lessons/lesson-01-html-css        tracks/web/m-01-html-css
git mv lessons/lesson-02-js              tracks/web/m-02-js-alive
git mv lessons/lesson-02b-js-console     tracks/web/m-03-js-console
git mv lessons/lesson-02c-js-conditions  tracks/web/m-04-js-conditions
git mv lessons/lesson-02d-js-loops       tracks/web/m-05-js-loops
git mv lessons/lesson-02e-js-recap       tracks/web/m-06-js-recap
git mv lessons/lesson-02f-js-functions   tracks/web/m-07-js-functions
git mv lessons/lesson-02g-vscode         tracks/web/m-08-vscode
git mv lessons/lesson-cs-01-computer     tracks/cs/m-01-computer
git mv lessons/lesson-cs-02-layers       tracks/cs/m-02-layers
git mv lessons/lesson-cs-03-languages    tracks/cs/m-03-languages
```

- [ ] **Step 2: Разложить файлы по ролям**

Правило раскладки одинаково для всех 11 модулей:

| Файл | Роль |
|---|---|
| `README.md` | остаётся в корне модуля |
| `scenario.md`, `live-code.md` | `teacher/` |
| `glossary.md`, `cheatsheet.html`, `homework.html` | `student/` |
| `slides.html`, `index-final.html`, `demos/` | `shared/` |

```bash
for m in tracks/web/m-0*/ tracks/cs/m-0*/; do
  mkdir -p "$m/shared" "$m/student" "$m/teacher"
  for f in scenario.md live-code.md; do
    [ -f "$m/$f" ] && git mv "$m/$f" "$m/teacher/$f"
  done
  for f in glossary.md cheatsheet.html homework.html; do
    [ -f "$m/$f" ] && git mv "$m/$f" "$m/student/$f"
  done
  for f in slides.html index-final.html demos; do
    [ -e "$m/$f" ] && git mv "$m/$f" "$m/shared/$f"
  done
done
```

- [ ] **Step 3: Перенести сопутствующие материалы**

```bash
mkdir -p tracks/web/reading playground/archive-2026-08
git mv docs/js-history.md tracks/web/reading/js-history.md
git mv docs/js-vs-ts.md   tracks/web/reading/js-vs-ts.md
git mv lessons/playground playground/archive-2026-08/js-playground
git mv lessons/sandbox    playground/archive-2026-08/sandbox
mkdir -p tracks/cs/m-03-languages/shared/hello-world-sizes
git mv hello-world-sizes/* tracks/cs/m-03-languages/shared/hello-world-sizes/
rmdir hello-world-sizes 2>/dev/null || true
```

`lessons/playground` и `lessons/sandbox` сейчас не в индексе (untracked) — для них вместо `git mv` использовать обычный `mv`, если `git mv` откажется.

- [ ] **Step 4: Написать module.yml для каждого модуля**

Все 11 — уровень `optional` для трека `web` и `core` для `cs`. Пример для первого:

`tracks/web/m-01-html-css/module.yml`:

```yaml
id: web/m-01-html-css
title: "Первый сайт: HTML и CSS (first web page)"
track: web
level: optional
minutes: 75
textbook: []
requires: []
terms:
  - {ru: тег, en: tag}
  - {ru: стиль, en: style}
  - {ru: селектор, en: selector}
```

`tracks/cs/m-02-layers/module.yml`:

```yaml
id: cs/m-02-layers
title: "Слои компьютера: от битов до программы (layers)"
track: cs
level: core
minutes: 60
textbook: ["7:1.4"]
requires: [cs/m-01-computer]
terms:
  - {ru: бит, en: bit}
  - {ru: байт, en: byte}
  - {ru: оперативная память, en: RAM}
```

Остальные девять — по той же форме. `title` берётся из `README.md` модуля, `minutes` — из его `teacher/scenario.md`, `terms` — из `student/glossary.md` (по три-пять ключевых терминов с английским эквивалентом). Поле `textbook` заполняется только там, где связь с параграфом реальна: `cs/m-02-layers` → `7:1.4`, у остальных — пустой список.

- [ ] **Step 5: Прогнать валидатор**

Run: `cd tools && .venv/bin/python validate_modules.py ..`
Expected: 11 строк `ok`, `модулей с ошибками: 0`

- [ ] **Step 6: Убедиться, что история переезда сохранилась**

Run: `git log --oneline --follow -3 tracks/web/m-01-html-css/student/cheatsheet.html`
Expected: видны коммиты, сделанные до переезда

- [ ] **Step 7: Commit**

```bash
git add -A tracks playground docs
git commit -m "refactor: уроки переехали в tracks/ с разделением ролей"
```

---

### Task 8: Редиректы со старых URL

**Files:**
- Create: `tools/make_redirects.py`
- Create: `tools/tests/test_make_redirects.py`
- Create: `lessons/**/*.html` (генерируемые заглушки)

**Interfaces:**
- Consumes: карту переездов из Task 7
- Produces:
  - `MOVES: dict[str, str]` — старая папка урока → новый путь модуля
  - `ROLE_OF: dict[str, str]` — имя файла → роль в новом модуле
  - `redirect_html(target_url: str) -> str`
  - `plan_redirects(repo_root: Path) -> list[tuple[Path, str]]` — пары «куда писать заглушку, какой в ней URL»
  - `write_redirects(repo_root: Path) -> int` — число созданных файлов

- [ ] **Step 1: Написать падающие тесты**

`tools/tests/test_make_redirects.py`:

```python
from make_redirects import MOVES, plan_redirects, redirect_html, write_redirects


def test_redirect_html_has_refresh_and_link():
    html = redirect_html("../../tracks/web/m-01-html-css/student/cheatsheet.html")
    assert "http-equiv=\"refresh\"" in html
    assert "../../tracks/web/m-01-html-css/student/cheatsheet.html" in html
    assert "<html lang=\"ru\">" in html


def test_plan_covers_existing_files_only(tmp_path):
    module_dir = tmp_path / "tracks" / "web" / "m-01-html-css" / "student"
    module_dir.mkdir(parents=True)
    (module_dir / "cheatsheet.html").write_text("x", encoding="utf-8")
    plan = plan_redirects(tmp_path)
    stubs = {path.relative_to(tmp_path).as_posix() for path, _ in plan}
    assert "lessons/lesson-01-html-css/cheatsheet.html" in stubs
    assert "lessons/lesson-01-html-css/homework.html" not in stubs


def test_plan_target_is_relative_and_correct(tmp_path):
    module_dir = tmp_path / "tracks" / "cs" / "m-01-computer" / "shared"
    module_dir.mkdir(parents=True)
    (module_dir / "slides.html").write_text("x", encoding="utf-8")
    plan = plan_redirects(tmp_path)
    targets = dict(
        (path.relative_to(tmp_path).as_posix(), url) for path, url in plan
    )
    assert (
        targets["lessons/lesson-cs-01-computer/slides.html"]
        == "../../tracks/cs/m-01-computer/shared/slides.html"
    )


def test_write_creates_files(tmp_path):
    module_dir = tmp_path / "tracks" / "web" / "m-01-html-css" / "student"
    module_dir.mkdir(parents=True)
    (module_dir / "cheatsheet.html").write_text("x", encoding="utf-8")
    count = write_redirects(tmp_path)
    stub = tmp_path / "lessons" / "lesson-01-html-css" / "cheatsheet.html"
    assert count == 1
    assert "refresh" in stub.read_text(encoding="utf-8")


def test_moves_cover_all_eleven_lessons():
    assert len(MOVES) == 11
```

- [ ] **Step 2: Запустить и убедиться, что падают**

Run: `cd tools && .venv/bin/python -m pytest tests/test_make_redirects.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'make_redirects'`

- [ ] **Step 3: Реализовать генератор**

`tools/make_redirects.py`:

```python
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
```

- [ ] **Step 4: Запустить тесты**

Run: `cd tools && .venv/bin/python -m pytest -v`
Expected: PASS, 28 тестов

- [ ] **Step 5: Сгенерировать заглушки и проверить одну руками**

```bash
cd tools && .venv/bin/python make_redirects.py ..
```

Run: `cat ../lessons/lesson-01-html-css/cheatsheet.html`
Expected: заглушка со ссылкой `../../tracks/web/m-01-html-css/student/cheatsheet.html`

- [ ] **Step 6: Commit**

```bash
git add tools/make_redirects.py tools/tests/test_make_redirects.py lessons
git commit -m "chore: редиректы со старых URL уроков"
```

---

### Task 9: Сборка сайта без teacher/

**Files:**
- Create: `tools/build_site.sh`
- Create: `tools/tests/test_build_site.py`
- Modify: `.github/workflows/deploy.yml:36-39`

**Interfaces:**
- Consumes: дерево `tracks/` из Task 7
- Produces: `tools/build_site.sh [выходной каталог]` — собирает публикуемую часть, по умолчанию в `_site/`

- [ ] **Step 1: Написать падающий тест**

`tools/tests/test_build_site.py`:

```python
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "tools" / "build_site.sh"


def build(tmp_path):
    out = tmp_path / "site"
    subprocess.run([str(BUILD), str(out)], check=True)
    return out


def test_teacher_dirs_never_published(tmp_path):
    out = build(tmp_path)
    assert list(out.rglob("teacher")) == []


def test_student_and_shared_are_published(tmp_path):
    out = build(tmp_path)
    assert (out / "tracks" / "web" / "m-01-html-css" / "student" / "cheatsheet.html").is_file()
    assert (out / "tracks" / "web" / "m-01-html-css" / "shared").is_dir()


def test_landing_page_is_published(tmp_path):
    out = build(tmp_path)
    assert (out / "index.html").is_file()


def test_internal_dirs_never_published(tmp_path):
    out = build(tmp_path)
    for internal in ("tools", "meta", "refs", "homework", "playground", "provisioning"):
        assert not (out / internal).exists(), f"{internal}/ не должен публиковаться"
```

- [ ] **Step 2: Запустить и убедиться, что падает**

Run: `cd tools && .venv/bin/python -m pytest tests/test_build_site.py -v`
Expected: FAIL — файла `tools/build_site.sh` нет

- [ ] **Step 3: Написать сборку**

`tools/build_site.sh`:

```bash
#!/usr/bin/env bash
# Собирает публикуемую часть репозитория.
# teacher/ и внутренняя кухня на сайт не попадают.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/_site}"

rm -rf "$OUT"
mkdir -p "$OUT"

rsync -a \
  --exclude '.git/' \
  --exclude '.github/' \
  --exclude '.claude/' \
  --exclude '_site/' \
  --exclude 'teacher/' \
  --exclude 'tools/' \
  --exclude 'meta/' \
  --exclude 'refs/' \
  --exclude 'homework/' \
  --exclude 'playground/' \
  --exclude 'provisioning/' \
  --exclude 'print/' \
  --exclude 'students/' \
  --exclude 'recordings/' \
  --exclude 'TO_PARENTS/' \
  --exclude 'graphify-out/' \
  --exclude 'docs/superpowers/' \
  --exclude '.DS_Store' \
  --exclude '__pycache__/' \
  "$ROOT/" "$OUT/"

echo "сайт собран: $OUT"
```

```bash
chmod +x tools/build_site.sh
```

- [ ] **Step 4: Запустить тесты**

Run: `cd tools && .venv/bin/python -m pytest -v`
Expected: PASS, 32 теста

- [ ] **Step 5: Переключить деплой на сборку**

В `.github/workflows/deploy.yml` заменить шапку комментария и шаг `Upload artifact`.

Комментарий вверху файла — вместо «Деплоит весь репо как статический сайт»:

```yaml
# Собирает публикуемую часть репозитория и деплоит на каждый push в main.
# teacher/, инструменты и рабочие материалы на сайт не попадают.
# Адрес: https://dmitrtrc.github.io/Junior_IT/
```

Между `Setup Pages` и `Upload artifact` добавить шаг сборки, а у выгрузки поменять путь:

```yaml
      - name: Build site
        run: ./tools/build_site.sh _site
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: '_site'
```

- [ ] **Step 6: Проверить сборку локально**

Run: `./tools/build_site.sh /tmp/junior_it_site && find /tmp/junior_it_site -name teacher -type d | wc -l`
Expected: `0`

- [ ] **Step 7: Commit**

```bash
git add tools/build_site.sh tools/tests/test_build_site.py .github/workflows/deploy.yml
git commit -m "ci: деплой собирает сайт без teacher/ и внутренних папок"
```

---

### Task 10: Документация и команды под новую структуру

**Files:**
- Modify: `CLAUDE.md`
- Create: `.claude/commands/new-module.md`
- Delete: `.claude/commands/new-lesson.md`
- Modify: `.claude/commands/brand-check.md`
- Modify: `.claude/agents/brand-guardian.md`
- Modify: `meta/project-instructions.md`

**Interfaces:**
- Consumes: `meta/module-anatomy.md` (Task 6), токены треков (Task 2)
- Produces: `/new-module TRACK slug "тема"` вместо `/new-lesson`; `brand-guardian`, знающий цвета треков

- [ ] **Step 1: Обновить CLAUDE.md**

Заменить разделы, описывающие старую реальность:

- TL;DR: курс — подготовка к учебнику Босовой 7–8 с опережением, основной язык Python, формат 1:1 через Zoom с работой руками, два занятия в неделю (среда и воскресенье, 20:00).
- Методология: убрать «дети смотрят, делают дома» как единственный формат, добавить «делает вживую, шарит экран»; сохранить правила «теория ≤2 минут», «75 минут потолок», урок про `getElementById` как обоснование постепенного ввода сложного.
- Бренд-кит: добавить таблицу цветов треков с парами `--track-X` / `--track-X-ink`, сослаться на `meta/brand-tokens.css` как на источник истины.
- Конвенции: имена модулей `tracks/<track>/m-NN-slug`, только английские идентификаторы, правило двуязычных терминов, ссылка на `meta/module-anatomy.md` вместо `meta/lesson-anatomy.md`, команда валидации.
- Раздел запретов не трогать — он остаётся дословно.

- [ ] **Step 2: Создать команду /new-module**

`.claude/commands/new-module.md`:

```markdown
---
description: Развернуть новый модуль курса по анатомии Junior_IT и бренд-киту
argument-hint: TRACK slug "тема модуля"
---

Создай новый модуль Junior_IT.

- Трек: **$1** (book | python | pascal | devops | cs | web)
- Slug папки: **$2** (только английский, без транслитерации)
- Тема: **$ARGUMENTS** (всё после slug)

## Что сделать

1. Определи следующий свободный номер внутри трека: посмотри `tracks/$1/`.
   Номер — порядок создания, не порядок прохождения.

2. Скопируй `meta/module-template/` в `tracks/$1/m-NN-$2/` и заполни по
   анатомии из `meta/module-anatomy.md`:
   - `module.yml` — id, title с английским термином в скобках, level, minutes,
     textbook, requires, terms, homework
   - `shared/` — слайды, живой код, демки
   - `student/` — шпаргалка, словарик, условие домашки
   - `teacher/` — сценарий с таймингом, ответы, «где залипнет»

3. Цвета — пара токенов своего трека из `meta/brand-tokens.css`
   (`--track-$1` и `--track-$1-ink`), чип трека моноширинным шрифтом.
   Не выдумывай цвета и шрифты.

4. Каждый термин — парой ру/en: «Ветвление (branching)». Словарик — таблица
   из трёх колонок: учебник, в проде, что это одной строкой.

5. Соблюдай методологию и запреты из `CLAUDE.md`: теория ≤2 мин блоками,
   потолок 75 мин, никакой символики и слова «дружина».

6. Прогони проверки и почини найденное:
   - `cd tools && .venv/bin/python validate_modules.py ..`
   - `/brand-check tracks/$1/m-NN-$2`

7. Не пуши. Покажи дерево созданных файлов и краткое резюме — деплой отдельно
   через `/deploy`.

Если из темы неоднозначно, какой глубины модуль (core / deep / optional) —
уточни у Димаса одной фразой. Не вываливай весь объём без подтверждения.
```

- [ ] **Step 3: Удалить старую команду**

```bash
git rm .claude/commands/new-lesson.md
```

- [ ] **Step 4: Обновить brand-check и brand-guardian**

В `.claude/commands/brand-check.md` и `.claude/agents/brand-guardian.md`:

- в блок «Бренд» добавить проверку цветов треков: у модуля должна использоваться пара своего трека, `--track-X` на тёмном фоне и `--track-X-ink` в `@media print`;
- добавить проверку двуязычных терминов: термин в шпаргалке и словарике идёт парой ру/en;
- заменить упоминания «эстетик демок» на пометку, что три эстетики — правило трека `web`, а не всего курса;
- заменить ссылку `meta/lesson-anatomy.md` на `meta/module-anatomy.md`.

Блок «Запреты» не трогать.

- [ ] **Step 5: Обновить project-instructions**

В `meta/project-instructions.md` заменить раздел «Программа курса» на актуальную сентябрьскую сетку и раздел «Структура проекта» — на новое дерево. Раздел «Запреты», бренд-кит и сетап записи оставить.

- [ ] **Step 6: Проверить, что команды на месте**

Run: `ls .claude/commands/`
Expected: `brand-check.md deploy.md new-module.md parent-msg.md postmortem.md` — без `new-lesson.md`

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md .claude meta/project-instructions.md
git commit -m "docs: инструкции и команды под структуру модулей"
```

---

### Task 11: Модуль book/m-01-information-and-data

**Files:**
- Create: `tracks/book/m-01-information-and-data/module.yml`
- Create: `tracks/book/m-01-information-and-data/shared/slides.html`
- Create: `tracks/book/m-01-information-and-data/student/cheatsheet.html`
- Create: `tracks/book/m-01-information-and-data/student/glossary.md`
- Create: `tracks/book/m-01-information-and-data/teacher/scenario.md`
- Create: `homework/book-01-information-sources/task.md`
- Create: `textbook/errata.md`

**Interfaces:**
- Consumes: шаблон (Task 6), токены `--track-book` / `--track-book-ink` (Task 2)
- Produces: первый модуль трека `book`; `textbook/errata.md` как файл, который пополняют Task 12–13 и последующие планы

- [ ] **Step 1: Написать манифест**

```yaml
id: book/m-01-information-and-data
title: "Информация и данные (information and data)"
track: book
level: core
minutes: 15
textbook: ["7:1.1"]
requires: []
terms:
  - {ru: информация, en: information}
  - {ru: данные, en: data, note: "данные записаны, информация — то, что понял"}
  - {ru: сигнал, en: signal}
  - {ru: непрерывный, en: continuous}
  - {ru: дискретный, en: discrete}
homework: homework/book-01-information-sources
```

- [ ] **Step 2: Написать сценарий на 15 минут**

`teacher/scenario.md`, четыре такта:

| Мин | Такт | Чем закончится |
|---|---|---|
| 0–3 | Сигнал против информации: по проводу летит напряжение, информацией оно становится в голове | Ученица различает носитель и смысл |
| 3–7 | Данные против информации: данные записаны, информация — то, что понял. Пример: строка `19` в файле и «мне 19 лет» | Понимает, почему `data` — не то же, что `information` |
| 7–11 | Свойства информации по учебнику (достоверность, актуальность, полнота) на живом примере: три источника об одном событии | Умеет назвать три свойства и применить их |
| 11–15 | Непрерывное и дискретное: звук как волна и звук как числа. Мост к следующим модулям | Готова к §1.4 и к двоичному кодированию |

В разделе «Где залипнет»: различие «данные / информация» на слух звучит как игра слов — держать пример с `19` под рукой и не уходить в абстракцию.

- [ ] **Step 3: Написать шпаргалку и словарик**

`student/cheatsheet.html` — по шаблону, чип `BOOK`, `--track: #7aa2ff`, `--track-ink: #2b4fa8`. Содержит: три свойства информации, различие данные/информация одной строкой, пару непрерывное/дискретное.

`student/glossary.md` — таблица из пяти терминов манифеста в формате «Учебник (рус) · В проде (eng) · Что это одной строкой».

- [ ] **Step 4: Завести errata с первой записью**

`textbook/errata.md` — шапка с объяснением формата и четырьмя обязательными полями, затем первая запись:

> **7 кл, §1.1.2 — «виды информации по способу восприятия»**
> **Учебник:** зрительная, слуховая, обонятельная, вкусовая, тактильная.
> **В жизни:** это классификация того, как человек воспринимает, а не того, чем информация является. Компьютеру всё равно — он видит только байты, а «зрительная» картинка и «слуховой» звук в памяти отличаются форматом, а не природой.
> **Говорим ей:** учебник классифицирует восприятие человеком; для данных в компьютере эта шкала не работает.
> **В школе отвечай:** пять видов по органам чувств. Это то, что спрашивают.

- [ ] **Step 5: Написать домашку**

`homework/book-01-information-sources/task.md`: найти три источника об одном и том же событии (любом — от матча до новости о школе), выписать по каждому достоверность, актуальность и полноту, одним абзацем ответить, какому источнику веришь больше и почему. Сдача 13.09 — текстом в MAX: репозитория ещё нет, git начинается 16.09.

- [ ] **Step 6: Прогнать проверки**

Run: `cd tools && .venv/bin/python validate_modules.py ..`
Expected: `ok tracks/book/m-01-information-and-data`, ошибок нет

Затем `/brand-check tracks/book/m-01-information-and-data` — починить найденное.

- [ ] **Step 7: Commit**

```bash
git add tracks/book/m-01-information-and-data homework/book-01-information-sources textbook/errata.md
git commit -m "book: модуль об информации и данных, §1.1 седьмого класса"
```

---

### Task 12: Модуль devops/m-01-terminal-first-steps

**Files:**
- Create: `tracks/devops/m-01-terminal-first-steps/module.yml`
- Create: `tracks/devops/m-01-terminal-first-steps/shared/slides.html`
- Create: `tracks/devops/m-01-terminal-first-steps/shared/live-code.md`
- Create: `tracks/devops/m-01-terminal-first-steps/student/cheatsheet.html`
- Create: `tracks/devops/m-01-terminal-first-steps/student/glossary.md`
- Create: `tracks/devops/m-01-terminal-first-steps/teacher/scenario.md`
- Create: `homework/devops-01-terminal/task.md`

**Interfaces:**
- Consumes: шаблон (Task 6), токены `--track-ops` / `--track-ops-ink`
- Produces: рабочую папку `~/code/junior_it` на машине ученицы и проверенный `python3`, на которые опирается Task 13

- [ ] **Step 1: Написать манифест**

```yaml
id: devops/m-01-terminal-first-steps
title: "Терминал: где я и что вокруг (terminal first steps)"
track: devops
level: core
minutes: 25
textbook: ["7:2.3"]
requires: []
terms:
  - {ru: терминал, en: terminal}
  - {ru: оболочка, en: shell, note: "zsh — на маке по умолчанию"}
  - {ru: каталог, en: directory, note: "«папка» — то же самое"}
  - {ru: путь, en: path}
  - {ru: домашний каталог, en: home directory}
homework: homework/devops-01-terminal
```

`textbook: ["7:2.3"]` — параграф «Файлы и каталоги». Идём вперёд школы: тему берём в сентябре, в школе она будет во второй четверти.

- [ ] **Step 2: Написать живой код**

`shared/live-code.md`, шесть шагов, каждый набирается на экране при ученице:

1. `pwd` — где я сейчас. Читаем путь вслух слева направо.
2. `ls` и `ls -la` — что вокруг, и что бывают скрытые файлы.
3. `cd ~`, `cd ..`, `cd -` — три способа переехать. `~` это дом, `..` это на уровень выше.
4. `mkdir -p ~/code/junior_it` и `cd ~/code/junior_it` — рабочая папка на весь курс.
5. `touch notes.md`, `ls`, `open .` — файл появился и виден в Finder. Терминал и Finder смотрят на одно и то же.
6. `python3 --version` — проверка, что язык на месте.

Если `python3` отвечает версией 3.9 или его нет — ставим свежий через Homebrew: `brew install python@3.12`. Проверка окружения одной командой: `bash provisioning/check-mac.sh`.

- [ ] **Step 3: Написать сценарий на 25 минут**

| Мин | Такт | Чем закончится |
|---|---|---|
| 0–4 | Зачем терминал, если есть мышка: одна команда против пятнадцати кликов | Хочет попробовать |
| 4–14 | Живой код, шаги 1–5: она набирает сама, ты подсказываешь | Есть рабочая папка `~/code/junior_it` |
| 14–19 | Windows-параллель одним слайдом: `pwd` → `cd`, `ls` → `dir`, `~` → `%USERPROFILE%`. И главное: на сервере, где живут сайты, стоит Linux, а команды те же, что на маке | Понимает, что навык переносимый |
| 19–25 | Проверка окружения, шаг 6. Ставим Python, если надо | `python3 --version` отвечает 3.12 |

В «Где залипнет»: путь `/Users/имя/code/junior_it` читается как абракадабра, пока не прочитан вслух слева направо как адрес — от корня к дому и дальше вниз.

- [ ] **Step 4: Написать шпаргалку и словарик**

`student/cheatsheet.html` — чип `OPS`, `--track: #00e676`, `--track-ink: #00803d`. Таблица из десяти команд с колонкой «а в Windows», и блок «если что-то пошло не так»: `cd ~` возвращает домой всегда.

`student/glossary.md` — пять терминов манифеста.

- [ ] **Step 5: Написать домашку**

`homework/devops-01-terminal/task.md` — терминал-квест: не выходя из терминала, собрать в `~/code/junior_it` дерево

```
junior_it/
├── notes.md
├── hw/
│   └── 01/
│       └── answer.md
└── sandbox/
```

и прислать вывод `ls -R ~/code/junior_it` скриншотом в MAX. Отдельным пунктом: написать в `notes.md` одну строку о том, какая команда показалась самой полезной.

- [ ] **Step 6: Прогнать проверки**

Run: `cd tools && .venv/bin/python validate_modules.py ..`
Expected: `ok tracks/devops/m-01-terminal-first-steps`

Затем `/brand-check tracks/devops/m-01-terminal-first-steps`.

- [ ] **Step 7: Commit**

```bash
git add tracks/devops/m-01-terminal-first-steps homework/devops-01-terminal
git commit -m "devops: модуль первых шагов в терминале"
```

---

### Task 13: Модуль python/m-01-first-run

**Files:**
- Create: `tracks/python/m-01-first-run/module.yml`
- Create: `tracks/python/m-01-first-run/shared/slides.html`
- Create: `tracks/python/m-01-first-run/shared/live-code.md`
- Create: `tracks/python/m-01-first-run/student/cheatsheet.html`
- Create: `tracks/python/m-01-first-run/student/glossary.md`
- Create: `tracks/python/m-01-first-run/teacher/scenario.md`
- Create: `homework/python-01-first-run/task.md`
- Modify: `textbook/errata.md`

**Interfaces:**
- Consumes: рабочую папку и `python3` из Task 12; токены `--track-py` / `--track-py-ink`
- Produces: первый модуль трека `python`, на который ссылаются `requires` следующих модулей

- [ ] **Step 1: Написать манифест**

```yaml
id: python/m-01-first-run
title: "Первый запуск Python (first run)"
track: python
level: core
minutes: 25
textbook: ["8:5.1"]
requires: [devops/m-01-terminal-first-steps]
terms:
  - {ru: интерпретатор, en: interpreter}
  - {ru: скрипт, en: script}
  - {ru: вывод, en: output}
  - {ru: строка, en: string, note: "текст в кавычках"}
  - {ru: ошибка, en: traceback, note: "читается снизу вверх"}
homework: homework/python-01-first-run
```

`textbook: ["8:5.1"]` — параграф восьмого класса. Опережение на год начинается с первого же занятия по Python.

- [ ] **Step 2: Написать живой код**

`shared/live-code.md`, пять шагов:

1. `python3` в терминале — приглашение `>>>`. Считаем `2 + 2`, `10 / 3`, `10 // 3`. Это калькулятор, который умеет больше.
2. `print("Привет")` — первый вывод. Кавычки обязательны: без них Python ищет имя, а не текст.
3. `exit()` — выходим. REPL хорош для проб, программы живут в файлах.
4. `touch hello.py`, открыть в редакторе, написать три строки с `print`, запустить `python3 hello.py`.
5. **Ошибка нарочно:** убрать закрывающую кавычку, запустить, прочитать traceback снизу вверх — сначала что случилось, потом где. Вернуть кавычку.

Шаг 5 обязателен: первая ошибка должна случиться при тебе, а не дома в одиночестве.

- [ ] **Step 3: Написать сценарий на 25 минут**

| Мин | Такт | Чем закончится |
|---|---|---|
| 0–3 | Почему Python, а не JS: одна и та же задача, и то, где каждый язык живёт | Понимает смену языка без ощущения, что прошлое было зря |
| 3–10 | Живой код, шаги 1–3: REPL как калькулятор | Считает и печатает в интерактивном режиме |
| 10–18 | Шаг 4: первый файл и запуск из терминала | `python3 hello.py` печатает её три строки |
| 18–23 | Шаг 5: ошибка нарочно и чтение traceback | Не боится красного текста, знает, что читать снизу |
| 23–25 | Что дальше: это материал восьмого класса, школа дойдёт через год | Видит, зачем опережение |

В «Где залипнет»: разница между REPL и файлом. Держать формулировку наготове — «в `>>>` ты разговариваешь, в файле пишешь письмо».

- [ ] **Step 4: Написать шпаргалку и словарик**

`student/cheatsheet.html` — чип `PY`, `--track: #00ffc8`, `--track-ink: #00806a`. Содержит: запуск REPL и выход, `print` со строкой и с числом, запуск файла, разбор traceback на реальном примере с подписью «читай снизу вверх».

`student/glossary.md` — пять терминов манифеста.

- [ ] **Step 5: Написать домашку**

`homework/python-01-first-run/task.md`:

1. `hello.py` в `~/code/junior_it/hw/01/` печатает три строки о себе (имя, любимое занятие, что хочет уметь через год).
2. Второй файл `broken.py` даётся уже сломанным — три ошибки: пропущенная кавычка, `Print` с большой буквы, лишняя скобка. Починить и запустить.
3. Прислать скриншот терминала с выводом обеих программ.

Текст `broken.py` кладётся в `homework/python-01-first-run/broken.py`.

Тестов на этой домашке нет: `pytest` и репозиторий появляются 16.09, автопроверка — 30.09.

- [ ] **Step 6: Дописать errata**

Добавить в `textbook/errata.md` вторую запись:

> **8 кл, приложение 3 — «Некоторые операторы модуля Graph в Python»**
> **Учебник:** приводит `windowSize`, `canvasSize`, `penColor`, `line`, `circle` как операторы модуля `Graph`.
> **В жизни:** модуля `Graph` в стандартной библиотеке Python нет. Это самодельный модуль под конкретный учебник; программа из приложения на чистом Python не запустится. Рисовать будем через `turtle` — он в стандартной поставке и работает везде.
> **Говорим ей:** если код из учебника падает с `ModuleNotFoundError` — дело не в ней, модуля просто нет.
> **В школе отвечай:** как в учебнике. На бумаге код проверяют глазами, а не запуском.

- [ ] **Step 7: Прогнать проверки**

Run: `cd tools && .venv/bin/python validate_modules.py ..`
Expected: `ok tracks/python/m-01-first-run`, `модулей с ошибками: 0` по всей библиотеке (14 модулей)

Затем `/brand-check tracks/python/m-01-first-run`.

- [ ] **Step 8: Commit**

```bash
git add tracks/python/m-01-first-run homework/python-01-first-run textbook/errata.md
git commit -m "python: модуль первого запуска, §5.1 восьмого класса"
```

---

### Task 14: Занятие 13.09 и атлас седьмого класса

**Files:**
- Create: `playground/2026-09-13/session.yml`
- Create: `playground/2026-09-13/notes.md`
- Create: `playground/2026-09-13/code/.gitkeep`
- Create: `playground/2026-09-13/artifacts/.gitkeep`
- Create: `textbook/atlas-07.md`

**Interfaces:**
- Consumes: три модуля из Task 11–13
- Produces: плейлист первого занятия по новой системе; `textbook/atlas-07.md`, который пополняют следующие планы

- [ ] **Step 1: Собрать плейлист**

`playground/2026-09-13/session.yml`:

```yaml
date: 2026-09-13
time: "20:00"
duration: 75
theme: "Терминал и первый Python"
playlist:
  - {module: book/m-01-information-and-data, minutes: 15}
  - {module: devops/m-01-terminal-first-steps, minutes: 25}
  - {module: python/m-01-first-run, minutes: 25}
buffer: 10
homework:
  - homework/book-01-information-sources
  - homework/devops-01-terminal
  - homework/python-01-first-run
```

Сумма модулей — 65 минут, буфер 10 при потолке 75.

- [ ] **Step 2: Завести заметки занятия**

`playground/2026-09-13/notes.md` — заготовка с разделами: «Что успели», «Где залипли», «Её вопросы», «Что перенести в модуль». Заполняется по ходу и сразу после занятия.

- [ ] **Step 3: Завести атлас седьмого класса**

`textbook/atlas-07.md` — таблица по всем главам учебника со статусами. Заполнить строки главы 1 фактически, остальные — со статусом `запланирован` и пустым модулем:

| § | Тема | Наш модуль | Статус | Школа проходит | Δ |
|---|---|---|---|---|---|
| 1.1 | Информация и данные | `book/m-01-information-and-data` | закрыт 13.09 | сентябрь | 0 |
| 1.2 | Информационные процессы | — | запланирован 16.09 | сентябрь | +1 нед |
| 1.3 | Представление информации | — | запланирован 20.09 | октябрь | +4 нед |
| 1.4 | Двоичное представление данных | `cs/m-02-layers` частично | запланирован 23.09 | октябрь | +4 нед |
| 1.5 | Измерение информации | — | запланирован 30.09 | ноябрь | +6 нед |
| 2.3 | Файлы и каталоги | `devops/m-01-terminal-first-steps` | закрыт 13.09 | ноябрь | +9 нед |

Дальше — строки глав 2–5 со статусом `запланирован`. Главы 3–5 (текст, графика, мультимедиа) пометить как «закрываем тренажёром и тестами, без отдельных занятий» — это решение из спеки.

Шапка файла объясняет колонку Δ и правило: модуль ставится в плейлист не позже чем за две недели до школьного параграфа.

- [ ] **Step 4: Проверить связность**

Run: `cd tools && .venv/bin/python validate_modules.py ..`
Expected: `модулей с ошибками: 0`

Run: `grep -c "  - {module:" playground/2026-09-13/session.yml`
Expected: `3` — три модуля в плейлисте

- [ ] **Step 5: Убедиться, что playground не публикуется**

Run: `./tools/build_site.sh /tmp/junior_it_site && test ! -d /tmp/junior_it_site/playground && echo "playground не в сайте"`
Expected: `playground не в сайте`

- [ ] **Step 6: Прогнать весь тестовый набор**

Run: `cd tools && .venv/bin/python -m pytest -v`
Expected: PASS, 32 теста

- [ ] **Step 7: Commit**

```bash
git add playground/2026-09-13 textbook/atlas-07.md
git commit -m "session: занятие 13.09 и атлас седьмого класса"
```

---

## Что осталось за рамками этого плана

Каждый пункт — отдельный план, каждый даёт работающий результат сам по себе:

1. **Тренажёр и банк вопросов** — `trainer/` на статике, `textbook/quizzes/*.json`, семь типов вопросов, режимы тренировки и зачёта. Нужен OCR обоих учебников (гоняется в `~/Library/Caches/junior_it_ocr/`).
2. **Репозиторий ученицы, автопроверка и поощрения** — структура `hw/`, `check.yml` с pytest, приватный `Junior_IT-keys`, скрипт выдачи эталонов после merge, бейджи прогресса и ачивки в её `README.md`. Разворачивается к 16.09 (git, ступень 1) и добивается к 30.09 (CI).
3. **Лендинг и карта курса** — `index.html` переписывается под треки, модули загораются цветом по мере прохождения, бейджи прогресса.
4. **Атлас восьмого класса и errata целиком** — после OCR, с ручной вычиткой формул и кода.
5. **Модуль `python/m-00-why-python`** — восстанавливается по записи занятия 09.09, когда Димас пришлёт файл.
