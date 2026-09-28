from courier.config import Config
from courier.main import make_bot, parse_args


def test_parse_args_defaults():
    args = parse_args([])
    assert str(args.config) == "/srv/courier/courier.toml" and str(args.env) == "/srv/courier/courier.env"


def test_make_bot_with_and_without_proxy(tmp_path):
    base = dict(bot_token="123:abc", queue_dir=tmp_path, registry_path=tmp_path / "r.json",
                group_chat_id=-1, teacher_telegram_id=1)
    with_proxy = make_bot(Config(**base, proxy="socks5://127.0.0.1:1080"))
    assert with_proxy.session.proxy == "socks5://127.0.0.1:1080"
    assert make_bot(Config(**base)).session.proxy is None
