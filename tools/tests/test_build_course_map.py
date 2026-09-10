from datetime import date
from pathlib import Path

import pytest
import yaml

from build_course_map import load_modules, load_sessions, module_statuses

TODAY = date(2026, 9, 12)


def make_module(repo_root, module_id, level="core", minutes=25, textbook=None,
                shared=("slides.html",), student=("cheatsheet.html",)):
    """Модуль на диске: манифест + файлы ролей."""
    track, name = module_id.split("/")
    module_dir = repo_root / "tracks" / track / name
    for role in ("shared", "student", "teacher"):
        (module_dir / role).mkdir(parents=True)
    for f in shared:
        (module_dir / "shared" / f).write_text("x", encoding="utf-8")
    for f in student:
        (module_dir / "student" / f).write_text("x", encoding="utf-8")
    (module_dir / "teacher" / "scenario.md").write_text("x", encoding="utf-8")
    manifest = {
        "id": module_id, "title": f"Тест {name} (test)", "track": track,
        "level": level, "minutes": minutes, "textbook": textbook or [],
    }
    (module_dir / "module.yml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    return module_dir


def make_session(repo_root, day, modules, completed=None, theme="Тема"):
    session_dir = repo_root / "playground" / day.isoformat()
    session_dir.mkdir(parents=True)
    data = {
        "date": day.isoformat(), "theme": theme,
        "playlist": [{"module": m, "minutes": 25} for m in modules],
    }
    if completed is not None:
        data["completed"] = completed
    (session_dir / "session.yml").write_text(
        yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_collects_all_modules_with_fields(tmp_path):
    make_module(tmp_path, "book/m-01-info", textbook=["7:1.1"])
    make_module(tmp_path, "web/m-01-html", level="optional")
    modules = load_modules(tmp_path)
    assert {m["id"] for m in modules} == {"book/m-01-info", "web/m-01-html"}
    info = next(m for m in modules if m["id"] == "book/m-01-info")
    assert info["textbook"] == ["7:1.1"] and info["minutes"] == 25


def test_sessions_sorted_and_dates_parsed(tmp_path):
    make_session(tmp_path, date(2026, 9, 20), ["a/b"])
    make_session(tmp_path, date(2026, 9, 13), ["c/d"])
    sessions = load_sessions(tmp_path)
    assert [s["date"] for s in sessions] == [date(2026, 9, 13), date(2026, 9, 20)]


def test_status_done_for_past_session(tmp_path):
    make_module(tmp_path, "book/m-01-info")
    make_session(tmp_path, date(2026, 9, 10), ["book/m-01-info"])
    statuses = module_statuses(load_modules(tmp_path), load_sessions(tmp_path), TODAY)
    assert statuses["book/m-01-info"] == "done"


def test_status_current_for_next_upcoming_session(tmp_path):
    make_module(tmp_path, "python/m-01-run")
    make_module(tmp_path, "book/m-02-later")
    make_session(tmp_path, date(2026, 9, 13), ["python/m-01-run"])
    make_session(tmp_path, date(2026, 9, 16), ["book/m-02-later"])
    statuses = module_statuses(load_modules(tmp_path), load_sessions(tmp_path), TODAY)
    assert statuses["python/m-01-run"] == "current"
    assert statuses["book/m-02-later"] == "planned"


def test_session_today_is_current(tmp_path):
    make_module(tmp_path, "python/m-01-run")
    make_session(tmp_path, TODAY, ["python/m-01-run"])
    statuses = module_statuses(load_modules(tmp_path), load_sessions(tmp_path), TODAY)
    assert statuses["python/m-01-run"] == "current"


def test_status_planned_when_not_scheduled(tmp_path):
    make_module(tmp_path, "cs/m-01-computer")
    statuses = module_statuses(load_modules(tmp_path), [], TODAY)
    assert statuses["cs/m-01-computer"] == "planned"


def test_status_library_for_optional(tmp_path):
    make_module(tmp_path, "web/m-01-html", level="optional")
    make_session(tmp_path, date(2026, 9, 10), ["web/m-01-html"])
    statuses = module_statuses(load_modules(tmp_path), load_sessions(tmp_path), TODAY)
    assert statuses["web/m-01-html"] == "library"


def test_completed_field_overrides_playlist(tmp_path):
    make_module(tmp_path, "book/m-01-info")
    make_module(tmp_path, "python/m-01-run")
    make_session(tmp_path, date(2026, 9, 10),
                 ["book/m-01-info", "python/m-01-run"],
                 completed=["book/m-01-info"])
    statuses = module_statuses(load_modules(tmp_path), load_sessions(tmp_path), TODAY)
    assert statuses["book/m-01-info"] == "done"
    assert statuses["python/m-01-run"] == "planned"


def test_empty_playground_yields_no_done(tmp_path):
    make_module(tmp_path, "book/m-01-info")
    assert load_sessions(tmp_path) == []
    statuses = module_statuses(load_modules(tmp_path), [], TODAY)
    assert "done" not in statuses.values()
