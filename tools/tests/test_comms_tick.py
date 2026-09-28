import json
from datetime import datetime

from comms import apply, github_poll, schedule, tick, transport
from comms.config import Config
from comms.github_poll import Submission
from comms.identity import Identity
from comms.queue import read_items, write_item
from comms.state import State

NOW = datetime(2026, 9, 25, 15, 0)


def make_cfg(tmp_path, journal_root, course_root, every=5):
    cfg = Config(repo_root=course_root, students_root=journal_root, hp_host="h", hp_queue_dir="/q",
                 local_dir=tmp_path / "local", state_path=tmp_path / "state.json", github_poll_every=every)
    Identity(journal_root / "comms.yml").ensure("alice")
    return cfg


def no_transport(monkeypatch):
    monkeypatch.setattr(transport, "pull", lambda cfg, runner: 0)
    monkeypatch.setattr(transport, "push", lambda cfg, runner: len(read_items(cfg.local_dir / "outbox-staging")))
    monkeypatch.setattr(schedule, "run", lambda *a, **k: [])


def runner(cmd, *, timeout, stdin_text=None):
    raise AssertionError("runner не должен вызываться в этом тесте")


def test_tick_survives_apply_error_and_keeps_item(tmp_path, journal_root, course_root, monkeypatch):
    cfg = make_cfg(tmp_path, journal_root, course_root)
    no_transport(monkeypatch)
    inbox = cfg.local_dir / "inbox"
    bad = write_item(inbox, {"id": "00000000T000000000000-000000aa", "kind": "text", "from": "teacher", "text": "/status"})
    good = write_item(inbox, {"id": "00000000T000000000000-000000bb", "kind": "text", "from": "teacher", "text": "/status"})
    original = apply.apply_item

    def flaky(item, ctx):
        if item.id == bad:
            raise RuntimeError("boom")
        return original(item, ctx)

    monkeypatch.setattr(apply, "apply_item", flaky)
    counts = tick.run_tick(cfg, NOW, runner, log=lambda m: None)
    assert counts["applied"] == 1 and counts["errors"] == 1 and counts["pushed"] == 1
    assert [i.id for i in read_items(inbox)] == [bad]                 # битый остался, хороший удалён
    state = State(cfg.state_path)
    assert state.processed(good) and not state.processed(bad) and state.tick == 1
    last = json.loads((cfg.local_dir / "last_tick.json").read_text(encoding="utf-8"))
    assert last["counts"]["errors"] == 1 and last["inbox_left"] == 1 and last["ts"].startswith("2026-09-25T15:00")


def test_processed_items_are_skipped_and_removed(tmp_path, journal_root, course_root, monkeypatch):
    cfg = make_cfg(tmp_path, journal_root, course_root)
    no_transport(monkeypatch)
    item_id = write_item(cfg.local_dir / "inbox", {"kind": "text", "from": "teacher", "text": "/status"})
    st = State(cfg.state_path)
    st.mark_processed(item_id, NOW)
    st.save()
    counts = tick.run_tick(cfg, NOW, runner, log=lambda m: None)
    assert counts["applied"] == 0 and read_items(cfg.local_dir / "inbox") == []


def test_github_every_nth_tick(tmp_path, journal_root, course_root, monkeypatch):
    cfg = make_cfg(tmp_path, journal_root, course_root, every=2)
    no_transport(monkeypatch)
    calls = []
    monkeypatch.setattr(github_poll, "poll", lambda *a, **k: calls.append(1) or [])
    tick.run_tick(cfg, NOW, runner, log=lambda m: None)
    assert calls == []
    tick.run_tick(cfg, NOW, runner, log=lambda m: None)
    assert calls == [1]


def test_pull_failure_still_processes_local(tmp_path, journal_root, course_root, monkeypatch):
    cfg = make_cfg(tmp_path, journal_root, course_root)
    no_transport(monkeypatch)

    def broken_pull(cfg, runner):
        raise transport.TransportError("ssh: connect timeout")

    monkeypatch.setattr(transport, "pull", broken_pull)
    write_item(cfg.local_dir / "inbox", {"kind": "text", "from": "teacher", "text": "/status"})
    logs = []
    counts = tick.run_tick(cfg, NOW, runner, log=logs.append)
    assert counts["applied"] == 1 and any("connect timeout" in m for m in logs)


def test_dry_run_prints_state(tmp_path, journal_root, course_root, monkeypatch, capsys):
    cfg = make_cfg(tmp_path, journal_root, course_root)
    (tmp_path / "c.toml").write_text(
        f'repo_root = "{course_root}"\nstudents_root = "{journal_root}"\nhp_host = "h"\nhp_queue_dir = "/q"\n'
        f'local_dir = "{cfg.local_dir}"\n', encoding="utf-8")
    assert tick.main(["--config", str(tmp_path / "c.toml"), "--dry-run"]) == 0
    assert "ожидают кнопок" in capsys.readouterr().out
