from __future__ import annotations
import tomllib
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    bot_token: str
    queue_dir: Path
    registry_path: Path
    group_chat_id: int
    teacher_telegram_id: int
    proxy: str | None = None
    outbox_poll_seconds: int = 5
    brain_silent_minutes: int = 30
    heartbeat_hour: int = 9
    reconnect_notice_minutes: int = 2
    max_attempts: int = 5


def _read_env(env_path: Path) -> dict[str, str]:
    if not env_path.is_file():
        raise ConfigError(f"нет файла секретов: {env_path}")
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    if not values.get("BOT_TOKEN"):
        raise ConfigError(f"в {env_path} нет BOT_TOKEN")
    return values


def load_config(toml_path: Path, env_path: Path) -> Config:
    toml_path, env_path = Path(toml_path), Path(env_path)
    if not toml_path.is_file():
        raise ConfigError(f"нет конфига: {toml_path}")
    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)
    try:
        return Config(
            bot_token=_read_env(env_path)["BOT_TOKEN"],
            queue_dir=Path(data["queue_dir"]),
            registry_path=Path(data["registry_path"]),
            group_chat_id=int(data["group_chat_id"]),
            teacher_telegram_id=int(data["teacher_telegram_id"]),
            proxy=data.get("proxy") or None,
            outbox_poll_seconds=int(data.get("outbox_poll_seconds", 5)),
            brain_silent_minutes=int(data.get("brain_silent_minutes", 30)),
            heartbeat_hour=int(data.get("heartbeat_hour", 9)),
            reconnect_notice_minutes=int(data.get("reconnect_notice_minutes", 2)),
            max_attempts=int(data.get("max_attempts", 5)),
        )
    except KeyError as exc:
        raise ConfigError(f"в {toml_path} нет ключа {exc}") from exc
