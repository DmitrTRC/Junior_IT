"""outbox -> Telegram. Элемент уходит текстом с кнопками, вложения следом документами."""
from __future__ import annotations
import asyncio
import logging

from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramServerError
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from courier.config import Config
from courier.queue import Item, Queue
from courier.registry import Registry

log = logging.getLogger("courier.delivery")
RETRY_AFTER_CAP = 60


def resolve_chat(to: str, cfg: Config, registry: Registry) -> int | None:
    if to == "group":
        return cfg.group_chat_id
    if to == "teacher":
        return cfg.teacher_telegram_id
    return registry.telegram_id_of(to)


def keyboard(buttons: list[dict] | None) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None
    row = [InlineKeyboardButton(text=b["label"], callback_data=b["data"]) for b in buttons]
    return InlineKeyboardMarkup(inline_keyboard=[row])


def apply_control(data: dict, registry: Registry) -> str:
    if data.get("action") == "add_code":
        registry.add_code(str(data["code"]), str(data["comms_id"]))
        return "код добавлен"
    raise ValueError(f"неизвестное control-действие {data.get('action')!r}")


async def _send(item: Item, chat_id: int, bot, queue: Queue) -> None:
    """Досылает текст (если ещё не уходил) и оставшиеся вложения; уже отправленное не повторяет."""
    if item.data.get("message_id") is None:
        message = await bot.send_message(
            chat_id, item.data.get("text") or "", parse_mode=item.data.get("parse_mode") or "HTML",
            reply_markup=keyboard(item.data.get("buttons")), reply_to_message_id=item.data.get("reply_to"))
        item.data["message_id"] = message.message_id
        queue.save(item, "sending")
    sent_files = item.data.setdefault("sent_files", [])
    for name in item.data.get("files") or []:
        if name in sent_files:
            continue
        await bot.send_document(chat_id, FSInputFile(item.files_dir / name), caption=None)
        sent_files.append(name)
        queue.save(item, "sending")


async def _notify_teacher(bot, cfg: Config, text: str) -> None:
    try:
        await bot.send_message(cfg.teacher_telegram_id, text, parse_mode="HTML", reply_markup=None,
                               reply_to_message_id=None)
    except Exception as exc:
        log.warning("не смог уведомить преподавателя: %s", exc)


async def deliver_once(queue: Queue, bot, cfg: Config, registry: Registry) -> int:
    delivered = 0
    for item in queue.items("outbox"):
        to = item.data.get("to", "")
        if to == "courier":
            try:
                result = apply_control(item.data, registry)
            except Exception as exc:
                queue.move(item.id, "outbox", "failed")
                await _notify_teacher(bot, cfg, f"Control-элемент {item.id} не применён: {exc}")
                log.warning("control %s не применён: %s", item.id, exc)
                continue
            log.info("control %s: %s", item.id, result)
            queue.move(item.id, "outbox", "sent")
            continue
        chat_id = resolve_chat(to, cfg, registry)
        if chat_id is None:
            queue.move(item.id, "outbox", "failed")
            await _notify_teacher(bot, cfg, f"Не доставлено {item.id}: адресат {to} не зарегистрирован.")
            continue
        queue.move(item.id, "outbox", "sending")
        item = queue.load("sending", item.id)               # files_dir после move должен указывать на новый каталог
        try:
            await _send(item, chat_id, bot, queue)
        except (TelegramNetworkError, TelegramServerError, TelegramRetryAfter) as exc:
            queue.move(item.id, "sending", "outbox")      # сеть, а не элемент: попытку не тратим
            log.warning("сеть при доставке %s: %s", item.id, exc)
            if isinstance(exc, TelegramRetryAfter):
                await asyncio.sleep(min(int(exc.retry_after), RETRY_AFTER_CAP))
            break
        except Exception as exc:
            item.data["attempts"] = int(item.data.get("attempts", 0)) + 1
            item.data["last_error"] = str(exc)[:200]
            queue.save(item, "sending")
            if item.data["attempts"] >= cfg.max_attempts:
                queue.move(item.id, "sending", "failed")
                await _notify_teacher(bot, cfg, f"Не доставлено {item.id} после {cfg.max_attempts} попыток: {exc}")
            else:
                queue.move(item.id, "sending", "outbox")
            log.warning("доставка %s не удалась: %s", item.id, exc)
            continue
        queue.move(item.id, "sending", "sent")
        delivered += 1
    return delivered


async def deliver_loop(queue: Queue, bot, cfg: Config, registry: Registry, stop: asyncio.Event) -> None:
    for item in queue.items("sending"):                    # хвост после падения процесса
        queue.move(item.id, "sending", "outbox")
    while not stop.is_set():
        try:
            await deliver_once(queue, bot, cfg, registry)
        except Exception as exc:
            log.exception("цикл доставки: %s", exc)
        try:
            await asyncio.wait_for(stop.wait(), timeout=cfg.outbox_poll_seconds)
        except asyncio.TimeoutError:
            pass
