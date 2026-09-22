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
