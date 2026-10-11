import json
import stat
from datetime import datetime, timedelta, timezone

import pytest

from zoom_pipeline.state import PHASES, State, StateError


def test_unknown_uuid_is_new(tmp_path):
    state = State.load(tmp_path / "s.json")
    assert state.phase("x") == "new"


def test_advance_persists_and_reloads(tmp_path):
    path = tmp_path / "s.json"
    state = State.load(path)
    state.advance("u1", "downloaded", date="2026-09-16", topic="Python")
    reloaded = State.load(path)
    assert reloaded.phase("u1") == "downloaded"
    assert reloaded.meta("u1")["topic"] == "Python"


def test_broken_json_stops(tmp_path):
    path = tmp_path / "s.json"
    path.write_text("{оборвано", encoding="utf-8")
    with pytest.raises(StateError):
        State.load(path)


def test_uuids_in_phase(tmp_path):
    state = State.load(tmp_path / "s.json")
    state.advance("u1", "backed_up", date="2026-09-16")
    state.advance("u2", "analyzed", date="2026-09-13")
    assert state.uuids_in_phase("backed_up") == ["u1"]
    assert PHASES[-1] == "cloud_deleted"


def test_advance_keeps_first_date_and_topic(tmp_path):
    state = State.load(tmp_path / "s.json")
    state.advance("u1", "downloaded", date="2026-09-16", topic="Python")
    state.advance("u1", "backed_up", date="2026-01-01", topic="другое")
    assert state.phase("u1") == "backed_up"
    assert state.meta("u1") == {"date": "2026-09-16", "topic": "Python"}


NOW = datetime(2026, 10, 11, tzinfo=timezone.utc)


def pending(tmp_path):
    state = State.load(tmp_path / 'state.json')
    state.advance('u', 'transcribed')
    return state


def test_retry_budget_persists_and_deadlines_are_inclusive(tmp_path):
    state = pending(tmp_path)
    now = NOW
    for attempt, hours in [(1, 1), (2, 4), (3, None)]:
        assert state.analysis_allowed('u', now)
        state.begin_analysis('u', now)
        state = State.load(tmp_path / 'state.json')
        assert state.analysis('u')['status'] == 'running'
        assert state.analysis('u')['attempts'] == attempt
        assert not state.analysis_allowed('u', now)
        state.fail_analysis('u', 'timeout', now, retryable=True)
        state = State.load(tmp_path / 'state.json')
        if hours:
            now += timedelta(hours=hours)
            assert not state.analysis_allowed('u', now - timedelta(microseconds=1))
        else:
            assert state.analysis('u')['status'] == 'exhausted'
            assert not state.analysis_allowed('u', now + timedelta(days=100))


def test_later_server_deadline_wins(tmp_path):
    state = pending(tmp_path)
    state.begin_analysis('u', NOW)
    later = NOW + timedelta(days=2)
    state.fail_analysis('u', 'rate_limit', NOW, retryable=True, retry_at=later)
    assert not state.analysis_allowed('u', later - timedelta(seconds=1))
    assert state.analysis_allowed('u', later)


def test_global_block_and_individual_resume_are_independent(tmp_path):
    state = pending(tmp_path)
    state.advance('v', 'transcribed')
    state.begin_analysis('u', NOW)
    state.fail_analysis('u', 'auth', NOW, global_block=True)
    state = State.load(tmp_path / 'state.json')
    assert state.engine_block == 'auth'
    assert not state.analysis_allowed('v', NOW)
    state.resume_analysis('u')
    assert state.analysis('u')['attempts'] == 0
    assert not state.analysis_allowed('u', NOW)
    state.resume_engine()
    assert state.analysis_allowed('u', NOW)
    assert state.analysis_allowed('v', NOW)


def test_resume_engine_does_not_clear_entry_block(tmp_path):
    state = pending(tmp_path)
    state.begin_analysis('u', NOW)
    state.fail_analysis('u', 'auth', NOW, global_block=True)
    state.resume_engine()
    assert state.analysis('u')['status'] == 'blocked'
    assert state.analysis('u')['attempts'] == 1


def test_interrupted_attempt_is_not_retried(tmp_path):
    state = pending(tmp_path)
    state.begin_analysis('u', NOW)
    state = State.load(tmp_path / 'state.json')
    state.recover_interrupted()
    state = State.load(tmp_path / 'state.json')
    assert state.analysis('u') == dict(status='blocked', attempts=1,
                                      next_attempt_at=None, last_error_code='interrupted')
    assert not state.analysis_allowed('u', NOW)


def test_success_and_resume_phase_guard(tmp_path):
    state = pending(tmp_path)
    state.begin_analysis('u', NOW)
    state.complete_analysis('u')
    reloaded = State.load(tmp_path / 'state.json')
    assert reloaded.phase('u') == 'analyzed'
    assert reloaded.analysis('u')['status'] == 'succeeded'
    with pytest.raises(StateError):
        reloaded.resume_analysis('u')


def test_migration_preserves_phase_and_blocks_untracked(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text(json.dumps({'u': {'phase': 'transcribed', 'date': '2026-10-01'},
                                'v': {'phase': 'analyzed', 'topic': 'Python'}}))
    state = State.load(path)
    assert state.analysis('u')['last_error_code'] == 'legacy_untracked'
    assert not state.analysis_allowed('u', NOW)
    assert state.phase('v') == 'analyzed'
    state.resume_analysis('u')
    assert json.loads(path.read_text())['version'] == 2


@pytest.mark.parametrize('raw', [[], None, {'version': 3, 'entries': {}},
    {'version': 2, 'entries': [], 'analysis_block': None},
    {'u': {'phase': 'oops'}}, {'u': []},
    {'version': 2, 'entries': {'u': {'phase': 'transcribed'}}, 'analysis_block': None}])
def test_invalid_schema_stops(tmp_path, raw):
    path = tmp_path / 'state.json'
    path.write_text(json.dumps(raw))
    with pytest.raises(StateError):
        State.load(path)


def test_lock_is_nonblocking_and_released(tmp_path):
    state = pending(tmp_path)
    other = State.load(tmp_path / 'state.json')
    with state.locked():
        with pytest.raises(StateError):
            with other.locked():
                pytest.fail('second lock acquired')
    with other.locked():
        pass


def test_private_file_access_metadata_and_snapshot(tmp_path):
    state = pending(tmp_path)
    state.advance('u', 'transcribed', share_url='https://example.invalid', passcode='test')
    state = State.load(tmp_path / 'state.json')
    assert state.meta('u')['passcode'] == 'test'
    assert stat.S_IMODE((tmp_path / 'state.json').stat().st_mode) == 0o600
    snapshot = state.analysis('u')
    snapshot['attempts'] = 99
    assert state.analysis('u')['attempts'] == 0


def test_invalid_transitions_and_naive_clock_fail(tmp_path):
    state = pending(tmp_path)
    with pytest.raises(StateError):
        state.analysis_allowed('u', datetime(2026, 10, 11))
    with pytest.raises(StateError):
        state.fail_analysis('u', 'unknown', NOW)
    state.begin_analysis('u', NOW)
    with pytest.raises(StateError):
        state.begin_analysis('u', NOW)
    state.fail_analysis('u', 'unknown', NOW)
    assert state.analysis('u')['status'] == 'blocked'


def test_atomic_replace_failure_keeps_previous_state(tmp_path, monkeypatch):
    state = pending(tmp_path)
    path = tmp_path / 'state.json'
    before = path.read_bytes()

    def fail_replace(*args):
        raise OSError('injected replace failure')

    monkeypatch.setattr('zoom_pipeline.state.os.replace', fail_replace)
    with pytest.raises(OSError):
        state.begin_analysis('u', NOW)
    assert path.read_bytes() == before
    assert list(tmp_path.glob('*.tmp')) == []
    assert State.load(path).analysis('u')['status'] == 'pending'


@pytest.mark.parametrize('change', [
    {'status': []}, {'attempts': True}, {'attempts': -1}, {'attempts': 4},
    {'status': 'retry_wait', 'attempts': 1, 'next_attempt_at': 'not a date'},
    {'status': 'retry_wait', 'attempts': 1, 'next_attempt_at': '2026-10-11T00:00:00'},
    {'status': 'running'}, {'status': 'exhausted', 'last_error_code': 'timeout'},
    {'last_error_code': 'raw error with private content'},
])
def test_invalid_analysis_schema_stops(tmp_path, change):
    pending(tmp_path)
    path = tmp_path / 'state.json'
    raw = json.loads(path.read_text())
    raw['entries']['u']['analysis'].update(change)
    path.write_text(json.dumps(raw))
    with pytest.raises(StateError):
        State.load(path)


def test_start_time_is_persisted_only_when_available(tmp_path):
    state = pending(tmp_path)
    assert 'start_time' not in state.meta('u')
    state.advance('u', 'transcribed', start_time='2026-10-11T17:00:00Z')
    assert State.load(tmp_path / 'state.json').meta('u')['start_time'] == '2026-10-11T17:00:00Z'


def test_lock_rejects_another_process(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    state = pending(tmp_path)
    script = '''
import sys
from zoom_pipeline.state import State, StateError
try:
    with State.load(sys.argv[1]).locked():
        sys.exit(2)
except StateError:
    sys.exit(0)
'''
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    with state.locked():
        result = subprocess.run([sys.executable, '-c', script, str(tmp_path / 'state.json')],
                                env=env, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr.decode()


def test_lock_path_precedes_load_even_when_corrupt(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('{broken')
    with State.locked_path(path):
        with pytest.raises(StateError, match='locked'):
            with State.locked_path(path):
                pass
        with pytest.raises(StateError, match='Cannot read'):
            State.load(path)
    with State.locked_path(path):
        pass
