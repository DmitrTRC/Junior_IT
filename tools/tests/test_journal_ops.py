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
