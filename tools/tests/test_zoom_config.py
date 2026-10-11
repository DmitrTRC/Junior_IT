import pytest

from zoom_pipeline.config import ConfigError, load_config


def write_files(tmp_path, toml_text=None, env_text=None):
    toml_path = tmp_path / "zoom-pipeline.toml"
    env_path = tmp_path / "zoom.env"
    toml_path.write_text(toml_text if toml_text is not None else (
        f'repo_root = "{tmp_path}/repo"\n'
        'backup_dir = "/Volumes/backup/JuniorIT/recordings"\n'
        'retention_days = 30\n'
        'student_stems = ["Наст"]\n'
    ), encoding="utf-8")
    env_path.write_text(env_text if env_text is not None else (
        "ZOOM_ACCOUNT_ID=acc\nZOOM_CLIENT_ID=cid\nZOOM_CLIENT_SECRET=sec\n"
    ), encoding="utf-8")
    return toml_path, env_path


def test_loads_and_derives_paths(tmp_path):
    toml_path, env_path = write_files(tmp_path)
    cfg = load_config(toml_path, env_path)
    assert cfg.recordings_dir == tmp_path / "repo" / "recordings"
    assert cfg.drafts_dir == tmp_path / "repo" / "meta" / "drafts"
    assert cfg.retention_days == 30
    assert cfg.zoom_client_secret == "sec"
    assert cfg.whisper_cmd[0] == "uvx"
    assert cfg.state_path.name == "zoom-state.json"


def test_missing_env_key_raises(tmp_path):
    toml_path, env_path = write_files(tmp_path, env_text="ZOOM_ACCOUNT_ID=acc\n")
    with pytest.raises(ConfigError):
        load_config(toml_path, env_path)


def test_missing_toml_raises(tmp_path):
    _, env_path = write_files(tmp_path)
    with pytest.raises(ConfigError):
        load_config(tmp_path / "нет.toml", env_path)


def test_loads_analysis_settings_without_zoom_credentials(tmp_path):
    toml_path, env_path = write_files(tmp_path)
    with toml_path.open('a') as handle:
        handle.write('\n[analysis]\nengine="codex"\ncommand="/bin/codex"\nmodel="chosen-model"\nreasoning_effort="high"\n')
    env_path.unlink()
    cfg = load_config(toml_path, env_path, require_zoom=False)
    assert cfg.analysis_command == '/bin/codex'
    assert cfg.analysis_model == 'chosen-model'
    assert cfg.analysis_reasoning_effort == 'high'
    assert not cfg.zoom_client_secret


@pytest.mark.parametrize('extra', [
    '\nclaude_cmd=["claude"]\n',
    '\n[analysis]\nengine="claude"\n',
    '\n[analysis]\ncommand=["codex"]\n',
    '\n[analysis]\nmodel=""\n',
    '\n[analysis]\nreasoning_effort="unlimited"\n',
    '\n[analysis]\nallow_tools=true\n',
])
def test_rejects_unsafe_or_legacy_analysis_config(tmp_path, extra):
    toml_path, env_path = write_files(tmp_path)
    with toml_path.open('a') as handle:
        handle.write(extra)
    with pytest.raises(ConfigError):
        load_config(toml_path, env_path)
