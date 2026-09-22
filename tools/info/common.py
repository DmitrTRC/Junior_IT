from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TUI_CMD = "tools/.venv/bin/python tools/journal/tui.py"
PAGES_URL = "https://dmitrtrc.github.io/Junior_IT/"
WEEKDAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


@dataclass(frozen=True)
class Line:
    text: str
    open: str | None = None
    style: str | None = None


def emit(lines, out=None) -> None:
    payload = {"lines": [{"text": line.text, "open": line.open, "style": line.style} for line in lines]}
    print(json.dumps(payload, ensure_ascii=False), file=out)


def next_session(sessions, today: date) -> tuple[dict | None, bool]:
    """Ближайший план (дата >= today); нет — последний прошедший и stale=True; нет планов — (None, False)."""
    upcoming = [s for s in sessions if s["date"] >= today]
    if upcoming:
        return min(upcoming, key=lambda s: s["date"]), False
    if sessions:
        return max(sessions, key=lambda s: s["date"]), True
    return None, False


def countdown(day: date, today: date) -> str:
    delta = (day - today).days
    if delta == 0:
        return "сегодня"
    if delta == 1:
        return "завтра"
    if delta > 1:
        return f"через {delta} дн."
    return f"{-delta} дн. назад"


def weekday_ru(day: date) -> str:
    return WEEKDAYS[day.weekday()]


def fmt_day(day: date) -> str:
    return day.strftime("%d.%m")


def as_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def hw_id_from_ref(ref) -> str:
    return str(ref).rstrip("/").split("/")[-1]


def module_dir(module_id: str, repo_root=REPO_ROOT) -> Path:
    track, _, name = str(module_id).partition("/")
    return Path(repo_root) / "tracks" / track / name


def scenario_target(module_id: str, repo_root=REPO_ROOT) -> str:
    """open-цель модуля относительно корня: teacher/scenario.md, иначе module.yml."""
    directory = module_dir(module_id, repo_root)
    rel = directory.relative_to(Path(repo_root))
    if (directory / "teacher" / "scenario.md").is_file():
        return str(rel / "teacher" / "scenario.md")
    return str(rel / "module.yml")


def homework_task(hw_id: str) -> str:
    return f"homework/{hw_id}/task.md"
