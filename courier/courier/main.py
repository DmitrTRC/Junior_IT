from __future__ import annotations
import argparse
import asyncio
import logging
import signal
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from courier.config import Config, load_config
from courier.delivery import deliver_loop
from courier.handlers import build_router
from courier.queue import Queue
from courier.registry import Registry
from courier.watchdog import Watchdog, watchdog_loop

log = logging.getLogger("courier")


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="courier", description="Почтальон: Telegram <-> файловые очереди")
    ap.add_argument("--config", type=Path, default=Path("/srv/courier/courier.toml"))
    ap.add_argument("--env", type=Path, default=Path("/srv/courier/courier.env"))
    return ap.parse_args(argv)


def make_bot(cfg: Config) -> Bot:
    session = AiohttpSession(proxy=cfg.proxy) if cfg.proxy else AiohttpSession()
    return Bot(cfg.bot_token, session=session)


async def run(cfg: Config) -> None:
    queue, registry, bot = Queue(cfg.queue_dir), Registry(cfg.registry_path), make_bot(cfg)
    me = await bot.get_me()
    dp = Dispatcher()
    dp.include_router(build_router(queue, registry, cfg, me.username))
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    polling = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    delivery = asyncio.create_task(deliver_loop(queue, bot, cfg, registry, stop))
    guard = asyncio.create_task(watchdog_loop(Watchdog(cfg, queue, bot), stop))
    await stop.wait()
    await dp.stop_polling()
    await asyncio.gather(polling, delivery, guard, return_exceptions=True)
    await bot.session.close()


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    args = parse_args(argv)
    cfg = load_config(args.config, args.env)
    asyncio.run(run(cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
