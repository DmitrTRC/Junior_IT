import asyncio
from types import SimpleNamespace as NS

from courier.config import Config
from courier.delivery import apply_control, deliver_once, keyboard, resolve_chat
from courier.queue import Queue
from courier.registry import Registry


class FakeBot:
    def __init__(self, fail_times=0):
        self.sent, self.docs, self.fail_times, self.next_id = [], [], fail_times, 100

    async def send_message(self, chat_id, text, parse_mode=None, reply_markup=None, reply_to_message_id=None):
        if self.fail_times:
            self.fail_times -= 1
            raise RuntimeError("network")
        self.next_id += 1
        self.sent.append((chat_id, text, reply_markup, reply_to_message_id))
        return NS(message_id=self.next_id)

    async def send_document(self, chat_id, document, caption=None):
        self.docs.append((chat_id, document.path if hasattr(document, "path") else document, caption))
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
    assert apply_control({"action": "nope"}, reg).startswith("неизвестное")
