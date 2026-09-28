from __future__ import annotations
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    repo_root: Path
    students_root: Path
    hp_host: str
    hp_queue_dir: str
    local_dir: Path
    state_path: Path
    pages_url: str = "https://dmitrtrc.github.io/Junior_IT/"
    claude_cmd: list[str] = field(default_factory=lambda: ["claude", "-p", "--model", "sonnet"])
    github_poll_every: int = 5
    reminder_hour: int = 12
    digest_hour: int = 18
    telegram_fallback: bool = True
    tests_timeout_s: int = 30


def load_config(toml_path: Path) -> Config:
    toml_path = Path(toml_path)
    if not toml_path.is_file():
        raise ConfigError(f"нет конфига: {toml_path}")
    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)
    try:
        repo_root = Path(data["repo_root"]).expanduser()
        local_dir = Path(data["local_dir"]).expanduser()
        return Config(
            repo_root=repo_root,
            students_root=Path(data.get("students_root") or repo_root / "students").expanduser(),
            hp_host=str(data["hp_host"]),
            hp_queue_dir=str(data["hp_queue_dir"]).rstrip("/"),
            local_dir=local_dir,
            state_path=Path(data.get("state_path") or local_dir / "state.json").expanduser(),
            pages_url=str(data.get("pages_url") or Config.pages_url),
            claude_cmd=list(data.get("claude_cmd") or ["claude", "-p", "--model", "sonnet"]),
            github_poll_every=int(data.get("github_poll_every", 5)),
            reminder_hour=int(data.get("reminder_hour", 12)),
            digest_hour=int(data.get("digest_hour", 18)),
            telegram_fallback=bool(data.get("telegram_fallback", True)),
            tests_timeout_s=int(data.get("tests_timeout_s", 30)),
        )
    except KeyError as exc:
        raise ConfigError(f"в {toml_path} нет ключа {exc}") from exc
