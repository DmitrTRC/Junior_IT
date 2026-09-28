from types import SimpleNamespace as NS

from courier.config import Config
from courier.handlers import attachment_of, classify_sender, inbox_from_callback, inbox_from_message, parse_start
from courier.queue import Queue
from courier.registry import Registry


def cfg(tmp_path):
    return Config(bot_token="t", queue_dir=tmp_path / "q", registry_path=tmp_path / "r.json",
                  group_chat_id=-100, teacher_telegram_id=42)


def registry(tmp_path, **binds):
    reg = Registry(tmp_path / "r.json")
    for comms_id, tg in binds.items():
        reg.add_code(comms_id, comms_id)
        reg.bind(comms_id, tg)
    return reg


def msg(uid=7, chat_id=7, chat_type="private", text="hi", message_id=1, reply=None, **extra):
    base = dict(from_user=NS(id=uid), chat=NS(id=chat_id, type=chat_type), text=text, caption=None,
                message_id=message_id, reply_to_message=reply, photo=None, document=None,
                voice=None, sticker=None, video=None, video_note=None, date=None)
    base.update(extra)
    return NS(**base)


def test_parse_start():
    assert parse_start("/start KX7-42") == "KX7-42" and parse_start("/start") is None and parse_start("hi") is None


def test_classify_sender(tmp_path):
    reg = registry(tmp_path, **{"s-1": 7})
    c = cfg(tmp_path)
    assert classify_sender(42, reg, c) == "teacher"
    assert classify_sender(7, reg, c) == "s-1" and classify_sender(9, reg, c) == "unknown:9"


def test_private_text_from_registered(tmp_path):
    item = inbox_from_message(msg(text="не работает"), registry(tmp_path, **{"s-1": 7}), cfg(tmp_path), "jitbot")
    assert item["from"] == "s-1" and item["chat"] == "private" and item["kind"] == "text"
    assert item["text"] == "не работает" and item["message_id"] == 1 and item["ts"]


def test_private_from_unknown_is_ignored(tmp_path):
    assert inbox_from_message(msg(uid=9, chat_id=9), registry(tmp_path), cfg(tmp_path), "jitbot") is None


def test_group_needs_mention_or_reply_to_bot(tmp_path):
    reg = registry(tmp_path, **{"s-1": 7})
    plain = msg(chat_id=-100, chat_type="supergroup", text="привет всем")
    assert inbox_from_message(plain, reg, cfg(tmp_path), "jitbot") is None
    mention = msg(chat_id=-100, chat_type="supergroup", text="@jitbot а как?")
    assert inbox_from_message(mention, reg, cfg(tmp_path), "jitbot")["chat"] == "group"
    reply = msg(chat_id=-100, chat_type="supergroup", text="а как?",
                reply=NS(message_id=5, from_user=NS(id=1, is_bot=True, username="jitbot")))
    assert inbox_from_message(reply, reg, cfg(tmp_path), "jitbot")["reply_to_message_id"] == 5


def test_photo_and_document(tmp_path):
    reg = registry(tmp_path, **{"s-1": 7})
    photo = msg(text=None, caption="вот", photo=[NS(file_id="small"), NS(file_id="big")])
    item = inbox_from_message(photo, reg, cfg(tmp_path), "jitbot")
    assert item["kind"] == "photo" and item["text"] == "вот" and attachment_of(photo) == ("big", "photo.jpg")
    doc = msg(text=None, document=NS(file_id="d1", file_name="hello.py"))
    assert attachment_of(doc) == ("d1", "hello.py") and inbox_from_message(doc, reg, cfg(tmp_path), "jitbot")["kind"] == "document"


def test_unsupported_content_becomes_note(tmp_path):
    reg = registry(tmp_path, **{"s-1": 7})
    item = inbox_from_message(msg(text=None, voice=NS(file_id="v")), reg, cfg(tmp_path), "jitbot")
    assert item["kind"] == "text" and item["unsupported"] == "voice" and item["text"] == ""
    assert attachment_of(msg(text=None, voice=NS(file_id="v"))) is None


def test_teacher_reply_links_sent_item(tmp_path):
    c = cfg(tmp_path)
    q = Queue(c.queue_dir)
    sent_id = q.put("sent", {"to": "teacher", "text": "вопрос от s-1", "message_id": 77})
    reply = msg(uid=42, chat_id=42, text="ответ", reply=NS(message_id=77, from_user=NS(id=1, is_bot=True, username="jitbot")))
    item = inbox_from_message(reply, registry(tmp_path), c, "jitbot", queue=q)
    assert item["from"] == "teacher" and item["kind"] == "reply" and item["reply_to_item"] == sent_id


def test_start_registers_and_emits_registered(tmp_path):
    reg = registry(tmp_path)
    reg.add_code("KX7-42", "s-9")
    item = inbox_from_message(msg(uid=8, chat_id=8, text="/start KX7-42"), reg, cfg(tmp_path), "jitbot")
    assert item["kind"] == "registered" and item["from"] == "s-9" and item["telegram_id"] == 8 and reg.who(8) == "s-9"
    assert inbox_from_message(msg(uid=8, chat_id=8, text="/start KX7-42"), reg, cfg(tmp_path), "jitbot")["kind"] == "text"


def test_callback(tmp_path):
    cb = NS(id="cb1", from_user=NS(id=42), data="send:01X", message=NS(message_id=9, chat=NS(id=42, type="private")))
    item = inbox_from_callback(cb, registry(tmp_path), cfg(tmp_path))
    assert item == {**item, "from": "teacher", "kind": "callback", "callback": "send:01X", "message_id": 9, "chat": "private"}
