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
from journal.model import JournalError, LessonRecord, num  # noqa: E402

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
            stats.collect(self.root, self.repo_root, self.today)
            store.load_tariff(self.root)
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
        else:
            self.say(f"открываю {path.name}")


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
        keep = table.cursor_row
        table.clear()
        g = stats.collect(app.root, app.repo_root, app.today)
        lessons = store.load_lessons(app.root)[-HISTORY:]
        for s in g.students:
            glyphs = "".join(GLYPH.get(rec.attendance.get(s.id), "·") for rec in lessons)
            tails = Text(str(len(s.tails)), style="yellow" if s.tails else "dim")
            table.add_row(s.name, glyphs, str(num(s.points_total)), f"{s.hw_accepted}/{s.hw_issued}", tails, key=s.id)
        if keep is not None and table.row_count:
            table.move_cursor(row=min(keep, table.row_count - 1))
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
        full = store.load_roster(app.root)
        self.rec = store.load_lesson(self.day, app.root, full) or LessonRecord(date=self.day)
        roster = [s for s in full if s.status == "active"]
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
            self.app.say("нет ученика в фокусе", "warning")
            return
        new = ATTEND_CYCLE[self.rec.attendance.get(sid)]
        if self._do(ops.mark_attendance, self.day, sid, new, self.app.root):
            self.app.say(f"{sid}: {new}")

    def action_hw_next(self) -> None:
        sid = _selected_key(self.query_one(DataTable))
        if sid is None:
            self.app.say("нет ученика в фокусе", "warning")
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
            self.app.say("нет ученика в фокусе", "warning")
            return
        ids = self._hw_ids(sid)
        if not ids:
            self.app.say(f"{sid}: домашка не выдана", "warning")
            return
        for hid in ids:
            if self._do(ops.set_homework, self.day, hid, sid, "rework", None, self.app.root, self.app.today):
                self.app.say(f"{hid} {sid}: rework")

    def _prompt(self, mode: str, placeholder: str) -> None:
        sid = _selected_key(self.query_one(DataTable))
        if sid is None:
            self.app.say("нет ученика в фокусе", "warning")
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
