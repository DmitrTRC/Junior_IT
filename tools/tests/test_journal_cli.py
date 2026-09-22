import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from conftest import DAY, TODAY
from journal import store
from journal.cli import run

CLI = Path(__file__).resolve().parents[1] / "journal" / "cli.py"


def test_attend_and_hw_via_run(journal_root, course_root, capsys):
    root, repo = str(journal_root), str(course_root)
    assert run(["--root", root, "attend", "2026-09-27", "bob", "present"]) == 0
    assert store.load_lesson(date(2026, 9, 27), journal_root).attendance == {"bob": "present"}
    assert run(["--root", root, "--repo", repo, "hw", DAY.isoformat(), "python-01-first-run", "bob", "accepted"],
               today=date(2026, 9, 22)) == 0
    assert run(["--root", root, "hw", DAY.isoformat(), "python-01-first-run", "bob", "rework"]) == 2
    assert "недопустим" in capsys.readouterr().err
    assert run(["--root", root, "attend", "2026-09-27", "zed", "present"]) == 2


def test_issue_points_note(journal_root, course_root):
    root, repo = str(journal_root), str(course_root)
    assert run(["--root", root, "--repo", repo, "issue", "2026-09-27", "--hw", "extra", "--students", "alice"]) == 0
    assert run(["--root", root, "points", "2026-09-27", "alice", "0.5", "зачёт", "--by", "telegram"]) == 0
    assert run(["--root", root, "note", "2026-09-27", "alice", "молодец"]) == 0
    rec = store.load_lesson(date(2026, 9, 27), journal_root)
    assert rec.homework["extra"]["alice"].status == "issued"
    assert rec.points[-1].by == "telegram" and rec.notes == {"alice": "молодец"}


def test_hw_by_flag(journal_root, course_root):
    root, repo = str(journal_root), str(course_root)
    assert run(["--root", root, "--repo", repo, "hw", DAY.isoformat(), "python-01-first-run", "bob",
               "accepted", "--by", "telegram"], today=date(2026, 9, 22)) == 0
    rec = store.load_lesson(DAY, journal_root)
    assert rec.homework["python-01-first-run"]["bob"].by == "telegram"


def test_report_and_json(journal_root, course_root, capsys):
    root, repo = str(journal_root), str(course_root)
    assert run(["--root", root, "--repo", repo, "report"], today=TODAY) == 0
    out = capsys.readouterr().out
    assert "Алиса" in out and "просрочена" in out and "без журнала: 2026-09-13" in out
    assert run(["--root", root, "--repo", repo, "report", "bob"], today=TODAY) == 0
    out = capsys.readouterr().out
    assert "Боб" in out and "Алиса" not in out and "ждёт решения" in out
    assert run(["--root", root, "--repo", repo, "json"], today=TODAY) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["students"][0]["id"] == "alice" and data["missing_journals"] == ["2026-09-13"]


def test_broken_data_is_3(journal_root, capsys):
    (journal_root / "roster.yml").write_text("students: [\n", encoding="utf-8")
    assert run(["--root", str(journal_root), "report"]) == 3
    assert "roster.yml" in capsys.readouterr().err


def test_script_runs_from_repo_root(journal_root, course_root):
    proc = subprocess.run([sys.executable, str(CLI), "--root", str(journal_root), "--repo", str(course_root), "json"],
                          capture_output=True, text=True, cwd=str(course_root))
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["lessons_total"] == 1
