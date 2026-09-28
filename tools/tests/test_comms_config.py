import pytest

from comms.config import ConfigError, load_config

TOML = """
repo_root = "{r}"
hp_host = "courier@hp"
hp_queue_dir = "/srv/courier/queue"
local_dir = "{r}/comms"
"""


def test_defaults(tmp_path):
    (tmp_path / "c.toml").write_text(TOML.format(r=tmp_path), encoding="utf-8")
    cfg = load_config(tmp_path / "c.toml")
    assert cfg.students_root == tmp_path / "students" and cfg.state_path == tmp_path / "comms" / "state.json"
    assert cfg.pages_url.endswith("/") and cfg.claude_cmd[:2] == ["claude", "-p"]
    assert cfg.github_poll_every == 5 and cfg.reminder_hour == 12 and cfg.digest_hour == 18 and cfg.telegram_fallback


def test_missing_key(tmp_path):
    (tmp_path / "c.toml").write_text('repo_root = "x"\n', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(tmp_path / "c.toml")
