from datetime import date, datetime

from comms import schedule
from comms.config import Config
from comms.outbox import Outbox
from comms.queue import read_items
from comms.state import State

DRAFT = "## Тайминги\n\nx\n\n## Сообщение в MAX\n\nДобрый вечер! Итог.\n\nЗапись: https://z/x\nКод доступа: abc\n"


def setup(tmp_path, course_root):
    cfg = Config(repo_root=course_root, students_root=course_root / "students", hp_host="h", hp_queue_dir="/q",
                 local_dir=tmp_path / "local", state_path=tmp_path / "state.json", pages_url="https://s/")
    hw = course_root / "homework" / "python-01-first-run"
    hw.mkdir(parents=True)
    (hw / "task.md").write_text("# Домашка\n\nСделай `hello.py`.", encoding="utf-8")
    (hw / "broken.py").write_text("print('x)", encoding="utf-8")
    return cfg, State(cfg.state_path), Outbox(cfg.local_dir / "outbox-staging")


def staged(cfg):
    return [i.data for i in read_items(cfg.local_dir / "outbox-staging")]


def test_reminder_day_before_after_hour(tmp_path, course_root):
    cfg, state, outbox = setup(tmp_path, course_root)
    assert schedule.run(cfg, state, outbox, datetime(2026, 9, 19, 11, 0), lambda: []) == []
    assert schedule.run(cfg, state, outbox, datetime(2026, 9, 19, 12, 5), lambda: []) == ["reminder"]
    assert schedule.run(cfg, state, outbox, datetime(2026, 9, 19, 13, 0), lambda: []) == []
    item = staged(cfg)[0]
    assert item["to"] == "teacher" and "20:00" in item["text"] and "Первый Python" in item["text"]
    assert [b["data"].split(":")[0] for b in item["buttons"]] == ["send", "discard"]
    meta = state.pending[item["id"]]
    assert meta["kind"] == "post" and meta["target"] == "group" and "20:00" in meta["text"]


def test_post_from_new_draft_with_homework(tmp_path, course_root):
    cfg, state, outbox = setup(tmp_path, course_root)
    drafts = course_root / "meta" / "drafts"
    drafts.mkdir(parents=True)
    (drafts / "lesson-2026-09-20-1731-analysis.md").write_text(DRAFT, encoding="utf-8")
    done = schedule.run(cfg, state, outbox, datetime(2026, 9, 20, 22, 30), lambda: [])
    assert done == ["post:lesson-2026-09-20-1731-analysis.md"]
    item = staged(cfg)[0]
    assert "Добрый вечер! Итог." in item["text"] and "<b>Домашка до ср 23.09</b>" in item["text"]
    assert "<code>hello.py</code>" in item["text"] and "https://s/homework/python-01-first-run/" in item["text"]
    meta = state.pending[item["id"]]
    assert meta["max_copy"] is True and meta["files"] == ["broken.py"]
    assert (cfg.local_dir / "pending" / item["id"] / "broken.py").is_file()
    assert schedule.run(cfg, state, outbox, datetime(2026, 9, 20, 22, 31), lambda: []) == []


def test_digest_with_tails_and_buttons(tmp_path, course_root):
    cfg, state, outbox = setup(tmp_path, course_root)
    tails = [{"student": "alice", "name": "Алиса", "hw_id": "python-01-first-run", "since": "2026-09-23"}]
    assert schedule.run(cfg, state, outbox, datetime(2026, 9, 25, 18, 0), lambda: tails) == ["digest"]
    item = staged(cfg)[0]
    assert "Алиса" in item["text"] and item["buttons"][0]["data"] == f"remind:0:{item['id']}"
    assert state.pending[item["id"]] == {"kind": "digest", "tails": tails}
    assert schedule.run(cfg, state, outbox, datetime(2026, 9, 25, 18, 1), lambda: tails) == []


def test_digest_without_tails_marks_day(tmp_path, course_root):
    cfg, state, outbox = setup(tmp_path, course_root)
    assert schedule.run(cfg, state, outbox, datetime(2026, 9, 25, 18, 0), lambda: []) == []
    assert state.data["digest_sent_on"] == "2026-09-25" and staged(cfg) == []


def test_collect_tails(journal_root, course_root):
    tails = schedule.collect_tails(journal_root, course_root, date(2026, 9, 25))
    assert tails == [{"student": "alice", "name": "Алиса", "hw_id": "python-01-first-run", "since": "2026-09-23"}]
