import subprocess
from datetime import date, datetime
from pathlib import Path

import pytest

from comms import apply
from comms.config import Config
from comms.github_poll import Submission
from comms.identity import Identity
from comms.outbox import Outbox
from comms.queue import Item, read_items
from comms.state import State
from journal import ops, store

NOW = datetime(2026, 9, 25, 15, 0)


def claude_runner(reply="Черновик от Claude."):
    def runner(cmd, *, timeout, stdin_text=None):
        return subprocess.CompletedProcess(cmd, 0, reply, "")
    return runner


@pytest.fixture
def ctx(tmp_path, journal_root, course_root):
    hw = course_root / "homework" / "python-01-first-run"
    hw.mkdir(parents=True)
    (hw / "task.md").write_text("# Домашка\n\nСделай `hello.py`.", encoding="utf-8")
    cfg = Config(repo_root=course_root, students_root=journal_root, hp_host="h", hp_queue_dir="/q",
                 local_dir=tmp_path / "local", state_path=tmp_path / "state.json", pages_url="https://s/")
    ident = Identity(journal_root / "comms.yml")
    for sid in ("alice", "bob"):
        ident.new_code(ident.ensure(sid))
    ident.bind(ident.by_student("alice").comms_id, 701)
    ident.bind(ident.by_student("bob").comms_id, 702)
    return apply.Context(cfg=cfg, state=State(cfg.state_path), identity=ident,
                         outbox=Outbox(cfg.local_dir / "outbox-staging"), runner=claude_runner(), now=NOW,
                         names={"alice": "Алиса", "bob": "Боб", "carol": "Кэрол"})


def staged(ctx):
    return [i.data for i in read_items(ctx.cfg.local_dir / "outbox-staging")]


def clear(ctx):
    for i in read_items(ctx.cfg.local_dir / "outbox-staging"):
        (ctx.cfg.local_dir / "outbox-staging" / f"{i.id}.json").unlink()


def item(tmp_path, **data):
    base = {"from": "teacher", "chat": "private", "kind": "text", "text": "", "message_id": 1,
            "reply_to_item": None, "callback": None, "unsupported": None, "files": [], "ts": "2026-09-25T12:00:00"}
    base.update(data)
    files_dir = tmp_path / "in" / "x"
    files_dir.mkdir(parents=True, exist_ok=True)
    return Item(id=data.get("id", "00000000T000000000000-0000000a"), data=base, files_dir=files_dir)


def mark(journal_root, hw_id, student):
    rec = [r for r in store.load_lessons(journal_root) if r.date == date(2026, 9, 20)][0]
    return rec.homework[hw_id][student]


def test_registered_binds_and_notifies(ctx, tmp_path):
    carol = ctx.identity.ensure("carol")
    apply.apply_item(item(tmp_path, **{"from": carol.comms_id, "kind": "registered", "telegram_id": 703}), ctx)
    assert ctx.identity.by_student("carol").telegram_id == 703
    assert staged(ctx)[0]["to"] == "teacher" and "Кэрол" in staged(ctx)[0]["text"]


def test_fallback_submission_records_journal_and_asks_teacher(ctx, tmp_path, journal_root):
    it = item(tmp_path, **{"from": ctx.identity.by_student("alice").comms_id, "kind": "photo", "text": "вот",
                          "files": ["photo.jpg"]})
    (it.files_dir / "photo.jpg").write_bytes(b"\xff\xd8")
    apply.apply_item(it, ctx)
    assert mark(journal_root, "python-01-first-run", "alice").status == "submitted"
    assert mark(journal_root, "python-01-first-run", "alice").by == "telegram"
    notice = staged(ctx)[0]
    assert notice["to"] == "teacher" and "Алиса" in notice["text"] and notice["files"] == ["photo.jpg"]
    assert [b["data"].split(":")[0] for b in notice["buttons"]] == ["accept", "rework", "claude"]
    meta = ctx.state.pending[notice["id"]]
    assert meta["kind"] == "submission" and meta["hw_id"] == "python-01-first-run" and meta["day"] == "2026-09-20"
    assert (journal_root / "submissions" / "alice" / "python-01-first-run" / it.id / "photo.jpg").is_file()


def test_submission_without_issued_mark_issues_first(ctx, tmp_path, journal_root):
    import yaml
    lesson = journal_root / "journal" / "2026-09-20.yml"
    data = yaml.safe_load(lesson.read_text(encoding="utf-8"))
    del data["homework"]["python-01-first-run"]["alice"]               # alice домашку не выдавали
    lesson.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    it = item(tmp_path, **{"from": ctx.identity.by_student("alice").comms_id, "kind": "document", "files": ["hello.py"]})
    (it.files_dir / "hello.py").write_text("print(1)", encoding="utf-8")
    apply.apply_item(it, ctx)                           # выдаём по последнему плану и принимаем сдачу
    m = mark(journal_root, "python-01-first-run", "alice")
    assert m.status == "submitted" and m.by == "telegram"


def test_accept_twice_is_idempotent(ctx, tmp_path, journal_root):
    sub = item(tmp_path, **{"from": ctx.identity.by_student("bob").comms_id, "kind": "document", "files": ["h.py"]})
    (sub.files_dir / "h.py").write_text("x", encoding="utf-8")
    apply.apply_item(sub, ctx)
    notice_id = staged(ctx)[0]["id"]
    clear(ctx)
    apply.apply_item(item(tmp_path, kind="callback", callback=f"accept:{notice_id}"), ctx)
    assert mark(journal_root, "python-01-first-run", "bob").status == "accepted"
    rec = [r for r in store.load_lessons(journal_root) if r.date == date(2026, 9, 20)][0]
    points_before = sum(p.amount for p in rec.points if p.who == "bob")
    to_bob = [d for d in staged(ctx) if d["to"] == ctx.identity.by_student("bob").comms_id]
    assert to_bob and "принята" in to_bob[0]["text"]
    clear(ctx)
    apply.apply_item(item(tmp_path, kind="callback", callback=f"accept:{notice_id}"), ctx)
    rec = [r for r in store.load_lessons(journal_root) if r.date == date(2026, 9, 20)][0]
    assert sum(p.amount for p in rec.points if p.who == "bob") == points_before
    assert staged(ctx) == [] or "Уже сделано" in staged(ctx)[0]["text"]


def test_rework_needs_teacher_reply(ctx, tmp_path, journal_root):
    sub = item(tmp_path, **{"from": ctx.identity.by_student("bob").comms_id, "kind": "document", "files": ["h.py"]})
    (sub.files_dir / "h.py").write_text("x", encoding="utf-8")
    apply.apply_item(sub, ctx)
    notice_id = staged(ctx)[0]["id"]
    clear(ctx)
    apply.apply_item(item(tmp_path, kind="callback", callback=f"rework:{notice_id}"), ctx)
    assert ctx.state.pending[notice_id]["await_reply"] is True and "reply" in staged(ctx)[0]["text"].lower()
    clear(ctx)
    apply.apply_item(item(tmp_path, kind="reply", text="Добавь третий print", reply_to_item=notice_id), ctx)
    m = mark(journal_root, "python-01-first-run", "bob")
    assert m.status == "rework" and m.note == "Добавь третий print"
    to_bob = [d for d in staged(ctx) if d["to"] == ctx.identity.by_student("bob").comms_id]
    assert "Добавь третий print" in to_bob[0]["text"] and notice_id not in ctx.state.pending


def test_failed_transition_keeps_pending(ctx, tmp_path, journal_root):
    it = item(tmp_path, **{"from": ctx.identity.by_student("alice").comms_id, "kind": "photo", "files": ["photo.jpg"]})
    (it.files_dir / "photo.jpg").write_bytes(b"\xff\xd8")
    apply.apply_item(it, ctx)
    notice_id = staged(ctx)[0]["id"]
    ops.set_homework(date(2026, 9, 20), "python-01-first-run", "alice", "accepted", None,
                     journal_root, NOW.date(), "teacher")
    clear(ctx)
    apply.apply_item(item(tmp_path, kind="callback", callback=f"rework:{notice_id}"), ctx)
    clear(ctx)
    apply.apply_item(item(tmp_path, kind="reply", text="текст", reply_to_item=notice_id), ctx)
    assert "Статус не изменён" in staged(ctx)[0]["text"]
    assert notice_id in ctx.state.pending
    assert ctx.pending_dir(notice_id).is_dir()


def test_accept_failed_transition_keeps_pending(ctx, tmp_path, journal_root):
    import yaml
    sub = item(tmp_path, **{"from": ctx.identity.by_student("bob").comms_id, "kind": "document", "files": ["h.py"]})
    (sub.files_dir / "h.py").write_text("x", encoding="utf-8")
    apply.apply_item(sub, ctx)
    notice_id = staged(ctx)[0]["id"]
    lesson = journal_root / "journal" / "2026-09-20.yml"
    data = yaml.safe_load(lesson.read_text(encoding="utf-8"))
    del data["homework"]["python-01-first-run"]["bob"]          # отметку убрали из-под кнопки
    lesson.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    clear(ctx)
    apply.apply_item(item(tmp_path, kind="callback", callback=f"accept:{notice_id}"), ctx)
    assert "Не принято" in staged(ctx)[0]["text"]
    assert notice_id in ctx.state.pending
    assert ctx.pending_dir(notice_id).is_dir()


def test_question_claude_draft_then_send(ctx, tmp_path):
    alice = ctx.identity.by_student("alice").comms_id
    apply.apply_item(item(tmp_path, **{"from": alice, "kind": "text", "text": "зачем >>>?"}), ctx)
    q = staged(ctx)[0]
    assert q["to"] == "teacher" and "зачем &gt;&gt;&gt;?" in q["text"] and q["buttons"][0]["data"] == f"claude:{q['id']}"
    clear(ctx)
    apply.apply_item(item(tmp_path, kind="callback", callback=f"claude:{q['id']}"), ctx)
    d = staged(ctx)[0]
    assert "Черновик от Claude." in d["text"] and [b["data"].split(":")[0] for b in d["buttons"]] == ["send", "discard"]
    assert ctx.state.pending[d["id"]] == {"kind": "post", "target": alice, "text": "Черновик от Claude.",
                                          "files": [], "max_copy": False}
    clear(ctx)
    apply.apply_item(item(tmp_path, kind="callback", callback=f"send:{d['id']}"), ctx)
    assert [x["to"] for x in staged(ctx)] == [alice, "teacher"] and d["id"] not in ctx.state.pending


def test_teacher_reply_to_question_goes_to_student(ctx, tmp_path):
    alice = ctx.identity.by_student("alice").comms_id
    apply.apply_item(item(tmp_path, **{"from": alice, "kind": "text", "text": "а?"}), ctx)
    q_id = staged(ctx)[0]["id"]
    clear(ctx)
    apply.apply_item(item(tmp_path, kind="reply", text="Потому что REPL.", reply_to_item=q_id), ctx)
    assert staged(ctx)[0]["to"] == alice and staged(ctx)[0]["text"].endswith("— Димас")


def test_send_post_to_group_with_max_copy(ctx, tmp_path):
    post_id = ctx.outbox.teacher_with_self_buttons("превью", [("отправить", "send:{id}")], files={"a.py": b"1"})
    pending_dir = ctx.cfg.local_dir / "pending" / post_id
    pending_dir.mkdir(parents=True)
    (pending_dir / "a.py").write_bytes(b"1")
    ctx.state.pending[post_id] = {"kind": "post", "target": "group", "text": "<b>Итог</b> &amp; домашка",
                                  "files": ["a.py"], "max_copy": True}
    clear(ctx)
    apply.apply_item(item(tmp_path, kind="callback", callback=f"send:{post_id}"), ctx)
    out = staged(ctx)
    assert out[0]["to"] == "group" and out[0]["files"] == ["a.py"]
    assert out[1]["to"] == "teacher" and "Дубль для MAX" in out[1]["text"] and "Итог &amp; домашка" in out[1]["text"]
    assert not pending_dir.exists()


def test_discard_and_unknown_callback(ctx, tmp_path):
    ctx.state.pending["p1"] = {"kind": "post", "target": "group", "text": "x", "files": [], "max_copy": False}
    apply.apply_item(item(tmp_path, kind="callback", callback="discard:p1"), ctx)
    assert "p1" not in ctx.state.pending and "Отброшено" in staged(ctx)[0]["text"]
    clear(ctx)
    apply.apply_item(item(tmp_path, kind="callback", callback="discard:p1"), ctx)
    assert "Уже сделано" in staged(ctx)[0]["text"]


def test_remind_from_digest(ctx, tmp_path):
    alice = ctx.identity.by_student("alice").comms_id
    ctx.state.pending["d1"] = {"kind": "digest", "tails": [
        {"student": "alice", "name": "Алиса", "hw_id": "python-01-first-run", "since": "2026-09-23"}]}
    apply.apply_item(item(tmp_path, kind="callback", callback="remind:0:d1"), ctx)
    out = staged(ctx)
    assert out[0]["to"] == alice and "python-01-first-run" in out[0]["text"] and "https://s/homework/python-01-first-run/" in out[0]["text"]
    assert "d1" in ctx.state.pending                    # кнопок несколько — сводка живёт


def test_remind_bad_index_is_already_done(ctx, tmp_path):
    ctx.state.pending["d1"] = {"kind": "digest", "tails": [
        {"student": "alice", "name": "Алиса", "hw_id": "python-01-first-run", "since": "2026-09-23"}]}
    apply.apply_item(item(tmp_path, kind="callback", callback="remind:9:d1"), ctx)
    assert "Уже сделано" in staged(ctx)[0]["text"]
    assert "d1" in ctx.state.pending


def test_unsupported_content_is_reported(ctx, tmp_path):
    alice = ctx.identity.by_student("alice").comms_id
    apply.apply_item(item(tmp_path, **{"from": alice, "kind": "text", "text": "", "unsupported": "voice"}), ctx)
    assert "голосовое" in staged(ctx)[0]["text"] and ctx.state.pending == {}


def test_download_error_is_not_a_submission(ctx, tmp_path, journal_root):
    alice = ctx.identity.by_student("alice").comms_id
    it = item(tmp_path, **{"from": alice, "kind": "photo", "files": [], "download_error": "timeout"})
    apply.apply_item(it, ctx)
    assert "файл не дошёл" in staged(ctx)[0]["text"]
    assert mark(journal_root, "python-01-first-run", "alice").status == "issued"
    assert ctx.state.pending == {}


def test_github_submission(ctx, journal_root):
    alice = ctx.identity.by_student("alice").comms_id
    apply.handle_github(ctx, [Submission("alice", alice, "python-01-first-run", "abc1234def", 2, 0, "2 passed")])
    m = mark(journal_root, "python-01-first-run", "alice")
    assert m.status == "submitted" and m.by == "github" and "abc1234" in m.note
    notice = staged(ctx)[0]
    assert "тесты 2/2" in notice["text"] and ctx.state.pending[notice["id"]]["kind"] == "submission"


def test_github_submission_log_escaped_once(ctx, journal_root):
    alice = ctx.identity.by_student("alice").comms_id
    apply.handle_github(ctx, [Submission("alice", alice, "python-01-first-run", "abc1234def", 1, 1,
                                         "assert 1 < 2\nFAILED")])
    notice = staged(ctx)[0]
    assert notice["text"].count("&lt;") == 1 and "&amp;lt;" not in notice["text"]


def test_github_unknown_student_is_skipped(ctx, journal_root):
    apply.handle_github(ctx, [Submission("zed", "s-unknown", "python-01-first-run", "abc1234def", 2, 0, "2 passed")])
    notice = staged(ctx)[0]
    assert notice["to"] == "teacher" and "zed" in notice["text"] and "не заведён" in notice["text"]
    assert ctx.state.pending == {}


def test_teacher_claude_command(ctx, tmp_path):
    apply.apply_item(item(tmp_path, kind="text", text="/claude напомни всем про зачёт"), ctx)
    d = staged(ctx)[0]
    assert "Черновик от Claude." in d["text"] and ctx.state.pending[d["id"]]["target"] == "group"
    assert ctx.state.pending[d["id"]]["max_copy"] is True


def test_plain():
    assert apply.plain("<b>Итог</b> &amp; <a href=\"u\">ссылка</a>") == "Итог & ссылка"
