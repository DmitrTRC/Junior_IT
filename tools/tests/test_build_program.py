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
