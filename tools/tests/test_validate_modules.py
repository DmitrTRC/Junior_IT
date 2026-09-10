import yaml

from validate_modules import iter_module_dirs, main


def make_module(repo_root, track, name, manifest=None):
    module_dir = repo_root / "tracks" / track / name
    for role in ("shared", "student", "teacher"):
        (module_dir / role).mkdir(parents=True)
    data = manifest or {
        "id": f"{track}/{name}",
        "title": "Тестовый модуль",
        "track": track,
        "level": "core",
        "minutes": 20,
    }
    (module_dir / "module.yml").write_text(
        yaml.safe_dump(data, allow_unicode=True), encoding="utf-8"
    )
    return module_dir


def test_iter_finds_modules_sorted(tmp_path):
    make_module(tmp_path, "python", "m-02-io")
    make_module(tmp_path, "book", "m-01-information")
    found = [d.name for d in iter_module_dirs(tmp_path)]
    assert found == ["m-01-information", "m-02-io"]


def test_iter_returns_empty_without_tracks_dir(tmp_path):
    assert iter_module_dirs(tmp_path) == []


def test_main_returns_zero_when_all_modules_valid(tmp_path):
    make_module(tmp_path, "python", "m-01-first-run")
    assert main([str(tmp_path)]) == 0


def test_main_returns_one_when_module_broken(tmp_path):
    make_module(
        tmp_path,
        "python",
        "m-01-first-run",
        manifest={"id": "python/m-01-first-run", "track": "python"},
    )
    assert main([str(tmp_path)]) == 1


def test_main_prints_module_name_and_error(tmp_path, capsys):
    make_module(
        tmp_path,
        "python",
        "m-01-first-run",
        manifest={"id": "python/m-01-first-run", "track": "wrong"},
    )
    main([str(tmp_path)])
    out = capsys.readouterr().out
    assert "m-01-first-run" in out
    assert "wrong" in out
