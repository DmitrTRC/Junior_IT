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
        if not isinstance(data, dict):
            raise ValueError(f"битый манифест: {manifest}")
        data["_dir"] = manifest.parent
        modules.append(data)
    return modules


def load_sessions(repo_root):
    sessions = []
    for path in sorted(Path(repo_root).glob("playground/*/session.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "date" not in data:
            raise ValueError(f"битый журнал занятия: {path} — нет поля date или не словарь")
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


def completion_dates(sessions, today):
    """id модуля -> дата первого прошедшего занятия, где он завершён."""
    dates = {}
    for session in sessions:
        if session["date"] >= today:
            continue
        done_ids = (session["completed"] or []) if "completed" in session \
            else _playlist_ids(session)
        for mid in done_ids:
            dates.setdefault(mid, session["date"])
    return dates


def module_links(module):
    """Ссылки только на реально существующие публикуемые файлы."""
    module_dir = module["_dir"]
    rel = f"tracks/{module['id']}"
    links = {}
    if (module_dir / "shared" / "slides.html").is_file():
        links["slides"] = f"{rel}/shared/slides.html"
    if (module_dir / "student" / "cheatsheet.html").is_file():
        links["cheatsheet"] = f"{rel}/student/cheatsheet.html"
    return links


def build_course_map(repo_root, today):
    modules = load_modules(repo_root)
    sessions = load_sessions(repo_root)
    statuses = module_statuses(modules, sessions, today)
    dates = completion_dates(sessions, today)

    track_ids = {t["id"] for t in TRACKS_META}

    out_modules = []
    for m in modules:
        if m["track"] not in track_ids:
            raise ValueError(f"модуль {m['id']}: неизвестный трек {m['track']!r}")
        out_modules.append({
            "id": m["id"], "track": m["track"], "title": m["title"],
            "level": m["level"], "minutes": m["minutes"],
            "textbook": m.get("textbook") or [],
            "status": statuses[m["id"]],
            "links": module_links(m),
            "completed_on": dates[m["id"]].isoformat() if m["id"] in dates else None,
        })

    upcoming = [s for s in sessions if s["date"] >= today]
    next_session = None
    if upcoming:
        s = upcoming[0]
        next_session = {"date": s["date"].isoformat(),
                        "theme": s.get("theme", ""),
                        "modules": _playlist_ids(s)}

    done = [m for m in out_modules if m["status"] == "done"]
    core_total = sum(1 for m in out_modules if m["level"] in ("core", "deep"))
    paragraphs = {ref for m in done for ref in m["textbook"]}

    return {
        "generated_at": today.isoformat(),
        "positioning": POSITIONING,
        "tracks": TRACKS_META,
        "modules": out_modules,
        "next_session": next_session,
        "counters": {"modules_done": len(done),
                     "modules_core_total": core_total,
                     "paragraphs_closed": len(paragraphs)},
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    repo_root = Path(args[0]) if args else Path(__file__).resolve().parent.parent
    out_path = Path(args[1]) if len(args) > 1 else repo_root / "course-map.json"
    try:
        course_map = build_course_map(repo_root, date.today())
    except (yaml.YAMLError, KeyError, ValueError) as exc:
        broken = [p.parent.name for p in Path(repo_root).glob("tracks/*/*/module.yml")]
        print(f"course-map: не удалось собрать карту ({exc}); "
              f"модули: {broken}", file=sys.stderr)
        return 1
    out_path.write_text(
        json.dumps(course_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(f"карта курса: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
