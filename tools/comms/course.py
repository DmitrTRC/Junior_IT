"""Всё, что brain знает про устройство именно этого курса. Для другого курса меняется только этот модуль."""
from __future__ import annotations
from datetime import date
from pathlib import Path

from build_course_map import load_sessions
from build_homework_pages import attachments_for
from journal import store as journal_store


def sessions(repo_root: Path) -> list[dict]:
    return load_sessions(Path(repo_root))


def plan_for(repo_root: Path, day: date) -> dict | None:
    return journal_store.load_plan(day, repo_root)


def homework_ids(plan: dict) -> list[str]:
    return journal_store.hw_ids_from_plan(plan)


def due(plan: dict) -> date | None:
    return journal_store.hw_due_from_plan(plan)


def latest_plan_with_homework(repo_root: Path, today: date) -> tuple[date, dict] | None:
    for day in sorted(journal_store.plan_dates(repo_root), reverse=True):
        if day > today:
            continue
        plan = plan_for(repo_root, day)
        if plan and homework_ids(plan):
            return day, plan
    return None


def task_path(repo_root: Path, hw_id: str) -> Path:
    return Path(repo_root) / "homework" / hw_id / "task.md"


def task_text(repo_root: Path, hw_id: str) -> str:
    path = task_path(repo_root, hw_id)
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def attachments(repo_root: Path, hw_id: str) -> dict[str, bytes]:
    hw_dir = Path(repo_root) / "homework" / hw_id
    if not hw_dir.is_dir():
        return {}
    return {p.name: p.read_bytes() for p in attachments_for(hw_dir)}


def page_url(pages_url: str, hw_id: str) -> str:
    return f"{pages_url.rstrip('/')}/homework/{hw_id}/"


def student_names(students_root) -> dict[str, str]:
    return {s.id: s.name for s in journal_store.load_roster(students_root)}


def drafts_dir(repo_root: Path) -> Path:
    return Path(repo_root) / "meta" / "drafts"
