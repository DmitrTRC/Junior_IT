from zoom_pipeline.state import PHASES, State


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


def test_broken_json_starts_clean(tmp_path):
    path = tmp_path / "s.json"
    path.write_text("{оборвано", encoding="utf-8")
    assert State.load(path).phase("u1") == "new"


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
