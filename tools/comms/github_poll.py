"""Репозитории учеников: новые коммиты в hw/<id>/ -> тесты домашки -> Submission."""
from __future__ import annotations
import logging
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from comms.config import Config
from comms.identity import Identity
from comms.state import State

log = logging.getLogger("comms.github")
GIT_TIMEOUT = 60
HW_PATH_RE = re.compile(r"^hw/([^/]+)/")
HW_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass
class Submission:
    student: str
    comms_id: str
    hw_id: str
    sha: str
    passed: int
    failed: int
    log: str


def _run(cmd, runner, timeout=GIT_TIMEOUT) -> str:
    result = runner(cmd, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:4])}: код {result.returncode}: {(result.stderr or '').strip()[:200]}")
    return result.stdout or ""


def ensure_clone(repo: str, dest: Path, runner) -> None:
    if dest.is_dir():
        _run(["git", "-C", str(dest), "fetch", "-q", "origin", "+refs/heads/*:refs/heads/*"], runner)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run(["gh", "repo", "clone", repo, str(dest), "--", "--bare"], runner)


def head_sha(dest: Path, runner) -> str:
    return _run(["git", "-C", str(dest), "rev-parse", "HEAD"], runner).strip()


def commits_since(dest: Path, since: str | None, runner) -> list[str]:
    span = f"{since}..HEAD" if since else "HEAD"
    return _run(["git", "-C", str(dest), "rev-list", "--reverse", span], runner).split()


def changed_hw_ids(dest: Path, sha: str, runner) -> list[str]:
    out: list[str] = []
    for path in _run(["git", "-C", str(dest), "show", "--name-only", "--format=", sha], runner).splitlines():
        path = path.strip()
        m = HW_PATH_RE.match(path)
        if not m:
            continue
        hw_id = m.group(1)
        if not HW_ID_RE.match(hw_id):
            log.warning("пропущен подозрительный путь %s", path)
            continue
        if hw_id not in out:
            out.append(hw_id)
    return out


def export_subtree(dest: Path, sha: str, hw_id: str, target: Path, runner) -> Path:
    """git archive отдаёт tar байтами — единственное место, где brain зовёт git не через runner."""
    target.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(["git", "-C", str(dest), "archive", "--format=tar", sha, f"hw/{hw_id}"],
                             capture_output=True, check=True, timeout=GIT_TIMEOUT)
    subprocess.run(["tar", "-x", "-C", str(target)], input=archive.stdout, check=True, timeout=GIT_TIMEOUT)
    return target / "hw" / hw_id


def parse_summary(text: str) -> tuple[int, int]:
    passed = re.search(r"(\d+) passed", text)
    failed = re.search(r"(\d+) failed", text)
    return (int(passed.group(1)) if passed else 0, int(failed.group(1)) if failed else 0)


def run_tests(repo_root: Path, hw_id: str, workdir: Path, runner, timeout_s: int) -> tuple[int, int, str]:
    """pytest ученика — с cwd в его подпапке; у runner нет cwd, поэтому subprocess напрямую."""
    tests_src = Path(repo_root) / "homework" / hw_id / "tests"
    if not tests_src.is_dir():
        return 0, 0, "тестов нет"
    shutil.copytree(tests_src, workdir / "tests", dirs_exist_ok=True)
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
                                cwd=workdir, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return 0, 1, f"тесты не уложились в {timeout_s} с"
    output = (result.stdout or "") + (result.stderr or "")
    passed, failed = parse_summary(output)
    return passed, failed, output[-2000:]


def poll(cfg: Config, identity: Identity, state: State, runner, now: datetime) -> list[Submission]:
    submissions: list[Submission] = []
    for person in identity.people:
        if person.role != "student" or not person.github:
            continue
        dest = cfg.local_dir / "hw-repos" / person.comms_id
        try:
            ensure_clone(person.github, dest, runner)
            since = (state.github.get(person.comms_id) or {}).get("sha")
            commits = commits_since(dest, since, runner)
            hw_ids: list[str] = []
            for commit_sha in commits:
                for hw_id in changed_hw_ids(dest, commit_sha, runner):
                    if hw_id not in hw_ids:
                        hw_ids.append(hw_id)
            head = head_sha(dest, runner)
            for hw_id in hw_ids:
                with tempfile.TemporaryDirectory(prefix="jit-hw-") as tmp:
                    subtree = export_subtree(dest, head, hw_id, Path(tmp), runner)
                    passed, failed, output = run_tests(cfg.repo_root, hw_id, subtree, runner, cfg.tests_timeout_s)
                submissions.append(Submission(person.student, person.comms_id, hw_id, head, passed, failed, output))
            state.github[person.comms_id] = {"sha": head, "polled": now.isoformat(timespec="seconds")}
        except (RuntimeError, subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError) as exc:
            log.warning("github %s: %s", person.student, exc)
    return submissions
