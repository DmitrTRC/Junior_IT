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
    by: str = "teacher"


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


def _section(data: dict, key: str, kind: type, path):
    """Секция манифеста нужной формы; отсутствие/null — пустая секция."""
    value = data.get(key)
    if value is None:
        return {} if kind is dict else []
    if not isinstance(value, kind):
        raise JournalError(f"{path}: {key} должна быть {'mapping' if kind is dict else 'list'}", path)
    return value


def _number(value, what: str, path) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise JournalError(f"{path}: {what} должен быть числом, а не {value!r}", path)
    return float(value)


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
        zoom_names = raw.get("zoom_names")
        if zoom_names is not None and not isinstance(zoom_names, list):
            raise JournalError(f"{path}: у {sid} zoom_names должен быть list", path)
        for key in ("contacts", "parent"):
            value = raw.get(key)
            if value is not None and not isinstance(value, dict):
                raise JournalError(f"{path}: у {sid} {key} должен быть mapping", path)
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
    return Tariff(**{k: _number(v, k, "points.yml") for k, v in data.items()})


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
    for sid, status in _section(data, "attendance", dict, path).items():
        known(sid, "attendance")
        if status not in ATTENDANCE:
            raise JournalError(f"{path}: attendance {sid}: неизвестный статус {status!r}", path)
        attendance[sid] = status
    homework: dict[str, dict[str, HomeworkMark]] = {}
    for hw_id, marks in _section(data, "homework", dict, path).items():
        if marks is not None and not isinstance(marks, dict):
            raise JournalError(f"{path}: homework {hw_id} должна быть mapping", path)
        homework[hw_id] = {}
        for sid, raw in (marks or {}).items():
            known(sid, f"homework {hw_id}")
            if raw is not None and not isinstance(raw, dict):
                raise JournalError(f"{path}: homework {hw_id} {sid}: отметка должна быть mapping", path)
            raw = raw or {}
            status = raw.get("status", "issued")
            if status not in HW_STATUSES:
                raise JournalError(f"{path}: homework {hw_id} {sid}: неизвестный статус {status!r}", path)
            by = raw.get("by", "teacher")
            if by not in SOURCES:
                raise JournalError(f"{path}: homework {hw_id} {sid}: неизвестный источник {by!r}", path)
            homework[hw_id][sid] = HomeworkMark(
                status=status,
                at=_as_date(raw["at"], f"at у {hw_id}/{sid}", path) if raw.get("at") else None,
                note=raw.get("note"), reworked=bool(raw.get("reworked", False)), by=by)
    points: list[PointEntry] = []
    for raw in _section(data, "points", list, path):
        if not isinstance(raw, dict) or "who" not in raw or "amount" not in raw:
            raise JournalError(f"{path}: запись points без who/amount", path)
        known(raw["who"], "points")
        by = raw.get("by", "teacher")
        if by not in SOURCES:
            raise JournalError(f"{path}: points {raw['who']}: неизвестный источник {by!r}", path)
        points.append(PointEntry(who=raw["who"], amount=_number(raw["amount"], f"points {raw['who']}: amount", path),
                                 reason=str(raw.get("reason", "")), by=by))
    notes: dict[str, str] = {}
    for sid, text in _section(data, "notes", dict, path).items():
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
            if m.by != "teacher":
                entry["by"] = m.by
            homework[hw_id][sid] = entry
    return {
        "date": rec.date,
        "attendance": dict(rec.attendance),
        "homework": homework,
        "points": [{"who": p.who, "amount": num(p.amount), "reason": p.reason, "by": p.by}
                   for p in rec.points],
        "notes": dict(rec.notes),
    }
