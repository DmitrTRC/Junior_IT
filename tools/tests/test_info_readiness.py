import yaml

from info import readiness
from test_build_course_map import make_module

FULL = dict(shared=("slides.html", "live-code.md"), student=("cheatsheet.html", "glossary.md"))


def _ok(_dir, _root):
    return []


def test_readiness_all_green(tmp_path):
    d = make_module(tmp_path, "python/m-01-first-run", **FULL)
    manifest = yaml.safe_load((d / "module.yml").read_text(encoding="utf-8"))
    manifest["homework"] = "homework/python-01-first-run"
    (d / "module.yml").write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    (tmp_path / "homework" / "python-01-first-run").mkdir(parents=True)
    (tmp_path / "homework" / "python-01-first-run" / "task.md").write_text("x", encoding="utf-8")
    out = readiness.lines(["python/m-01-first-run"], tmp_path, _ok)
    assert out[0].text == "python/m-01-first-run · scenario ✓ live-code ✓ slides ✓ cheatsheet ✓ glossary ✓ · validate ✓"
    assert out[0].style == "ok" and out[0].open == "tracks/python/m-01-first-run/teacher/scenario.md"
    assert out[1].text == "  домашка python-01-first-run: task.md ✓" and out[1].style == "ok"
    assert out[1].open == "homework/python-01-first-run/task.md"


def test_readiness_missing_file_is_warn(tmp_path):
    make_module(tmp_path, "python/m-01-first-run", shared=("slides.html",), student=("cheatsheet.html",))
    out = readiness.lines(["python/m-01-first-run"], tmp_path, _ok)
    assert "live-code ✗" in out[0].text and "glossary ✗" in out[0].text and out[0].style == "warn"
    assert len(out) == 1                                   # домашки в module.yml нет — строки нет


def test_readiness_validate_errors_are_err(tmp_path):
    make_module(tmp_path, "python/m-01-first-run", **FULL)
    out = readiness.lines(["python/m-01-first-run"], tmp_path, lambda d, r: ["битая ссылка requires", "ещё"])
    assert out[0].style == "err" and out[0].text.endswith("· validate ✗ битая ссылка requires")


def test_readiness_missing_module_and_homework(tmp_path):
    d = make_module(tmp_path, "python/m-01-first-run", **FULL)
    manifest = yaml.safe_load((d / "module.yml").read_text(encoding="utf-8"))
    manifest["homework"] = "homework/python-01-first-run"
    (d / "module.yml").write_text(yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8")
    out = readiness.lines(["python/m-01-first-run", "python/m-09-nope"], tmp_path, _ok)
    assert out[1].text == "  домашка python-01-first-run: task.md ✗" and out[1].style == "warn"
    assert out[2].text == "python/m-09-nope · модуля нет" and out[2].style == "err"


def test_readiness_empty_playlist():
    out = readiness.lines([], "/nonexistent", _ok)
    assert len(out) == 1 and out[0].text == "нет плейлиста" and out[0].style == "dim"


def test_readiness_id_without_slash_is_module_missing(tmp_path):
    out = readiness.lines(["python-01-first-run"], tmp_path, _ok)
    assert len(out) == 1
    assert out[0].text == "python-01-first-run · модуля нет" and out[0].style == "err"
