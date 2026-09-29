import json
from datetime import date
from pathlib import Path

import pytest
import yaml

from build_program import block_status, load_program, month_label, textbook_label

TODAY = date(2026, 10, 5)


def program_yaml(blocks, **over):
    data = {
        "year": "2026/27",
        "goal": {"student": "Своя программа на GitHub.", "parents": "Ребёнок пишет программы на Python."},
        "disclaimer": "Программа живая: темп подстраивается под учеников.",
        "next_year": "Восьмой класс: Python глубже.",
        "principles": ["Учебник с опережением школы."],
        "blocks": blocks,
    }
    data.update(over)
    return data


def write_program(repo_root, blocks, **over):
    meta = repo_root / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "program.yml").write_text(
        yaml.safe_dump(program_yaml(blocks, **over), allow_unicode=True), encoding="utf-8")


def block(month, modules=(), events=(), **over):
    data = {"month": month, "title": f"Тема {month}", "outcome": f"Результат {month}",
            "why": f"Потому что {month}", "modules": list(modules), "events": list(events)}
    data.update(over)
    return data


def test_textbook_labels():
    assert textbook_label("7:1.2") == "7 кл §1.2"
    assert textbook_label("8:1") == "8 кл гл. 1"
    with pytest.raises(ValueError):
        textbook_label("глава 1")


def test_month_label_and_block_status_across_year_boundary():
    assert month_label("2026-10") == "Октябрь"
    assert month_label("2027-01") == "Январь"
    assert block_status("2026-09", TODAY) == "done"
    assert block_status("2026-10", TODAY) == "current"
    assert block_status("2027-01", date(2026, 12, 20)) == "upcoming"


def test_load_program_normalizes_lists(tmp_path):
    write_program(tmp_path, [block("2026-10", modules=["python/m-02-variables"])])
    program = load_program(tmp_path)
    first = program["blocks"][0]
    assert first["month"] == "2026-10"
    assert first["textbook"] == [] and first["trainer"] == [] and first["events"] == []
    assert first["modules"] == ["python/m-02-variables"]


def test_load_program_rejects_unordered_or_duplicate_months(tmp_path):
    write_program(tmp_path, [block("2026-11", events=["x"]), block("2026-10", events=["x"])])
    with pytest.raises(ValueError, match="по возрастанию"):
        load_program(tmp_path)
    write_program(tmp_path, [block("2026-10", events=["x"]), block("2026-10", events=["y"])])
    with pytest.raises(ValueError, match="уникальн"):
        load_program(tmp_path)


def test_load_program_requires_modules_or_events(tmp_path):
    write_program(tmp_path, [block("2027-05")])
    with pytest.raises(ValueError, match="без модулей и без событий"):
        load_program(tmp_path)
    write_program(tmp_path, [block("2027-05", events=["демо-день"])])
    assert load_program(tmp_path)["blocks"][0]["events"] == ["демо-день"]


def test_load_program_requires_top_fields_and_month_format(tmp_path):
    write_program(tmp_path, [block("2026-10", events=["x"])], disclaimer="")
    with pytest.raises(ValueError, match="disclaimer"):
        load_program(tmp_path)
    write_program(tmp_path, [block("октябрь", events=["x"])])
    with pytest.raises(ValueError, match="YYYY-MM"):
        load_program(tmp_path)


from build_program import build_program  # noqa: E402


def make_module(repo_root, module_id, level="core", minutes=25):
    track, name = module_id.split("/")
    module_dir = repo_root / "tracks" / track / name
    (module_dir / "shared").mkdir(parents=True)
    (module_dir / "student").mkdir()
    (module_dir / "shared" / "slides.html").write_text("x", encoding="utf-8")
    (module_dir / "student" / "cheatsheet.html").write_text("x", encoding="utf-8")
    manifest = {"id": module_id, "title": f"Тест {name} (test)", "track": track,
                "level": level, "minutes": minutes, "textbook": []}
    (module_dir / "module.yml").write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    return module_dir


def make_session(repo_root, day, modules):
    session_dir = repo_root / "playground" / day.isoformat()
    session_dir.mkdir(parents=True)
    data = {"date": day.isoformat(), "theme": "Тема",
            "playlist": [{"module": m, "minutes": 25} for m in modules]}
    (session_dir / "session.yml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_existing_module_resolves_from_manifest_and_map(tmp_path):
    make_module(tmp_path, "python/m-01-first-run")
    make_session(tmp_path, date(2026, 9, 27), ["python/m-01-first-run"])
    write_program(tmp_path, [block("2026-09", modules=["python/m-01-first-run"], textbook=["8:5.1"])])
    program = build_program(tmp_path, TODAY)
    assert program["current_month"] == "2026-10"
    first = program["blocks"][0]
    assert first["label"] == "Сентябрь" and first["status"] == "done"
    assert first["textbook"] == [{"ref": "8:5.1", "label": "8 кл §5.1"}]
    module = first["modules"][0]
    assert module["title"] == "Тест m-01-first-run (test)" and module["track"] == "python"
    assert module["status"] == "done" and module["minutes"] == 25
    assert module["links"]["cheatsheet"] == "tracks/python/m-01-first-run/student/cheatsheet.html"


def test_future_module_needs_title_and_track(tmp_path):
    write_program(tmp_path, [block("2026-10", modules=["python/m-02-variables"])])
    with pytest.raises(ValueError, match="python/m-02-variables"):
        build_program(tmp_path, TODAY)
    write_program(tmp_path, [block("2026-10", modules=[
        {"id": "python/m-02-variables", "title": "Переменные (variables)", "track": "python"}])])
    module = build_program(tmp_path, TODAY)["blocks"][0]["modules"][0]
    assert module == {"id": "python/m-02-variables", "title": "Переменные (variables)",
                      "track": "python", "status": "planned", "minutes": None, "links": {}}


def test_future_module_track_must_be_known_and_match_id(tmp_path):
    write_program(tmp_path, [block("2026-10", modules=[
        {"id": "python/m-02-variables", "title": "x", "track": "devops"}])])
    with pytest.raises(ValueError, match="не совпадает с треком"):
        build_program(tmp_path, TODAY)
    write_program(tmp_path, [block("2026-10", modules=[
        {"id": "ruby/m-01-start", "title": "x", "track": "ruby"}])])
    with pytest.raises(ValueError, match="неизвестный трек"):
        build_program(tmp_path, TODAY)


def test_existing_module_with_title_in_program_is_an_error(tmp_path):
    make_module(tmp_path, "python/m-01-first-run")
    write_program(tmp_path, [block("2026-09", modules=[
        {"id": "python/m-01-first-run", "title": "Другое имя", "track": "python"}])])
    with pytest.raises(ValueError, match="лишние"):
        build_program(tmp_path, TODAY)


def test_every_core_module_must_appear_once(tmp_path):
    make_module(tmp_path, "python/m-01-first-run")
    make_module(tmp_path, "devops/m-01-terminal-first-steps")
    make_module(tmp_path, "web/m-01-html-css", level="library")
    write_program(tmp_path, [block("2026-09", modules=["python/m-01-first-run"])])
    with pytest.raises(ValueError, match="devops/m-01-terminal-first-steps"):
        build_program(tmp_path, TODAY)
    write_program(tmp_path, [block("2026-09", modules=["python/m-01-first-run", "devops/m-01-terminal-first-steps"]),
                             block("2026-10", modules=["python/m-01-first-run"])])
    with pytest.raises(ValueError, match="дважды"):
        build_program(tmp_path, TODAY)
