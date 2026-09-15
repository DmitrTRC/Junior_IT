import subprocess
from datetime import date
from pathlib import Path

from zoom_pipeline.config import Config
from zoom_pipeline.phases import run_tick
from zoom_pipeline.state import State
from zoom_pipeline.zoom_api import Meeting, RecFile


def make_cfg(tmp_path):
    return Config(
        repo_root=tmp_path / "repo",
        backup_dir=tmp_path / "nas",
        retention_days=30,
        student_stems=["Наст"],
        zoom_account_id="a", zoom_client_id="c", zoom_client_secret="s",
        state_path=tmp_path / "state.json",
    )


def meeting(uuid="u1", start="2026-09-16T17:00:00Z"):
    return Meeting(
        uuid=uuid, topic="Занятие", start_time=start,
        share_url="https://zoom.us/rec/share/x", passcode="pc",
        files=[RecFile("MP4", "mp4", "https://dl/v"),
               RecFile("M4A", "m4a", "https://dl/a")],
    )


class FakeApi:
    def __init__(self, meetings):
        self.meetings = meetings
        self.downloaded = []
        self.deleted = []

    def list_recordings(self, from_date):
        return self.meetings

    def download(self, url, dest):
        self.downloaded.append(url)
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(b"data")

    def delete_recording(self, uuid):
        self.deleted.append(uuid)


def ok_runner(calls):
    def runner(cmd, *, timeout, stdin_text=None):
        calls.append(cmd)
        if cmd[0] == "uvx":
            # mlx_whisper пишет <аудио>.txt в --output-dir — эмулируем
            out_dir = Path(cmd[cmd.index("--output-dir") + 1])
            audio = Path(cmd[-1])
            (out_dir / (audio.stem + ".txt")).write_text(
                "Настя молодец", encoding="utf-8")
        # claude -p печатает markdown анализа в stdout
        out = "# Анализ\n" if cmd[0] == "claude" else ""
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")
    return runner


def failing_rsync_runner(calls):
    def runner(cmd, *, timeout, stdin_text=None):
        calls.append(cmd)
        code = 23 if cmd[0] == "rsync" else 0
        return subprocess.CompletedProcess(cmd, code, stdout="", stderr="нет шары")
    return runner


def run(cfg, api, runner_fn, today=date(2026, 9, 16)):
    state = State.load(cfg.state_path)
    logs = []
    run_tick(cfg, api, state, runner_fn, today, log=logs.append)
    return state, logs


def test_full_pass_reaches_analyzed(tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.backup_dir.mkdir(parents=True)  # «шара смонтирована»
    api = FakeApi([meeting()])
    calls = []
    state, _ = run(cfg, api, ok_runner(calls))
    assert state.phase("u1") == "analyzed"
    assert len(api.downloaded) == 2
    assert any(c[0] == "rsync" for c in calls)
    assert any(c[0] == "uvx" for c in calls)
    assert any(c[0] == "claude" for c in calls)
    draft = cfg.drafts_dir / "lesson-2026-09-16-analysis.md"
    assert draft.is_file()
    assert "Анализ" in draft.read_text(encoding="utf-8")


def test_backup_failure_stalls_phase(tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.backup_dir.mkdir(parents=True)
    api = FakeApi([meeting()])
    calls = []
    state, logs = run(cfg, api, failing_rsync_runner(calls))
    assert state.phase("u1") == "downloaded"
    assert not any(c[0] == "uvx" for c in calls)  # дальше бэкапа не пошли
    assert any("rsync" in line for line in logs)


def test_unmounted_share_stalls_phase(tmp_path):
    cfg = make_cfg(tmp_path)  # backup_dir не существует = не смонтирован
    api = FakeApi([meeting()])
    state, logs = run(cfg, api, ok_runner([]))
    assert state.phase("u1") == "downloaded"


def test_second_tick_is_idempotent(tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.backup_dir.mkdir(parents=True)
    api = FakeApi([meeting()])
    run(cfg, api, ok_runner([]))
    api.downloaded.clear()
    state, _ = run(cfg, api, ok_runner([]))
    assert state.phase("u1") == "analyzed"
    assert api.downloaded == []  # повторно не качали


def test_retention_deletes_old_backed_up(tmp_path):
    cfg = make_cfg(tmp_path)
    api = FakeApi([])
    state = State.load(cfg.state_path)
    state.advance("old", "analyzed", date="2026-08-01")
    state.advance("fresh", "analyzed", date="2026-09-10")
    run_tick(cfg, api, state, ok_runner([]), date(2026, 9, 16), log=lambda s: None)
    assert api.deleted == ["old"]
    assert state.phase("old") == "cloud_deleted"
    assert state.phase("fresh") == "analyzed"
