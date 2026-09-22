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


def test_load_lessons_skips_orphaned_temp_files(journal_root):
    (journal_root / "journal" / ".tmp-abc.yml").write_text("date: 2026-09-20\n", encoding="utf-8")
    assert [r.date for r in store.load_lessons(journal_root)] == [DAY]


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
