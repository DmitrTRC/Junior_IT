from datetime import date, datetime

import pytest
import yaml

from comms import schedule
from comms.config import Config
from comms.outbox import Outbox
from comms.queue import read_items
from comms.state import State
from journal.model import JournalError

DRAFT = "## Тайминги\n\nx\n\n## Сообщение в MAX\n\nДобрый вечер! Итог.\n\nЗапись: https://z/x\nКод доступа: abc\n"


def setup(tmp_path, course_root, fresh=False):
    cfg = Config(repo_root=course_root, students_root=course_root / "students", hp_host="h", hp_queue_dir="/q",
                 local_dir=tmp_path / "local", state_path=tmp_path / "state.json", pages_url="https://s/")
    hw = course_root / "homework" / "python-01-first-run"
    hw.mkdir(parents=True)
    (hw / "task.md").write_text("# Домашка\n\nСделай `hello.py`.", encoding="utf-8")
    (hw / "broken.py").write_text("print('x)", encoding="utf-8")
    state = State(cfg.state_path)
    if not fresh:
        state.save()                                      # мозг уже работал: состояние на диске есть
        state = State(cfg.state_path)
    return cfg, state, Outbox(cfg.local_dir / "outbox-staging")


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


def test_first_run_seeds_existing_drafts(tmp_path, course_root):
    cfg, state, outbox = setup(tmp_path, course_root, fresh=True)
    drafts = course_root / "meta" / "drafts"
    drafts.mkdir(parents=True)
    (drafts / "lesson-2026-09-20-1731-analysis.md").write_text(DRAFT, encoding="utf-8")
    assert schedule.run(cfg, state, outbox, datetime(2026, 9, 20, 22, 30), lambda: []) == []
    assert state.data["drafts_seen"] == ["lesson-2026-09-20-1731-analysis.md"] and staged(cfg) == []
    (drafts / "lesson-2026-09-21-1800-analysis.md").write_text(DRAFT, encoding="utf-8")
    done = schedule.run(cfg, state, outbox, datetime(2026, 9, 21, 22, 30), lambda: [])
    assert done == ["post:lesson-2026-09-21-1800-analysis.md"] and len(staged(cfg)) == 1


def test_post_with_long_homework_fits_4096(tmp_path, course_root):
    cfg, state, outbox = setup(tmp_path, course_root)
    hw = course_root / "homework" / "python-01-first-run"
    (hw / "task.md").write_text("# Домашка\n\n" + "\n".join(f"шаг {i}: " + "x" * 70 for i in range(200)),
                                encoding="utf-8")
    drafts = course_root / "meta" / "drafts"
    drafts.mkdir(parents=True)
    long_section = DRAFT.replace("Добрый вечер! Итог.", "Добрый вечер! Итог. " + "Разобрали цикл. " * 100)
    (drafts / "lesson-2026-09-20-1731-analysis.md").write_text(long_section, encoding="utf-8")
    assert schedule.run(cfg, state, outbox, datetime(2026, 9, 20, 22, 30), lambda: []) == \
        ["post:lesson-2026-09-20-1731-analysis.md"]
    item = staged(cfg)[0]
    text = state.pending[item["id"]]["text"]
    assert len(item["text"]) <= 4096 and len(text) <= 4096
    assert text.count("<b>") == text.count("</b>") and item["text"].count("<b>") == item["text"].count("</b>")
    assert "Добрый вечер! Итог." in text and text.endswith("Страница: https://s/homework/python-01-first-run/")


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


def test_digest_error_does_not_consume_day(tmp_path, course_root):
    cfg, state, outbox = setup(tmp_path, course_root)

    def broken():
        raise JournalError("журнал не прочитан")

    with pytest.raises(JournalError):
        schedule.run(cfg, state, outbox, datetime(2026, 9, 25, 18, 0), broken)
    assert state.data["digest_sent_on"] is None
    assert schedule.run(cfg, state, outbox, datetime(2026, 9, 25, 18, 5), lambda: []) == []
    assert state.data["digest_sent_on"] == "2026-09-25"


def test_collect_tails(journal_root, course_root):
    tails = schedule.collect_tails(journal_root, course_root, date(2026, 9, 25))
    assert tails == [{"student": "alice", "name": "Алиса", "hw_id": "python-01-first-run", "since": "2026-09-23"}]


def test_collect_tails_skips_left_students(journal_root, course_root):
    path = journal_root / "journal" / "2026-09-20.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["homework"]["python-01-first-run"]["carol"] = {"status": "issued", "at": date(2026, 9, 20)}
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    tails = schedule.collect_tails(journal_root, course_root, date(2026, 9, 25))
    assert [t["student"] for t in tails] == ["alice"]     # Кэрол ушла из группы — в хвостах её нет
