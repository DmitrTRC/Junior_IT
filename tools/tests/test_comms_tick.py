import fcntl
import json
import os
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


def test_state_saved_when_push_raises(tmp_path, journal_root, course_root, monkeypatch):
    cfg = make_cfg(tmp_path, journal_root, course_root)
    no_transport(monkeypatch)

    def broken_push(cfg, runner):
        raise RuntimeError("boom")

    monkeypatch.setattr(transport, "push", broken_push)
    write_item(cfg.local_dir / "inbox", {"kind": "text", "from": "teacher", "text": "/status"})
    counts = tick.run_tick(cfg, NOW, runner, log=lambda m: None)
    assert counts["applied"] == 1
    assert State(cfg.state_path).tick == 1
    assert (cfg.local_dir / "last_tick.json").is_file()


def test_second_tick_is_skipped_while_locked(tmp_path, journal_root, course_root, monkeypatch):
    cfg = make_cfg(tmp_path, journal_root, course_root)
    no_transport(monkeypatch)
    cfg.local_dir.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(cfg.local_dir / "tick.lock", os.O_CREAT | os.O_RDWR)
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        counts = tick.run_tick(cfg, NOW, runner, log=lambda m: None)
        assert counts["locked"] is True
        assert not (cfg.local_dir / "last_tick.json").is_file()
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def test_tick_waits_for_missing_attachment(tmp_path, journal_root, course_root, monkeypatch):
    cfg = make_cfg(tmp_path, journal_root, course_root)
    no_transport(monkeypatch)
    inbox = cfg.local_dir / "inbox"
    item_id = write_item(inbox, {"kind": "text", "from": "teacher", "text": "/status"}, files={"a.py": b"1"})
    (inbox / item_id / "a.py").unlink()                   # JSON доехал, вложение ещё нет
    logs = []
    counts = tick.run_tick(cfg, NOW, runner, log=logs.append)
    assert counts["applied"] == 0 and counts["errors"] == 0
    assert [i.id for i in read_items(inbox)] == [item_id]
    assert any("вложения ещё не доехали" in m for m in logs)
    assert not State(cfg.state_path).processed(item_id)


def test_poison_item_goes_to_dead_after_three_failures(tmp_path, journal_root, course_root, monkeypatch):
    cfg = make_cfg(tmp_path, journal_root, course_root)
    no_transport(monkeypatch)
    inbox = cfg.local_dir / "inbox"
    item_id = write_item(inbox, {"kind": "text", "from": "teacher", "text": "/status"}, files={"a.py": b"1"})

    def boom(item, ctx):
        raise RuntimeError("boom")

    monkeypatch.setattr(apply, "apply_item", boom)
    for _ in range(2):
        tick.run_tick(cfg, NOW, runner, log=lambda m: None)
    assert [i.id for i in read_items(inbox)] == [item_id]
    counts = tick.run_tick(cfg, NOW, runner, log=lambda m: None)
    assert counts["errors"] == 1 and read_items(inbox) == []
    assert (cfg.local_dir / "dead" / f"{item_id}.json").is_file()
    assert (cfg.local_dir / "dead" / item_id / "a.py").is_file()
    staged = [i.data["text"] for i in read_items(cfg.local_dir / "outbox-staging")]
    assert any("отложен после 3 ошибок" in text and "boom" in text for text in staged)


def test_failure_counter_resets_after_success(tmp_path, journal_root, course_root, monkeypatch):
    cfg = make_cfg(tmp_path, journal_root, course_root)
    no_transport(monkeypatch)
    item_id = write_item(cfg.local_dir / "inbox", {"kind": "text", "from": "teacher", "text": "/status"})
    original = apply.apply_item
    calls = []

    def flaky(item, ctx):
        calls.append(item.id)
        if len(calls) == 1:
            raise RuntimeError("журнал занят")
        return original(item, ctx)

    monkeypatch.setattr(apply, "apply_item", flaky)
    tick.run_tick(cfg, NOW, runner, log=lambda m: None)
    assert State(cfg.state_path).data["failures"] == {item_id: 1}
    tick.run_tick(cfg, NOW, runner, log=lambda m: None)
    assert State(cfg.state_path).data["failures"] == {}


def test_main_bad_config_exits_2(tmp_path, capsys):
    assert tick.main(["--config", str(tmp_path / "missing.toml")]) == 2
    assert "comms:" in capsys.readouterr().err
