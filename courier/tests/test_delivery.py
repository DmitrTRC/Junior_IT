import asyncio
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from aiogram.exceptions import TelegramEntityTooLarge, TelegramNetworkError, TelegramRetryAfter

from courier.config import Config
from courier.delivery import apply_control, deliver_once, keyboard, resolve_chat
from courier.queue import Queue
from courier.registry import Registry


class FakeBot:
    def __init__(self, fail_times=0, fail_document_times=0):
        self.sent, self.docs, self.next_id = [], [], 100
        self.fail_times, self.fail_document_times = fail_times, fail_document_times

    async def send_message(self, chat_id, text, parse_mode=None, reply_markup=None, reply_to_message_id=None):
        if self.fail_times:
            self.fail_times -= 1
            raise RuntimeError("network")
        self.next_id += 1
        self.sent.append((chat_id, text, reply_markup, reply_to_message_id))
        return NS(message_id=self.next_id)

    async def send_document(self, chat_id, document, caption=None):
        if self.fail_document_times:
            self.fail_document_times -= 1
            raise RuntimeError("network")
        path = document.path if hasattr(document, "path") else document
        assert Path(path).is_file()                       # вложение должно существовать на момент отправки
        self.docs.append((chat_id, path, caption))
        return NS(message_id=0)


def setup(tmp_path, **kw):
    cfg = Config(bot_token="t", queue_dir=tmp_path / "q", registry_path=tmp_path / "r.json",
                 group_chat_id=-100, teacher_telegram_id=42, **kw)
    reg = Registry(cfg.registry_path)
    reg.add_code("A", "s-1")
    reg.bind("A", 7)
    return cfg, Queue(cfg.queue_dir), reg


def test_resolve_chat(tmp_path):
    cfg, _, reg = setup(tmp_path)
    assert resolve_chat("group", cfg, reg) == -100 and resolve_chat("teacher", cfg, reg) == 42
    assert resolve_chat("s-1", cfg, reg) == 7 and resolve_chat("s-9", cfg, reg) is None


def test_keyboard():
    kb = keyboard([{"label": "отправить", "data": "send:1"}, {"label": "нет", "data": "discard:1"}])
    assert [b.text for b in kb.inline_keyboard[0]] == ["отправить", "нет"]
    assert kb.inline_keyboard[0][0].callback_data == "send:1" and keyboard([]) is None


def test_deliver_text_with_buttons_and_file(tmp_path):
    cfg, q, reg = setup(tmp_path)
    item_id = q.put("outbox", {"to": "teacher", "text": "черновик", "parse_mode": "HTML",
                               "buttons": [{"label": "ок", "data": "send:x"}], "reply_to": None},
                    files={"broken.py": b"print('x)"})
    bot = FakeBot()
    assert asyncio.run(deliver_once(q, bot, cfg, reg)) == 1
    assert bot.sent[0][0] == 42 and bot.sent[0][1] == "черновик" and bot.sent[0][2] is not None
    assert bot.docs[0][0] == 42 and str(bot.docs[0][1]).endswith("broken.py")
    sent = q.load("sent", item_id)
    assert sent.data["message_id"] == 101 and q.sizes()["outbox"] == 0


def test_attachment_failure_does_not_duplicate_text(tmp_path):
    cfg, q, reg = setup(tmp_path)
    item_id = q.put("outbox", {"to": "teacher", "text": "с вложениями"},
                    files={"a.txt": b"1", "b.txt": b"2"})
    bot = FakeBot(fail_document_times=1)
    asyncio.run(deliver_once(q, bot, cfg, reg))            # текст ушёл, первое вложение упало
    asyncio.run(deliver_once(q, bot, cfg, reg))            # текст не повторяется, вложения дошли
    assert len(bot.sent) == 1
    assert [Path(d[1]).name for d in bot.docs] == ["a.txt", "b.txt"]
    sent = q.load("sent", item_id)
    assert sent.data["message_id"] is not None


def test_failure_keeps_item_and_counts_attempts(tmp_path):
    cfg, q, reg = setup(tmp_path, max_attempts=2)
    item_id = q.put("outbox", {"to": "group", "text": "x"})
    bot = FakeBot(fail_times=5)
    assert asyncio.run(deliver_once(q, bot, cfg, reg)) == 0
    assert q.load("outbox", item_id).data["attempts"] == 1
    asyncio.run(deliver_once(q, bot, cfg, reg))
    assert q.sizes()["failed"] == 1 and q.sizes()["outbox"] == 0
    assert bot.sent == []                                 # уведомление Димасу тоже упало — не страшно, лог


def test_unknown_recipient_goes_to_failed(tmp_path):
    cfg, q, reg = setup(tmp_path)
    q.put("outbox", {"to": "s-404", "text": "x"})
    bot = FakeBot()
    asyncio.run(deliver_once(q, bot, cfg, reg))
    assert q.sizes()["failed"] == 1 and bot.sent[0][0] == 42 and "s-404" in bot.sent[0][1]


def test_control_add_code(tmp_path):
    cfg, q, reg = setup(tmp_path)
    q.put("outbox", {"to": "courier", "action": "add_code", "code": "ZZ-1", "comms_id": "p-3"})
    asyncio.run(deliver_once(q, FakeBot(), cfg, reg))
    assert reg.codes["ZZ-1"] == "p-3" and q.sizes()["sent"] == 1
    with pytest.raises(ValueError):
        apply_control({"action": "nope"}, reg)


class NetworkBot:
    """Сеть лежит: каждый send_message падает сетевой ошибкой Telegram."""

    def __init__(self, exc):
        self.calls, self.exc = 0, exc

    async def send_message(self, chat_id, text, **kw):
        self.calls += 1
        raise self.exc


def test_network_errors_do_not_burn_attempts(tmp_path):
    cfg, q, reg = setup(tmp_path, max_attempts=2)
    item_id = q.put("outbox", {"to": "group", "text": "x"})
    bot = NetworkBot(TelegramNetworkError(method=None, message="connection reset"))
    for _ in range(10):
        assert asyncio.run(deliver_once(q, bot, cfg, reg)) == 0
    assert bot.calls == 10                                # одна попытка на проход, Димаса не будим
    assert q.sizes() == {"outbox": 1, "sending": 0, "sent": 0, "inbox": 0, "failed": 0}
    assert q.load("outbox", item_id).data.get("attempts", 0) == 0


def test_retry_after_sleeps_capped_and_keeps_item(tmp_path, monkeypatch):
    cfg, q, reg = setup(tmp_path)
    q.put("outbox", {"to": "group", "text": "x"})
    q.put("outbox", {"to": "group", "text": "y"})
    slept = []
    monkeypatch.setattr(asyncio, "sleep", _record(slept))
    bot = NetworkBot(TelegramRetryAfter(method=None, message="flood", retry_after=600))
    assert asyncio.run(deliver_once(q, bot, cfg, reg)) == 0
    assert slept == [60] and bot.calls == 1               # второй элемент в этот проход не трогаем
    assert q.sizes()["outbox"] == 2


def _record(slept):
    async def fake_sleep(seconds):
        slept.append(seconds)
    return fake_sleep


def test_control_unknown_action_goes_to_failed(tmp_path):
    cfg, q, reg = setup(tmp_path)
    q.put("outbox", {"to": "courier", "action": "nope"})
    bot = FakeBot()
    asyncio.run(deliver_once(q, bot, cfg, reg))
    assert q.sizes()["failed"] == 1
    assert len(bot.sent) == 1 and bot.sent[0][0] == 42


class TooLargeBot(FakeBot):
    """Telegram отвечает 413 на элемент с текстом «x»; остальное уходит нормально."""

    async def send_message(self, chat_id, text, parse_mode=None, reply_markup=None, reply_to_message_id=None):
        if text == "x":
            raise TelegramEntityTooLarge(method=None, message="Request Entity Too Large")
        return await super().send_message(chat_id, text, parse_mode, reply_markup, reply_to_message_id)


def test_entity_too_large_counts_attempt_and_does_not_stall(tmp_path):
    cfg, q, reg = setup(tmp_path, max_attempts=2)
    poison = q.put("outbox", {"to": "group", "text": "x"})
    q.put("outbox", {"to": "group", "text": "y"})
    bot = TooLargeBot()
    asyncio.run(deliver_once(q, bot, cfg, reg))           # x: попытка 1, y доставлен в тот же проход
    assert q.load("outbox", poison).data["attempts"] == 1 and q.sizes()["sent"] == 1
    asyncio.run(deliver_once(q, bot, cfg, reg))           # x: попытка 2 -> failed + заметка Димасу
    assert q.sizes() == {"outbox": 0, "sending": 0, "sent": 1, "inbox": 0, "failed": 1}
    assert [s[0] for s in bot.sent] == [-100, 42] and "после 2 попыток" in bot.sent[1][1]
