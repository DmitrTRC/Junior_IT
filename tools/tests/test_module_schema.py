from pathlib import Path

import pytest
import yaml

from module_schema import check_fields, check_layout, check_links, validate_module


def valid_module():
    return {
        "id": "python/m-04-branching",
        "title": "Ветвление (branching): if / elif / else",
        "track": "python",
        "level": "core",
        "minutes": 25,
        "textbook": ["8:3.5", "8:5.4"],
        "terms": [{"ru": "ветвление", "en": "branching"}],
    }


def test_valid_module_has_no_errors():
    assert check_fields(valid_module()) == []


def test_missing_required_field_is_reported():
    data = valid_module()
    del data["minutes"]
    errors = check_fields(data)
    assert any("minutes" in e for e in errors)


def test_unknown_track_is_reported():
    data = valid_module()
    data["track"] = "informatika"
    errors = check_fields(data)
    assert any("informatika" in e for e in errors)


def test_unknown_level_is_reported():
    data = valid_module()
    data["level"] = "hard"
    errors = check_fields(data)
    assert any("hard" in e for e in errors)


def test_minutes_must_be_positive_int():
    data = valid_module()
    data["minutes"] = 0
    assert check_fields(data) != []
    data["minutes"] = "25"
    assert check_fields(data) != []


def test_textbook_reference_format_is_checked():
    data = valid_module()
    data["textbook"] = ["8-3.5"]
    errors = check_fields(data)
    assert any("8-3.5" in e for e in errors)


def test_term_without_english_is_reported():
    data = valid_module()
    data["terms"] = [{"ru": "ветвление"}]
    errors = check_fields(data)
    assert any("en" in e for e in errors)


def test_non_dict_input_is_reported():
    assert check_fields("не словарь") != []


@pytest.fixture
def fake_repo(tmp_path):
    """Мини-репозиторий с одним валидным модулем python/m-01-first-run."""
    module_dir = tmp_path / "tracks" / "python" / "m-01-first-run"
    for role in ("shared", "student", "teacher"):
        (module_dir / role).mkdir(parents=True)
    (tmp_path / "homework" / "python-01-first-run").mkdir(parents=True)
    manifest = {
        "id": "python/m-01-first-run",
        "title": "Первый запуск Python",
        "track": "python",
        "level": "core",
        "minutes": 25,
        "homework": "homework/python-01-first-run",
    }
    (module_dir / "module.yml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8"
    )
    return tmp_path, module_dir


def test_layout_ok_when_all_role_dirs_exist(fake_repo):
    _, module_dir = fake_repo
    assert check_layout(module_dir) == []


def test_missing_role_dir_is_reported(fake_repo):
    _, module_dir = fake_repo
    (module_dir / "teacher").rmdir()
    errors = check_layout(module_dir)
    assert any("teacher" in e for e in errors)


def test_id_must_match_path(fake_repo):
    repo_root, module_dir = fake_repo
    data = {"id": "python/m-99-wrong"}
    errors = check_links(data, module_dir, repo_root)
    assert any("m-99-wrong" in e for e in errors)


def test_missing_dependency_is_reported(fake_repo):
    repo_root, module_dir = fake_repo
    data = {"id": "python/m-01-first-run", "requires": ["python/m-00-nonexistent"]}
    errors = check_links(data, module_dir, repo_root)
    assert any("m-00-nonexistent" in e for e in errors)


def test_missing_homework_path_is_reported(fake_repo):
    repo_root, module_dir = fake_repo
    data = {"id": "python/m-01-first-run", "homework": "homework/nope"}
    errors = check_links(data, module_dir, repo_root)
    assert any("homework/nope" in e for e in errors)


def test_validate_module_accepts_good_module(fake_repo):
    repo_root, module_dir = fake_repo
    assert validate_module(module_dir, repo_root) == []


def test_validate_module_reports_missing_manifest(tmp_path):
    module_dir = tmp_path / "tracks" / "python" / "m-02-io"
    module_dir.mkdir(parents=True)
    errors = validate_module(module_dir, tmp_path)
    assert any("module.yml" in e for e in errors)


def test_validate_module_reports_broken_yaml(fake_repo):
    repo_root, module_dir = fake_repo
    (module_dir / "module.yml").write_text("id: [unclosed", encoding="utf-8")
    errors = validate_module(module_dir, repo_root)
    assert errors != []
