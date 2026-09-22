import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

from conftest import TODAY
from info.cli import BOXES, run
from journal import store as journal_store
from test_build_course_map import make_module

CLI = Path(__file__).resolve().parents[1] / "info" / "cli.py"


@pytest.fixture
def repo(course_root):
    """course_root + модуль плейлиста 20.09 + домашка → полный фикстурный репо."""
    make_module(course_root, "python/m-01-first-run",
                shared=("slides.html", "live-code.md"), student=("cheatsheet.html", "glossary.md"))
    plan_path = course_root / "playground" / "2026-09-20" / "session.yml"
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    plan["playlist"] = [{"module": "python/m-01-first-run", "minutes": 25}]
    plan_path.write_text(yaml.safe_dump(plan, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (course_root / "homework" / "python-01-first-run").mkdir(parents=True)
    (course_root / "homework" / "python-01-first-run" / "task.md").write_text("x", encoding="utf-8")
    return course_root


def _run(box, repo, students, capsys, today=date(2026, 9, 19)):
    code = run([box, "--repo", str(repo), "--students", str(students), "--today", today.isoformat()])
    out = capsys.readouterr()
    return code, out


@pytest.mark.parametrize("box", BOXES)
def test_every_box_emits_lines(box, repo, journal_root, capsys):
    code, out = _run(box, repo, journal_root, capsys)
    assert code == 0, out.err
    data = json.loads(out.out)
    assert data["lines"] and all({"text", "open", "style"} <= set(l) for l in data["lines"])


def test_lesson_box_points_to_plan(repo, journal_root, capsys):
    _, out = _run("lesson", repo, journal_root, capsys)
    lines = json.loads(out.out)["lines"]
    assert lines[0]["open"] == "playground/2026-09-20/session.yml" and "завтра" in lines[0]["text"]
    assert any(l["open"] == "tracks/python/m-01-first-run/teacher/scenario.md" for l in lines)


def test_readiness_box_uses_real_validate(repo, journal_root, capsys):
    _, out = _run("readiness", repo, journal_root, capsys)
    lines = json.loads(out.out)["lines"]
    assert lines[0]["text"].startswith("python/m-01-first-run · scenario ✓") and lines[0]["style"] == "ok"


def test_students_and_homework_without_roster(repo, tmp_path, capsys, monkeypatch, journal_root):
    empty = tmp_path / "no-students"
    empty.mkdir()
    _, out = _run("students", repo, empty, capsys)
    assert json.loads(out.out)["lines"][0]["style"] == "warn"
    _, out = _run("homework", repo, empty, capsys)
    lines = json.loads(out.out)["lines"]
    assert lines[0]["text"] == "python-01-first-run · не выдана"

    # без --students дефолт должен браться из --repo, а не из
    # $JUNIOR_IT_STUDENTS/реального REPO_ROOT — иначе читаем чужой ростер.
    monkeypatch.setattr(journal_store, "REPO_ROOT", journal_root.parent)
    code = run(["students", "--repo", str(repo), "--today", "2026-09-19"])
    out = capsys.readouterr()
    assert code == 0
    lines = json.loads(out.out)["lines"]
    assert lines[0]["style"] == "warn" and "roster.yml" in lines[0]["text"]


def test_students_box_uses_journal(repo, journal_root, capsys):
    _, out = _run("students", repo, journal_root, capsys, today=TODAY)
    texts = [l["text"] for l in json.loads(out.out)["lines"]]
    assert texts[0] == "журнал · занятий 1" and texts[1].startswith("Алиса")


def test_homework_box_ignores_marks_of_non_active_students(repo, journal_root, capsys):
    """carol в ростере journal_root — status left; отметка ей в журнале не должна менять счётчики."""
    lesson_path = journal_root / "journal" / "2026-09-20.yml"
    data = yaml.safe_load(lesson_path.read_text(encoding="utf-8"))
    data["homework"]["python-01-first-run"]["carol"] = {"status": "accepted", "at": date(2026, 9, 21)}
    lesson_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    _, out = _run("homework", repo, journal_root, capsys, today=TODAY)
    lines = json.loads(out.out)["lines"]
    assert lines[0]["text"] == "python-01-first-run · сдано 1/2 · принято 0/2 · до 23.09"


def test_unknown_box_is_2_and_broken_plan_is_3(repo, journal_root, capsys):
    with pytest.raises(SystemExit) as info:
        run(["weather", "--repo", str(repo)])
    assert info.value.code == 2
    capsys.readouterr()  # argparse печатает usage в stderr при SystemExit — не мешаем следующей проверке
    (repo / "playground" / "2026-09-20" / "session.yml").write_text("theme: [\n", encoding="utf-8")
    code, out = _run("lesson", repo, journal_root, capsys)
    assert code == 3 and out.err.startswith("info:")   # YAMLError из load_sessions без имени файла — известное ограничение


def test_broken_roster_is_3_with_single_stderr_line(repo, journal_root, capsys):
    (journal_root / "roster.yml").write_text(
        "students:\n  - {id: alice, name: Алиса, contacts: {tg: '@alice', email: x@example.com}\n", encoding="utf-8")
    code, out = _run("students", repo, journal_root, capsys)
    assert code == 3
    assert out.err.startswith("info:") and out.err.count("\n") == 1
    assert "example.com" not in out.err


def test_script_runs_from_repo_root(repo, journal_root):
    proc = subprocess.run([sys.executable, str(CLI), "course", "--repo", str(repo), "--students", str(journal_root)],
                          capture_output=True, text=True, cwd=str(repo))
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["lines"][0]["text"].startswith("занятий проведено")
