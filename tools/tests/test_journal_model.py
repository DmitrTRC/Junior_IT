from datetime import date

import pytest

from journal.model import (
    HomeworkMark, JournalError, LessonRecord, PointEntry, Tariff,
    lesson_to_dict, num, parse_lesson, parse_roster, parse_tariff,
)

ROSTER = {"students": [
    {"id": "alice", "name": "Алиса", "status": "active", "platform": "mac",
     "joined": "2026-09-09", "zoom_names": ["Алиса", "Alice"], "contacts": {"tg": "@a"}},
    {"id": "bob", "name": "Боб"},
]}
DAY = date(2026, 9, 20)


def test_parse_roster_ok():
    students = parse_roster(ROSTER)
    assert [s.id for s in students] == ["alice", "bob"]
    assert students[0].joined == date(2026, 9, 9) and students[0].zoom_names == ["Алиса", "Alice"]
    assert students[1].status == "active" and students[1].contacts == {}


@pytest.mark.parametrize("bad, needle", [
    ({"students": [{"id": "Bad Id", "name": "x"}]}, "id"),
    ({"students": [{"id": "a", "name": "x"}, {"id": "a", "name": "y"}]}, "дубль"),
    ({"students": [{"id": "a"}]}, "name"),
    ({"students": [{"id": "a", "name": "x", "status": "gone"}]}, "status"),
    ({"students": [{"id": "a", "name": "x", "joined": "вчера"}]}, "дата"),
    ({"students": "nope"}, "students"),
    ({}, "students"),
])
def test_parse_roster_errors(bad, needle):
    with pytest.raises(JournalError, match=needle):
        parse_roster(bad, path="r.yml")


def test_parse_tariff_defaults_and_override():
    assert parse_tariff(None) == Tariff()
    assert parse_tariff({"presence": 5}).presence == 5.0
    with pytest.raises(JournalError, match="неизвестные"):
        parse_tariff({"bonus": 1})


LESSON = {
    "date": DAY,
    "attendance": {"alice": "present", "bob": "late"},
    "homework": {"python-01": {"alice": {"status": "accepted", "at": date(2026, 9, 22)},
                               "bob": {"status": "rework", "note": "без traceback", "reworked": True}}},
    "points": [{"who": "alice", "amount": 2, "reason": "присутствие", "by": "teacher"},
               {"who": "alice", "amount": 0.5, "reason": "зачёт", "by": "telegram"}],
    "notes": {"bob": "опоздал"},
}


def test_parse_lesson_ok():
    rec = parse_lesson(LESSON, DAY, {"alice", "bob"})
    assert rec.attendance == {"alice": "present", "bob": "late"}
    assert rec.homework["python-01"]["alice"] == HomeworkMark("accepted", date(2026, 9, 22))
    assert rec.homework["python-01"]["bob"].reworked is True
    assert rec.points[1] == PointEntry("alice", 0.5, "зачёт", "telegram")
    assert rec.notes == {"bob": "опоздал"}


@pytest.mark.parametrize("patch, needle", [
    ({"date": date(2026, 9, 21)}, "не совпадает"),
    ({"attendance": {"zed": "present"}}, "zed"),
    ({"attendance": {"alice": "here"}}, "статус"),
    ({"homework": {"h": {"alice": {"status": "done"}}}}, "статус"),
    ({"points": [{"who": "alice"}]}, "who/amount"),
    ({"points": [{"who": "alice", "amount": 1, "by": "mail"}]}, "источник"),
    ({"notes": {"zed": "x"}}, "zed"),
])
def test_parse_lesson_errors(patch, needle):
    with pytest.raises(JournalError, match=needle):
        parse_lesson({**LESSON, **patch}, DAY, {"alice", "bob"}, path="l.yml")


def test_homework_mark_by_round_trip():
    data = {**LESSON, "homework": {"python-01": {
        "alice": {"status": "accepted", "at": date(2026, 9, 22), "by": "telegram"},
        "bob": {"status": "issued"},
    }}}
    rec = parse_lesson(data, DAY, {"alice", "bob"})
    assert rec.homework["python-01"]["alice"].by == "telegram"
    assert rec.homework["python-01"]["bob"].by == "teacher"
    out = lesson_to_dict(rec)
    assert out["homework"]["python-01"]["alice"]["by"] == "telegram"
    assert "by" not in out["homework"]["python-01"]["bob"]
    assert parse_lesson(out, DAY, {"alice", "bob"}) == rec


def test_parse_lesson_rejects_unknown_homework_by():
    data = {**LESSON, "homework": {"python-01": {"alice": {"status": "issued", "by": "mail"}}}}
    with pytest.raises(JournalError, match="источник"):
        parse_lesson(data, DAY, {"alice", "bob"}, path="l.yml")


def test_lesson_round_trip_and_key_order():
    rec = parse_lesson(LESSON, DAY, {"alice", "bob"})
    data = lesson_to_dict(rec)
    assert list(data) == ["date", "attendance", "homework", "points", "notes"]
    assert data["homework"]["python-01"]["alice"] == {"status": "accepted", "at": date(2026, 9, 22)}
    assert data["points"][0]["amount"] == 2 and isinstance(data["points"][0]["amount"], int)
    assert parse_lesson(data, DAY, {"alice", "bob"}) == rec


def test_empty_lesson_serialises_with_all_sections():
    assert lesson_to_dict(LessonRecord(date=DAY)) == {
        "date": DAY, "attendance": {}, "homework": {}, "points": [], "notes": {}}


def test_num():
    assert num(2.0) == 2 and isinstance(num(2.0), int) and num(0.5) == 0.5


@pytest.mark.parametrize("patch, needle", [
    ({"attendance": ["alice"]}, "attendance должна быть mapping"),
    ({"homework": ["h"]}, "homework должна быть mapping"),
    ({"homework": {"h": ["alice"]}}, "homework h должна быть mapping"),
    ({"points": {"who": "alice"}}, "points должна быть list"),
    ({"points": [{"who": "alice", "amount": True}]}, "числом"),
    ({"points": [{"who": "alice", "amount": "много"}]}, "числом"),
    ({"notes": ["x"]}, "notes должна быть mapping"),
    ({"homework": {"h": {"alice": "accepted"}}}, "отметка должна быть mapping"),
])
def test_parse_lesson_bad_section_shapes(patch, needle):
    with pytest.raises(JournalError, match=needle):
        parse_lesson({**LESSON, **patch}, DAY, {"alice", "bob"}, path="l.yml")


@pytest.mark.parametrize("bad, needle", [
    ({"students": [{"id": "a", "name": "x", "zoom_names": "Алиса"}]}, "zoom_names"),
    ({"students": [{"id": "a", "name": "x", "contacts": "tg"}]}, "contacts"),
    ({"students": [{"id": "a", "name": "x", "parent": "tg"}]}, "parent"),
])
def test_parse_roster_bad_field_shapes(bad, needle):
    with pytest.raises(JournalError, match=needle):
        parse_roster(bad, path="r.yml")


@pytest.mark.parametrize("bad", [{"presence": "abc"}, {"late": True}, {"presence": None}])
def test_parse_tariff_rejects_non_numeric(bad):
    with pytest.raises(JournalError, match="числом"):
        parse_tariff(bad)


def test_parse_tariff_error_has_single_prefix():
    with pytest.raises(JournalError, match=r"^points\.yml: presence"):
        parse_tariff({"presence": "abc"})
