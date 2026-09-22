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
async def test_lesson_screen_tolerates_left_student_records(journal_root, course_root):
    import yaml
    path = journal_root / "journal" / "2026-09-20.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["attendance"]["carol"] = "present"      # carol в ростере со status left
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    app = _app(journal_root, course_root, date_arg=DAY)
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, LessonScreen)
        table = app.screen.query_one("#lesson", DataTable)
        assert table.row_count == 2                # alice, bob; carol не показывается


@pytest.mark.asyncio
async def test_lesson_actions_toast_when_no_student_focused(journal_root, course_root):
    import yaml
    path = journal_root / "roster.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for s in data["students"]:
        s["status"] = "left"
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    app = _app(journal_root, course_root, date_arg=DAY)
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        table = app.screen.query_one("#lesson", DataTable)
        assert table.row_count == 0
        await pilot.press("space")
        await pilot.pause()
        await pilot.press("h")
        await pilot.pause()
        await pilot.press("r")
        await pilot.pause()
        await pilot.press("plus")
        await pilot.pause()
        assert _toasts(app).count("нет ученика в фокусе") == 4


@pytest.mark.asyncio
async def test_group_screen_reload_keeps_cursor(journal_root, course_root):
    app = _app(journal_root, course_root)
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        table = app.screen.query_one("#group", DataTable)
        table.move_cursor(row=1)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, StudentScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, GroupScreen)
        assert app.screen.query_one("#group", DataTable).cursor_row == 1


@pytest.mark.asyncio
async def test_error_screen_on_broken_plan(journal_root, course_root):
    (course_root / "playground" / "2026-09-13" / "session.yml").write_text("theme: [\n", encoding="utf-8")
    app = _app(journal_root, course_root)
    async with app.run_test(size=(120, 30)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, ErrorScreen)
        assert "2026-09-13" in str(app.screen.error)


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
        assert any("открываю roster.yml" in m for m in _toasts(app))
        await pilot.press("q")
