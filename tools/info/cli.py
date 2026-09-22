#!/usr/bin/env python3
"""info — провайдеры боксов info-панели. Печатает JSON lines по контракту command."""
from __future__ import annotations
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tools/

import yaml  # noqa: E402

from build_course_map import load_modules, load_sessions  # noqa: E402
from info import common, course, homework, lesson, readiness, students  # noqa: E402
from info.common import Line, emit  # noqa: E402
from journal import stats as journal_stats  # noqa: E402
from journal import store as journal_store  # noqa: E402
from journal.model import JournalError  # noqa: E402
from module_schema import validate_module  # noqa: E402

BOXES = ("lesson", "students", "homework", "readiness", "course")


def _playlist_ids(session: dict | None) -> list[str]:
    if not session:
        return []
    return [str(item["module"]) for item in session.get("playlist") or []
            if isinstance(item, dict) and item.get("module")]


def build(box: str, repo_root, students_root, today: date) -> list[Line]:
    repo_root = Path(repo_root)
    if box == "lesson":
        session, stale = common.next_session(load_sessions(repo_root), today)
        return lesson.lines(session, stale, today, repo_root)
    if box == "course":
        return course.lines(load_modules(repo_root), load_sessions(repo_root), today)
    if box == "readiness":
        session, _ = common.next_session(load_sessions(repo_root), today)
        return readiness.lines(_playlist_ids(session), repo_root, validate_module)
    roster_path = journal_store.students_root(students_root) / "roster.yml"
    if box == "students":
        group = journal_stats.collect(students_root, repo_root, today) if roster_path.exists() else None
        return students.lines(group)
    if box == "homework":
        lessons = []
        active = None
        if roster_path.exists():
            roster = journal_store.load_roster(students_root)
            lessons = journal_store.load_lessons(students_root, roster)
            active = {s.id for s in roster if s.status == "active"}
        session, _ = common.next_session(load_sessions(repo_root), today)
        return homework.lines(lessons, journal_stats.load_plans(repo_root), today, session, active_ids=active)
    raise ValueError(f"неизвестный бокс {box!r}")


def run(argv, today: date | None = None) -> int:
    ap = argparse.ArgumentParser(prog="info")
    ap.add_argument("box", choices=BOXES)
    ap.add_argument("--today", type=date.fromisoformat)
    ap.add_argument("--repo", help="корень репо (по умолчанию — этот)")
    ap.add_argument("--students", help="каталог students/ (по умолчанию <repo>/students или $JUNIOR_IT_STUDENTS)")
    args = ap.parse_args(argv)
    day = args.today or today or date.today()
    students_root = args.students or (str(Path(args.repo) / "students") if args.repo else None)
    try:
        emit(build(args.box, args.repo or common.REPO_ROOT, students_root, day))
    except (JournalError, ValueError, yaml.YAMLError, KeyError) as exc:
        print(f"info: {str(exc).splitlines()[0] if str(exc) else type(exc).__name__}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
