from __future__ import annotations
import os
import tempfile
from datetime import date
from pathlib import Path

import yaml

from journal.model import (
    JournalError, LessonRecord, Student, Tariff,
    lesson_to_dict, parse_lesson, parse_roster, parse_tariff,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def students_root(root=None) -> Path:
    if root is not None:
        return Path(root)
    env = os.environ.get("JUNIOR_IT_STUDENTS")
    return Path(env) if env else REPO_ROOT / "students"


def _load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise JournalError(f"{path}: битый YAML — {exc}", path) from exc


def load_roster(root=None) -> list[Student]:
    path = students_root(root) / "roster.yml"
    if not path.exists():
        raise JournalError(f"нет {path}", path)
    return parse_roster(_load_yaml(path), str(path))


def load_tariff(root=None) -> Tariff:
    path = students_root(root) / "points.yml"
    if not path.exists():
        return Tariff()
    return parse_tariff(_load_yaml(path))


def lesson_path(day: date, root=None) -> Path:
    return students_root(root) / "journal" / f"{day.isoformat()}.yml"


def _ids(root, roster) -> set[str]:
    return {s.id for s in (roster if roster is not None else load_roster(root))}


def load_lesson(day: date, root=None, roster=None) -> LessonRecord | None:
    path = lesson_path(day, root)
    if not path.exists():
        return None
    return parse_lesson(_load_yaml(path), day, _ids(root, roster), str(path))


def load_lessons(root=None, roster=None) -> list[LessonRecord]:
    ids = _ids(root, roster)
    lessons: list[LessonRecord] = []
    for path in sorted((students_root(root) / "journal").glob("*.yml")):
        try:
            day = date.fromisoformat(path.stem)
        except ValueError:
            raise JournalError(f"{path}: имя файла не дата", path) from None
        lessons.append(parse_lesson(_load_yaml(path), day, ids, str(path)))
    return lessons


def save_lesson(rec: LessonRecord, root=None) -> Path:
    path = lesson_path(rec.date, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(lesson_to_dict(rec), allow_unicode=True, sort_keys=False)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".yml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return path


def load_plan(day: date, repo_root=None) -> dict | None:
    """План занятия из playground/<дата>/session.yml; None, если плана нет."""
    path = Path(repo_root or REPO_ROOT) / "playground" / day.isoformat() / "session.yml"
    if not path.exists():
        return None
    data = _load_yaml(path)
    return data if isinstance(data, dict) else None


def plan_dates(repo_root=None) -> list[date]:
    dates: list[date] = []
    for path in sorted((Path(repo_root or REPO_ROOT) / "playground").glob("*/session.yml")):
        try:
            dates.append(date.fromisoformat(path.parent.name))
        except ValueError:
            continue
    return dates


def hw_ids_from_plan(plan: dict) -> list[str]:
    items = (plan.get("homework") or {}).get("items") or []
    return [str(item).rstrip("/").split("/")[-1] for item in items]


def hw_due_from_plan(plan: dict) -> date | None:
    due = (plan.get("homework") or {}).get("due")
    if not due:
        return None
    return due if isinstance(due, date) else date.fromisoformat(str(due))
