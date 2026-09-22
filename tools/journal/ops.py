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
