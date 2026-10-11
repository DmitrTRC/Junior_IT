from pathlib import Path
import pytest
from zoom_pipeline import pipeline
from zoom_pipeline.state import State


def prepare(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, 'CONFIG_DIR', tmp_path)
    (tmp_path / 'zoom-pipeline.toml').write_text(
        f'repo_root="{tmp_path}"\nbackup_dir="{tmp_path}"\nretention_days=30\nstudent_stems=[]\n')
    state = State.load(tmp_path / 'zoom-state.json')
    state.advance('u', 'transcribed', date='2026-10-11', topic='Python', start_time='2026-10-11T17:00:00Z')
    return state


def test_resume_modes_work_without_credentials_or_api(monkeypatch, tmp_path):
    state = prepare(monkeypatch, tmp_path)
    monkeypatch.setattr(pipeline, 'ZoomApi', lambda *args: pytest.fail('network mode'))
    assert pipeline.main(['--resume-analysis', 'u']) == 0
    assert pipeline.main(['--resume-engine']) == 0
    assert State.load(state._path).analysis('u')['status'] == 'pending'


def test_analysis_only_never_calls_api_or_retention(monkeypatch, tmp_path):
    prepare(monkeypatch, tmp_path)
    monkeypatch.setattr(pipeline, 'ZoomApi', lambda *args: pytest.fail('network mode'))
    calls = []
    monkeypatch.setattr(pipeline, 'analyze_recording', lambda *args, **kw: calls.append(args) or True)
    assert pipeline.main(['--analyze-only', 'u']) == 0
    assert len(calls) == 1
    assert calls[0][3].start_time == '2026-10-11T17:00:00Z'


def test_corrupt_state_fails_before_api(monkeypatch, tmp_path):
    state = prepare(monkeypatch, tmp_path)
    state._path.write_text('{broken')
    monkeypatch.setattr(pipeline, 'ZoomApi', lambda *args: pytest.fail('network mode'))
    assert pipeline.main(['--resume-engine']) == 1


def test_unknown_analysis_id_is_error(monkeypatch, tmp_path):
    prepare(monkeypatch, tmp_path)
    assert pipeline.main(['--analyze-only', 'missing']) == 1
