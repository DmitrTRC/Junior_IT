import io
import json
from datetime import date

from info.common import (
    Line, as_date, countdown, emit, fmt_day, homework_task, hw_id_from_ref,
    module_dir, next_session, scenario_target, weekday_ru,
)

TODAY = date(2026, 9, 22)


def _s(day, **extra):
    return {"date": day, **extra}


def test_next_session_prefers_nearest_future():
    sessions = [_s(date(2026, 9, 13)), _s(date(2026, 9, 27)), _s(date(2026, 9, 24))]
    session, stale = next_session(sessions, TODAY)
    assert session["date"] == date(2026, 9, 24) and stale is False


def test_next_session_today_counts_as_upcoming():
    session, stale = next_session([_s(date(2026, 9, 13)), _s(TODAY)], TODAY)
    assert session["date"] == TODAY and stale is False


def test_next_session_falls_back_to_last_past():
    session, stale = next_session([_s(date(2026, 9, 13)), _s(date(2026, 9, 20))], TODAY)
    assert session["date"] == date(2026, 9, 20) and stale is True
    assert next_session([], TODAY) == (None, False)


def test_countdown_and_weekday():
    assert countdown(TODAY, TODAY) == "сегодня"
    assert countdown(date(2026, 9, 23), TODAY) == "завтра"
    assert countdown(date(2026, 9, 25), TODAY) == "через 3 дн."
    assert countdown(date(2026, 9, 20), TODAY) == "2 дн. назад"
    assert weekday_ru(date(2026, 9, 23)) == "ср" and weekday_ru(date(2026, 9, 27)) == "вс"
    assert fmt_day(date(2026, 9, 3)) == "03.09"
    assert as_date("2026-09-23") == date(2026, 9, 23) and as_date(TODAY) == TODAY


def test_hw_id_and_paths(tmp_path):
    assert hw_id_from_ref("homework/python-01-first-run") == "python-01-first-run"
    assert hw_id_from_ref("python-01-first-run/") == "python-01-first-run"
    assert homework_task("python-01-first-run") == "homework/python-01-first-run/task.md"
    assert module_dir("python/m-01-first-run", tmp_path) == tmp_path / "tracks" / "python" / "m-01-first-run"
    d = tmp_path / "tracks" / "python" / "m-01-first-run"
    (d / "teacher").mkdir(parents=True)
    assert scenario_target("python/m-01-first-run", tmp_path) == "tracks/python/m-01-first-run/module.yml"
    (d / "teacher" / "scenario.md").write_text("x", encoding="utf-8")
    assert scenario_target("python/m-01-first-run", tmp_path) == "tracks/python/m-01-first-run/teacher/scenario.md"


def test_emit_prints_contract_json():
    buf = io.StringIO()
    emit([Line("занятие", open="playground/x/session.yml", style="ok"), Line("буфер")], out=buf)
    data = json.loads(buf.getvalue())
    assert data == {"lines": [
        {"text": "занятие", "open": "playground/x/session.yml", "style": "ok"},
        {"text": "буфер", "open": None, "style": None}]}
    assert "\\u" not in buf.getvalue()
