"""Сторожок: heartbeat раз в день, «был в отключке», «мозг молчит», status.json для info-панели."""
from __future__ import annotations
import asyncio
import json
import logging
import os
from datetime import date, datetime
from pathlib import Path

from courier.config import Config
from courier.queue import Queue

log = logging.getLogger("courier.watchdog")


def write_status(queue: Queue, cfg: Config, now: datetime, online: bool, outage_since: datetime | None) -> Path:
    path = queue.root / "status.json"
    data = {"ts": now.isoformat(timespec="seconds"), "online": online,
            "outage_since": outage_since.isoformat(timespec="seconds") if outage_since else None,
            "sizes": queue.sizes(), "last_pull_age_s": queue.last_pull_age(now)}
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
    return path


class Watchdog:
    def __init__(self, cfg: Config, queue: Queue, bot):
        self.cfg, self.queue, self.bot = cfg, queue, bot
        self.outage_since: datetime | None = None
        self.last_heartbeat_day: date | None = None
        self.brain_silent_notified = False
        self.started_at: datetime | None = None

    async def _say(self, text: str, notices: list[str]) -> None:
        try:
            await self.bot.send_message(self.cfg.teacher_telegram_id, text)
            notices.append(text)
        except Exception as exc:
            log.warning("сторожок не дозвонился: %s", exc)

    async def tick(self, now: datetime) -> list[str]:
        notices: list[str] = []
        if self.started_at is None:
            self.started_at = now
        try:
            await self.bot.get_me()
            online = True
        except Exception:
            online = False
        if not online:
            if self.outage_since is None:
                self.outage_since = now
            write_status(self.queue, self.cfg, now, False, self.outage_since)
            return notices
        if self.outage_since is not None:
            minutes = int((now - self.outage_since).total_seconds() // 60)
            self.outage_since = None
            if minutes >= self.cfg.reconnect_notice_minutes:
                sizes = self.queue.sizes()
                await self._say(f"Был в отключке {minutes} мин. В очереди: исходящих {sizes['outbox']}, "
                                f"входящих {sizes['inbox']}.", notices)
        if now.hour >= self.cfg.heartbeat_hour and self.last_heartbeat_day != now.date():
            self.last_heartbeat_day = now.date()
            sizes = self.queue.sizes()
            await self._say(f"Почтальон жив. Очередь: исходящих {sizes['outbox']}, входящих {sizes['inbox']}, "
                            f"не доставлено {sizes['failed']}.", notices)
        threshold = self.cfg.brain_silent_minutes * 60
        age = self.queue.last_pull_age(now)
        if age is None:
            age = (now - self.started_at).total_seconds()
        silent = age > threshold
        if silent and not self.brain_silent_notified:
            self.brain_silent_notified = True
            await self._say(f"Мозг молчит {int(age // 60)} мин: Mac не забирал очередь.", notices)
        elif not silent:
            self.brain_silent_notified = False
        write_status(self.queue, self.cfg, now, True, None)
        return notices


async def watchdog_loop(wd: Watchdog, stop: asyncio.Event, interval_s: int = 60) -> None:
    while not stop.is_set():
        try:
            await wd.tick(datetime.now())
        except Exception as exc:
            log.exception("сторожок: %s", exc)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_s)
        except asyncio.TimeoutError:
            pass
