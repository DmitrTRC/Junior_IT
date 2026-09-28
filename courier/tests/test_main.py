import asyncio

from courier.config import Config
from courier.main import make_bot, parse_args, supervise


def test_parse_args_defaults():
    args = parse_args([])
    assert str(args.config) == "/srv/courier/courier.toml" and str(args.env) == "/srv/courier/courier.env"


def test_make_bot_with_and_without_proxy(tmp_path):
    base = dict(bot_token="123:abc", queue_dir=tmp_path, registry_path=tmp_path / "r.json",
                group_chat_id=-1, teacher_telegram_id=1)
    with_proxy = make_bot(Config(**base, proxy="socks5://127.0.0.1:1080"))
    assert with_proxy.session.proxy == "socks5://127.0.0.1:1080"
    assert make_bot(Config(**base)).session.proxy is None


def test_supervise_returns_name_of_crashed_task():
    async def crash():
        await asyncio.sleep(0)
        raise RuntimeError("boom")

    async def scenario():
        stop = asyncio.Event()
        sleeper = asyncio.create_task(asyncio.sleep(10), name="sleeper")
        crasher = asyncio.create_task(crash(), name="crasher")
        tasks = {"sleeper": sleeper, "crasher": crasher}
        failed = await supervise(stop, tasks)
        assert failed == "crasher"
        assert stop.is_set()
        sleeper.cancel()
        await asyncio.gather(sleeper, return_exceptions=True)

    asyncio.run(scenario())


def test_supervise_returns_none_on_stop():
    async def scenario():
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        loop.call_later(0.01, stop.set)
        tasks = {
            "a": asyncio.create_task(asyncio.sleep(10), name="a"),
            "b": asyncio.create_task(asyncio.sleep(10), name="b"),
        }
        failed = await supervise(stop, tasks)
        assert failed is None
        for task in tasks.values():
            task.cancel()
        await asyncio.gather(*tasks.values(), return_exceptions=True)

    asyncio.run(scenario())
