from datetime import datetime, timedelta

from comms.state import State


def test_processed_and_prune(tmp_path):
    st = State(tmp_path / "state.json")
    now = datetime(2026, 9, 28, 12, 0)
    assert not st.processed("a")
    st.mark_processed("a", now)
    st.mark_processed("b", now - timedelta(days=40))
    st.prune(now)
    assert st.processed("a") and not st.processed("b")


def test_pending_github_tick_survive_reload(tmp_path):
    st = State(tmp_path / "state.json")
    st.pending["x"] = {"kind": "post"}
    st.github["s-1"] = {"sha": "abc"}
    st.tick += 1
    st.save()
    again = State(tmp_path / "state.json")
    assert again.pending == {"x": {"kind": "post"}} and again.github["s-1"]["sha"] == "abc" and again.tick == 1
