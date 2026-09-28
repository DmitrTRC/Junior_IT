import subprocess

from comms import claude_draft
from comms.config import Config


def cfg(tmp_path):
    return Config(repo_root=tmp_path, students_root=tmp_path, hp_host="h", hp_queue_dir="/q",
                  local_dir=tmp_path, state_path=tmp_path / "s.json", claude_cmd=["claude", "-p"])


def test_render_prompt_fills_fields_and_keeps_rules():
    text = claude_draft.render_prompt("answer", {"student_name": "Алиса", "question": "почему >>>?"})
    assert "Алиса" in text and "почему >>>?" in text
    assert "не создавай и не изменяй файлы" in text and "на «ты»" in text
    assert "{task_text}" not in text


def test_draft_runs_claude_with_prompt_on_stdin(tmp_path):
    calls = []

    def runner(cmd, *, timeout, stdin_text=None):
        calls.append((cmd, timeout, stdin_text))
        return subprocess.CompletedProcess(cmd, 0, "Черновик ответа.\n", "")

    out = claude_draft.draft("answer", {"student_name": "Боб", "question": "?"}, cfg(tmp_path), runner)
    assert out == "Черновик ответа." and calls[0][0] == ["claude", "-p"] and calls[0][1] == 900
    assert "Боб" in calls[0][2]


def test_draft_failure_returns_none(tmp_path):
    def runner(cmd, *, timeout, stdin_text=None):
        return subprocess.CompletedProcess(cmd, 1, "", "boom")

    assert claude_draft.draft("task", {"task": "сводка"}, cfg(tmp_path), runner) is None

    def empty(cmd, *, timeout, stdin_text=None):
        return subprocess.CompletedProcess(cmd, 0, "  \n", "")

    assert claude_draft.draft("review", {}, cfg(tmp_path), empty) is None


def test_draft_timeout_returns_none(tmp_path):
    def slow(cmd, *, timeout, stdin_text=None):
        raise subprocess.TimeoutExpired(cmd, timeout)

    assert claude_draft.draft("answer", {"question": "?"}, cfg(tmp_path), slow) is None
