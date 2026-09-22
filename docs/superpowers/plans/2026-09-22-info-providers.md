# Провайдеры info-панели Junior_IT — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Семь боксов вкладки `info` для Junior_IT: пять `command`-провайдеров (`занятие`, `ученики`, `домашки`, `готовность`, `курс`) в пакете `tools/info/` и манифест `.zellij/info.yml`; `clock` и `git` даёт движок.

**Architecture:** Пакет `tools/info/`: `common.py` (модель строки, печать JSON lines, «ближайшее занятие», отсчёт, пути), по модулю на бокс с одной чистой функцией `lines(...) -> list[Line]` (тестируется на фикстурах без диска), `cli.py <box>` — единственный вход, который грузит данные через уже существующие `build_course_map`, `module_schema`, `journal.store/stats` и печатает по контракту движка `{"lines": [{"text","open","style"}]}`. Манифест валидируется тестом через движок из деплойнутого venv.

**Tech Stack:** Python 3.12 (`tools/.venv`), PyYAML, pytest (`cd tools && .venv/bin/python -m pytest -q`, 185 зелёных); движок info-панели — `~/.local/lib/terminal-commander/cockpit` (Textual 8.2.8, цель `run:` есть).

**Spec:** `docs/superpowers/specs/2026-09-22-info-providers-design.md` — исполнитель читает обе.

## Global Constraints

- **Приватность:** на панель попадают только `name` из ростера и счётчики; тесты — в `tmp_path`, только `alice`/`bob`/`carol`; реальный `students/` тестами не читается. Скриншот с реальными именами — только в scratchpad сессии.
- **Рабочее дерево содержит чужие незакоммиченные правки** (`homework/python-01-first-run/task.md`, `playground/2026-09-20/session.yml`, `provisioning/setup-windows.*`, `tracks/python/m-01-first-run/…`). Стейджить только свои файлы поимённо; `git add -A`/`.` запрещены.
- Контракт движка: stdout — `{"lines": [{"text": str, "open": str|null, "style": "ok|warn|err|dim"|null}]}`; `open` — путь относительно корня репо, URL или `run:<команда>`; код ≠ 0 → бокс `⚠` с хвостом stderr.
- Коды CLI: 0 ок; 2 неизвестный бокс/аргументы (argparse); 3 битые данные (`JournalError`, `ValueError` из `build_course_map`, `yaml.YAMLError`).
- «Ближайшее занятие»: минимальная дата плана ≥ today; нет — последний прошедший со `stale=True`; нет планов — `None`.
- Отсчёт: `сегодня` / `завтра` / `через N дн.` / `N дн. назад`. Дни недели: `пн вт ср чт пт сб вс`. Даты на экране — `ДД.ММ`.
- Идентификаторы модулей показываются как в `module.yml` (`python/m-01-first-run`), не сокращаются — в спеке пример с укороченным именем читать как иллюстрацию.
- Файлы анатомии для «готовности»: `teacher/scenario.md`, `shared/live-code.md`, `shared/slides.html`, `student/cheatsheet.html`, `student/glossary.md`; метки `scenario live-code slides cheatsheet glossary`.
- Команда TUI журнала: `tools/.venv/bin/python tools/journal/tui.py`; GH Pages: `https://dmitrtrc.github.io/Junior_IT/`.
- Коммиты: conventional, русское описание, без emoji, футер:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01XFthZUabadDPVaHxjhrY4Q
  ```
  `git commit` — да, `git push` — нет. Ветка `feat/info-providers` от `main` (057c9a3).

## File Structure

- `tools/info/__init__.py` — CREATE (T1): docstring.
- `tools/info/common.py` — CREATE (T1): `REPO_ROOT`, `TUI_CMD`, `PAGES_URL`, `WEEKDAYS`, `Line`, `emit`, `next_session`, `countdown`, `weekday_ru`, `fmt_day`, `as_date`, `hw_id_from_ref`, `module_dir`, `scenario_target`, `homework_task`.
- `tools/info/lesson.py`, `tools/info/course.py` — CREATE (T2).
- `tools/info/students.py`, `tools/info/homework.py` — CREATE (T3).
- `tools/info/readiness.py` — CREATE (T4).
- `tools/info/cli.py` — CREATE (T5), `+x`.
- `.zellij/info.yml` — CREATE (T6).
- Тесты: `tools/tests/test_info_common.py` (T1), `test_info_lesson_course.py` (T2), `test_info_journal_boxes.py` (T3), `test_info_readiness.py` (T4), `test_info_cli.py` (T5), `test_info_manifest.py` (T6). Фикстуры: `journal_root`/`course_root`/`DAY`/`TODAY` из `tools/tests/conftest.py`; `make_module` из `tools/tests/test_build_course_map.py` (импортируется как модуль: `from test_build_course_map import make_module`).

---

### Task 1: `info/common.py` — модель строки, печать, ближайшее занятие, пути

**Files:**
- Create: `tools/info/__init__.py`, `tools/info/common.py`
- Test: `tools/tests/test_info_common.py`

**Interfaces:**
- Produces: `REPO_ROOT: Path` (= `Path(__file__).resolve().parents[2]`); `TUI_CMD = "tools/.venv/bin/python tools/journal/tui.py"`; `PAGES_URL`; `WEEKDAYS`; `@dataclass(frozen=True) Line(text: str, open: str|None=None, style: str|None=None)`; `emit(lines, out=None)` печатает одну JSON-строку; `next_session(sessions: list[dict], today) -> tuple[dict|None, bool]`; `countdown(day, today) -> str`; `weekday_ru(day) -> str`; `fmt_day(day) -> "ДД.ММ"`; `as_date(value) -> date` (date или ISO-строка); `hw_id_from_ref(ref) -> str` (`homework/python-01` → `python-01`); `module_dir(module_id, repo_root) -> Path`; `scenario_target(module_id, repo_root) -> str` (относительный `teacher/scenario.md`, иначе `module.yml`); `homework_task(hw_id) -> str` (`homework/<id>/task.md`).

- [ ] **Step 1: Провальные тесты** — `tools/tests/test_info_common.py`

```python
import io
import json
from datetime import date

from info.common import (
    Line, as_date, countdown, emit, fmt_day, homework_task, hw_id_from_ref,
    module_dir, next_session, scenario_target, weekday_ru,
)

TODAY = date(2026, 9, 22)


def _s(day, **extra):
    return {"date": day, **extra}


def test_next_session_prefers_nearest_future():
    sessions = [_s(date(2026, 9, 13)), _s(date(2026, 9, 27)), _s(date(2026, 9, 24))]
    session, stale = next_session(sessions, TODAY)
    assert session["date"] == date(2026, 9, 24) and stale is False


def test_next_session_today_counts_as_upcoming():
    session, stale = next_session([_s(date(2026, 9, 13)), _s(TODAY)], TODAY)
    assert session["date"] == TODAY and stale is False


def test_next_session_falls_back_to_last_past():
    session, stale = next_session([_s(date(2026, 9, 13)), _s(date(2026, 9, 20))], TODAY)
    assert session["date"] == date(2026, 9, 20) and stale is True
    assert next_session([], TODAY) == (None, False)


def test_countdown_and_weekday():
    assert countdown(TODAY, TODAY) == "сегодня"
    assert countdown(date(2026, 9, 23), TODAY) == "завтра"
    assert countdown(date(2026, 9, 25), TODAY) == "через 3 дн."
    assert countdown(date(2026, 9, 20), TODAY) == "2 дн. назад"
    assert weekday_ru(date(2026, 9, 23)) == "ср" and weekday_ru(date(2026, 9, 27)) == "вс"
    assert fmt_day(date(2026, 9, 3)) == "03.09"
    assert as_date("2026-09-23") == date(2026, 9, 23) and as_date(TODAY) == TODAY


def test_hw_id_and_paths(tmp_path):
    assert hw_id_from_ref("homework/python-01-first-run") == "python-01-first-run"
    assert hw_id_from_ref("python-01-first-run/") == "python-01-first-run"
    assert homework_task("python-01-first-run") == "homework/python-01-first-run/task.md"
    assert module_dir("python/m-01-first-run", tmp_path) == tmp_path / "tracks" / "python" / "m-01-first-run"
    d = tmp_path / "tracks" / "python" / "m-01-first-run"
    (d / "teacher").mkdir(parents=True)
    assert scenario_target("python/m-01-first-run", tmp_path) == "tracks/python/m-01-first-run/module.yml"
    (d / "teacher" / "scenario.md").write_text("x", encoding="utf-8")
    assert scenario_target("python/m-01-first-run", tmp_path) == "tracks/python/m-01-first-run/teacher/scenario.md"


def test_emit_prints_contract_json():
    buf = io.StringIO()
    emit([Line("занятие", open="playground/x/session.yml", style="ok"), Line("буфер")], out=buf)
    data = json.loads(buf.getvalue())
    assert data == {"lines": [
        {"text": "занятие", "open": "playground/x/session.yml", "style": "ok"},
        {"text": "буфер", "open": None, "style": None}]}
    assert "\\u" not in buf.getvalue()
```

- [ ] **Step 2: Запустить — падает на импорте**

Run: `cd tools && .venv/bin/python -m pytest tests/test_info_common.py -q`
Expected: `ModuleNotFoundError: No module named 'info'`

- [ ] **Step 3: Реализация**

`tools/info/__init__.py`:

```python
"""Провайдеры боксов info-панели Junior_IT: печатают JSON lines по контракту command."""
```

`tools/info/common.py`:

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TUI_CMD = "tools/.venv/bin/python tools/journal/tui.py"
PAGES_URL = "https://dmitrtrc.github.io/Junior_IT/"
WEEKDAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


@dataclass(frozen=True)
class Line:
    text: str
    open: str | None = None
    style: str | None = None


def emit(lines, out=None) -> None:
    payload = {"lines": [{"text": line.text, "open": line.open, "style": line.style} for line in lines]}
    print(json.dumps(payload, ensure_ascii=False), file=out)


def next_session(sessions, today: date) -> tuple[dict | None, bool]:
    """Ближайший план (дата >= today); нет — последний прошедший и stale=True; нет планов — (None, False)."""
    upcoming = [s for s in sessions if s["date"] >= today]
    if upcoming:
        return min(upcoming, key=lambda s: s["date"]), False
    if sessions:
        return max(sessions, key=lambda s: s["date"]), True
    return None, False


def countdown(day: date, today: date) -> str:
    delta = (day - today).days
    if delta == 0:
        return "сегодня"
    if delta == 1:
        return "завтра"
    if delta > 1:
        return f"через {delta} дн."
    return f"{-delta} дн. назад"


def weekday_ru(day: date) -> str:
    return WEEKDAYS[day.weekday()]


def fmt_day(day: date) -> str:
    return day.strftime("%d.%m")


def as_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def hw_id_from_ref(ref) -> str:
    return str(ref).rstrip("/").split("/")[-1]


def module_dir(module_id: str, repo_root=REPO_ROOT) -> Path:
    track, name = str(module_id).split("/", 1)
    return Path(repo_root) / "tracks" / track / name


def scenario_target(module_id: str, repo_root=REPO_ROOT) -> str:
    """open-цель модуля относительно корня: teacher/scenario.md, иначе module.yml."""
    directory = module_dir(module_id, repo_root)
    rel = directory.relative_to(Path(repo_root))
    if (directory / "teacher" / "scenario.md").is_file():
        return str(rel / "teacher" / "scenario.md")
    return str(rel / "module.yml")


def homework_task(hw_id: str) -> str:
    return f"homework/{hw_id}/task.md"
```

- [ ] **Step 4: Запустить — зелёные, старые не тронуты**

Run: `cd tools && .venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/info/__init__.py tools/info/common.py tools/tests/test_info_common.py
git commit -m "feat(info): общий слой провайдеров — строка, JSON lines, ближайшее занятие, отсчёт, пути"
```

---

### Task 2: боксы `занятие` и `курс`

**Files:**
- Create: `tools/info/lesson.py`, `tools/info/course.py`
- Test: `tools/tests/test_info_lesson_course.py`

**Interfaces:**
- Consumes: `common.*` (Task 1); `build_course_map.module_statuses(modules, sessions, today) -> dict[id, "done|current|planned|library"]` (существующий, `tools/build_course_map.py`).
- Produces: `lesson.lines(session: dict|None, stale: bool, today: date, repo_root=REPO_ROOT) -> list[Line]`; `course.lines(modules: list[dict], sessions: list[dict], today: date) -> list[Line]`. `modules` — dicts с `id`, `track`, `level` (как из `load_modules`); `sessions` — dicts с `date: date`, `playlist`, опц. `completed`.

- [ ] **Step 1: Провальные тесты** — `tools/tests/test_info_lesson_course.py`

```python
from datetime import date

from info import course, lesson
from info.common import PAGES_URL

TODAY = date(2026, 9, 22)
PLAN = {
    "date": date(2026, 9, 24), "time": "20:00", "theme": "Ветвление",
    "playlist": [{"module": "python/m-02-branching", "minutes": 35}, {"module": "book/m-01-information-and-data"}],
    "buffer": 10,
    "homework": {"due": date(2026, 9, 27), "items": ["homework/python-02-branching"]},
}


def test_lesson_lines_future_plan(tmp_path):
    (tmp_path / "tracks" / "python" / "m-02-branching" / "teacher").mkdir(parents=True)
    (tmp_path / "tracks" / "python" / "m-02-branching" / "teacher" / "scenario.md").write_text("x", encoding="utf-8")
    out = lesson.lines(PLAN, False, TODAY, tmp_path)
    assert [l.text for l in out] == [
        "чт 24.09 20:00 · через 2 дн.", "Ветвление",
        "python/m-02-branching · 35 мин", "book/m-01-information-and-data",
        "домашка до 27.09: python-02-branching", "буфер 10 мин"]
    assert out[0].open == "playground/2026-09-24/session.yml" and out[0].style is None
    assert out[2].open == "tracks/python/m-02-branching/teacher/scenario.md"
    assert out[3].open == "tracks/book/m-01-information-and-data/module.yml"
    assert out[4].open == "homework/python-02-branching/task.md"
    assert out[5].style == "dim"


def test_lesson_lines_today_and_stale(tmp_path):
    today_plan = {**PLAN, "date": TODAY}
    assert lesson.lines(today_plan, False, TODAY, tmp_path)[0].style == "ok"
    assert lesson.lines(today_plan, False, TODAY, tmp_path)[0].text.startswith("вт 22.09 20:00 · сегодня")
    stale = lesson.lines({**PLAN, "date": date(2026, 9, 20)}, True, TODAY, tmp_path)
    assert stale[0].style == "warn" and "план на следующее не создан" in stale[0].text
    assert "2 дн. назад" in stale[0].text


def test_lesson_lines_without_plan_or_homework(tmp_path):
    out = lesson.lines(None, False, TODAY, tmp_path)
    assert len(out) == 1 and out[0].style == "warn" and "планов нет" in out[0].text
    bare = lesson.lines({"date": date(2026, 9, 24)}, False, TODAY, tmp_path)
    assert [l.text for l in bare] == ["чт 24.09 · через 2 дн."]


MODULES = [
    {"id": "python/m-01", "track": "python", "level": "core"},
    {"id": "python/m-02", "track": "python", "level": "core"},
    {"id": "devops/m-01", "track": "devops", "level": "core"},
    {"id": "web/reading", "track": "web", "level": "optional"},
]
SESSIONS = [
    {"date": date(2026, 9, 13), "playlist": [{"module": "devops/m-01"}]},
    {"date": date(2026, 9, 20), "playlist": [{"module": "python/m-01"}], "completed": ["python/m-01"]},
    {"date": date(2026, 9, 24), "playlist": [{"module": "python/m-02"}]},
]


def test_course_lines():
    out = course.lines(MODULES, SESSIONS, TODAY)
    assert [l.text for l in out] == ["занятий проведено: 2", "модулей: 2/3", "devops 1/1 · python 1/2"]
    assert all(l.style == "dim" and l.open == PAGES_URL for l in out)


def test_course_lines_empty():
    assert [l.text for l in course.lines([], [], TODAY)] == ["занятий проведено: 0", "модулей: 0/0", "модулей нет"]
```

- [ ] **Step 2: Запустить — падает**

Run: `cd tools && .venv/bin/python -m pytest tests/test_info_lesson_course.py -q`
Expected: `ImportError: cannot import name 'course' from 'info'`

- [ ] **Step 3: Реализация**

`tools/info/lesson.py`:

```python
from __future__ import annotations
from datetime import date

from info.common import (
    REPO_ROOT, Line, as_date, countdown, fmt_day, homework_task, hw_id_from_ref,
    scenario_target, weekday_ru,
)


def lines(session: dict | None, stale: bool, today: date, repo_root=REPO_ROOT) -> list[Line]:
    if session is None:
        return [Line("планов нет — заведи playground/<дата>/session.yml", style="warn")]
    day = as_date(session["date"])
    plan_path = f"playground/{day.isoformat()}/session.yml"
    head = f"{weekday_ru(day)} {fmt_day(day)}"
    if session.get("time"):
        head += f" {session['time']}"
    head += f" · {countdown(day, today)}"
    if stale:
        out = [Line(head + " · план на следующее не создан", open=plan_path, style="warn")]
    else:
        out = [Line(head, open=plan_path, style="ok" if day == today else None)]
    if session.get("theme"):
        out.append(Line(str(session["theme"]), open=plan_path))
    for item in session.get("playlist") or []:
        if not isinstance(item, dict) or not item.get("module"):
            continue
        module_id = str(item["module"])
        text = f"{module_id} · {item['minutes']} мин" if item.get("minutes") else module_id
        out.append(Line(text, open=scenario_target(module_id, repo_root)))
    homework = session.get("homework") or {}
    due = homework.get("due")
    for ref in homework.get("items") or []:
        hw_id = hw_id_from_ref(ref)
        prefix = f"домашка до {fmt_day(as_date(due))}: " if due else "домашка: "
        out.append(Line(prefix + hw_id, open=homework_task(hw_id)))
    if session.get("buffer"):
        out.append(Line(f"буфер {session['buffer']} мин", style="dim"))
    return out
```

`tools/info/course.py`:

```python
from __future__ import annotations
from datetime import date

from build_course_map import module_statuses
from info.common import PAGES_URL, Line


def lines(modules: list[dict], sessions: list[dict], today: date) -> list[Line]:
    held = sum(1 for s in sessions if s["date"] < today)
    statuses = module_statuses(modules, sessions, today)
    counted = [m for m in modules if statuses[m["id"]] != "library"]
    done_total = sum(1 for m in counted if statuses[m["id"]] == "done")
    by_track: dict[str, list[int]] = {}
    for module in counted:
        done, total = by_track.setdefault(module["track"], [0, 0])
        by_track[module["track"]] = [done + (statuses[module["id"]] == "done"), total + 1]
    tracks = " · ".join(f"{track} {done}/{total}" for track, (done, total) in sorted(by_track.items()))
    return [
        Line(f"занятий проведено: {held}", open=PAGES_URL, style="dim"),
        Line(f"модулей: {done_total}/{len(counted)}", open=PAGES_URL, style="dim"),
        Line(tracks or "модулей нет", open=PAGES_URL, style="dim"),
    ]
```

- [ ] **Step 4: Запустить — зелёные**

Run: `cd tools && .venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/info/lesson.py tools/info/course.py tools/tests/test_info_lesson_course.py
git commit -m "feat(info): боксы «занятие» и «курс» — ближайший план, плейлист, домашка, сводка по трекам"
```

---

### Task 3: боксы `ученики` и `домашки` (из журнала)

**Files:**
- Create: `tools/info/students.py`, `tools/info/homework.py`
- Test: `tools/tests/test_info_journal_boxes.py`

**Interfaces:**
- Consumes: `common.*`; `journal.stats.GroupStats/StudentStats/collect(root, repo_root, today)`, `journal.store.load_roster/load_lessons/hw_due_from_plan`, `journal.stats.load_plans(repo_root)`, `journal.model.num`; фикстуры `journal_root`, `course_root`, `DAY`, `TODAY` (TODAY = 2026-09-25).
- Produces: `students.lines(group: GroupStats|None, tui_cmd=TUI_CMD) -> list[Line]`; `homework.lines(lessons: list[LessonRecord], plans: dict[date, dict|None], today: date, next_plan: dict|None=None) -> list[Line]`.

- [ ] **Step 1: Провальные тесты** — `tools/tests/test_info_journal_boxes.py`

```python
from datetime import date

from conftest import DAY, TODAY
from info import homework, students
from info.common import TUI_CMD
from journal import stats, store


def test_students_lines_from_journal(journal_root, course_root):
    group = stats.collect(journal_root, course_root, TODAY)
    out = students.lines(group)
    assert out[0].text == "журнал · занятий 1" and out[0].open == f"run:{TUI_CMD}"
    assert out[1].text == "Алиса · был 1/1 · дз 0/1 · 2 б" and out[1].style == "warn"   # хвост: просрочена
    assert out[2].text == "Боб · был 1/1 · дз 0/1 · 1 б" and out[2].style == "warn"     # хвост: ждёт решения
    assert out[3].text == "без журнала: 2026-09-13" and out[3].style == "warn"
    assert out[3].open == f"run:{TUI_CMD} --date 2026-09-13"
    assert len(out) == 4                                                                    # carol (left) не показывается


def test_students_lines_no_tails_no_style(journal_root, course_root):
    group = stats.collect(journal_root, course_root, date(2026, 9, 21))
    assert all(l.style is None for l in students.lines(group)[1:3])


def test_students_lines_without_roster():
    out = students.lines(None)
    assert len(out) == 1 and out[0].style == "warn" and "roster.yml" in out[0].text
    assert out[0].open == "tools/journal/roster.example.yml"


def test_homework_lines_from_journal(journal_root, course_root):
    roster = store.load_roster(journal_root)
    lessons = store.load_lessons(journal_root, roster)
    plans = stats.load_plans(course_root)
    out = homework.lines(lessons, plans, TODAY, next_plan=plans[DAY])
    assert [l.text for l in out] == ["python-01-first-run · сдано 1/2 · принято 0/2 · до 23.09"]
    assert out[0].style == "warn" and out[0].open == "homework/python-01-first-run/task.md"
    fresh = homework.lines(lessons, plans, date(2026, 9, 22), next_plan=plans[DAY])
    assert fresh[0].style is None


def test_homework_lines_not_issued_and_all_accepted(journal_root, course_root):
    from journal import ops
    ops.set_homework(DAY, "python-01-first-run", "bob", "accepted", root=journal_root, today=date(2026, 9, 22))
    ops.set_homework(DAY, "python-01-first-run", "alice", "submitted", root=journal_root, today=date(2026, 9, 22))
    ops.set_homework(DAY, "python-01-first-run", "alice", "accepted", root=journal_root, today=date(2026, 9, 22))
    roster = store.load_roster(journal_root)
    lessons = store.load_lessons(journal_root, roster)
    plans = stats.load_plans(course_root)
    next_plan = {"date": date(2026, 9, 27), "homework": {"items": ["homework/python-02-branching"]}}
    out = homework.lines(lessons, plans, TODAY, next_plan=next_plan)
    assert out[0].text.startswith("python-01-first-run · сдано 2/2 · принято 2/2") and out[0].style == "ok"
    assert out[1].text == "python-02-branching · не выдана" and out[1].style == "dim"
    assert out[1].open == "homework/python-02-branching/task.md"


def test_homework_lines_empty():
    out = homework.lines([], {}, TODAY)
    assert len(out) == 1 and out[0].text == "нет журнала" and out[0].style == "dim"
```

- [ ] **Step 2: Запустить — падает**

Run: `cd tools && .venv/bin/python -m pytest tests/test_info_journal_boxes.py -q`
Expected: `ImportError: cannot import name 'homework' from 'info'`

- [ ] **Step 3: Реализация**

`tools/info/students.py`:

```python
from __future__ import annotations

from info.common import TUI_CMD, Line
from journal.model import num

ROSTER_EXAMPLE = "tools/journal/roster.example.yml"


def lines(group, tui_cmd: str = TUI_CMD) -> list[Line]:
    """group — journal.stats.GroupStats или None, если нет students/roster.yml."""
    if group is None:
        return [Line("нет students/roster.yml — шаблон: tools/journal/roster.example.yml",
                     open=ROSTER_EXAMPLE, style="warn")]
    out = [Line(f"журнал · занятий {group.lessons_total}", open=f"run:{tui_cmd}")]
    for s in group.students:
        attended = s.present + s.late
        text = f"{s.name} · был {attended}/{s.lessons_total} · дз {s.hw_accepted}/{s.hw_issued} · {num(s.points_total)} б"
        out.append(Line(text, open=f"run:{tui_cmd}", style="warn" if s.tails else None))
    for day in group.missing_journals:
        out.append(Line(f"без журнала: {day.isoformat()}",
                        open=f"run:{tui_cmd} --date {day.isoformat()}", style="warn"))
    return out
```

`tools/info/homework.py`:

```python
from __future__ import annotations
from datetime import date

from info.common import Line, fmt_day, homework_task, hw_id_from_ref
from journal.store import hw_due_from_plan

SUBMITTED = ("submitted", "accepted", "rework")


def lines(lessons, plans: dict, today: date, next_plan: dict | None = None) -> list[Line]:
    """lessons — journal.model.LessonRecord; plans — {date: план}; next_plan — план ближайшего занятия."""
    out: list[Line] = []
    for rec in sorted(lessons, key=lambda r: r.date, reverse=True):
        plan = plans.get(rec.date)
        due = hw_due_from_plan(plan) if plan else None
        for hw_id, marks in rec.homework.items():
            total = len(marks)
            submitted = sum(1 for m in marks.values() if m.status in SUBMITTED)
            accepted = sum(1 for m in marks.values() if m.status == "accepted")
            text = f"{hw_id} · сдано {submitted}/{total} · принято {accepted}/{total}"
            if due:
                text += f" · до {fmt_day(due)}"
            if total and accepted == total:
                style = "ok"
            elif due and due < today:
                style = "warn"
            else:
                style = None
            out.append(Line(text, open=homework_task(hw_id), style=style))
    issued = {hw_id for rec in lessons for hw_id in rec.homework}
    for ref in ((next_plan or {}).get("homework") or {}).get("items") or []:
        hw_id = hw_id_from_ref(ref)
        if hw_id not in issued:
            out.append(Line(f"{hw_id} · не выдана", open=homework_task(hw_id), style="dim"))
    if not out:
        out.append(Line("нет журнала", style="dim"))
    return out
```

- [ ] **Step 4: Запустить — зелёные**

Run: `cd tools && .venv/bin/python -m pytest -q`
Expected: PASS. (Фикстура: alice `issued`, bob `submitted` → «сдано 1/2 · принято 0/2»; due 23.09 < 25.09 → `warn`; при today 22.09 — без стиля.)

- [ ] **Step 5: Commit**

```bash
git add tools/info/students.py tools/info/homework.py tools/tests/test_info_journal_boxes.py
git commit -m "feat(info): боксы «ученики» и «домашки» из журнала — хвосты, просрочка, не выданные"
```

---

### Task 4: бокс `готовность`

**Files:**
- Create: `tools/info/readiness.py`
- Test: `tools/tests/test_info_readiness.py`

**Interfaces:**
- Consumes: `common.module_dir/scenario_target/homework_task/hw_id_from_ref`; `make_module(repo_root, module_id, level=, minutes=, textbook=, shared=, student=)` из `tools/tests/test_build_course_map.py` (создаёт `module.yml`, `teacher/scenario.md` и файлы из `shared`/`student`); `module_schema.validate_module(module_dir: Path, repo_root: Path) -> list[str]` (в тестах подменяется).
- Produces: `readiness.ANATOMY` (кортеж `(метка, относительный путь)`), `readiness.lines(module_ids: list[str], repo_root, validate_fn) -> list[Line]`, `readiness.module_homework(module_dir) -> str|None` (`hw_id` из `module.yml: homework`).

- [ ] **Step 1: Провальные тесты** — `tools/tests/test_info_readiness.py`

```python
import yaml

from info import readiness
from test_build_course_map import make_module

FULL = dict(shared=("slides.html", "live-code.md"), student=("cheatsheet.html", "glossary.md"))


def _ok(_dir, _root):
    return []


def test_readiness_all_green(tmp_path):
    d = make_module(tmp_path, "python/m-01-first-run", **FULL)
    manifest = yaml.safe_load((d / "module.yml").read_text(encoding="utf-8"))
    manifest["homework"] = "homework/python-01-first-run"
    (d / "module.yml").write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    (tmp_path / "homework" / "python-01-first-run").mkdir(parents=True)
    (tmp_path / "homework" / "python-01-first-run" / "task.md").write_text("x", encoding="utf-8")
    out = readiness.lines(["python/m-01-first-run"], tmp_path, _ok)
    assert out[0].text == "python/m-01-first-run · scenario ✓ live-code ✓ slides ✓ cheatsheet ✓ glossary ✓ · validate ✓"
    assert out[0].style == "ok" and out[0].open == "tracks/python/m-01-first-run/teacher/scenario.md"
    assert out[1].text == "  домашка python-01-first-run: task.md ✓" and out[1].style == "ok"
    assert out[1].open == "homework/python-01-first-run/task.md"


def test_readiness_missing_file_is_warn(tmp_path):
    make_module(tmp_path, "python/m-01-first-run", shared=("slides.html",), student=("cheatsheet.html",))
    out = readiness.lines(["python/m-01-first-run"], tmp_path, _ok)
    assert "live-code ✗" in out[0].text and "glossary ✗" in out[0].text and out[0].style == "warn"
    assert len(out) == 1                                   # домашки в module.yml нет — строки нет


def test_readiness_validate_errors_are_err(tmp_path):
    make_module(tmp_path, "python/m-01-first-run", **FULL)
    out = readiness.lines(["python/m-01-first-run"], tmp_path, lambda d, r: ["битая ссылка requires", "ещё"])
    assert out[0].style == "err" and out[0].text.endswith("· validate ✗ битая ссылка requires")


def test_readiness_missing_module_and_homework(tmp_path):
    d = make_module(tmp_path, "python/m-01-first-run", **FULL)
    manifest = yaml.safe_load((d / "module.yml").read_text(encoding="utf-8"))
    manifest["homework"] = "homework/python-01-first-run"
    (d / "module.yml").write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    out = readiness.lines(["python/m-01-first-run", "python/m-09-nope"], tmp_path, _ok)
    assert out[1].text == "  домашка python-01-first-run: task.md ✗" and out[1].style == "warn"
    assert out[2].text == "python/m-09-nope · модуля нет" and out[2].style == "err"


def test_readiness_empty_playlist():
    out = readiness.lines([], "/nonexistent", _ok)
    assert len(out) == 1 and out[0].text == "нет плейлиста" and out[0].style == "dim"
```

- [ ] **Step 2: Запустить — падает**

Run: `cd tools && .venv/bin/python -m pytest tests/test_info_readiness.py -q`
Expected: `ImportError: cannot import name 'readiness' from 'info'`

- [ ] **Step 3: Реализация** — `tools/info/readiness.py`

```python
from __future__ import annotations
from pathlib import Path

import yaml

from info.common import Line, homework_task, hw_id_from_ref, module_dir, scenario_target

ANATOMY = (
    ("scenario", "teacher/scenario.md"),
    ("live-code", "shared/live-code.md"),
    ("slides", "shared/slides.html"),
    ("cheatsheet", "student/cheatsheet.html"),
    ("glossary", "student/glossary.md"),
)


def module_homework(directory: Path) -> str | None:
    manifest = directory / "module.yml"
    if not manifest.is_file():
        return None
    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    ref = data.get("homework") if isinstance(data, dict) else None
    return hw_id_from_ref(ref) if ref else None


def lines(module_ids: list[str], repo_root, validate_fn) -> list[Line]:
    """validate_fn(module_dir: Path, repo_root: Path) -> list[str] — ошибки module_schema.validate_module."""
    if not module_ids:
        return [Line("нет плейлиста", style="dim")]
    root = Path(repo_root)
    out: list[Line] = []
    for module_id in module_ids:
        directory = module_dir(module_id, root)
        if not directory.is_dir():
            out.append(Line(f"{module_id} · модуля нет", style="err"))
            continue
        marks = [(label, (directory / rel).is_file()) for label, rel in ANATOMY]
        errors = validate_fn(directory, root)
        parts = " ".join(f"{label} {'✓' if present else '✗'}" for label, present in marks)
        validate = "validate ✓" if not errors else f"validate ✗ {errors[0]}"
        style = "err" if errors else ("ok" if all(present for _, present in marks) else "warn")
        out.append(Line(f"{module_id} · {parts} · {validate}", open=scenario_target(module_id, root), style=style))
        hw_id = module_homework(directory)
        if hw_id:
            task = homework_task(hw_id)
            present = (root / task).is_file()
            out.append(Line(f"  домашка {hw_id}: task.md {'✓' if present else '✗'}",
                            open=task, style="ok" if present else "warn"))
    return out
```

- [ ] **Step 4: Запустить — зелёные**

Run: `cd tools && .venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/info/readiness.py tools/tests/test_info_readiness.py
git commit -m "feat(info): бокс «готовность» — файлы анатомии, validate_module, домашка плана"
```

---

### Task 5: `info/cli.py` — единый вход провайдеров

**Files:**
- Create: `tools/info/cli.py` (`chmod +x`)
- Test: `tools/tests/test_info_cli.py`

**Interfaces:**
- Consumes: `lesson/course/students/homework/readiness.lines` (Tasks 2–4), `common.next_session/emit/REPO_ROOT`; `build_course_map.load_modules(repo_root)`, `load_sessions(repo_root)` (кидают `ValueError` на битые файлы); `module_schema.validate_module`; `journal.store.students_root/load_roster/load_lessons`, `journal.stats.collect/load_plans`, `journal.model.JournalError`.
- Produces: `python3 tools/info/cli.py <box> [--today D] [--repo P] [--students R]`; `BOXES = ("lesson", "students", "homework", "readiness", "course")`; `build(box, repo_root, students_root, today) -> list[Line]`; `run(argv, today=None) -> int` (0 / 3; неизвестный бокс — argparse `SystemExit(2)`). Нет `roster.yml` → `students` получает `None`, `homework` — пустой список занятий. Самолокация `sys.path`, как у `journal/cli.py`.

- [ ] **Step 1: Провальные тесты** — `tools/tests/test_info_cli.py`

```python
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from conftest import TODAY
from info.cli import BOXES, run
from test_build_course_map import make_module

CLI = Path(__file__).resolve().parents[1] / "info" / "cli.py"


@pytest.fixture
def repo(course_root):
    """course_root + модуль плейлиста 20.09 + домашка → полный фикстурный репо."""
    make_module(course_root, "python/m-01-first-run",
                shared=("slides.html", "live-code.md"), student=("cheatsheet.html", "glossary.md"))
    (course_root / "homework" / "python-01-first-run").mkdir(parents=True)
    (course_root / "homework" / "python-01-first-run" / "task.md").write_text("x", encoding="utf-8")
    return course_root


def _run(box, repo, students, capsys, today=date(2026, 9, 19)):
    code = run([box, "--repo", str(repo), "--students", str(students), "--today", today.isoformat()])
    out = capsys.readouterr()
    return code, out


@pytest.mark.parametrize("box", BOXES)
def test_every_box_emits_lines(box, repo, journal_root, capsys):
    code, out = _run(box, repo, journal_root, capsys)
    assert code == 0, out.err
    data = json.loads(out.out)
    assert data["lines"] and all({"text", "open", "style"} <= set(l) for l in data["lines"])


def test_lesson_box_points_to_plan(repo, journal_root, capsys):
    _, out = _run("lesson", repo, journal_root, capsys)
    lines = json.loads(out.out)["lines"]
    assert lines[0]["open"] == "playground/2026-09-20/session.yml" and "завтра" in lines[0]["text"]
    assert any(l["open"] == "tracks/python/m-01-first-run/teacher/scenario.md" for l in lines)


def test_readiness_box_uses_real_validate(repo, journal_root, capsys):
    _, out = _run("readiness", repo, journal_root, capsys)
    lines = json.loads(out.out)["lines"]
    assert lines[0]["text"].startswith("python/m-01-first-run · scenario ✓") and lines[0]["style"] == "ok"


def test_students_and_homework_without_roster(repo, tmp_path, capsys):
    empty = tmp_path / "no-students"
    empty.mkdir()
    _, out = _run("students", repo, empty, capsys)
    assert json.loads(out.out)["lines"][0]["style"] == "warn"
    _, out = _run("homework", repo, empty, capsys)
    lines = json.loads(out.out)["lines"]
    assert lines[0]["text"] == "python-01-first-run · не выдана"


def test_students_box_uses_journal(repo, journal_root, capsys):
    _, out = _run("students", repo, journal_root, capsys, today=TODAY)
    texts = [l["text"] for l in json.loads(out.out)["lines"]]
    assert texts[0] == "журнал · занятий 1" and texts[1].startswith("Алиса")


def test_unknown_box_is_2_and_broken_plan_is_3(repo, journal_root, capsys):
    with pytest.raises(SystemExit) as info:
        run(["weather", "--repo", str(repo)])
    assert info.value.code == 2
    (repo / "playground" / "2026-09-20" / "session.yml").write_text("theme: [\n", encoding="utf-8")
    code, out = _run("lesson", repo, journal_root, capsys)
    assert code == 3 and out.err.startswith("info:")   # YAMLError из load_sessions без имени файла — известное ограничение


def test_script_runs_from_repo_root(repo, journal_root):
    proc = subprocess.run([sys.executable, str(CLI), "course", "--repo", str(repo), "--students", str(journal_root)],
                          capture_output=True, text=True, cwd=str(repo))
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["lines"][0]["text"].startswith("занятий проведено")
```

- [ ] **Step 2: Запустить — падает**

Run: `cd tools && .venv/bin/python -m pytest tests/test_info_cli.py -q`
Expected: `ModuleNotFoundError: No module named 'info.cli'`

- [ ] **Step 3: Реализация** — `tools/info/cli.py`

```python
#!/usr/bin/env python3
"""info — провайдеры боксов info-панели. Печатает JSON lines по контракту command."""
from __future__ import annotations
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tools/

import yaml  # noqa: E402

from build_course_map import load_modules, load_sessions  # noqa: E402
from info import common, course, homework, lesson, readiness, students  # noqa: E402
from info.common import Line, emit  # noqa: E402
from journal import stats as journal_stats  # noqa: E402
from journal import store as journal_store  # noqa: E402
from journal.model import JournalError  # noqa: E402
from module_schema import validate_module  # noqa: E402

BOXES = ("lesson", "students", "homework", "readiness", "course")


def _playlist_ids(session: dict | None) -> list[str]:
    if not session:
        return []
    return [str(item["module"]) for item in session.get("playlist") or []
            if isinstance(item, dict) and item.get("module")]


def build(box: str, repo_root, students_root, today: date) -> list[Line]:
    repo_root = Path(repo_root)
    if box == "lesson":
        session, stale = common.next_session(load_sessions(repo_root), today)
        return lesson.lines(session, stale, today, repo_root)
    if box == "course":
        return course.lines(load_modules(repo_root), load_sessions(repo_root), today)
    if box == "readiness":
        session, _ = common.next_session(load_sessions(repo_root), today)
        return readiness.lines(_playlist_ids(session), repo_root, validate_module)
    roster_path = journal_store.students_root(students_root) / "roster.yml"
    if box == "students":
        group = journal_stats.collect(students_root, repo_root, today) if roster_path.exists() else None
        return students.lines(group)
    if box == "homework":
        lessons = []
        if roster_path.exists():
            roster = journal_store.load_roster(students_root)
            lessons = journal_store.load_lessons(students_root, roster)
        session, _ = common.next_session(load_sessions(repo_root), today)
        return homework.lines(lessons, journal_stats.load_plans(repo_root), today, session)
    raise ValueError(f"неизвестный бокс {box!r}")


def run(argv, today: date | None = None) -> int:
    ap = argparse.ArgumentParser(prog="info")
    ap.add_argument("box", choices=BOXES)
    ap.add_argument("--today", type=date.fromisoformat)
    ap.add_argument("--repo", help="корень репо (по умолчанию — этот)")
    ap.add_argument("--students", help="каталог students/ (по умолчанию <repo>/students или $JUNIOR_IT_STUDENTS)")
    args = ap.parse_args(argv)
    day = args.today or today or date.today()
    try:
        emit(build(args.box, args.repo or common.REPO_ROOT, args.students, day))
    except (JournalError, ValueError, yaml.YAMLError) as exc:
        print(f"info: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
```

Затем `chmod +x tools/info/cli.py`.

- [ ] **Step 4: Запустить — зелёные; живой прогон на репо**

Run: `cd tools && .venv/bin/python -m pytest -q && cd .. && for b in lesson students homework readiness course; do tools/.venv/bin/python tools/info/cli.py $b | head -c 300; echo; done`
Expected: PASS; каждый бокс печатает JSON с непустым `lines` (реальные имена учеников — не копировать в отчёт, только счётчики).

- [ ] **Step 5: Commit**

```bash
git add tools/info/cli.py tools/tests/test_info_cli.py
git commit -m "feat(info): единый CLI провайдеров — lesson/students/homework/readiness/course, коды 0/2/3"
```

---

### Task 6: манифест `.zellij/info.yml`, его тест, скриншот вкладки

**Files:**
- Create: `.zellij/info.yml`
- Test: `tools/tests/test_info_manifest.py`

**Interfaces:**
- Consumes: движок `cockpit.info.manifest.load_info_manifest(path) -> InfoManifest` (`.warnings`, `.placed()`), деплойнутый в `~/.local/lib/terminal-commander/cockpit` (нужен только PyYAML, Textual не импортируется); `tc-info` для скриншота.

- [ ] **Step 1: Провальный тест** — `tools/tests/test_info_manifest.py`

```python
import sys
from pathlib import Path

import pytest

ENGINE = Path.home() / ".local" / "lib" / "terminal-commander" / "cockpit"
MANIFEST = Path(__file__).resolve().parents[2] / ".zellij" / "info.yml"


def test_info_manifest_loads_in_engine():
    if not (ENGINE / "cockpit" / "info" / "manifest.py").exists():
        pytest.skip("движок info-панели не задеплоен")
    sys.path.insert(0, str(ENGINE))
    from cockpit.info.manifest import load_info_manifest
    manifest = load_info_manifest(MANIFEST)
    assert manifest.warnings == []
    assert [b.id for b in manifest.placed()] == ["lesson", "students", "clock", "homework", "readiness", "course", "git"]
    for box in manifest.placed():
        if box.type == "command":
            assert box.run.startswith("tools/.venv/bin/python tools/info/cli.py ")
```

- [ ] **Step 2: Запустить — падает**

Run: `cd tools && .venv/bin/python -m pytest tests/test_info_manifest.py -q`
Expected: FAIL (`FileNotFoundError: .zellij/info.yml`).

- [ ] **Step 3: Манифест** — `.zellij/info.yml`

```yaml
# Вкладка info (tc-info): боксы курса. Провайдеры — tools/info/cli.py <box>.
# Сетка — ряды с весами; clock и git даёт движок.
version: 1
layout:
  - [{box: lesson, weight: 2}, {box: students, weight: 2}, {box: clock, weight: 1}]
  - [{box: homework, weight: 2}, {box: readiness, weight: 3}, {box: course, weight: 1}, {box: git, weight: 1}]
boxes:
  - id: clock
    type: clock
  - id: git
    type: git
    title: "хвосты"
  - id: lesson
    type: command
    title: "занятие"
    run: "tools/.venv/bin/python tools/info/cli.py lesson"
    interval: 300
  - id: students
    type: command
    title: "ученики"
    run: "tools/.venv/bin/python tools/info/cli.py students"
    interval: 120
  - id: homework
    type: command
    title: "домашки"
    run: "tools/.venv/bin/python tools/info/cli.py homework"
    interval: 300
  - id: readiness
    type: command
    title: "готовность"
    run: "tools/.venv/bin/python tools/info/cli.py readiness"
    interval: 120
  - id: course
    type: command
    title: "курс"
    run: "tools/.venv/bin/python tools/info/cli.py course"
    interval: 600
```

- [ ] **Step 4: Тесты и dry-run обёртки**

Run: `cd tools && .venv/bin/python -m pytest -q && cd .. && tc-info --dry-run`
Expected: PASS; `launch` (манифест найден).

- [ ] **Step 5: Скриншот вкладки на реальном репо** (только scratchpad — на экране реальные имена)

Скрипт `info_shot.py` в scratchpad, запускать из `~/.local/lib/terminal-commander/cockpit` его venv:

```python
import asyncio, sys
from pathlib import Path
from cockpit.info.manifest import load_info_manifest
from cockpit.info.app import InfoPanel

root = Path(sys.argv[1]); out = sys.argv[2]

async def main():
    app = InfoPanel(load_info_manifest(root / ".zellij" / "info.yml"), root.name, str(root))
    async with app.run_test(size=(208, 44)) as pilot:
        app._tick()
        await app.workers.wait_for_complete()
        await pilot.pause()
        app.save_screenshot(out)

asyncio.run(main())
```

```bash
cd ~/.local/lib/terminal-commander/cockpit && PYTHONPATH=. .venv/bin/python <scratchpad>/info_shot.py ~/Projects/Junior_IT <scratchpad>/info-junior.svg
qlmanage -t -s 2000 -o <scratchpad> <scratchpad>/info-junior.svg
```

Открыть PNG: два ряда, семь боксов, заголовки `занятие · ученики · clock / домашки · готовность · курс · хвосты`, ни одного `⚠` в заголовках, строки не обрезаны. Бокс с `⚠` — читать хвост stderr в нём, чинить провайдер, переснимать. PNG в репо и в workspace плана не класть.

- [ ] **Step 6: Commit**

```bash
git add .zellij/info.yml tools/tests/test_info_manifest.py
git commit -m "feat(info): манифест вкладки info — семь боксов курса"
```

Итог в отчёте: коммиты, счёт тестов, вывод `tc-info --dry-run`, путь к PNG и что на нём (без имён детей). `git push` — только по слову Димаса.
