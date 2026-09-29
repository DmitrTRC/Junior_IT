#!/usr/bin/env python3
"""Собирает program.json — программу курса на год — из meta/program.yml.

Существующие модули берутся из tracks/*/*/module.yml и карты курса
(статусы), будущие описаны прямо в program.yml полями title и track.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml

from build_course_map import TRACKS_META, load_modules, load_sessions, module_links, module_statuses

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
TEXTBOOK_RE = re.compile(r"^(?P<grade>\d{1,2}):(?P<chapter>\d+)(?:\.(?P<paragraph>\d+))?$")
MONTH_NAMES = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
               "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
TRACK_IDS = {t["id"] for t in TRACKS_META}
ARCHIVE_TRACKS = {"web"}
REQUIRED_TOP = ("year", "goal", "disclaimer", "next_year", "principles", "blocks")
REQUIRED_BLOCK = ("month", "title", "outcome", "why")
LIST_FIELDS = ("modules", "textbook", "trainer", "events")


def textbook_label(ref):
    match = TEXTBOOK_RE.match(str(ref))
    if not match:
        raise ValueError(f"ссылка на учебник не по формату grade:chapter[.paragraph]: {ref!r}")
    grade, chapter, paragraph = match.group("grade", "chapter", "paragraph")
    if paragraph is None:
        return f"{grade} кл гл. {chapter}"
    return f"{grade} кл §{chapter}.{paragraph}"


def month_label(month):
    return MONTH_NAMES[int(month[5:7]) - 1]


def block_status(month, today):
    current = today.strftime("%Y-%m")
    if month < current:
        return "done"
    return "current" if month == current else "upcoming"


def load_program(repo_root):
    path = Path(repo_root) / "meta" / "program.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"битая программа: {path}")
    missing = [key for key in REQUIRED_TOP if not data.get(key)]
    if missing:
        raise ValueError(f"program.yml: пустые или отсутствующие поля {missing}")
    for key in ("student", "parents"):
        if not data["goal"].get(key):
            raise ValueError(f"program.yml: goal.{key} пустой")
    months = []
    for block in data["blocks"]:
        missing = [key for key in REQUIRED_BLOCK if not block.get(key)]
        if missing:
            raise ValueError(f"program.yml: блок {block.get('month')!r} без полей {missing}")
        month = str(block["month"])
        if not MONTH_RE.match(month):
            raise ValueError(f"program.yml: месяц не по формату YYYY-MM: {month!r}")
        block["month"] = month
        for key in LIST_FIELDS:
            block[key] = list(block.get(key) or [])
        if not block["modules"] and not block["events"]:
            raise ValueError(f"program.yml: блок {month} без модулей и без событий")
        months.append(month)
    if len(set(months)) != len(months):
        raise ValueError("program.yml: месяцы должны быть уникальны")
    if months != sorted(months):
        raise ValueError("program.yml: месяцы должны идти по возрастанию")
    return data


def resolve_module(entry, modules_by_id, statuses):
    if isinstance(entry, str):
        entry = {"id": entry}
    if not isinstance(entry, dict) or not entry.get("id"):
        raise ValueError(f"program.yml: модуль без id: {entry!r}")
    module_id = str(entry["id"])
    existing = modules_by_id.get(module_id)
    if existing is not None:
        extra = [key for key in ("title", "track") if key in entry]
        if extra:
            raise ValueError(f"program.yml: {module_id} есть в tracks/, поля {extra} лишние")
        return {"id": module_id, "title": existing["title"], "track": existing["track"],
                "status": statuses[module_id], "minutes": existing["minutes"],
                "links": module_links(existing)}
    missing = [key for key in ("title", "track") if not entry.get(key)]
    if missing:
        raise ValueError(f"program.yml: будущий модуль {module_id} без полей {missing}")
    track = entry["track"]
    if track not in TRACK_IDS:
        raise ValueError(f"program.yml: {module_id}: неизвестный трек {track!r}")
    if not module_id.startswith(track + "/"):
        raise ValueError(f"program.yml: {module_id}: id не совпадает с треком {track!r}")
    return {"id": module_id, "title": entry["title"], "track": track,
            "status": "planned", "minutes": None, "links": {}}


def build_program(repo_root, today):
    program = load_program(repo_root)
    modules = load_modules(repo_root)
    sessions = load_sessions(repo_root)
    statuses = module_statuses(modules, sessions, today)
    modules_by_id = {m["id"]: m for m in modules}

    blocks, seen = [], set()
    for block in program["blocks"]:
        resolved = [resolve_module(entry, modules_by_id, statuses) for entry in block["modules"]]
        for module in resolved:
            if module["id"] in seen:
                raise ValueError(f"program.yml: модуль {module['id']} встречается дважды")
            seen.add(module["id"])
        blocks.append({
            "month": block["month"], "label": month_label(block["month"]),
            "status": block_status(block["month"], today),
            "title": block["title"], "outcome": block["outcome"], "why": block["why"],
            "textbook": [{"ref": ref, "label": textbook_label(ref)} for ref in block["textbook"]],
            "trainer": [{"ref": ref, "label": textbook_label(ref)} for ref in block["trainer"]],
            "events": block["events"], "modules": resolved,
        })
    core = [m["id"] for m in modules
            if m["level"] in ("core", "deep") and m["track"] not in ARCHIVE_TRACKS]
    forgotten = sorted(set(core) - seen)
    if forgotten:
        raise ValueError(f"program.yml: модули из tracks/ не вошли в программу: {forgotten}")
    return {
        "generated_at": today.isoformat(), "year": program["year"], "goal": program["goal"],
        "disclaimer": program["disclaimer"], "next_year": program["next_year"],
        "principles": list(program["principles"]),
        "current_month": today.strftime("%Y-%m"),
        "blocks": blocks,
    }


def program_text(program, view):
    if view not in ("student", "parents"):
        raise ValueError(f"ракурс должен быть student или parents: {view!r}")
    lines = [f"Программа Junior_IT {program['year']}", program["goal"][view], program["disclaimer"], ""]
    for block in program["blocks"]:
        lines.append(f"{block['label']} — {block['title']}")
        if view == "parents":
            lines.append(block["outcome"])
            refs = [item["label"] for item in block["textbook"]]
            if refs:
                lines.append("Учебник: " + ", ".join(refs))
        else:
            lines.extend(f"- {module['title']}" for module in block["modules"])
            lines.extend(f"- {event}" for event in block["events"])
        lines.append("")
    if view == "parents":
        lines.append(program["next_year"])
    return "\n".join(lines).rstrip() + "\n"


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    view = None
    if "--text" in args:
        at = args.index("--text")
        if at + 1 >= len(args):
            print("usage: build_program.py <repo_root> [<out_dir>] [--text student|parents]", file=sys.stderr)
            return 2
        view = args[at + 1]
        del args[at:at + 2]
    repo_root = Path(args[0]) if args else Path(__file__).resolve().parent.parent
    try:
        program = build_program(repo_root, date.today())
        if view is not None:
            print(program_text(program, view), end="")
            return 0
    except (yaml.YAMLError, KeyError, ValueError, OSError) as exc:
        print(f"program: не удалось собрать программу ({exc})", file=sys.stderr)
        return 1
    out_dir = Path(args[1]) if len(args) > 1 else repo_root
    out_path = out_dir / "program.json"
    out_path.write_text(json.dumps(program, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"программа курса: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
