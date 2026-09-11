import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from build_course_map import build_course_map, load_modules, load_sessions, main, module_statuses

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


def test_links_only_existing_files(tmp_path):
    make_module(tmp_path, "book/m-01-info", student=())  # нет шпаргалки
    result = build_course_map(tmp_path, TODAY)
    module = result["modules"][0]
    assert module["links"] == {"slides": "tracks/book/m-01-info/shared/slides.html"}


def test_links_never_teacher_or_livecode(tmp_path):
    make_module(tmp_path, "book/m-01-info",
                shared=("slides.html", "live-code.md"))
    result = build_course_map(tmp_path, TODAY)
    dumped = json.dumps(result)
    assert "teacher/" not in dumped
    assert "live-code.md" not in dumped


def test_counters(tmp_path):
    make_module(tmp_path, "book/m-01-info", textbook=["7:1.1"])
    make_module(tmp_path, "devops/m-01-term", textbook=["7:2.3"])
    make_module(tmp_path, "web/m-01-html", level="optional")
    make_session(tmp_path, date(2026, 9, 10),
                 ["book/m-01-info", "devops/m-01-term"])
    counters = build_course_map(tmp_path, TODAY)["counters"]
    assert counters == {"modules_done": 2, "modules_core_total": 2,
                        "paragraphs_closed": 2}


def test_next_session_earliest_future(tmp_path):
    make_module(tmp_path, "python/m-01-run")
    make_session(tmp_path, date(2026, 9, 16), ["python/m-01-run"], theme="Git")
    make_session(tmp_path, date(2026, 9, 20), ["python/m-01-run"])
    ns = build_course_map(tmp_path, TODAY)["next_session"]
    assert ns["date"] == "2026-09-16" and ns["theme"] == "Git"
    assert ns["modules"] == ["python/m-01-run"]


def test_no_future_session_gives_null(tmp_path):
    make_module(tmp_path, "book/m-01-info")
    make_session(tmp_path, date(2026, 9, 10), ["book/m-01-info"])
    assert build_course_map(tmp_path, TODAY)["next_session"] is None


def test_main_writes_valid_json(tmp_path):
    make_module(tmp_path, "book/m-01-info")
    out = tmp_path / "course-map.json"
    assert main([str(tmp_path), str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["positioning"].startswith("Углублённая")
    assert "generated_at" in data
    assert [t["id"] for t in data["tracks"]] == \
        ["book", "python", "pascal", "devops", "cs", "web"]


def test_main_fails_loudly_on_broken_manifest(tmp_path, capsys):
    module_dir = tmp_path / "tracks" / "book" / "m-01-bad"
    module_dir.mkdir(parents=True)
    (module_dir / "module.yml").write_text("id: [unclosed", encoding="utf-8")
    assert main([str(tmp_path), str(tmp_path / "out.json")]) == 1
    assert "m-01-bad" in capsys.readouterr().err


def test_broken_session_fails_loudly(tmp_path):
    make_module(tmp_path, "book/m-01-info")
    session_dir = tmp_path / "playground" / "2026-09-10"
    session_dir.mkdir(parents=True)
    (session_dir / "session.yml").write_text("- просто список\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_sessions(tmp_path)


def test_unknown_track_fails_loudly(tmp_path):
    make_module(tmp_path, "algo/m-01-sort")
    with pytest.raises(ValueError):
        build_course_map(tmp_path, TODAY)


def test_broken_manifest_fails_loudly(tmp_path):
    module_dir = tmp_path / "tracks" / "book" / "m-01-bad"
    module_dir.mkdir(parents=True)
    (module_dir / "module.yml").write_text("- просто список\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_modules(tmp_path)
