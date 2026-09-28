import json
from datetime import datetime, timedelta, timezone

from info import cli, comms

NOW = datetime(2026, 9, 28, 12, 10)


def test_lines_ok():
    status = {"ts": "2026-09-28T12:09:00", "online": True, "sizes": {"outbox": 0, "sending": 0, "sent": 5, "inbox": 2, "failed": 0}}
    last = {"ts": "2026-09-28T12:09:30", "counts": {"errors": 0}, "pending": 3, "inbox_left": 0}
    out = comms.lines(status, last, NOW)
    assert out[0].text == "почтальон: онлайн · исходящих 0 · входящих 2 · не доставлено 0" and out[0].style == "ok"
    assert out[1].text == "мозг: тик 0 мин назад · ждут кнопок 3 · ошибок 0" and out[1].style == "ok"


def test_lines_stale_offline_and_missing():
    status = {"ts": "2026-09-28T11:50:00", "online": False, "sizes": {"outbox": 1, "sending": 0, "sent": 0, "inbox": 0, "failed": 2}}
    last = {"ts": "2026-09-28T12:00:00", "counts": {"errors": 1}, "pending": 0, "inbox_left": 1}
    out = comms.lines(status, last, NOW)
    assert out[0].text.startswith("почтальон: офлайн") and "статус 20 мин назад" in out[0].text and out[0].style == "err"
    assert out[1].text == "мозг: тик 10 мин назад · ждут кнопок 0 · ошибок 1" and out[1].style == "warn"
    none = comms.lines(None, None, NOW)
    assert none[0].text == "почтальон: статус не забирали" and none[0].style == "warn"
    assert none[1].text == "мозг: тик не запускался" and none[1].style == "warn"


def test_age_min_handles_aware_and_garbage():
    msk = timezone(timedelta(hours=3))
    now = datetime(2026, 9, 28, 12, 10, tzinfo=msk)
    assert comms._age_min("2026-09-28T12:00:00+03:00", now) == 10
    assert comms._age_min("2026-09-28T08:10:00+00:00", now) == 60
    assert comms._age_min("2026-09-28T12:00:00", datetime(2026, 9, 28, 12, 10)) == 10
    assert comms._age_min("не время", now) is None and comms._age_min(12345, now) is None
    assert comms._age_min(None, now) is None


def test_cli_box_reads_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("JUNIOR_IT_COMMS_DIR", str(tmp_path))
    (tmp_path / "status.json").write_text(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), "online": True,
                                                       "sizes": {"outbox": 0, "inbox": 0, "failed": 0}}), encoding="utf-8")
    assert cli.run(["comms"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["lines"][0]["text"].startswith("почтальон: онлайн")
