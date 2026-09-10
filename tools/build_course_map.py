#!/usr/bin/env python3
"""Собирает course-map.json для лендинга из манифестов и журналов занятий.

Единственные источники правды — tracks/*/*/module.yml и
playground/*/session.yml. Атлас и прочие документы не читаются:
меньше парсеров — меньше расхождений.
"""

import json
import sys
from datetime import date
from pathlib import Path

import yaml

POSITIONING = "Углублённая информатика и программирование · 7–8 классы"

TRACKS_META = [
    {"id": "book", "title": "Учебник", "chip": "BOOK"},
    {"id": "python", "title": "Python", "chip": "PY"},
    {"id": "pascal", "title": "Pascal", "chip": "PAS"},
    {"id": "devops", "title": "DevOps", "chip": "OPS"},
    {"id": "cs", "title": "Компьютер изнутри", "chip": "CS"},
    {"id": "web", "title": "Web (архив)", "chip": "WEB"},
]


def load_modules(repo_root):
    modules = []
    for manifest in sorted(Path(repo_root).glob("tracks/*/*/module.yml")):
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        data["_dir"] = manifest.parent
        modules.append(data)
    return modules


def load_sessions(repo_root):
    sessions = []
    for path in sorted(Path(repo_root).glob("playground/*/session.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "date" not in data:
            continue
        data["date"] = date.fromisoformat(str(data["date"]))
        sessions.append(data)
    return sorted(sessions, key=lambda s: s["date"])


def _playlist_ids(session):
    return [item["module"] for item in session.get("playlist") or []]


def module_statuses(modules, sessions, today):
    """id модуля -> done | current | planned | library."""
    done, current = set(), set()
    for session in sessions:
        if session["date"] < today:
            if "completed" in session:
                done.update(session["completed"] or [])
            else:
                done.update(_playlist_ids(session))
    upcoming = [s for s in sessions if s["date"] >= today]
    if upcoming:
        current.update(_playlist_ids(upcoming[0]))

    statuses = {}
    for module in modules:
        mid = module["id"]
        if module.get("level") == "optional":
            statuses[mid] = "library"
        elif mid in done:
            statuses[mid] = "done"
        elif mid in current:
            statuses[mid] = "current"
        else:
            statuses[mid] = "planned"
    return statuses


def main(argv=None):
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
