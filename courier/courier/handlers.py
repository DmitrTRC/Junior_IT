"""Входящие из Telegram -> элементы inbox. Чистые сборщики отдельно от aiogram-обвязки."""
from __future__ import annotations
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from courier.config import Config
from courier.queue import Queue
from courier.registry import Registry

log = logging.getLogger("courier.handlers")

UNSUPPORTED = (("voice", "voice"), ("sticker", "sticker"), ("video", "video"), ("video_note", "video"))
NAME_LIMIT = 80


def safe_name(name: str) -> str:
    """Имя файла из Telegram -> безопасное: без каталогов, без скрытых, только ASCII-алфавит."""
    base = Path(name or "").name.lstrip(".")
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base)[:NAME_LIMIT]
    return cleaned if cleaned.strip("._") else "file.bin"


def parse_start(text: str | None) -> str | None:
    if not text or not text.startswith("/start"):
        return None
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 and parts[1].strip() else None


def classify_sender(user_id: int, registry: Registry, cfg: Config) -> str:
    if user_id == cfg.teacher_telegram_id:
        return "teacher"
    return registry.who(user_id) or f"unknown:{user_id}"


def attachment_of(msg) -> tuple[str, str] | None:
    if getattr(msg, "photo", None):
        return msg.photo[-1].file_id, "photo.jpg"
    doc = getattr(msg, "document", None)
    if doc:
        return doc.file_id, safe_name(doc.file_name or "file.bin")
    return None


def _unsupported(msg) -> str | None:
    for attr, label in UNSUPPORTED:
        if getattr(msg, attr, None):
            return label
    return None


def _addressed_to_bot(msg, bot_username: str) -> bool:
    text = msg.text or msg.caption or ""
    if f"@{bot_username}" in text:
        return True
    reply = getattr(msg, "reply_to_message", None)
    return bool(reply and getattr(reply.from_user, "is_bot", False) and reply.from_user.username == bot_username)


def inbox_from_message(msg, registry: Registry, cfg: Config, bot_username: str, queue: Queue | None = None) -> dict | None:
    sender = classify_sender(msg.from_user.id, registry, cfg)
    chat = "private" if msg.chat.type == "private" else "group"
    code = parse_start(msg.text)
    if chat == "private" and code:
        comms_id = registry.bind(code, msg.from_user.id)
        if comms_id:
            item = _item(comms_id, chat, "registered", "", msg)
            item["telegram_id"] = msg.from_user.id
            return item
    if chat == "private" and sender.startswith("unknown:"):
        return None
    if chat == "group" and not _addressed_to_bot(msg, bot_username):
        return None
    kind = "photo" if getattr(msg, "photo", None) else "document" if getattr(msg, "document", None) else "text"
    text = msg.text or msg.caption or ""
    item = _item(sender, chat, kind, text, msg)
    item["unsupported"] = _unsupported(msg)
    reply = getattr(msg, "reply_to_message", None)
    if reply is not None:
        item["reply_to_message_id"] = reply.message_id
        if sender == "teacher" and queue is not None:
            sent = queue.find_sent_by_message(reply.message_id)
            if sent is not None:
                item["kind"] = "reply"
                item["reply_to_item"] = sent.id
    return item


def inbox_from_callback(cb, registry: Registry, cfg: Config) -> dict:
    sender = classify_sender(cb.from_user.id, registry, cfg)
    chat = "private" if cb.message.chat.type == "private" else "group"
    item = _item(sender, chat, "callback", "", cb.message)
    item["callback"] = cb.data
    return item


def _item(sender: str, chat: str, kind: str, text: str, msg) -> dict:
    return {"from": sender, "chat": chat, "kind": kind, "text": text, "message_id": msg.message_id,
            "reply_to_message_id": None, "reply_to_item": None, "callback": None, "unsupported": None,
            "download_error": None, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def build_router(queue: Queue, registry: Registry, cfg: Config, bot_username: str) -> Router:
    router = Router()

    @router.message()
    async def on_message(message: Message):
        item = inbox_from_message(message, registry, cfg, bot_username, queue=queue)
        if item is None:
            return
        files: dict[str, bytes] = {}
        attachment = attachment_of(message)
        download_failed = False
        if attachment:
            file_id, name = attachment
            tmp = Path(cfg.queue_dir) / ".download" / f"{message.chat.id}-{message.message_id}-{name}"
            tmp.parent.mkdir(parents=True, exist_ok=True)
            try:
                await message.bot.download(file_id, destination=tmp)
                files[name] = tmp.read_bytes()
            except Exception as exc:
                log.warning("не смог скачать вложение %s: %s", name, exc)
                item["download_error"] = str(exc)[:200]
                download_failed = True
            finally:
                if tmp.exists():
                    tmp.unlink()
        queue.put("inbox", item, files)
        if item["kind"] == "registered":
            await message.answer("Привязал. Теперь сюда можно присылать домашки и вопросы.")
        elif item["chat"] == "private" and item["from"] != "teacher":
            if download_failed:
                await message.answer("Файл не дошёл до бота, пришли ещё раз.")
            else:
                await message.answer("Получил, передал Димасу.")

    @router.callback_query(F.data)
    async def on_callback(callback: CallbackQuery):
        if callback.from_user.id != cfg.teacher_telegram_id:
            await callback.answer("Кнопки — только для преподавателя.")
            return
        if callback.message is None:
            await callback.answer("Кнопка устарела.")
            return
        queue.put("inbox", inbox_from_callback(callback, registry, cfg))
        await callback.answer("Принято.")

    return router
