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
