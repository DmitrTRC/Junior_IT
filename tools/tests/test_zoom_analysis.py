from datetime import datetime, timedelta, timezone
import pytest

from zoom_pipeline.analysis import (AnalysisError, HEADINGS, classify_error,
                                    validate_markdown)


def valid_analysis():
    return '\n\n'.join(f'## {title}\nСодержание.' for title in HEADINGS)


def test_accepts_six_nonempty_sections():
    assert validate_markdown(valid_analysis()) == valid_analysis()


@pytest.mark.parametrize('transform', [
    lambda s: 'Ошибка авторизации\n' + s,
    lambda s: '```markdown\n' + s + '\n```',
    lambda s: s.replace('## Где буксовали', '## Где буксовали\nТекст.\n## Где буксовали'),
    lambda s: s.replace('## Cutting plan', '## Другой раздел'),
    lambda s: s.replace('## Фактические тайминги\nСодержание.', '## Фактические тайминги'),
    lambda s: s.replace('## Где буксовали', '```\n## Где буксовали\n```'),
    lambda s: s.replace('## Где буксовали', '## Cutting plan').replace('## Cutting plan\nСодержание.\n\n## Рекомендации', '## Где буксовали\nСодержание.\n\n## Рекомендации'),
])
def test_rejects_invalid_sections(transform):
    with pytest.raises(AnalysisError, match='invalid_output'):
        validate_markdown(transform(valid_analysis()))


def test_allows_nested_headings_and_code_in_sections():
    result = valid_analysis().replace('Содержание.', 'Содержание.\n### Детали\n```python\n## не раздел\nprint(1)\n```', 1)
    assert validate_markdown(result) == result


@pytest.mark.parametrize('message,code,retryable,blocked', [
    ('Your account has been suspended', 'account_blocked', False, True),
    ('Your organization has been placed on hold', 'account_blocked', False, True),
    ('Your account has been deactivated', 'account_blocked', False, True),
    ('Please log in again', 'authentication', False, True),
    ('model not found', 'model_unavailable', False, True),
    ("model 'chosen' is not supported", 'model_unavailable', False, True),
    ('insufficient_quota', 'quota', False, True),
    ('HTTP 503 service unavailable', 'service_unavailable', True, False),
    ('connection reset by peer', 'network', True, False),
    ('HTTP 429 rate limit exceeded', 'rate_limit', True, False),
    ('something unknown with private-content', 'unknown', False, False),
])
def test_error_classification_does_not_expose_raw_text(message, code, retryable, blocked):
    error = classify_error(message, datetime(2026, 10, 11, tzinfo=timezone.utc))
    assert (error.code, error.retryable, error.global_block) == (code, retryable, blocked)
    assert str(error) == code


def test_explicit_retry_delay_is_preserved():
    now = datetime(2026, 10, 11, tzinfo=timezone.utc)
    error = classify_error('HTTP 429 retry-after: 18000', now)
    assert error.retry_at == now + timedelta(hours=5)


@pytest.fixture
def adapter_setup(tmp_path, monkeypatch):
    from zoom_pipeline.config import Config
    home = tmp_path / 'auth-home'
    home.mkdir()
    (home / 'auth.json').write_text('{}')
    monkeypatch.setenv('CODEX_HOME', str(home))
    cfg = Config(repo_root=tmp_path, backup_dir=tmp_path, retention_days=30,
                 student_stems=[], zoom_account_id='', zoom_client_id='',
                 zoom_client_secret='', state_path=tmp_path / 'state.json')
    return cfg, home


def adapter_runner(answer=None, code=0, stderr='', event=None):
    import json
    import subprocess
    from pathlib import Path
    def runner(cmd, *, timeout, stdin_text=None, env=None):
        if cmd[1:4] == ['debug', 'models', '--bundled']:
            return subprocess.CompletedProcess(cmd, 0, json.dumps({'models': [{'slug': 'gpt-6-astra'}]}), '')
        if answer is not None:
            Path(cmd[cmd.index('-o') + 1]).write_text(answer)
        return subprocess.CompletedProcess(cmd, code, json.dumps(event) if event else '', stderr)
    return runner


def test_adapter_isolates_home_uses_stdin_and_cleans_output(adapter_setup):
    import json
    from pathlib import Path
    from zoom_pipeline.analysis import analyze
    cfg, auth_home = adapter_setup
    used = []
    success = adapter_runner(valid_analysis())
    def runner(cmd, **kwargs):
        if cmd[1] == 'exec':
            assert kwargs['stdin_text'] == 'private prompt'
            assert 'private prompt' not in cmd
            assert '--ephemeral' in cmd
            assert kwargs['timeout'] == 900
            root = Path(cmd[cmd.index('-C') + 1])
            used.append(root)
            assert Path(kwargs['env']['CODEX_HOME']) == root / 'home'
            assert (root / 'home' / 'auth.json').resolve() == auth_home / 'auth.json'
            catalog = json.loads((root / 'catalog.json').read_text())
            assert catalog['models'][0]['apply_patch_tool_type'] is None
            assert catalog['models'][0]['multi_agent_version'] is None
            assert not (root / 'answer.md').exists()
            assert 'model_providers.zoom-analysis.request_max_retries=0' in cmd
            assert 'model_providers.zoom-analysis.stream_max_retries=0' in cmd
        return success(cmd, **kwargs)
    assert analyze(cfg, 'private prompt', runner) == valid_analysis()
    assert not used[0].exists()


@pytest.mark.parametrize('answer,code,stderr,expected', [
    (None, 0, '', 'missing_output'), ('', 0, '', 'invalid_output'),
    ('Account error', 0, '', 'invalid_output'),
    (valid_analysis(), 1, 'Your account has been suspended', 'account_blocked'),
])
def test_adapter_requires_new_valid_successful_answer(adapter_setup, answer, code, stderr, expected):
    from zoom_pipeline.analysis import analyze
    with pytest.raises(AnalysisError, match=expected):
        analyze(adapter_setup[0], 'prompt', adapter_runner(answer, code, stderr))


def test_adapter_rejects_tool_execution(adapter_setup):
    from zoom_pipeline.analysis import analyze
    event = {'type': 'item.completed', 'item': {'type': 'command_execution'}}
    with pytest.raises(AnalysisError, match='isolation_violation'):
        analyze(adapter_setup[0], 'prompt', adapter_runner(valid_analysis(), event=event))
