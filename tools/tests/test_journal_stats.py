from datetime import date

from conftest import DAY, TODAY
from journal import ops, stats


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
