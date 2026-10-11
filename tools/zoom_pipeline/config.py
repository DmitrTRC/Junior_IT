import tomllib
from dataclasses import dataclass, field
from pathlib import Path

API_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 1800
RSYNC_TIMEOUT = 1800
WHISPER_TIMEOUT = 3600
ANALYSIS_TIMEOUT = 900
NOTIFY_TIMEOUT = 10

ENV_KEYS = ("ZOOM_ACCOUNT_ID", "ZOOM_CLIENT_ID", "ZOOM_CLIENT_SECRET")


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    repo_root: Path
    backup_dir: Path
    retention_days: int
    student_stems: list[str]
    zoom_account_id: str
    zoom_client_id: str
    zoom_client_secret: str
    state_path: Path
    whisper_cmd: list[str] = field(default_factory=lambda: [
        "uvx", "mlx_whisper", "--model",
        "mlx-community/whisper-large-v3-mlx", "--language", "ru",
        "--output-format", "txt",
        # без этого whisper зацикливается на хвостовой тишине записи
        "--condition-on-previous-text", "False",
    ])
    analysis_engine: str = "codex"
    analysis_command: str = "codex"
    analysis_model: str = "gpt-6-astra"
    analysis_reasoning_effort: str = "medium"

    @property
    def recordings_dir(self):
        return self.repo_root / "recordings"

    @property
    def drafts_dir(self):
        return self.repo_root / "meta" / "drafts"

    @property
    def playground_dir(self):
        return self.repo_root / "playground"


def _read_env(env_path):
    if not env_path.is_file():
        raise ConfigError(f"нет файла секретов: {env_path}")
    values = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    missing = [k for k in ENV_KEYS if not values.get(k)]
    if missing:
        raise ConfigError(f"в {env_path} нет ключей: {', '.join(missing)}")
    return values


def load_config(toml_path, env_path, *, require_zoom=True):
    if not toml_path.is_file():
        raise ConfigError(f"нет конфига: {toml_path}")
    with open(toml_path, "rb") as fh:
        data = tomllib.load(fh)
    try:
        repo_root = Path(data["repo_root"])
        backup_dir = Path(data["backup_dir"])
        retention_days = int(data["retention_days"])
        student_stems = list(data["student_stems"])
    except KeyError as exc:
        raise ConfigError(f"в {toml_path} нет ключа {exc}") from exc
    analysis = data.get("analysis", {})
    if not isinstance(analysis, dict):
        raise ConfigError("analysis должна быть таблицей TOML")
    if "claude_cmd" in data or "claude_cmd" in analysis:
        raise ConfigError("claude_cmd больше не поддерживается; используйте [analysis]")
    unknown = set(analysis) - {"engine", "command", "model", "reasoning_effort"}
    if unknown:
        raise ConfigError("неизвестные настройки analysis")
    defaults = {"engine": "codex", "command": "codex", "model": "gpt-6-astra",
                "reasoning_effort": "medium"}
    analysis = defaults | analysis
    if any(not isinstance(value, str) or not value.strip() for value in analysis.values()):
        raise ConfigError("настройки analysis должны быть непустыми строками")
    if analysis["engine"] != "codex":
        raise ConfigError("поддерживается только analysis.engine = codex")
    if analysis["reasoning_effort"] not in {"minimal", "low", "medium", "high", "xhigh"}:
        raise ConfigError("неподдерживаемый analysis.reasoning_effort")
    env = _read_env(env_path) if require_zoom else dict.fromkeys(ENV_KEYS, "")
    return Config(
        repo_root=repo_root,
        backup_dir=backup_dir,
        retention_days=retention_days,
        student_stems=student_stems,
        zoom_account_id=env["ZOOM_ACCOUNT_ID"],
        zoom_client_id=env["ZOOM_CLIENT_ID"],
        zoom_client_secret=env["ZOOM_CLIENT_SECRET"],
        state_path=env_path.parent / "zoom-state.json",
        analysis_engine=analysis["engine"],
        analysis_command=analysis["command"],
        analysis_model=analysis["model"],
        analysis_reasoning_effort=analysis["reasoning_effort"],
    )
