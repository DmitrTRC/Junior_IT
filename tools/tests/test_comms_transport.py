import subprocess
from pathlib import Path

import pytest

from comms.config import Config
from comms.outbox import Outbox
from comms.queue import read_items
from comms.transport import TransportError, pull, push


class FakeRunner:
    """Записывает команды; rsync inbox имитирует приход элемента, push — успех/провал по флагу."""

    def __init__(self, local: Path, fail_push=False):
        self.calls, self.local, self.fail_push = [], local, fail_push

    def __call__(self, cmd, *, timeout, stdin_text=None):
        self.calls.append(cmd)
        rc = 0
        if cmd[0] == "rsync" and cmd[-1].endswith("/inbox/"):
            (self.local / "inbox").mkdir(parents=True, exist_ok=True)
            (self.local / "inbox" / "00000000T000000000000-aaaaaaaa.json").write_text('{"id":"x","kind":"text"}', encoding="utf-8")
        if cmd[0] == "rsync" and "/outbox/" in cmd[-1] and self.fail_push:
            rc = 23
        return subprocess.CompletedProcess(cmd, rc, "", "rsync error" if rc else "")


def cfg(tmp_path):
    return Config(repo_root=tmp_path, students_root=tmp_path / "s", hp_host="courier@hp",
                  hp_queue_dir="/srv/courier/queue", local_dir=tmp_path / "local", state_path=tmp_path / "st.json")


def test_pull_fetches_inbox_status_and_touches_marker(tmp_path):
    c, r = cfg(tmp_path), FakeRunner(tmp_path / "local")
    assert pull(c, r) == 1
    rsync_inbox, ssh_cleanup, rsync_status = r.calls[0], r.calls[1], r.calls[2]
    assert rsync_inbox[:3] == ["rsync", "-a", "--remove-source-files"]
    assert rsync_inbox[-2] == "courier@hp:/srv/courier/queue/inbox/" and rsync_inbox[-1] == str(tmp_path / "local" / "inbox") + "/"
    assert ssh_cleanup[0] == "ssh" and "touch /srv/courier/queue/.last_pull" in ssh_cleanup[-1] and "-empty -delete" in ssh_cleanup[-1]
    assert rsync_status[-2] == "courier@hp:/srv/courier/queue/status.json"


def test_push_two_passes_then_clears_staging(tmp_path):
    c, r = cfg(tmp_path), FakeRunner(tmp_path / "local")
    Outbox(c.local_dir / "outbox-staging").teacher("x", files={"a.py": b"1"})
    assert push(c, r) == 1
    first, second = [call for call in r.calls if call[0] == "rsync"]
    assert "--exclude" in first and first[first.index("--exclude") + 1] == "*.json"
    assert second[second.index("--include") + 1] == "*.json" and second[second.index("--exclude") + 1] == "*"
    assert first[-1] == "courier@hp:/srv/courier/queue/outbox/"
    assert read_items(c.local_dir / "outbox-staging") == []


def test_push_failure_keeps_staging(tmp_path):
    c, r = cfg(tmp_path), FakeRunner(tmp_path / "local", fail_push=True)
    Outbox(c.local_dir / "outbox-staging").group("x")
    with pytest.raises(TransportError):
        push(c, r)
    assert len(read_items(c.local_dir / "outbox-staging")) == 1


def test_push_nothing_is_noop(tmp_path):
    c, r = cfg(tmp_path), FakeRunner(tmp_path / "local")
    assert push(c, r) == 0 and r.calls == []
