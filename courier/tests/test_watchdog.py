import asyncio
import json
import os
import time
from datetime import datetime, timedelta

from courier.config import Config
from courier.queue import Queue
from courier.watchdog import Watchdog, write_status


class FakeBot:
    def __init__(self):
        self.online, self.sent = True, []

    async def get_me(self):
        if not self.online:
            raise RuntimeError("no network")

    async def send_message(self, chat_id, text, **kw):
        self.sent.append((chat_id, text))


def setup(tmp_path):
    cfg = Config(bot_token="t", queue_dir=tmp_path / "q", registry_path=tmp_path / "r.json",
                 group_chat_id=-100, teacher_telegram_id=42, brain_silent_minutes=30, heartbeat_hour=9)
    q = Queue(cfg.queue_dir)
    q.touch_pull()
    bot = FakeBot()
    return cfg, q, bot, Watchdog(cfg, q, bot)


def run(coro):
    return asyncio.run(coro)


def pulled_at(q, when: datetime):
    """Ставит маркер последнего pull ровно на синтетическое время тика,
    чтобы last_pull_age не подглядывал в реальные часы."""
    q.touch_pull()
    ts = when.timestamp()
    os.utime(q.root / ".last_pull", (ts, ts))


def test_heartbeat_once_per_day_after_hour(tmp_path):
    cfg, q, bot, wd = setup(tmp_path)
    pulled_at(q, datetime(2026, 9, 28, 8, 59))
    assert run(wd.tick(datetime(2026, 9, 28, 8, 59))) == []
    pulled_at(q, datetime(2026, 9, 28, 9, 0))
    notices = run(wd.tick(datetime(2026, 9, 28, 9, 0)))
    assert len(notices) == 1 and "жив" in notices[0]
    pulled_at(q, datetime(2026, 9, 28, 15, 0))
    assert run(wd.tick(datetime(2026, 9, 28, 15, 0))) == []
    next_day = datetime(2026, 9, 29, 9, 30)
    pulled_at(q, next_day)
    assert len(run(wd.tick(next_day))) == 1


def test_outage_then_recovery_notifies(tmp_path):
    cfg, q, bot, wd = setup(tmp_path)
    wd.last_heartbeat_day = datetime(2026, 9, 28).date()
    bot.online = False
    pulled_at(q, datetime(2026, 9, 28, 12, 0))
    assert run(wd.tick(datetime(2026, 9, 28, 12, 0))) == [] and wd.outage_since == datetime(2026, 9, 28, 12, 0)
    pulled_at(q, datetime(2026, 9, 28, 12, 1))
    run(wd.tick(datetime(2026, 9, 28, 12, 1)))
    bot.online = True
    pulled_at(q, datetime(2026, 9, 28, 12, 8))
    notices = run(wd.tick(datetime(2026, 9, 28, 12, 8)))
    assert len(notices) == 1 and "8 мин" in notices[0] and wd.outage_since is None


def test_short_outage_is_silent(tmp_path):
    cfg, q, bot, wd = setup(tmp_path)
    wd.last_heartbeat_day = datetime(2026, 9, 28).date()
    bot.online = False
    pulled_at(q, datetime(2026, 9, 28, 12, 0))
    run(wd.tick(datetime(2026, 9, 28, 12, 0)))
    bot.online = True
    pulled_at(q, datetime(2026, 9, 28, 12, 1))
    assert run(wd.tick(datetime(2026, 9, 28, 12, 1))) == []


def test_brain_silent_notified_once_until_pull(tmp_path):
    cfg, q, bot, wd = setup(tmp_path)
    wd.last_heartbeat_day = datetime.now().date()          # heartbeat сегодня уже был
    old = time.time() - 31 * 60
    os.utime(q.root / ".last_pull", (old, old))
    now = datetime.now()
    notices = run(wd.tick(now))
    assert len(notices) == 1 and "молчит" in notices[0]
    assert run(wd.tick(now + timedelta(minutes=1))) == []
    q.touch_pull()
    run(wd.tick(now + timedelta(minutes=2)))
    assert wd.brain_silent_notified is False


def test_missing_marker_counts_as_silent_after_threshold(tmp_path):
    cfg, q, bot, wd = setup(tmp_path)
    (q.root / ".last_pull").unlink()          # свежая очередь: Mac ещё ни разу не забирал
    wd.last_heartbeat_day = datetime(2026, 9, 28).date()
    t0 = datetime(2026, 9, 28, 12, 0)
    assert run(wd.tick(t0)) == [] and wd.started_at == t0
    notices = run(wd.tick(t0 + timedelta(minutes=31)))
    assert len(notices) == 1 and "молчит" in notices[0]
    assert run(wd.tick(t0 + timedelta(minutes=32))) == []
    pulled_at(q, t0 + timedelta(minutes=33))
    run(wd.tick(t0 + timedelta(minutes=33)))
    assert wd.brain_silent_notified is False


def test_write_status(tmp_path):
    cfg, q, bot, wd = setup(tmp_path)
    path = write_status(q, cfg, datetime(2026, 9, 28, 12, 0), online=True, outage_since=None)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["online"] is True and data["sizes"]["inbox"] == 0 and data["ts"].startswith("2026-09-28T12:00")
