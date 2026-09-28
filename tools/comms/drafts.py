"""Черновики Zoom-пайплайна (meta/drafts/lesson-<дата>-<HHMM>-analysis.md) -> раздел для поста."""
from __future__ import annotations
import re
from datetime import date
from pathlib import Path

NAME_RE = re.compile(r"^lesson-(\d{4}-\d{2}-\d{2})-\d{4}-analysis\.md$")
SECTION = "## Сообщение в MAX"


def new_drafts(drafts_dir: Path, seen: list[str]) -> list[Path]:
    drafts_dir = Path(drafts_dir)
    if not drafts_dir.is_dir():
        return []
    return sorted(p for p in drafts_dir.iterdir() if NAME_RE.match(p.name) and p.name not in seen)


def max_section(text: str) -> str | None:
    start = text.find(SECTION)
    if start < 0:
        return None
    body = text[start + len(SECTION):]
    nxt = re.search(r"^## ", body, flags=re.MULTILINE)
    return (body[:nxt.start()] if nxt else body).strip() or None


def lesson_date(path: Path) -> date | None:
    match = NAME_RE.match(Path(path).name)
    return date.fromisoformat(match.group(1)) if match else None
