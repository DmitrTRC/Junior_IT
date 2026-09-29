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
