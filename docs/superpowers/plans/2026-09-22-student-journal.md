# Журнал классного руководителя — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Приватный журнал учеников в `students/` (ростер, посещаемость, домашки, баллы, заметки), ядро операций + CLI для автоматики, TUI для ввода после занятия, статистика и хвосты, бэкап на NAS, и одна нейтральная добавка в движок info-панели (`run:`-цель).

**Architecture:** Пакет `tools/journal/` в репо курса: чистое ядро (`model.py` — схема и валидация, `store.py` — YAML-хранилище и план занятия, `ops.py` — идемпотентные операции с тарифными начислениями, `stats.py` — статистика на чтении) и два потребителя (`cli.py` для автоматики и агента, `tui.py` на Textual для тебя). Хранилище — `students/roster.yml` + `students/journal/<дата>.yml` + `students/points.yml`; план занятия читается из `playground/<дата>/session.yml`. Бэкап — bash + launchd по образцу zoom-пайплайна. Движок terminal-commander получает цель `run:<команда>` (плавающая панель Zellij).

**Tech Stack:** Python 3.12 (`tools/.venv`), PyYAML 6, Textual ≥ 8 (новая зависимость), pytest 9 + pytest-asyncio (новая), bash/rsync/launchd; в terminal-commander — тот же пакет `cockpit` (Textual 8.2.8, uv).

**Spec:** `docs/superpowers/specs/2026-09-22-student-journal-design.md` — исполнитель читает обе.

## Global Constraints

- **Приватность:** `students/` в `.gitignore`; тесты работают только в `tmp_path` (параметр `root=` или переменная `JUNIOR_IT_STUDENTS`), никогда в реальном `students/`. В коде, тестах, коммитах и плане — только вымышленные `alice`/`bob`/`carol`, никаких имён детей.
- **Рабочее дерево Junior_IT содержит чужие незакоммиченные правки** (`homework/python-01-first-run/task.md`, `playground/2026-09-20/session.yml`, `provisioning/setup-windows.*`, `tracks/python/m-01-first-run/…`). Стейджить только свои файлы, поимённо; `git add -A`/`git add .` запрещены.
- Тесты: `cd tools && .venv/bin/python -m pytest -q` (сейчас все зелёные; `pytest.ini`: `testpaths = tests`, `pythonpath = .`). Новые тесты — `tools/tests/test_journal_*.py`; фикстуры — `tools/tests/conftest.py` (создаётся в Task 2; имена `journal_root`, `course_root`).
- Все операции идемпотентны; запись файла занятия — атомарная (temp + `os.replace`), порядок ключей фиксирован: `date, attendance, homework, points, notes`.
- Статусы: посещаемость `present|late|absent|recording`; домашка `issued→submitted→accepted|rework`, `rework→submitted`, прочее — `TransitionError`; источник `teacher|zoom|telegram`; ученик `active|paused|left`.
- Тариф по умолчанию: `presence 2, late 1, homework_accepted 3, homework_after_rework 2, activity_max 3, quiz_per_correct 0.25`.
- Хвосты: домашка в `issued|rework` при `homework.due < today`; `submitted` c `at` старше 3 дней; занятие с планом (`session.yml`, дата < today) без файла журнала.
- Коды CLI: 0 ок; 2 — `TransitionError`/аргументы; 3 — `JournalError` (битые данные).
- Цвета в TUI — роли (`green/yellow/red/dim`, `$error`), без хексов. Тост на каждую клавишу.
- Коммиты: conventional, русское описание, без emoji, футер:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01XFthZUabadDPVaHxjhrY4Q
  ```
  `git commit` — да, `git push` — нет. Junior_IT: ветка `feat/student-journal` от `main` (2f250a0). terminal-commander (Task 8): ветка `feat/info-run-target` от `main` (ecf65be).

## File Structure

Junior_IT (пути от корня репо):
- `tools/journal/__init__.py` — CREATE (T1): docstring.
- `tools/journal/model.py` — CREATE (T1): константы, dataclasses, `JournalError`/`TransitionError`, `parse_roster`, `parse_tariff`, `parse_lesson`, `lesson_to_dict`, `num`.
- `tools/journal/store.py` — CREATE (T2): `students_root`, `load_roster`, `load_tariff`, `lesson_path`, `load_lesson`, `load_lessons`, `save_lesson`, `load_plan`, `plan_dates`, `hw_ids_from_plan`, `hw_due_from_plan`.
- `tools/tests/conftest.py` — CREATE (T2): фикстуры `journal_root`, `course_root`, константы `TODAY`, `DAY`.
- `tools/journal/ops.py` — CREATE (T3): `mark_attendance`, `issue_homework`, `set_homework`, `add_points`, `set_note`, константы причин.
- `tools/journal/stats.py` — CREATE (T4): `StudentStats`, `GroupStats`, `student_stats`, `group_stats`, `collect`, `to_json_dict`.
- `tools/journal/cli.py` — CREATE (T5); `tools/group_status.py` — MODIFY (T5).
- `tools/journal/tui.py` — CREATE (T6); `tools/requirements.txt`, `tools/pytest.ini` — MODIFY (T6).
- `tools/students_backup.sh`, `provisioning/students-backup/{com.juniorit.students-backup.plist,setup.md}` — CREATE (T7); `.zellij/cockpit.yml` — MODIFY (T7).
- Тесты: `tools/tests/test_journal_model.py` (T1), `test_journal_store.py` (T2), `test_journal_ops.py` (T3), `test_journal_stats.py` (T4), `test_journal_cli.py` (T5), `test_journal_tui.py` (T6), `test_students_backup.py` (T7).

terminal-commander:
- `home/dot_local/lib/terminal-commander/cockpit/cockpit/info/providers.py` — MODIFY (T8): `open_cmd` понимает `run:`.
- `home/dot_local/lib/terminal-commander/cockpit/tests/test_info_providers.py` — MODIFY (T8).
- `docs/superpowers/specs/2026-09-21-info-panel-design.md` — MODIFY (T8): одна строка про `run:`.

---

### Task 1: `journal/model.py` — схема, валидация, сериализация

**Files:**
- Create: `tools/journal/__init__.py`, `tools/journal/model.py`
- Test: `tools/tests/test_journal_model.py`

**Interfaces:**
- Produces: `ATTENDANCE`, `HW_STATUSES`, `HW_TRANSITIONS: dict[str, set[str]]`, `SOURCES`, `STUDENT_STATUSES`; `class JournalError(Exception)` с атрибутом `path: str|None`; `class TransitionError(JournalError)`; dataclasses `Student(id, name, status="active", full_name=None, nick=None, zoom_names=[], platform=None, contacts={}, parent={}, joined: date|None=None, notes=None)`, `HomeworkMark(status="issued", at: date|None=None, note=None, reworked=False)`, `PointEntry(who, amount: float, reason, by="teacher")`, `LessonRecord(date, attendance={}, homework={}, points=[], notes={})`, `Tariff(presence=2, late=1, homework_accepted=3, homework_after_rework=2, activity_max=3, quiz_per_correct=0.25)`; функции `parse_roster(data, path="roster.yml") -> list[Student]`, `parse_tariff(data) -> Tariff`, `parse_lesson(data, file_date: date, roster_ids: set[str], path="lesson.yml") -> LessonRecord`, `lesson_to_dict(rec) -> dict` (фиксированный порядок ключей), `num(x: float) -> int|float` (2.0 → 2).

- [ ] **Step 1: Провальные тесты** — создать `tools/tests/test_journal_model.py`

```python
from datetime import date

import pytest

from journal.model import (
    HomeworkMark, JournalError, LessonRecord, PointEntry, Tariff,
    lesson_to_dict, num, parse_lesson, parse_roster, parse_tariff,
)

ROSTER = {"students": [
    {"id": "alice", "name": "Алиса", "status": "active", "platform": "mac",
     "joined": "2026-09-09", "zoom_names": ["Алиса", "Alice"], "contacts": {"tg": "@a"}},
    {"id": "bob", "name": "Боб"},
]}
DAY = date(2026, 9, 20)


def test_parse_roster_ok():
    students = parse_roster(ROSTER)
    assert [s.id for s in students] == ["alice", "bob"]
    assert students[0].joined == date(2026, 9, 9) and students[0].zoom_names == ["Алиса", "Alice"]
    assert students[1].status == "active" and students[1].contacts == {}


@pytest.mark.parametrize("bad, needle", [
    ({"students": [{"id": "Bad Id", "name": "x"}]}, "id"),
    ({"students": [{"id": "a", "name": "x"}, {"id": "a", "name": "y"}]}, "дубль"),
    ({"students": [{"id": "a"}]}, "name"),
    ({"students": [{"id": "a", "name": "x", "status": "gone"}]}, "status"),
    ({"students": [{"id": "a", "name": "x", "joined": "вчера"}]}, "дата"),
    ({"students": "nope"}, "students"),
    ({}, "students"),
])
def test_parse_roster_errors(bad, needle):
    with pytest.raises(JournalError, match=needle):
        parse_roster(bad, path="r.yml")


def test_parse_tariff_defaults_and_override():
    assert parse_tariff(None) == Tariff()
    assert parse_tariff({"presence": 5}).presence == 5.0
    with pytest.raises(JournalError, match="неизвестные"):
        parse_tariff({"bonus": 1})


LESSON = {
    "date": DAY,
    "attendance": {"alice": "present", "bob": "late"},
    "homework": {"python-01": {"alice": {"status": "accepted", "at": date(2026, 9, 22)},
                               "bob": {"status": "rework", "note": "без traceback", "reworked": True}}},
    "points": [{"who": "alice", "amount": 2, "reason": "присутствие", "by": "teacher"},
               {"who": "alice", "amount": 0.5, "reason": "зачёт", "by": "telegram"}],
    "notes": {"bob": "опоздал"},
}


def test_parse_lesson_ok():
    rec = parse_lesson(LESSON, DAY, {"alice", "bob"})
    assert rec.attendance == {"alice": "present", "bob": "late"}
    assert rec.homework["python-01"]["alice"] == HomeworkMark("accepted", date(2026, 9, 22))
    assert rec.homework["python-01"]["bob"].reworked is True
    assert rec.points[1] == PointEntry("alice", 0.5, "зачёт", "telegram")
    assert rec.notes == {"bob": "опоздал"}


@pytest.mark.parametrize("patch, needle", [
    ({"date": date(2026, 9, 21)}, "не совпадает"),
    ({"attendance": {"zed": "present"}}, "zed"),
    ({"attendance": {"alice": "here"}}, "статус"),
    ({"homework": {"h": {"alice": {"status": "done"}}}}, "статус"),
    ({"points": [{"who": "alice"}]}, "who/amount"),
    ({"points": [{"who": "alice", "amount": 1, "by": "mail"}]}, "источник"),
    ({"notes": {"zed": "x"}}, "zed"),
])
def test_parse_lesson_errors(patch, needle):
    with pytest.raises(JournalError, match=needle):
        parse_lesson({**LESSON, **patch}, DAY, {"alice", "bob"}, path="l.yml")


def test_lesson_round_trip_and_key_order():
    rec = parse_lesson(LESSON, DAY, {"alice", "bob"})
    data = lesson_to_dict(rec)
    assert list(data) == ["date", "attendance", "homework", "points", "notes"]
    assert data["homework"]["python-01"]["alice"] == {"status": "accepted", "at": date(2026, 9, 22)}
    assert data["points"][0]["amount"] == 2 and isinstance(data["points"][0]["amount"], int)
    assert parse_lesson(data, DAY, {"alice", "bob"}) == rec


def test_empty_lesson_serialises_with_all_sections():
    assert lesson_to_dict(LessonRecord(date=DAY)) == {
        "date": DAY, "attendance": {}, "homework": {}, "points": [], "notes": {}}


def test_num():
    assert num(2.0) == 2 and isinstance(num(2.0), int) and num(0.5) == 0.5
```

- [ ] **Step 2: Запустить — падает на импорте**

Run: `cd tools && .venv/bin/python -m pytest tests/test_journal_model.py -q`
Expected: `ModuleNotFoundError: No module named 'journal'`

- [ ] **Step 3: Реализация**

`tools/journal/__init__.py`:

```python
"""Журнал классного руководителя: схема, хранилище, операции, статистика, CLI и TUI."""
```

`tools/journal/model.py`:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
import re

ATTENDANCE = ("present", "late", "absent", "recording")
HW_STATUSES = ("issued", "submitted", "accepted", "rework")
HW_TRANSITIONS = {
    "issued": {"submitted"},
    "submitted": {"accepted", "rework"},
    "rework": {"submitted"},
    "accepted": set(),
}
SOURCES = ("teacher", "zoom", "telegram")
STUDENT_STATUSES = ("active", "paused", "left")
_ID_RE = re.compile(r"^[a-z0-9-]+$")


class JournalError(Exception):
    """Битые данные: сообщение называет файл и id."""

    def __init__(self, message: str, path=None):
        super().__init__(message)
        self.path = str(path) if path else None


class TransitionError(JournalError):
    """Недопустимый переход статуса или неверный аргумент операции."""


@dataclass
class Student:
    id: str
    name: str
    status: str = "active"
    full_name: str | None = None
    nick: str | None = None
    zoom_names: list[str] = field(default_factory=list)
    platform: str | None = None
    contacts: dict = field(default_factory=dict)
    parent: dict = field(default_factory=dict)
    joined: date | None = None
    notes: str | None = None


@dataclass
class HomeworkMark:
    status: str = "issued"
    at: date | None = None
    note: str | None = None
    reworked: bool = False


@dataclass
class PointEntry:
    who: str
    amount: float
    reason: str
    by: str = "teacher"


@dataclass
class LessonRecord:
    date: date
    attendance: dict[str, str] = field(default_factory=dict)
    homework: dict[str, dict[str, HomeworkMark]] = field(default_factory=dict)
    points: list[PointEntry] = field(default_factory=list)
    notes: dict[str, str] = field(default_factory=dict)


@dataclass
class Tariff:
    presence: float = 2
    late: float = 1
    homework_accepted: float = 3
    homework_after_rework: float = 2
    activity_max: float = 3
    quiz_per_correct: float = 0.25


def num(x: float):
    """2.0 → 2, 0.5 → 0.5 — чтобы YAML и экран не пестрили «.0»."""
    x = float(x)
    return int(x) if x.is_integer() else x


def _as_date(value, what: str, path) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise JournalError(f"{path}: {what} — не дата: {value!r}", path) from None


def parse_roster(data, path="roster.yml") -> list[Student]:
    if not isinstance(data, dict) or not isinstance(data.get("students"), list):
        raise JournalError(f"{path}: нужен ключ students со списком", path)
    seen: set[str] = set()
    students: list[Student] = []
    for raw in data["students"]:
        if not isinstance(raw, dict):
            raise JournalError(f"{path}: ученик должен быть mapping", path)
        sid = str(raw.get("id", ""))
        if not _ID_RE.match(sid):
            raise JournalError(f"{path}: недопустимый id {sid!r} (нужно [a-z0-9-])", path)
        if sid in seen:
            raise JournalError(f"{path}: дубль id {sid}", path)
        seen.add(sid)
        if not raw.get("name"):
            raise JournalError(f"{path}: у {sid} нет name", path)
        status = raw.get("status", "active")
        if status not in STUDENT_STATUSES:
            raise JournalError(f"{path}: у {sid} неизвестный status {status!r}", path)
        students.append(Student(
            id=sid, name=str(raw["name"]), status=status,
            full_name=raw.get("full_name"), nick=raw.get("nick"),
            zoom_names=[str(x) for x in (raw.get("zoom_names") or [])],
            platform=raw.get("platform"),
            contacts=dict(raw.get("contacts") or {}), parent=dict(raw.get("parent") or {}),
            joined=_as_date(raw["joined"], f"joined у {sid}", path) if raw.get("joined") else None,
            notes=raw.get("notes"),
        ))
    return students


def parse_tariff(data) -> Tariff:
    if not data:
        return Tariff()
    if not isinstance(data, dict):
        raise JournalError("points.yml: нужен mapping", "points.yml")
    unknown = [k for k in data if k not in Tariff.__dataclass_fields__]
    if unknown:
        raise JournalError(f"points.yml: неизвестные ключи {unknown}", "points.yml")
    return Tariff(**{k: float(v) for k, v in data.items()})


def parse_lesson(data, file_date: date, roster_ids: set[str], path="lesson.yml") -> LessonRecord:
    if not isinstance(data, dict):
        raise JournalError(f"{path}: нужен mapping", path)
    rec_date = _as_date(data.get("date"), "date", path)
    if rec_date != file_date:
        raise JournalError(f"{path}: date {rec_date} не совпадает с именем файла", path)

    def known(sid, where):
        if sid not in roster_ids:
            raise JournalError(f"{path}: {where} — ученика {sid!r} нет в ростере", path)

    attendance: dict[str, str] = {}
    for sid, status in (data.get("attendance") or {}).items():
        known(sid, "attendance")
        if status not in ATTENDANCE:
            raise JournalError(f"{path}: attendance {sid}: неизвестный статус {status!r}", path)
        attendance[sid] = status
    homework: dict[str, dict[str, HomeworkMark]] = {}
    for hw_id, marks in (data.get("homework") or {}).items():
        homework[hw_id] = {}
        for sid, raw in (marks or {}).items():
            known(sid, f"homework {hw_id}")
            raw = raw or {}
            status = raw.get("status", "issued")
            if status not in HW_STATUSES:
                raise JournalError(f"{path}: homework {hw_id} {sid}: неизвестный статус {status!r}", path)
            homework[hw_id][sid] = HomeworkMark(
                status=status,
                at=_as_date(raw["at"], f"at у {hw_id}/{sid}", path) if raw.get("at") else None,
                note=raw.get("note"), reworked=bool(raw.get("reworked", False)))
    points: list[PointEntry] = []
    for raw in data.get("points") or []:
        if not isinstance(raw, dict) or "who" not in raw or "amount" not in raw:
            raise JournalError(f"{path}: запись points без who/amount", path)
        known(raw["who"], "points")
        by = raw.get("by", "teacher")
        if by not in SOURCES:
            raise JournalError(f"{path}: points {raw['who']}: неизвестный источник {by!r}", path)
        points.append(PointEntry(who=raw["who"], amount=float(raw["amount"]),
                                 reason=str(raw.get("reason", "")), by=by))
    notes: dict[str, str] = {}
    for sid, text in (data.get("notes") or {}).items():
        known(sid, "notes")
        notes[sid] = str(text)
    return LessonRecord(date=rec_date, attendance=attendance, homework=homework,
                        points=points, notes=notes)


def lesson_to_dict(rec: LessonRecord) -> dict:
    """Фиксированный порядок ключей и минимальные записи — round-trip без диффа."""
    homework: dict = {}
    for hw_id, marks in rec.homework.items():
        homework[hw_id] = {}
        for sid, m in marks.items():
            entry: dict = {"status": m.status}
            if m.at:
                entry["at"] = m.at
            if m.note:
                entry["note"] = m.note
            if m.reworked:
                entry["reworked"] = True
            homework[hw_id][sid] = entry
    return {
        "date": rec.date,
        "attendance": dict(rec.attendance),
        "homework": homework,
        "points": [{"who": p.who, "amount": num(p.amount), "reason": p.reason, "by": p.by}
                   for p in rec.points],
        "notes": dict(rec.notes),
    }
```

- [ ] **Step 4: Запустить — зелёные, старые тесты не тронуты**

Run: `cd tools && .venv/bin/python -m pytest -q`
Expected: все PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/journal/__init__.py tools/journal/model.py tools/tests/test_journal_model.py
git commit -m "feat(journal): схема журнала — ростер, занятие, тариф, валидация и сериализация"
```

---

### Task 2: `journal/store.py` — YAML-хранилище и план занятия; фикстуры

**Files:**
- Create: `tools/journal/store.py`, `tools/tests/conftest.py`
- Test: `tools/tests/test_journal_store.py`

**Interfaces:**
- Consumes: всё из `journal.model` (Task 1).
- Produces: `REPO_ROOT: Path` (корень репо = `Path(__file__).resolve().parents[2]`); `students_root(root=None) -> Path` (аргумент → `$JUNIOR_IT_STUDENTS` → `REPO_ROOT/students`); `load_roster(root=None) -> list[Student]` (нет файла → `JournalError`); `load_tariff(root=None) -> Tariff` (нет файла → дефолт); `lesson_path(day, root=None) -> Path`; `load_lesson(day, root=None, roster=None) -> LessonRecord|None`; `load_lessons(root=None, roster=None) -> list[LessonRecord]` (по дате); `save_lesson(rec, root=None) -> Path` (атомарно); `load_plan(day, repo_root=None) -> dict|None`; `plan_dates(repo_root=None) -> list[date]`; `hw_ids_from_plan(plan) -> list[str]` (`homework/python-01` → `python-01`); `hw_due_from_plan(plan) -> date|None`.
- Фикстуры (conftest): `journal_root` — `tmp_path/students` с ростером `alice`(active, mac, joined 2026-09-09)/`bob`(active, win)/`carol`(left) и занятием `2026-09-20` (alice present + 2 «присутствие», bob late + 1 «опоздание»; домашка `python-01-first-run`: alice issued at 09-20, bob submitted at 09-21); `course_root` — `tmp_path/repo` с планами `playground/2026-09-20/session.yml` (theme «Первый Python», homework due 2026-09-23, items `["homework/python-01-first-run"]`) и `playground/2026-09-13/session.yml` (theme «Терминал», без домашки). Константы `TODAY = date(2026, 9, 25)`, `DAY = date(2026, 9, 20)`.

- [ ] **Step 1: Фикстуры и провальные тесты**

`tools/tests/conftest.py`:

```python
from datetime import date

import pytest
import yaml

TODAY = date(2026, 9, 25)
DAY = date(2026, 9, 20)


def _dump(path, data):
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


@pytest.fixture
def journal_root(tmp_path):
    """students/ с вымышленной группой alice/bob/carol и одним занятием."""
    root = tmp_path / "students"
    (root / "journal").mkdir(parents=True)
    _dump(root / "roster.yml", {"students": [
        {"id": "alice", "name": "Алиса", "status": "active", "platform": "mac", "joined": "2026-09-09"},
        {"id": "bob", "name": "Боб", "status": "active", "platform": "win"},
        {"id": "carol", "name": "Кэрол", "status": "left"},
    ]})
    _dump(root / "journal" / "2026-09-20.yml", {
        "date": DAY,
        "attendance": {"alice": "present", "bob": "late"},
        "homework": {"python-01-first-run": {
            "alice": {"status": "issued", "at": DAY},
            "bob": {"status": "submitted", "at": date(2026, 9, 21)}}},
        "points": [{"who": "alice", "amount": 2, "reason": "присутствие", "by": "teacher"},
                   {"who": "bob", "amount": 1, "reason": "опоздание", "by": "teacher"}],
        "notes": {},
    })
    return root


@pytest.fixture
def course_root(tmp_path):
    """Корень репо с двумя планами занятий в playground/."""
    root = tmp_path / "repo"
    d = root / "playground" / "2026-09-20"
    d.mkdir(parents=True)
    _dump(d / "session.yml", {"date": DAY, "time": "20:00", "theme": "Первый Python",
                              "homework": {"due": date(2026, 9, 23), "items": ["homework/python-01-first-run"]}})
    d = root / "playground" / "2026-09-13"
    d.mkdir(parents=True)
    _dump(d / "session.yml", {"date": date(2026, 9, 13), "theme": "Терминал"})
    return root
```

`tools/tests/test_journal_store.py`:

```python
from datetime import date

import pytest

from conftest import DAY
from journal import store
from journal.model import JournalError, LessonRecord, PointEntry, Tariff


def test_students_root_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("JUNIOR_IT_STUDENTS", str(tmp_path / "env"))
    assert store.students_root(tmp_path / "arg") == tmp_path / "arg"
    assert store.students_root() == tmp_path / "env"
    monkeypatch.delenv("JUNIOR_IT_STUDENTS")
    assert store.students_root() == store.REPO_ROOT / "students"


def test_load_roster_and_missing(journal_root, tmp_path):
    assert [s.id for s in store.load_roster(journal_root)] == ["alice", "bob", "carol"]
    with pytest.raises(JournalError, match="roster.yml"):
        store.load_roster(tmp_path / "empty")


def test_load_tariff_default_and_file(journal_root):
    assert store.load_tariff(journal_root) == Tariff()
    (journal_root / "points.yml").write_text("presence: 4\n", encoding="utf-8")
    assert store.load_tariff(journal_root).presence == 4.0


def test_load_lesson_and_lessons(journal_root):
    rec = store.load_lesson(DAY, journal_root)
    assert rec.attendance["bob"] == "late"
    assert store.load_lesson(date(2026, 9, 21), journal_root) is None
    assert [r.date for r in store.load_lessons(journal_root)] == [DAY]


def test_broken_yaml_names_file(journal_root):
    bad = journal_root / "journal" / "2026-09-22.yml"
    bad.write_text("date: 2026-09-22\nattendance: [\n", encoding="utf-8")
    with pytest.raises(JournalError, match="2026-09-22.yml") as info:
        store.load_lessons(journal_root)
    assert info.value.path == str(bad)


def test_bad_filename_is_error(journal_root):
    (journal_root / "journal" / "notes.yml").write_text("date: 2026-09-20\n", encoding="utf-8")
    with pytest.raises(JournalError, match="не дата"):
        store.load_lessons(journal_root)


def test_save_lesson_round_trip_no_diff(journal_root):
    path = store.lesson_path(DAY, journal_root)
    before = path.read_text(encoding="utf-8")
    store.save_lesson(store.load_lesson(DAY, journal_root), journal_root)
    assert path.read_text(encoding="utf-8") == before
    assert not list((journal_root / "journal").glob(".tmp-*"))


def test_save_lesson_creates_dir_and_file(tmp_path, journal_root):
    fresh = tmp_path / "fresh"
    (fresh).mkdir()
    (fresh / "roster.yml").write_text((journal_root / "roster.yml").read_text(encoding="utf-8"), encoding="utf-8")
    rec = LessonRecord(date=date(2026, 9, 27), points=[PointEntry("alice", 1.5, "зачёт", "telegram")])
    path = store.save_lesson(rec, fresh)
    assert path == fresh / "journal" / "2026-09-27.yml"
    assert store.load_lesson(date(2026, 9, 27), fresh) == rec


def test_plan_helpers(course_root):
    assert store.plan_dates(course_root) == [date(2026, 9, 13), DAY]
    plan = store.load_plan(DAY, course_root)
    assert plan["theme"] == "Первый Python"
    assert store.hw_ids_from_plan(plan) == ["python-01-first-run"]
    assert store.hw_due_from_plan(plan) == date(2026, 9, 23)
    assert store.hw_ids_from_plan(store.load_plan(date(2026, 9, 13), course_root)) == []
    assert store.hw_due_from_plan({}) is None
    assert store.load_plan(date(2026, 1, 1), course_root) is None
```

- [ ] **Step 2: Запустить — падает**

Run: `cd tools && .venv/bin/python -m pytest tests/test_journal_store.py -q`
Expected: `ModuleNotFoundError: No module named 'journal.store'`

- [ ] **Step 3: Реализация** — `tools/journal/store.py`

```python
from __future__ import annotations
import os
import tempfile
from datetime import date
from pathlib import Path

import yaml

from journal.model import (
    JournalError, LessonRecord, Student, Tariff,
    lesson_to_dict, parse_lesson, parse_roster, parse_tariff,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def students_root(root=None) -> Path:
    if root is not None:
        return Path(root)
    env = os.environ.get("JUNIOR_IT_STUDENTS")
    return Path(env) if env else REPO_ROOT / "students"


def _load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise JournalError(f"{path}: битый YAML — {exc}", path) from exc


def load_roster(root=None) -> list[Student]:
    path = students_root(root) / "roster.yml"
    if not path.exists():
        raise JournalError(f"нет {path}", path)
    return parse_roster(_load_yaml(path), str(path))


def load_tariff(root=None) -> Tariff:
    path = students_root(root) / "points.yml"
    if not path.exists():
        return Tariff()
    return parse_tariff(_load_yaml(path))


def lesson_path(day: date, root=None) -> Path:
    return students_root(root) / "journal" / f"{day.isoformat()}.yml"


def _ids(root, roster) -> set[str]:
    return {s.id for s in (roster if roster is not None else load_roster(root))}


def load_lesson(day: date, root=None, roster=None) -> LessonRecord | None:
    path = lesson_path(day, root)
    if not path.exists():
        return None
    return parse_lesson(_load_yaml(path), day, _ids(root, roster), str(path))


def load_lessons(root=None, roster=None) -> list[LessonRecord]:
    ids = _ids(root, roster)
    lessons: list[LessonRecord] = []
    for path in sorted((students_root(root) / "journal").glob("*.yml")):
        try:
            day = date.fromisoformat(path.stem)
        except ValueError:
            raise JournalError(f"{path}: имя файла не дата", path) from None
        lessons.append(parse_lesson(_load_yaml(path), day, ids, str(path)))
    return lessons


def save_lesson(rec: LessonRecord, root=None) -> Path:
    path = lesson_path(rec.date, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(lesson_to_dict(rec), allow_unicode=True, sort_keys=False)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".yml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path


def load_plan(day: date, repo_root=None) -> dict | None:
    """План занятия из playground/<дата>/session.yml; None, если плана нет."""
    path = Path(repo_root or REPO_ROOT) / "playground" / day.isoformat() / "session.yml"
    if not path.exists():
        return None
    data = _load_yaml(path)
    return data if isinstance(data, dict) else None


def plan_dates(repo_root=None) -> list[date]:
    dates: list[date] = []
    for path in sorted((Path(repo_root or REPO_ROOT) / "playground").glob("*/session.yml")):
        try:
            dates.append(date.fromisoformat(path.parent.name))
        except ValueError:
            continue
    return dates


def hw_ids_from_plan(plan: dict) -> list[str]:
    items = (plan.get("homework") or {}).get("items") or []
    return [str(item).rstrip("/").split("/")[-1] for item in items]


def hw_due_from_plan(plan: dict) -> date | None:
    due = (plan.get("homework") or {}).get("due")
    if not due:
        return None
    return due if isinstance(due, date) else date.fromisoformat(str(due))
```

- [ ] **Step 4: Запустить — зелёные**

Run: `cd tools && .venv/bin/python -m pytest -q`
Expected: все PASS (в т.ч. старые — `conftest.py` не добавляет автоиспользуемых фикстур).

- [ ] **Step 5: Commit**

```bash
git add tools/journal/store.py tools/tests/conftest.py tools/tests/test_journal_store.py
git commit -m "feat(journal): YAML-хранилище — ростер, занятия с атомарной записью, план из playground"
```

---

### Task 3: `journal/ops.py` — операции с тарифными начислениями

**Files:**
- Create: `tools/journal/ops.py`
- Test: `tools/tests/test_journal_ops.py`

**Interfaces:**
- Consumes: `store.*` (Task 2), `model.*` (Task 1), фикстуры `journal_root`/`course_root`.
- Produces: константы `REASON_PRESENCE = "присутствие"`, `REASON_LATE = "опоздание"`, `REASON_HW = "домашка принята: {hw}"`, `REASON_HW_REWORK = "домашка после доработки: {hw}"`; функции (все возвращают сохранённый `LessonRecord`, кидают `TransitionError` на неверный аргумент/переход, `JournalError` на битые данные):
  - `mark_attendance(day, student, status, root=None)`
  - `issue_homework(day, hw_id=None, students=None, root=None, repo_root=None)` — без `hw_id` берёт `homework.items` плана; без `students` — присутствовавших (`present|late|recording`); существующие отметки не трогает
  - `set_homework(day, hw_id, student, status, note=None, root=None, today=None)` — `today` для тестов (дефолт `date.today()`)
  - `add_points(day, student, amount, reason, by="teacher", root=None)`
  - `set_note(day, student, text, root=None)` — пустой текст удаляет заметку

- [ ] **Step 1: Провальные тесты** — `tools/tests/test_journal_ops.py`

```python
from datetime import date

import pytest

from conftest import DAY
from journal import ops, store
from journal.model import TransitionError

NEW = date(2026, 9, 27)


def _points(rec, who):
    return [(p.amount, p.reason, p.by) for p in rec.points if p.who == who]


def test_mark_attendance_creates_file_and_charges_tariff(journal_root):
    rec = ops.mark_attendance(NEW, "alice", "present", journal_root)
    assert store.lesson_path(NEW, journal_root).exists()
    assert rec.attendance == {"alice": "present"}
    assert _points(rec, "alice") == [(2.0, "присутствие", "teacher")]


def test_mark_attendance_is_idempotent_and_switches(journal_root):
    ops.mark_attendance(DAY, "alice", "present", journal_root)
    rec = ops.mark_attendance(DAY, "alice", "present", journal_root)
    assert _points(rec, "alice") == [(2.0, "присутствие", "teacher")]
    rec = ops.mark_attendance(DAY, "alice", "late", journal_root)
    assert _points(rec, "alice") == [(1.0, "опоздание", "teacher")]
    ops.add_points(DAY, "alice", 3, "активность", root=journal_root)
    rec = ops.mark_attendance(DAY, "alice", "absent", journal_root)
    assert _points(rec, "alice") == [(3.0, "активность", "teacher")]
    rec = ops.mark_attendance(DAY, "alice", "recording", journal_root)
    assert _points(rec, "alice") == [(3.0, "активность", "teacher")]


def test_mark_attendance_rejects_bad_input(journal_root):
    with pytest.raises(TransitionError, match="посещаемости"):
        ops.mark_attendance(DAY, "alice", "here", journal_root)
    with pytest.raises(TransitionError, match="zed"):
        ops.mark_attendance(DAY, "zed", "present", journal_root)


def test_issue_homework_from_plan_to_attendees(journal_root, course_root):
    ops.mark_attendance(DAY, "carol", "absent", journal_root)
    rec = ops.issue_homework(DAY, root=journal_root, repo_root=course_root)
    marks = rec.homework["python-01-first-run"]
    assert marks["alice"].status == "issued" and marks["bob"].status == "submitted"  # существующее не тронуто
    assert "carol" not in marks


def test_issue_homework_explicit_and_without_plan(journal_root, course_root):
    rec = ops.issue_homework(NEW, "extra-01", ["bob"], journal_root, course_root)
    assert rec.homework == {"extra-01": {"bob": store.load_lesson(NEW, journal_root).homework["extra-01"]["bob"]}}
    assert rec.homework["extra-01"]["bob"].at == NEW
    with pytest.raises(TransitionError, match="нет плана"):
        ops.issue_homework(NEW, root=journal_root, repo_root=course_root)


def test_set_homework_transitions_and_points(journal_root):
    hw, today = "python-01-first-run", date(2026, 9, 22)
    with pytest.raises(TransitionError, match="недопустим"):
        ops.set_homework(DAY, hw, "alice", "accepted", root=journal_root, today=today)
    rec = ops.set_homework(DAY, hw, "alice", "submitted", root=journal_root, today=today)
    assert rec.homework[hw]["alice"].at == today
    rec = ops.set_homework(DAY, hw, "alice", "rework", note="без traceback", root=journal_root, today=today)
    assert rec.homework[hw]["alice"].reworked and rec.homework[hw]["alice"].note == "без traceback"
    ops.set_homework(DAY, hw, "alice", "submitted", root=journal_root, today=today)
    rec = ops.set_homework(DAY, hw, "alice", "accepted", root=journal_root, today=today)
    assert (2.0, "домашка после доработки: python-01-first-run", "teacher") in _points(rec, "alice")
    rec = ops.set_homework(DAY, hw, "bob", "accepted", root=journal_root, today=today)
    assert (3.0, "домашка принята: python-01-first-run", "teacher") in _points(rec, "bob")
    with pytest.raises(TransitionError, match="недопустим"):
        ops.set_homework(DAY, hw, "bob", "rework", root=journal_root, today=today)
    rec = ops.set_homework(DAY, hw, "bob", "accepted", root=journal_root, today=today)  # повтор — no-op
    assert _points(rec, "bob").count((3.0, "домашка принята: python-01-first-run", "teacher")) == 1


def test_set_homework_unknown_hw(journal_root):
    with pytest.raises(TransitionError, match="не выдана"):
        ops.set_homework(DAY, "nope", "alice", "submitted", root=journal_root)


def test_add_points_and_note(journal_root):
    rec = ops.add_points(DAY, "bob", 0.5, "зачёт", "telegram", journal_root)
    assert _points(rec, "bob")[-1] == (0.5, "зачёт", "telegram")
    with pytest.raises(TransitionError, match="причина"):
        ops.add_points(DAY, "bob", 1, "  ", root=journal_root)
    with pytest.raises(TransitionError, match="источник"):
        ops.add_points(DAY, "bob", 1, "x", "mail", journal_root)
    assert ops.set_note(DAY, "bob", " опоздал ", journal_root).notes == {"bob": "опоздал"}
    assert ops.set_note(DAY, "bob", "", journal_root).notes == {}
```

- [ ] **Step 2: Запустить — падает**

Run: `cd tools && .venv/bin/python -m pytest tests/test_journal_ops.py -q`
Expected: `ModuleNotFoundError: No module named 'journal.ops'`

- [ ] **Step 3: Реализация** — `tools/journal/ops.py`

```python
from __future__ import annotations
from datetime import date

from journal import store
from journal.model import (
    ATTENDANCE, HW_STATUSES, HW_TRANSITIONS, SOURCES,
    HomeworkMark, LessonRecord, PointEntry, TransitionError,
)

REASON_PRESENCE = "присутствие"
REASON_LATE = "опоздание"
REASON_HW = "домашка принята: {hw}"
REASON_HW_REWORK = "домашка после доработки: {hw}"
_ATTEND_REASONS = {REASON_PRESENCE, REASON_LATE}
_ATTENDED = ("present", "late", "recording")


def _record(day: date, root, roster) -> LessonRecord:
    return store.load_lesson(day, root, roster) or LessonRecord(date=day)


def _check_student(student: str, roster) -> None:
    if student not in {s.id for s in roster}:
        raise TransitionError(f"ученика {student!r} нет в ростере")


def mark_attendance(day: date, student: str, status: str, root=None) -> LessonRecord:
    if status not in ATTENDANCE:
        raise TransitionError(f"неизвестный статус посещаемости {status!r}")
    roster = store.load_roster(root)
    _check_student(student, roster)
    tariff = store.load_tariff(root)
    rec = _record(day, root, roster)
    rec.attendance[student] = status
    rec.points = [p for p in rec.points
                  if not (p.who == student and p.by == "teacher" and p.reason in _ATTEND_REASONS)]
    if status == "present":
        rec.points.append(PointEntry(student, tariff.presence, REASON_PRESENCE))
    elif status == "late":
        rec.points.append(PointEntry(student, tariff.late, REASON_LATE))
    store.save_lesson(rec, root)
    return rec


def issue_homework(day: date, hw_id=None, students=None, root=None, repo_root=None) -> LessonRecord:
    roster = store.load_roster(root)
    rec = _record(day, root, roster)
    if hw_id is None:
        plan = store.load_plan(day, repo_root)
        hw_ids = store.hw_ids_from_plan(plan) if plan else []
        if not hw_ids:
            raise TransitionError(f"на {day} нет плана с домашкой — укажи hw_id")
    else:
        hw_ids = [hw_id]
    if students is None:
        students = [sid for sid, st in rec.attendance.items() if st in _ATTENDED]
    for sid in students:
        _check_student(sid, roster)
    for hid in hw_ids:
        marks = rec.homework.setdefault(hid, {})
        for sid in students:
            marks.setdefault(sid, HomeworkMark(status="issued", at=day))
    store.save_lesson(rec, root)
    return rec


def set_homework(day: date, hw_id: str, student: str, status: str, note=None,
                 root=None, today=None) -> LessonRecord:
    if status not in HW_STATUSES:
        raise TransitionError(f"неизвестный статус домашки {status!r}")
    roster = store.load_roster(root)
    _check_student(student, roster)
    tariff = store.load_tariff(root)
    rec = _record(day, root, roster)
    marks = rec.homework.get(hw_id)
    if not marks or student not in marks:
        raise TransitionError(f"{hw_id} не выдана {student} на {day}")
    mark = marks[student]
    if status == mark.status:
        if note is not None:
            mark.note = note
            store.save_lesson(rec, root)
        return rec
    if status not in HW_TRANSITIONS[mark.status]:
        raise TransitionError(f"{hw_id} {student}: переход {mark.status} → {status} недопустим")
    mark.status = status
    mark.at = today or date.today()
    if note is not None:
        mark.note = note
    if status == "rework":
        mark.reworked = True
    if status == "accepted":
        reason = (REASON_HW_REWORK if mark.reworked else REASON_HW).format(hw=hw_id)
        amount = tariff.homework_after_rework if mark.reworked else tariff.homework_accepted
        if not any(p.who == student and p.reason == reason for p in rec.points):
            rec.points.append(PointEntry(student, amount, reason))
    store.save_lesson(rec, root)
    return rec


def add_points(day: date, student: str, amount, reason: str, by="teacher", root=None) -> LessonRecord:
    if by not in SOURCES:
        raise TransitionError(f"неизвестный источник {by!r}")
    if not reason or not str(reason).strip():
        raise TransitionError("нужна причина")
    roster = store.load_roster(root)
    _check_student(student, roster)
    rec = _record(day, root, roster)
    rec.points.append(PointEntry(student, float(amount), str(reason).strip(), by))
    store.save_lesson(rec, root)
    return rec


def set_note(day: date, student: str, text, root=None) -> LessonRecord:
    roster = store.load_roster(root)
    _check_student(student, roster)
    rec = _record(day, root, roster)
    if text and str(text).strip():
        rec.notes[student] = str(text).strip()
    else:
        rec.notes.pop(student, None)
    store.save_lesson(rec, root)
    return rec
```

- [ ] **Step 4: Запустить — зелёные**

Run: `cd tools && .venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/journal/ops.py tools/tests/test_journal_ops.py
git commit -m "feat(journal): операции — посещаемость, выдача и статусы домашек, баллы, заметки; тариф начисляется сам"
```

---

### Task 4: `journal/stats.py` — статистика и хвосты

**Files:**
- Create: `tools/journal/stats.py`
- Test: `tools/tests/test_journal_stats.py`

**Interfaces:**
- Consumes: `store.*`, `model.*`.
- Produces: `SUBMITTED_STALE_DAYS = 3`; `@dataclass StudentStats(id, name, lessons_total=0, present=0, late=0, recording=0, absent=0, hw_issued=0, hw_submitted=0, hw_accepted=0, hw_rework=0, points_total=0.0, points_period=0.0, last_lesson: date|None=None, tails: list[str]=[])`; `@dataclass GroupStats(lessons_total: int, students: list[StudentStats], missing_journals: list[date])`; `student_stats(student, lessons, plans: dict[date, dict|None], today, since=None) -> StudentStats`; `group_stats(roster, lessons, plans, today, since=None) -> GroupStats` (только `active`, по убыванию `points_total`); `collect(root=None, repo_root=None, today=None, since=None) -> GroupStats`; `to_json_dict(g) -> dict` (даты → ISO-строки).

- [ ] **Step 1: Провальные тесты** — `tools/tests/test_journal_stats.py`

```python
from datetime import date

from conftest import DAY, TODAY
from journal import ops, stats, store


def test_student_and_group_stats(journal_root, course_root):
    g = stats.collect(journal_root, course_root, TODAY)
    assert g.lessons_total == 1
    assert [s.id for s in g.students] == ["alice", "bob"]          # carol left; alice 2 > bob 1
    alice, bob = g.students
    assert (alice.present, alice.late, alice.hw_issued, alice.points_total) == (1, 0, 1, 2.0)
    assert alice.last_lesson == DAY
    assert alice.tails == ["python-01-first-run: просрочена с 2026-09-23"]
    assert bob.hw_submitted == 1
    assert bob.tails == ["python-01-first-run: сдана 2026-09-21, ждёт решения"]
    assert g.missing_journals == [date(2026, 9, 13)]


def test_no_tails_when_fresh(journal_root, course_root):
    g = stats.collect(journal_root, course_root, date(2026, 9, 22))
    assert all(s.tails == [] for s in g.students)


def test_points_period(journal_root, course_root):
    ops.add_points(date(2026, 9, 27), "alice", 4, "зачёт", root=journal_root)
    g = stats.collect(journal_root, course_root, date(2026, 9, 28), since=date(2026, 9, 25))
    alice = next(s for s in g.students if s.id == "alice")
    assert (alice.points_total, alice.points_period, alice.lessons_total) == (6.0, 4.0, 2)


def test_to_json_dict_serialises_dates(journal_root, course_root):
    data = stats.to_json_dict(stats.collect(journal_root, course_root, TODAY))
    assert data["missing_journals"] == ["2026-09-13"]
    assert data["students"][0]["last_lesson"] == "2026-09-20"
```

- [ ] **Step 2: Запустить — падает**

Run: `cd tools && .venv/bin/python -m pytest tests/test_journal_stats.py -q`
Expected: `ModuleNotFoundError: No module named 'journal.stats'`

- [ ] **Step 3: Реализация** — `tools/journal/stats.py`

```python
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import date

from journal import store
from journal.model import LessonRecord, Student

SUBMITTED_STALE_DAYS = 3


@dataclass
class StudentStats:
    id: str
    name: str
    lessons_total: int = 0
    present: int = 0
    late: int = 0
    recording: int = 0
    absent: int = 0
    hw_issued: int = 0
    hw_submitted: int = 0
    hw_accepted: int = 0
    hw_rework: int = 0
    points_total: float = 0.0
    points_period: float = 0.0
    last_lesson: date | None = None
    tails: list[str] = field(default_factory=list)


@dataclass
class GroupStats:
    lessons_total: int
    students: list[StudentStats]
    missing_journals: list[date]


def student_stats(student: Student, lessons: list[LessonRecord], plans: dict,
                  today: date, since: date | None = None) -> StudentStats:
    s = StudentStats(id=student.id, name=student.name, lessons_total=len(lessons))
    for rec in lessons:
        status = rec.attendance.get(student.id)
        if status is not None:
            setattr(s, status, getattr(s, status) + 1)
            if s.last_lesson is None or rec.date > s.last_lesson:
                s.last_lesson = rec.date
        plan = plans.get(rec.date)
        due = store.hw_due_from_plan(plan) if plan else None
        for hw_id, marks in rec.homework.items():
            mark = marks.get(student.id)
            if mark is None:
                continue
            s.hw_issued += 1
            if mark.status == "submitted":
                s.hw_submitted += 1
            elif mark.status == "accepted":
                s.hw_accepted += 1
            elif mark.status == "rework":
                s.hw_rework += 1
            if mark.status in ("issued", "rework") and due and due < today:
                s.tails.append(f"{hw_id}: просрочена с {due.isoformat()}")
            if mark.status == "submitted" and mark.at and (today - mark.at).days > SUBMITTED_STALE_DAYS:
                s.tails.append(f"{hw_id}: сдана {mark.at.isoformat()}, ждёт решения")
        for p in rec.points:
            if p.who != student.id:
                continue
            s.points_total += p.amount
            if since is None or rec.date >= since:
                s.points_period += p.amount
    return s


def group_stats(roster: list[Student], lessons: list[LessonRecord], plans: dict,
                today: date, since: date | None = None) -> GroupStats:
    active = [st for st in roster if st.status == "active"]
    students = sorted((student_stats(st, lessons, plans, today, since) for st in active),
                      key=lambda x: -x.points_total)
    journaled = {rec.date for rec in lessons}
    missing = sorted(d for d in plans if d < today and d not in journaled)
    return GroupStats(lessons_total=len(lessons), students=students, missing_journals=missing)


def load_plans(repo_root=None) -> dict:
    return {d: store.load_plan(d, repo_root) for d in store.plan_dates(repo_root)}


def collect(root=None, repo_root=None, today: date | None = None, since: date | None = None) -> GroupStats:
    roster = store.load_roster(root)
    lessons = store.load_lessons(root, roster)
    return group_stats(roster, lessons, load_plans(repo_root), today or date.today(), since)


def to_json_dict(g: GroupStats) -> dict:
    def conv(value):
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: conv(v) for k, v in value.items()}
        if isinstance(value, list):
            return [conv(v) for v in value]
        return value
    return conv(asdict(g))
```

- [ ] **Step 4: Запустить — зелёные**

Run: `cd tools && .venv/bin/python -m pytest -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/journal/stats.py tools/tests/test_journal_stats.py
git commit -m "feat(journal): статистика по ученику и группе, хвосты по дедлайну и по зависшей сдаче"
```

---

### Task 5: `journal/cli.py` — канал для автоматики; `group_status.py` на ростер

**Files:**
- Create: `tools/journal/cli.py`
- Modify: `tools/group_status.py` (целиком)
- Test: `tools/tests/test_journal_cli.py`

**Interfaces:**
- Consumes: `ops.*`, `stats.*`, `store.*`.
- Produces: `python3 tools/journal/cli.py [--root R] [--repo P] <cmd>`; `run(argv, today=None) -> int`; подкоманды `attend <date> <student> <status>`, `issue <date> [--hw ID] [--students a b]`, `hw <date> <hw_id> <student> <status> [--note T]`, `points <date> <student> <amount> <reason> [--by S]`, `note <date> <student> <text>`, `report [student] [--since D]`, `json [--since D]`; `format_report(g, student_id=None) -> str`. Коды 0/2/3 по Global Constraints. Скрипт самолокализуется: `sys.path.insert(0, <tools/>)` до импортов `journal`, чтобы запускаться и как `python3 tools/journal/cli.py`, и как `python -m journal.cli` из `tools/`.

- [ ] **Step 1: Провальные тесты** — `tools/tests/test_journal_cli.py`

```python
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from conftest import DAY, TODAY
from journal import store
from journal.cli import run

CLI = Path(__file__).resolve().parents[1] / "journal" / "cli.py"


def test_attend_and_hw_via_run(journal_root, course_root, capsys):
    root, repo = str(journal_root), str(course_root)
    assert run(["--root", root, "attend", "2026-09-27", "bob", "present"]) == 0
    assert store.load_lesson(date(2026, 9, 27), journal_root).attendance == {"bob": "present"}
    assert run(["--root", root, "--repo", repo, "hw", DAY.isoformat(), "python-01-first-run", "bob", "accepted"],
               today=date(2026, 9, 22)) == 0
    assert run(["--root", root, "hw", DAY.isoformat(), "python-01-first-run", "bob", "rework"]) == 2
    assert "недопустим" in capsys.readouterr().err
    assert run(["--root", root, "attend", "2026-09-27", "zed", "present"]) == 2


def test_issue_points_note(journal_root, course_root):
    root, repo = str(journal_root), str(course_root)
    assert run(["--root", root, "--repo", repo, "issue", "2026-09-27", "--hw", "extra", "--students", "alice"]) == 0
    assert run(["--root", root, "points", "2026-09-27", "alice", "0.5", "зачёт", "--by", "telegram"]) == 0
    assert run(["--root", root, "note", "2026-09-27", "alice", "молодец"]) == 0
    rec = store.load_lesson(date(2026, 9, 27), journal_root)
    assert rec.homework["extra"]["alice"].status == "issued"
    assert rec.points[-1].by == "telegram" and rec.notes == {"alice": "молодец"}


def test_report_and_json(journal_root, course_root, capsys):
    root, repo = str(journal_root), str(course_root)
    assert run(["--root", root, "--repo", repo, "report"], today=TODAY) == 0
    out = capsys.readouterr().out
    assert "Алиса" in out and "просрочена" in out and "без журнала: 2026-09-13" in out
    assert run(["--root", root, "--repo", repo, "report", "bob"], today=TODAY) == 0
    out = capsys.readouterr().out
    assert "Боб" in out and "Алиса" not in out and "ждёт решения" in out
    assert run(["--root", root, "--repo", repo, "json"], today=TODAY) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["students"][0]["id"] == "alice" and data["missing_journals"] == ["2026-09-13"]


def test_broken_data_is_3(journal_root, capsys):
    (journal_root / "roster.yml").write_text("students: [\n", encoding="utf-8")
    assert run(["--root", str(journal_root), "report"]) == 3
    assert "roster.yml" in capsys.readouterr().err


def test_script_runs_from_repo_root(journal_root, course_root):
    proc = subprocess.run([sys.executable, str(CLI), "--root", str(journal_root), "--repo", str(course_root), "json"],
                          capture_output=True, text=True, cwd=str(course_root))
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["lessons_total"] == 1
```

- [ ] **Step 2: Запустить — падает**

Run: `cd tools && .venv/bin/python -m pytest tests/test_journal_cli.py -q`
Expected: `ModuleNotFoundError: No module named 'journal.cli'`

- [ ] **Step 3: Реализация**

`tools/journal/cli.py`:

```python
#!/usr/bin/env python3
"""journal — канал для автоматики (zoom/telegram-тики) и агента. Ручная работа — tui.py."""
from __future__ import annotations
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tools/ — чтобы работал и python3 tools/journal/cli.py

from journal import ops, stats  # noqa: E402
from journal.model import JournalError, TransitionError, num  # noqa: E402


def _date(text: str) -> date:
    return date.fromisoformat(text)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="journal")
    ap.add_argument("--root", help="каталог students/ (по умолчанию <repo>/students или $JUNIOR_IT_STUDENTS)")
    ap.add_argument("--repo", help="корень репо для playground/ (по умолчанию — этот репо)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("attend", help="посещаемость")
    p.add_argument("date", type=_date); p.add_argument("student"); p.add_argument("status")
    p = sub.add_parser("issue", help="выдать домашку (по плану или --hw)")
    p.add_argument("date", type=_date); p.add_argument("--hw"); p.add_argument("--students", nargs="*")
    p = sub.add_parser("hw", help="статус домашки")
    p.add_argument("date", type=_date); p.add_argument("hw_id"); p.add_argument("student")
    p.add_argument("status"); p.add_argument("--note")
    p = sub.add_parser("points", help="баллы с причиной")
    p.add_argument("date", type=_date); p.add_argument("student"); p.add_argument("amount", type=float)
    p.add_argument("reason"); p.add_argument("--by", default="teacher")
    p = sub.add_parser("note", help="заметка (пусто — удалить)")
    p.add_argument("date", type=_date); p.add_argument("student"); p.add_argument("text")
    p = sub.add_parser("report", help="сводка текстом")
    p.add_argument("student", nargs="?"); p.add_argument("--since", type=_date)
    p = sub.add_parser("json", help="снимок статистики")
    p.add_argument("--since", type=_date)
    return ap


def _student_lines(s: stats.StudentStats) -> list[str]:
    lines = [f"{s.name} ({s.id}): был {s.present}/{s.lessons_total}, опоздал {s.late}, "
             f"по записи {s.recording}, нет {s.absent}; дз принято {s.hw_accepted}/{s.hw_issued}, "
             f"сдано {s.hw_submitted}, доработать {s.hw_rework}; баллы {num(s.points_total)} "
             f"(за период {num(s.points_period)})"]
    lines += [f"  хвост: {t}" for t in s.tails]
    return lines


def format_report(g: stats.GroupStats, student_id: str | None = None) -> str:
    lines: list[str] = []
    if student_id:
        match = [s for s in g.students if s.id == student_id]
        if not match:
            return f"{student_id}: нет в активном ростере"
        lines += _student_lines(match[0])
    else:
        lines.append(f"занятий: {g.lessons_total}")
        for s in g.students:
            lines += _student_lines(s)
    for day in g.missing_journals:
        lines.append(f"без журнала: {day.isoformat()}")
    return "\n".join(lines)


def run(argv, today: date | None = None) -> int:
    args = build_parser().parse_args(argv)
    root, repo = args.root, args.repo
    try:
        if args.cmd == "attend":
            ops.mark_attendance(args.date, args.student, args.status, root)
        elif args.cmd == "issue":
            ops.issue_homework(args.date, args.hw, args.students or None, root, repo)
        elif args.cmd == "hw":
            ops.set_homework(args.date, args.hw_id, args.student, args.status, args.note, root, today)
        elif args.cmd == "points":
            ops.add_points(args.date, args.student, args.amount, args.reason, args.by, root)
        elif args.cmd == "note":
            ops.set_note(args.date, args.student, args.text, root)
        elif args.cmd == "report":
            print(format_report(stats.collect(root, repo, today, args.since), args.student))
        elif args.cmd == "json":
            print(json.dumps(stats.to_json_dict(stats.collect(root, repo, today, args.since)),
                             ensure_ascii=False, indent=2))
    except TransitionError as exc:
        print(f"journal: {exc}", file=sys.stderr)
        return 2
    except JournalError as exc:
        print(f"journal: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
```

`tools/group_status.py` (заменить целиком; карточка кокпита вызывает его без venv, поэтому импорт `yaml` — только через `journal`, а его отсутствие — заглушка, не трейсбек):

```python
#!/usr/bin/env python3
"""Одна строка статуса группы для status-карточки кокпита.

Данные учеников приватны (students/ не в гите) — ростера может не быть.
Тогда печатаем нейтральную заглушку и выходим с кодом 0.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from journal import store
    from journal.model import JournalError
except ModuleNotFoundError:  # системный python без pyyaml — карточка не должна падать
    print("группа: нужен tools/.venv (pyyaml)")
    raise SystemExit(0)

try:
    roster = store.load_roster()
except JournalError:
    print("группа: нет данных (students/roster.yml)")
    raise SystemExit(0)

active = [s for s in roster if s.status == "active"]
print(f"учеников: {len(active)}")
```

- [ ] **Step 4: Запустить — зелёные; скрипт статуса не падает без ростера**

Run: `cd tools && .venv/bin/python -m pytest -q && JUNIOR_IT_STUDENTS=/nonexistent .venv/bin/python group_status.py`
Expected: PASS; `группа: нет данных (students/roster.yml)`.

- [ ] **Step 5: Commit**

```bash
git add tools/journal/cli.py tools/group_status.py tools/tests/test_journal_cli.py
git commit -m "feat(journal): CLI для автоматики и агента — attend/issue/hw/points/note/report/json; group_status по ростеру"
```

---

### Task 6: `journal/tui.py` — форма ввода после занятия

**Files:**
- Create: `tools/journal/tui.py`
- Modify: `tools/requirements.txt` (добавить `textual>=8,<9` и `pytest-asyncio>=0.23`), `tools/pytest.ini` (добавить `asyncio_mode = auto`)
- Test: `tools/tests/test_journal_tui.py`

**Interfaces:**
- Consumes: `ops.*`, `stats.*`, `store.*`, `model.*`.
- Produces: `JournalApp(root=None, repo_root=None, today=None, date_arg=None, opener=subprocess.Popen)`; экраны `GroupScreen`, `LessonPicker`, `LessonScreen(day)`, `StudentScreen(sid)`, `ErrorScreen(error)`; `main(argv=None) -> int` (`--date`, `--root`, `--repo`). Запуск: `tools/.venv/bin/python tools/journal/tui.py [--date YYYY-MM-DD]` (самолокализация как у cli.py).

- [ ] **Step 1: Зависимости**

В `tools/requirements.txt` добавить две строки: `textual>=8,<9` и `pytest-asyncio>=0.23`. В `tools/pytest.ini` добавить строку `asyncio_mode = auto`. Затем: `cd tools && .venv/bin/pip install -r requirements.txt` (сеть — PyPI). Проверить: `.venv/bin/python -c "import textual, pytest_asyncio; print(textual.__version__)"` → `8.x`.

- [ ] **Step 2: Провальные тесты** — `tools/tests/test_journal_tui.py`

```python
from datetime import date

import pytest
from textual.widgets import DataTable, Input

from conftest import DAY, TODAY
from journal import store
from journal.tui import ErrorScreen, GroupScreen, JournalApp, LessonScreen, StudentScreen


def _app(journal_root, course_root, **kw):
    return JournalApp(root=journal_root, repo_root=course_root, today=TODAY, **kw)


def _toasts(app):
    return [n.message for n in app._notifications._notifications.values()]


async def _type(pilot, text):
    """Набрать текст в Input: пробел у Textual — клавиша "space"."""
    await pilot.press(*("space" if ch == " " else ch for ch in text))


@pytest.mark.asyncio
async def test_group_screen_lists_active_students(journal_root, course_root):
    app = _app(journal_root, course_root)
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, GroupScreen)
        table = app.screen.query_one("#group", DataTable)
        assert table.row_count == 2
        assert table.get_row_at(0)[0] == "Алиса"          # по убыванию баллов
        assert "занятий 1" in app.screen.sub_title and "без журнала: 1" in app.screen.sub_title
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, StudentScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, GroupScreen)


@pytest.mark.asyncio
async def test_lesson_screen_space_cycles_attendance_and_saves(journal_root, course_root):
    app = _app(journal_root, course_root, date_arg=DAY)
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, LessonScreen)
        await pilot.press("space")               # alice: present → late
        await pilot.pause()
        rec = store.load_lesson(DAY, journal_root)
        assert rec.attendance["alice"] == "late"
        assert [p.reason for p in rec.points if p.who == "alice"] == ["опоздание"]
        assert any("late" in m for m in _toasts(app))


@pytest.mark.asyncio
async def test_lesson_screen_hw_and_points_prompt(journal_root, course_root):
    app = _app(journal_root, course_root, date_arg=DAY)
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await pilot.press("h")                   # alice: issued → submitted
        await pilot.pause()
        assert store.load_lesson(DAY, journal_root).homework["python-01-first-run"]["alice"].status == "submitted"
        await pilot.press("plus")
        await pilot.pause()
        prompt = app.screen.query_one("#prompt", Input)
        assert prompt.display and app.focused is prompt
        await _type(pilot, "2 сама нашла ошибку")
        await pilot.press("enter")
        await pilot.pause()
        rec = store.load_lesson(DAY, journal_root)
        assert (2.0, "сама нашла ошибку") in [(p.amount, p.reason) for p in rec.points if p.who == "alice"]
        assert not prompt.display
        await pilot.press("minus")
        await _type(pilot, "без причины")
        await pilot.press("enter")
        await pilot.pause()
        assert any("формат" in m for m in _toasts(app))
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, GroupScreen)


@pytest.mark.asyncio
async def test_invalid_transition_is_a_toast_not_a_crash(journal_root, course_root):
    app = _app(journal_root, course_root, date_arg=DAY)
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        await pilot.press("r")                   # alice issued → rework недопустим
        await pilot.pause()
        assert any("недопустим" in m for m in _toasts(app))
        assert store.load_lesson(DAY, journal_root).homework["python-01-first-run"]["alice"].status == "issued"


@pytest.mark.asyncio
async def test_error_screen_on_broken_roster(journal_root, course_root):
    (journal_root / "roster.yml").write_text("students: [\n", encoding="utf-8")
    opened = []
    app = _app(journal_root, course_root, opener=lambda cmd, **kw: opened.append(cmd))
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, ErrorScreen)
        await pilot.press("e")
        await pilot.pause()
        assert opened == [["tc-edit", str(journal_root / "roster.yml")]]
        await pilot.press("q")
```

- [ ] **Step 3: Запустить — падает**

Run: `cd tools && .venv/bin/python -m pytest tests/test_journal_tui.py -q`
Expected: `ModuleNotFoundError: No module named 'journal.tui'`

- [ ] **Step 4: Реализация** — `tools/journal/tui.py`

```python
#!/usr/bin/env python3
"""Журнал классного руководителя — TUI.

Запуск: tools/.venv/bin/python tools/journal/tui.py [--date YYYY-MM-DD]
Сохранение при каждом действии (операции ядра идемпотентны), тост на каждую клавишу.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tools/

from rich.text import Text  # noqa: E402
from textual.app import App, ComposeResult  # noqa: E402
from textual.binding import Binding  # noqa: E402
from textual.coordinate import Coordinate  # noqa: E402
from textual.screen import Screen  # noqa: E402
from textual.widgets import DataTable, Footer, Header, Input, Label, ListItem, ListView, Static  # noqa: E402

from journal import ops, stats, store  # noqa: E402
from journal.model import JournalError, LessonRecord, TransitionError, num  # noqa: E402

GLYPH = {"present": "●", "late": "◐", "absent": "○", "recording": "▶"}
HISTORY = 6
ATTEND_CYCLE = {None: "present", "present": "late", "late": "absent", "absent": "recording", "recording": "present"}
HW_CYCLE = {"issued": "submitted", "submitted": "accepted", "rework": "submitted"}


def _selected_key(table: DataTable) -> str | None:
    if table.row_count == 0 or table.cursor_row is None:
        return None
    return table.coordinate_to_cell_key(Coordinate(table.cursor_row, 0)).row_key.value


class JournalApp(App):
    BINDINGS = [("q", "quit", "выход")]
    CSS = """
    #error { padding: 1 2; color: $error; }
    #plan, #card { padding: 0 1; height: auto; }
    #prompt { dock: bottom; }
    """

    def __init__(self, root=None, repo_root=None, today: date | None = None,
                 date_arg: date | None = None, opener=subprocess.Popen):
        super().__init__()
        self.root = Path(root) if root else None
        self.repo_root = Path(repo_root) if repo_root else None
        self.today = today or date.today()
        self.date_arg = date_arg
        self._opener = opener
        self.title = "журнал"

    def on_mount(self) -> None:
        try:
            store.load_lessons(self.root)
        except JournalError as exc:
            self.push_screen(ErrorScreen(exc))
            return
        self.push_screen(GroupScreen())
        if self.date_arg:
            self.push_screen(LessonScreen(self.date_arg))

    def say(self, text: str, severity: str = "information") -> None:
        self.notify(text, severity=severity, timeout=3, markup=False)

    def open_in_editor(self, path: Path) -> None:
        try:
            self._opener(["tc-edit", str(path)])
        except Exception as exc:  # opener не найден — тост, не падение
            self.say(f"tc-edit: {exc}", "error")


class ErrorScreen(Screen):
    BINDINGS = [("e", "edit", "открыть файл"), ("q", "app.quit", "выход")]

    def __init__(self, error: JournalError):
        super().__init__()
        self.error = error

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"⚠ {self.error}\n\nПочини файл (e) и запусти снова.", id="error")
        yield Footer()

    def action_edit(self) -> None:
        if self.error.path:
            self.app.open_in_editor(Path(self.error.path))
        else:
            self.app.say("файл не известен", "warning")


class GroupScreen(Screen):
    BINDINGS = [
        Binding("enter", "student", "ученик", priority=True),
        ("l", "lessons", "занятие"),
        ("q", "app.quit", "выход"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="group")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("ученик", "занятия", "баллы", "дз", "хвосты")
        self.reload()

    def on_screen_resume(self) -> None:
        self.reload()

    def reload(self) -> None:
        app = self.app
        table = self.query_one(DataTable)
        table.clear()
        g = stats.collect(app.root, app.repo_root, app.today)
        lessons = store.load_lessons(app.root)[-HISTORY:]
        for s in g.students:
            glyphs = "".join(GLYPH.get(rec.attendance.get(s.id), "·") for rec in lessons)
            tails = Text(str(len(s.tails)), style="yellow" if s.tails else "dim")
            table.add_row(s.name, glyphs, str(num(s.points_total)), f"{s.hw_accepted}/{s.hw_issued}", tails, key=s.id)
        self.sub_title = f"занятий {g.lessons_total}" + (
            f" · без журнала: {len(g.missing_journals)}" if g.missing_journals else "")

    def action_student(self) -> None:
        sid = _selected_key(self.query_one(DataTable))
        if sid is None:
            self.app.say("нет учеников", "warning")
            return
        self.app.push_screen(StudentScreen(sid))

    def action_lessons(self) -> None:
        self.app.push_screen(LessonPicker())


class LessonPicker(Screen):
    BINDINGS = [("escape", "app.pop_screen", "назад")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(id="dates")
        yield Footer()

    def on_mount(self) -> None:
        app = self.app
        journaled = {rec.date for rec in store.load_lessons(app.root)}
        planned = {d for d in store.plan_dates(app.repo_root) if d <= app.today}
        dates = sorted(journaled | planned, reverse=True)
        view = self.query_one(ListView)
        for day in dates:
            mark = "" if day in journaled else "  · не заполнено"
            view.append(ListItem(Label(f"{day.isoformat()}{mark}"), name=day.isoformat()))
        if not dates:
            app.say("нет ни занятий, ни планов", "warning")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.app.pop_screen()
        self.app.push_screen(LessonScreen(date.fromisoformat(event.item.name)))


class LessonScreen(Screen):
    BINDINGS = [
        ("space", "attend", "посещаемость"),
        ("h", "hw_next", "дз →"),
        ("r", "hw_rework", "доработать"),
        ("plus", "points_plus", "+баллы"),
        ("minus", "points_minus", "-баллы"),
        ("n", "note", "заметка"),
        ("escape", "back", "назад"),
    ]

    def __init__(self, day: date):
        super().__init__()
        self.day = day
        self.rec = LessonRecord(date=day)
        self.mode: str | None = None
        self.mode_sid: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="plan")
        yield DataTable(id="lesson")
        yield Input(id="prompt")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("ученик", "посещаемость", "домашки", "баллы", "заметка")
        self.query_one(Input).display = False
        plan = store.load_plan(self.day, self.app.repo_root)
        theme = plan.get("theme", "") if plan else "план не найден"
        self.query_one("#plan", Static).update(f"{self.day.isoformat()} · {theme}")
        self.reload()

    def reload(self) -> None:
        app = self.app
        table = self.query_one(DataTable)
        keep = table.cursor_row
        table.clear()
        roster = [s for s in store.load_roster(app.root) if s.status == "active"]
        self.rec = store.load_lesson(self.day, app.root, roster) or LessonRecord(date=self.day)
        for s in roster:
            status = self.rec.attendance.get(s.id)
            hw = ", ".join(f"{hid}: {marks[s.id].status}"
                           for hid, marks in self.rec.homework.items() if s.id in marks) or "—"
            pts = num(sum(p.amount for p in self.rec.points if p.who == s.id))
            table.add_row(s.name, f"{GLYPH.get(status, '·')} {status or '—'}", hw, str(pts),
                          self.rec.notes.get(s.id, ""), key=s.id)
        if keep is not None and table.row_count:
            table.move_cursor(row=min(keep, table.row_count - 1))

    def _do(self, fn, *args) -> bool:
        try:
            fn(*args)
        except JournalError as exc:  # TransitionError — подкласс
            self.app.say(str(exc), "error")
            return False
        self.reload()
        return True

    def _hw_ids(self, sid: str) -> list[str]:
        return [hid for hid, marks in self.rec.homework.items() if sid in marks]

    def action_attend(self) -> None:
        sid = _selected_key(self.query_one(DataTable))
        if sid is None:
            return
        new = ATTEND_CYCLE[self.rec.attendance.get(sid)]
        if self._do(ops.mark_attendance, self.day, sid, new, self.app.root):
            self.app.say(f"{sid}: {new}")

    def action_hw_next(self) -> None:
        sid = _selected_key(self.query_one(DataTable))
        if sid is None:
            return
        ids = self._hw_ids(sid)
        if not ids:
            if self._do(ops.issue_homework, self.day, None, [sid], self.app.root, self.app.repo_root):
                self.app.say(f"{sid}: домашка выдана")
            return
        for hid in ids:
            current = self.rec.homework[hid][sid].status
            nxt = HW_CYCLE.get(current)
            if nxt is None:
                self.app.say(f"{hid}: уже {current}", "warning")
                continue
            if self._do(ops.set_homework, self.day, hid, sid, nxt, None, self.app.root, self.app.today):
                self.app.say(f"{hid} {sid}: {nxt}")

    def action_hw_rework(self) -> None:
        sid = _selected_key(self.query_one(DataTable))
        if sid is None:
            return
        ids = self._hw_ids(sid)
        if not ids:
            self.app.say(f"{sid}: домашка не выдана", "warning")
        for hid in ids:
            if self._do(ops.set_homework, self.day, hid, sid, "rework", None, self.app.root, self.app.today):
                self.app.say(f"{hid} {sid}: rework")

    def _prompt(self, mode: str, placeholder: str) -> None:
        sid = _selected_key(self.query_one(DataTable))
        if sid is None:
            return
        self.mode, self.mode_sid = mode, sid
        prompt = self.query_one(Input)
        prompt.value = ""
        prompt.placeholder = placeholder
        prompt.display = True
        prompt.focus()

    def action_points_plus(self) -> None:
        self._prompt("plus", "баллы и причина: 2 сама нашла ошибку")

    def action_points_minus(self) -> None:
        self._prompt("minus", "баллы и причина: 1 не сделал шаг 4")

    def action_note(self) -> None:
        self._prompt("note", "заметка (пусто — удалить)")

    def _hide_prompt(self) -> None:
        self.query_one(Input).display = False
        self.query_one(DataTable).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._hide_prompt()
        text, sid = event.value.strip(), self.mode_sid
        if self.mode == "note":
            if self._do(ops.set_note, self.day, sid, text, self.app.root):
                self.app.say(f"{sid}: заметка сохранена")
            return
        parts = text.split(maxsplit=1)
        try:
            amount = float(parts[0].replace(",", "."))
        except (IndexError, ValueError):
            self.app.say("формат: <баллы> <причина>", "error")
            return
        if len(parts) < 2:
            self.app.say("нужна причина", "error")
            return
        if self.mode == "minus":
            amount = -abs(amount)
        if self._do(ops.add_points, self.day, sid, amount, parts[1], "teacher", self.app.root):
            self.app.say(f"{sid}: {num(amount):+} — {parts[1]}")

    def action_back(self) -> None:
        if self.query_one(Input).display:
            self._hide_prompt()
            return
        self.app.pop_screen()


class StudentScreen(Screen):
    BINDINGS = [("e", "edit", "ростер в nvim"), ("escape", "app.pop_screen", "назад")]

    def __init__(self, sid: str):
        super().__init__()
        self.sid = sid

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="card")
        yield DataTable(id="history")
        yield DataTable(id="points")
        yield Footer()

    def on_mount(self) -> None:
        app = self.app
        roster = store.load_roster(app.root)
        student = next(s for s in roster if s.id == self.sid)
        lessons = store.load_lessons(app.root, roster)
        s = stats.student_stats(student, lessons, stats.load_plans(app.repo_root), app.today)
        card = (f"{s.name} ({s.id}) · {student.platform or '—'} · с {student.joined or '—'}\n"
                f"занятий {s.lessons_total}: был {s.present}, опоздал {s.late}, "
                f"по записи {s.recording}, нет {s.absent}\n"
                f"домашки: выдано {s.hw_issued}, сдано {s.hw_submitted}, принято {s.hw_accepted}, "
                f"доработать {s.hw_rework}\nбаллы: {num(s.points_total)}")
        if s.tails:
            card += "\nхвосты: " + "; ".join(s.tails)
        self.query_one("#card", Static).update(card)
        history = self.query_one("#history", DataTable)
        history.add_columns("дата", "посещаемость", "домашки", "баллы")
        points = self.query_one("#points", DataTable)
        points.add_columns("дата", "баллы", "причина", "кто")
        for rec in reversed(lessons):
            hw = ", ".join(f"{hid}: {marks[self.sid].status}"
                           for hid, marks in rec.homework.items() if self.sid in marks) or "—"
            day_points = num(sum(p.amount for p in rec.points if p.who == self.sid))
            history.add_row(rec.date.isoformat(), rec.attendance.get(self.sid, "—"), hw, str(day_points))
            for p in rec.points:
                if p.who == self.sid:
                    points.add_row(rec.date.isoformat(), f"{num(p.amount):+}", p.reason, p.by)

    def action_edit(self) -> None:
        self.app.open_in_editor(store.students_root(self.app.root) / "roster.yml")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="journal-tui")
    ap.add_argument("--date", type=date.fromisoformat, help="сразу открыть занятие")
    ap.add_argument("--root")
    ap.add_argument("--repo")
    args = ap.parse_args(argv)
    JournalApp(root=args.root, repo_root=args.repo, date_arg=args.date).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Запустить — зелёные**

Run: `cd tools && .venv/bin/python -m pytest -q`
Expected: PASS. Известные места, где Textual 8 может потребовать правку теста (не реализации): `table.get_row_at(0)` возвращает список ячеек — первая `"Алиса"`; если приоритетный `enter` на `GroupScreen` не срабатывает из-за фокуса на DataTable — оставить `priority=True` (как в cockpit). Если `pilot.press("plus")` не доходит — Textual называет клавишу `+` именно `plus`, проверить `app.screen.BINDINGS`.

- [ ] **Step 6: Скриншот на фикстурной группе** (визуальное ревью)

Скрипт в scratchpad `journal_shot.py`, запускать из `tools/`:

```python
import asyncio, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from conftest import DAY, TODAY  # фикстуры не нужны: соберём каталог вручную
import yaml
from journal.tui import JournalApp

root = Path(sys.argv[1]); out = sys.argv[2]
(root / "students" / "journal").mkdir(parents=True, exist_ok=True)
(root / "students" / "roster.yml").write_text(yaml.safe_dump({"students": [
    {"id": "alice", "name": "Алиса", "status": "active"}, {"id": "bob", "name": "Боб", "status": "active"}]},
    allow_unicode=True), encoding="utf-8")
(root / "students" / "journal" / "2026-09-20.yml").write_text(yaml.safe_dump({
    "date": DAY, "attendance": {"alice": "present", "bob": "late"},
    "homework": {"python-01-first-run": {"alice": {"status": "issued", "at": DAY}}},
    "points": [{"who": "alice", "amount": 2, "reason": "присутствие", "by": "teacher"}], "notes": {}},
    allow_unicode=True, sort_keys=False), encoding="utf-8")
(root / "repo" / "playground" / "2026-09-20").mkdir(parents=True, exist_ok=True)
(root / "repo" / "playground" / "2026-09-20" / "session.yml").write_text(
    "date: 2026-09-20\ntheme: Первый Python\nhomework: {due: 2026-09-23, items: [homework/python-01-first-run]}\n", encoding="utf-8")

async def main():
    app = JournalApp(root=root / "students", repo_root=root / "repo", today=TODAY, date_arg=DAY)
    async with app.run_test(size=(140, 36)) as pilot:
        await pilot.pause()
        app.save_screenshot(out)

asyncio.run(main())
```

```bash
cd tools && .venv/bin/python <scratchpad>/journal_shot.py <scratchpad>/shot <scratchpad>/journal.svg
qlmanage -t -s 1600 -o <scratchpad> <scratchpad>/journal.svg
```

Открыть `<scratchpad>/journal.svg.png`: шапка «2026-09-20 · Первый Python», две строки учеников с глифами `●`/`◐`, колонка домашек `python-01-first-run: issued`, футер с `space h r + - n esc`. Что криво — чинить CSS в `JournalApp.CSS`, переснимать.

- [ ] **Step 7: Commit**

```bash
git add tools/journal/tui.py tools/tests/test_journal_tui.py tools/requirements.txt tools/pytest.ini
git commit -m "feat(journal): TUI — группа, занятие (посещаемость, домашки, баллы, заметки), карточка ученика"
```

---

### Task 7: бэкап на NAS, launchd-агент, карточки кокпита

**Files:**
- Create: `tools/students_backup.sh`, `provisioning/students-backup/com.juniorit.students-backup.plist`, `provisioning/students-backup/setup.md`
- Modify: `.zellij/cockpit.yml`
- Test: `tools/tests/test_students_backup.py`

**Interfaces:**
- Produces: `tools/students_backup.sh` — переменные `JUNIOR_IT_STUDENTS` (источник, дефолт `<repo>/students`), `STUDENTS_BACKUP_SHARE` (точка монтирования, дефолт `/Volumes/BACKUP-VIDEO`), `STUDENTS_BACKUP_DEST` (дефолт `$SHARE/JuniorIT/students`); шара не смонтирована → одна строка «не смонтирована», exit 0; иначе `rsync -a --delete` и строка `ok N файлов`; ошибка rsync → exit 1. launchd `com.juniorit.students-backup`, раз в час, лог `~/Library/Logs/junior-it-students-backup.log`.

- [ ] **Step 1: Провальный тест** — `tools/tests/test_students_backup.py`

```python
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "students_backup.sh"


def _run(env_extra, tmp_path):
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(tmp_path), **env_extra}
    return subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, env=env)


def test_skips_when_share_not_mounted(tmp_path):
    src = tmp_path / "students"
    src.mkdir()
    proc = _run({"JUNIOR_IT_STUDENTS": str(src), "STUDENTS_BACKUP_SHARE": str(tmp_path / "nope")}, tmp_path)
    assert proc.returncode == 0 and "не смонтирована" in proc.stdout


def test_syncs_and_deletes_stale(tmp_path):
    src, share = tmp_path / "students", tmp_path / "share"
    (src / "journal").mkdir(parents=True)
    (src / "roster.yml").write_text("students: []\n", encoding="utf-8")
    (src / "journal" / "2026-09-20.yml").write_text("date: 2026-09-20\n", encoding="utf-8")
    dest = share / "JuniorIT" / "students"
    dest.mkdir(parents=True)
    (dest / "stale.yml").write_text("x", encoding="utf-8")
    proc = _run({"JUNIOR_IT_STUDENTS": str(src), "STUDENTS_BACKUP_SHARE": str(share)}, tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert (dest / "roster.yml").exists() and (dest / "journal" / "2026-09-20.yml").exists()
    assert not (dest / "stale.yml").exists()
    assert "ok 2 файлов" in proc.stdout
```

- [ ] **Step 2: Запустить — падает**

Run: `cd tools && .venv/bin/python -m pytest tests/test_students_backup.py -q`
Expected: FAIL (`bash: …/students_backup.sh: No such file or directory`, returncode ≠ 0).

- [ ] **Step 3: Скрипт, plist, setup, карточки**

`tools/students_backup.sh` (`chmod +x`):

```bash
#!/usr/bin/env bash
# students_backup.sh — зеркало приватного students/ на NAS. Раз в час из launchd
# (com.juniorit.students-backup). Шара не смонтирована — тихий пропуск, не ошибка.
set -uo pipefail

SRC="${JUNIOR_IT_STUDENTS:-$(cd "$(dirname "$0")/.." && pwd)/students}"
SHARE="${STUDENTS_BACKUP_SHARE:-/Volumes/BACKUP-VIDEO}"
DEST="${STUDENTS_BACKUP_DEST:-$SHARE/JuniorIT/students}"
stamp=$(date '+%Y-%m-%d %H:%M:%S')

if [[ ! -d "$SHARE" ]]; then
  echo "$stamp: шара $SHARE не смонтирована, пропуск"
  exit 0
fi
if [[ ! -d "$SRC" ]]; then
  echo "$stamp: нет источника $SRC, пропуск"
  exit 0
fi

mkdir -p "$DEST" || { echo "$stamp: не создать $DEST"; exit 1; }
if rsync -a --delete "$SRC/" "$DEST/"; then
  count=$(find "$SRC" -type f | wc -l | tr -d ' ')
  echo "$stamp: ok $count файлов → $DEST"
else
  echo "$stamp: rsync завершился с ошибкой"
  exit 1
fi
```

`provisioning/students-backup/com.juniorit.students-backup.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.juniorit.students-backup</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/dmitrymorozov/Projects/Junior_IT/tools/students_backup.sh</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>StartInterval</key>
  <integer>3600</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/Users/dmitrymorozov/Library/Logs/junior-it-students-backup.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/dmitrymorozov/Library/Logs/junior-it-students-backup.log</string>
</dict>
</plist>
```

`provisioning/students-backup/setup.md`:

```markdown
# Бэкап students/ на NAS

Приватные данные учеников (`students/`, не в гите) раз в час зеркалятся на
QNAP: `/Volumes/BACKUP-VIDEO/JuniorIT/students/`. Шара не смонтирована — тик
пропускается, в лог одна строка.

## Установка

```bash
cp provisioning/students-backup/com.juniorit.students-backup.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.juniorit.students-backup.plist
```

Проверка руками: `bash tools/students_backup.sh` → `… ok N файлов → …`.
Лог: `~/Library/Logs/junior-it-students-backup.log`. Статус — карточка
`students-backup` во вкладке `processes`.
```

`.zellij/cockpit.yml` — заменить карточку `students` и добавить `students-backup`:

```yaml
  - id: students
    type: status
    label: "ученики"
    status: "tools/.venv/bin/python tools/group_status.py"
    interval: 300

  - id: students-backup
    type: schedule
    label: "students → NAS"
    launchd: "com.juniorit.students-backup"
```

- [ ] **Step 4: Тесты, ручная проверка, установка агента**

```bash
cd tools && .venv/bin/python -m pytest -q
bash tools/students_backup.sh            # реальный запуск: «ok N файлов» или «не смонтирована»
cp provisioning/students-backup/com.juniorit.students-backup.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.juniorit.students-backup.plist
launchctl print gui/$(id -u)/com.juniorit.students-backup | grep -E "state|last exit|run interval"
tail -2 ~/Library/Logs/junior-it-students-backup.log
PYTHONPATH=~/.local/lib/terminal-commander/cockpit ~/.local/lib/terminal-commander/cockpit/.venv/bin/python -c "from cockpit.manifest import load_manifest; print([c.id for c in load_manifest('.zellij/cockpit.yml').cards])"
```

Expected: PASS; лог содержит строку тика (RunAtLoad); список карточек включает `students-backup`.

- [ ] **Step 5: Commit**

```bash
git add tools/students_backup.sh provisioning/students-backup/com.juniorit.students-backup.plist \
        provisioning/students-backup/setup.md .zellij/cockpit.yml tools/tests/test_students_backup.py
git commit -m "feat(students): бэкап students/ на NAS — скрипт, launchd-агент, карточка кокпита; ученики через tools/.venv"
```

---

### Task 8: движок info-панели — цель `run:` (terminal-commander)

**Files:** (репо `/Users/dmitrymorozov/Projects/terminal-commander`, ветка `feat/info-run-target` от `main`)
- Modify: `home/dot_local/lib/terminal-commander/cockpit/cockpit/info/providers.py` (`open_cmd`)
- Modify: `home/dot_local/lib/terminal-commander/cockpit/tests/test_info_providers.py` (`test_open_cmd` + новый тест)
- Modify: `docs/superpowers/specs/2026-09-21-info-panel-design.md` (§«Виджеты», пункт `links`/`command`)

**Interfaces:**
- Produces: `open_cmd("run:<cmd>", root)` → `["zellij", "action", "new-pane", "--floating", "--close-on-exit", "--cwd", str(root), "--", "bash", "-lc", "<cmd>"]`; пустая команда (`"run:"`, `"run:   "`) → `None`. Остальные цели без изменений.

- [ ] **Step 1: Провальный тест** — дописать в `tests/test_info_providers.py`

```python
def test_open_cmd_run_target(tmp_path):
    assert open_cmd("run:tools/.venv/bin/python tools/journal/tui.py", tmp_path) == [
        "zellij", "action", "new-pane", "--floating", "--close-on-exit", "--cwd", str(tmp_path),
        "--", "bash", "-lc", "tools/.venv/bin/python tools/journal/tui.py"]
    assert open_cmd("run:", tmp_path) is None
    assert open_cmd("run:   ", tmp_path) is None
```

- [ ] **Step 2: Запустить — падает**

Run: `cd home/dot_local/lib/terminal-commander/cockpit && uv run --extra dev pytest tests/test_info_providers.py -q -k run_target`
Expected: FAIL (`open_cmd` возвращает `None` — файла `run:…` нет).

- [ ] **Step 3: Реализация** — заменить `open_cmd` в `cockpit/info/providers.py`

```python
def open_cmd(target: str, root) -> list[str] | None:
    if target.startswith("run:"):
        command = target[len("run:"):].strip()
        if not command:
            return None
        return ["zellij", "action", "new-pane", "--floating", "--close-on-exit",
                "--cwd", str(root), "--", "bash", "-lc", command]
    if target.startswith(("http://", "https://")):
        return ["open", target]
    path = Path(root) / target
    if not path.exists():
        return None
    return ["tc-edit", str(path)]
```

В спеке info-панели, §«Виджеты», бокс `links`: после «`url` → `open <url>`» добавить «; цель с префиксом `run:` → команда в плавающей панели Zellij (`zellij action new-pane --floating --close-on-exit --cwd <корень>`), тот же контракт в `open` у `command`».

- [ ] **Step 4: Тесты, деплой, проверка**

```bash
cd home/dot_local/lib/terminal-commander/cockpit && uv run --extra dev pytest -q
chezmoi apply ~/.local/lib/terminal-commander/cockpit
grep -c 'run:' ~/.local/lib/terminal-commander/cockpit/cockpit/info/providers.py
```

Expected: 110 PASS; `grep` ≥ 1.

- [ ] **Step 5: Commit и слияние в main**

```bash
git add home/dot_local/lib/terminal-commander/cockpit/cockpit/info/providers.py \
        home/dot_local/lib/terminal-commander/cockpit/tests/test_info_providers.py \
        docs/superpowers/specs/2026-09-21-info-panel-design.md
git commit -m "feat(info): цель run: — команда в плавающей панели Zellij из бокса links/command"
git checkout main && git merge --no-edit feat/info-run-target && git branch -d feat/info-run-target
```

Итог в отчёте: коммиты обеих веток, число тестов в `tools/` и в cockpit, состояние launchd-агента, путь к PNG. `git push` — только по слову Димаса.
