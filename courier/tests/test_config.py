import pytest
import tomllib
from pathlib import Path

from courier.config import ConfigError, load_config

TOML = """
queue_dir = "{q}"
registry_path = "{q}/registry.json"
group_chat_id = -1001
teacher_telegram_id = 42
proxy = "socks5://127.0.0.1:1080"
"""


def test_load_config(tmp_path):
    (tmp_path / "c.toml").write_text(TOML.format(q=tmp_path), encoding="utf-8")
    (tmp_path / "c.env").write_text("BOT_TOKEN=123:abc\n", encoding="utf-8")
    cfg = load_config(tmp_path / "c.toml", tmp_path / "c.env")
    assert cfg.bot_token == "123:abc" and cfg.group_chat_id == -1001 and cfg.teacher_telegram_id == 42
    assert cfg.proxy == "socks5://127.0.0.1:1080" and cfg.outbox_poll_seconds == 5 and cfg.max_attempts == 5


def test_missing_token_is_error(tmp_path):
    (tmp_path / "c.toml").write_text(TOML.format(q=tmp_path), encoding="utf-8")
    (tmp_path / "c.env").write_text("# пусто\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(tmp_path / "c.toml", tmp_path / "c.env")


def test_missing_key_is_error(tmp_path):
    (tmp_path / "c.toml").write_text('queue_dir = "x"\n', encoding="utf-8")
    (tmp_path / "c.env").write_text("BOT_TOKEN=t\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(tmp_path / "c.toml", tmp_path / "c.env")


def test_non_integer_value_is_error(tmp_path):
    (tmp_path / "c.toml").write_text(TOML.format(q=tmp_path).replace("group_chat_id = -1001", 'group_chat_id = "not-an-int"'), encoding="utf-8")
    (tmp_path / "c.env").write_text("BOT_TOKEN=t\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(tmp_path / "c.toml", tmp_path / "c.env")


def test_example_toml_parses():
    example_path = Path(__file__).resolve().parents[1] / "courier.toml.example"
    with open(example_path, "rb") as fh:
        data = tomllib.load(fh)
    assert "queue_dir" in data
