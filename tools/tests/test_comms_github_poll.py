import subprocess
from datetime import datetime
from pathlib import Path

from comms import github_poll as gp
from comms.config import Config
from comms.identity import Identity
from comms.state import State


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def make_student_repo(tmp_path) -> Path:
    """Настоящий git-репозиторий ученика с двумя коммитами в hw/."""
    work = tmp_path / "student-work"
    work.mkdir()
    git("init", "-q", "-b", "main", cwd=work)
    git("config", "user.email", "t@t", cwd=work)
    git("config", "user.name", "t", cwd=work)
    (work / "README.md").write_text("hw\n", encoding="utf-8")
    git("add", ".", cwd=work)
    git("commit", "-q", "-m", "init", cwd=work)
    hw = work / "hw" / "python-01-first-run"
    hw.mkdir(parents=True)
    (hw / "hello.py").write_text("print(1)\nprint(2)\nprint(3)\n", encoding="utf-8")
    (hw / "broken.py").write_text("print('ok')\n", encoding="utf-8")
    git("add", ".", cwd=work)
    git("commit", "-q", "-m", "hw 01", cwd=work)
    return work


def real_runner(cmd, *, timeout, stdin_text=None):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, input=stdin_text)


def local_runner(work: Path):
    """gh repo clone заменяем на git clone --bare из локальной папки."""
    def runner(cmd, *, timeout, stdin_text=None):
        if cmd[:3] == ["gh", "repo", "clone"]:
            cmd = ["git", "clone", "-q", "--bare", str(work), cmd[4]]
        return real_runner(cmd, timeout=timeout, stdin_text=stdin_text)
    return runner


def setup(tmp_path):
    repo_root = tmp_path / "course"
    tests = repo_root / "homework" / "python-01-first-run" / "tests"
    tests.mkdir(parents=True)
    (tests / "test_hello.py").write_text(
        "import subprocess, sys\nfrom pathlib import Path\nHW = Path(__file__).resolve().parents[1]\n"
        "def test_three():\n    r = subprocess.run([sys.executable, str(HW / 'hello.py')], capture_output=True, text=True)\n"
        "    assert len(r.stdout.splitlines()) == 3\n"
        "def test_broken():\n    assert subprocess.run([sys.executable, str(HW / 'broken.py')]).returncode == 0\n",
        encoding="utf-8")
    cfg = Config(repo_root=repo_root, students_root=tmp_path / "s", hp_host="h", hp_queue_dir="/q",
                 local_dir=tmp_path / "local", state_path=tmp_path / "state.json")
    ident = Identity(tmp_path / "s" / "comms.yml")
    ident.set_github("alice", "owner/jit-hw-alice")
    return cfg, ident, State(cfg.state_path)


def test_parse_summary():
    assert gp.parse_summary("2 passed in 0.1s") == (2, 0)
    assert gp.parse_summary("1 failed, 1 passed in 0.2s") == (1, 1)
    assert gp.parse_summary("no tests ran") == (0, 0)


def test_poll_first_time_reports_submission_and_records_sha(tmp_path):
    work = make_student_repo(tmp_path)
    cfg, ident, state = setup(tmp_path)
    subs = gp.poll(cfg, ident, state, local_runner(work), datetime(2026, 9, 28, 12, 0))
    assert len(subs) == 1
    sub = subs[0]
    assert sub.student == "alice" and sub.hw_id == "python-01-first-run" and (sub.passed, sub.failed) == (2, 0)
    comms_id = ident.by_student("alice").comms_id
    assert state.github[comms_id]["sha"] == sub.sha and state.github[comms_id]["polled"].startswith("2026-09-28")
    assert gp.poll(cfg, ident, state, local_runner(work), datetime(2026, 9, 28, 12, 5)) == []


def test_commit_touching_two_homeworks(tmp_path):
    work = make_student_repo(tmp_path)
    cfg, ident, state = setup(tmp_path)
    gp.poll(cfg, ident, state, local_runner(work), datetime(2026, 9, 28, 12, 0))
    for hw_id in ("python-01-first-run", "devops-01-terminal"):
        d = work / "hw" / hw_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "notes.txt").write_text("x\n", encoding="utf-8")
    (work / "README.md").write_text("changed\n", encoding="utf-8")
    git("add", ".", cwd=work)
    git("commit", "-q", "-m", "two hw + readme", cwd=work)
    subs = gp.poll(cfg, ident, state, local_runner(work), datetime(2026, 9, 28, 13, 0))
    assert [s.hw_id for s in subs] == ["devops-01-terminal", "python-01-first-run"]   # порядок путей git show
    assert (subs[0].passed, subs[0].failed) == (0, 0) and "тестов нет" in subs[0].log
    assert (subs[1].passed, subs[1].failed) == (2, 0)


def test_failing_tests_are_reported_not_raised(tmp_path):
    work = make_student_repo(tmp_path)
    (work / "hw" / "python-01-first-run" / "hello.py").write_text("print(1)\n", encoding="utf-8")
    git("commit", "-q", "-am", "only one line", cwd=work)
    cfg, ident, state = setup(tmp_path)
    subs = gp.poll(cfg, ident, state, local_runner(work), datetime(2026, 9, 28, 12, 0))
    assert (subs[0].passed, subs[0].failed) == (1, 1) and "test_three" in subs[0].log


def test_student_without_repo_is_skipped(tmp_path):
    cfg, ident, state = setup(tmp_path)
    ident.ensure("bob")
    calls = []

    def runner(cmd, *, timeout, stdin_text=None):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, "", "no such repo")

    assert gp.poll(cfg, ident, state, runner, datetime(2026, 9, 28)) == []
    assert all("bob" not in " ".join(c) for c in calls)


def test_missing_binary_is_logged_and_skipped(tmp_path, caplog):
    """Отсутствующий gh/git — FileNotFoundError (OSError) — не роняет цикл по ученикам."""
    cfg, ident, state = setup(tmp_path)
    ident.set_github("bob", "owner/jit-hw-bob")

    def runner(cmd, *, timeout, stdin_text=None):
        raise FileNotFoundError("gh")

    with caplog.at_level("WARNING"):
        subs = gp.poll(cfg, ident, state, runner, datetime(2026, 9, 28))
    assert subs == []
    assert "alice" in caplog.text


def test_suspicious_hw_id_is_skipped(tmp_path):
    """hw_id из чужого репозитория — только курс-подобные id, остальное отбрасывается."""
    work = make_student_repo(tmp_path)
    (work / "hw" / "python-01-first-run" / "hello.py").write_text(
        "print(11)\nprint(2)\nprint(3)\n", encoding="utf-8")
    (work / "hw" / "Weird Name").mkdir(parents=True)
    (work / "hw" / "Weird Name" / "x.txt").write_text("x\n", encoding="utf-8")
    (work / "hw" / "UPPER").mkdir(parents=True)
    (work / "hw" / "UPPER" / "x.txt").write_text("x\n", encoding="utf-8")
    git("add", ".", cwd=work)
    git("commit", "-q", "-m", "weird paths", cwd=work)
    sha = git("rev-parse", "HEAD", cwd=work).stdout.strip()
    assert gp.changed_hw_ids(work, sha, real_runner) == ["python-01-first-run"]

    cfg, ident, state = setup(tmp_path)
    subs = gp.poll(cfg, ident, state, local_runner(work), datetime(2026, 9, 28, 12, 0))
    assert [s.hw_id for s in subs] == ["python-01-first-run"]
    assert (subs[0].passed, subs[0].failed) == (2, 0)
